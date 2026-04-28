/**
 * Axios Client — TaskFlow 前端統一 API 入口。
 *
 * 功能：
 * 1. Request interceptor：自動帶 `Authorization: Bearer <token>`
 * 2. Response interceptor：401 自動以 refresh token 換 access，並排隊重送並發請求
 *
 * Refresh Token 機制：
 * - Refresh Token 由後端寫入 httpOnly Cookie（前端不可讀）
 * - 透過 `withCredentials: true` 讓瀏覽器自動附帶 Cookie
 * - Access Token 存於 localStorage（透過 auth store）
 *
 * 規格：.doc/taskflow-frontend.md §4.3
 */
import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'

const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
  withCredentials: true, // 讓瀏覽器自動附帶 httpOnly refresh cookie
})

// ────────────── Request：自動附 Access Token ──────────────

client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // 動態 import 避免 store ↔ client 互相 import 形成循環
  // 規避：在 client.ts 模組頂層 import auth store，store 又 import client → 死循環
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ────────────── Response：401 自動 Refresh + 並發請求排隊 ──────────────

interface RetryableConfig extends AxiosRequestConfig {
  _retry?: boolean
  headers?: Record<string, string>
}

interface PendingRequest {
  resolve: (token: string) => void
  reject: (err: unknown) => void
}

let isRefreshing = false
let pendingQueue: PendingRequest[] = []

/** Refresh 完成後，喚醒所有等待中的並發請求 */
function flushQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token!)
  })
  pendingQueue = []
}

/**
 * Refresh 失敗時清除前端狀態並導向 /login。
 * 動態 import 避免模組循環依賴。
 */
async function handleRefreshFailure() {
  const { useAuthStore } = await import('@/stores/auth')
  const { default: router } = await import('@/router')
  useAuthStore().clearSession()
  router.push('/login')
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryableConfig

    // 非 401 / 已重試過 / 沒有 config → 直接拋出
    if (
      !originalRequest
      || error.response?.status !== 401
      || originalRequest._retry
    ) {
      return Promise.reject(error)
    }

    // refresh / login 端點本身回 401 不應再嘗試 refresh，避免無限迴圈
    if (originalRequest.url?.includes('/auth/refresh/') || originalRequest.url?.includes('/auth/login/')) {
      return Promise.reject(error)
    }

    // 已有其他請求正在 refresh：本請求進入排隊，等待新 token
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${token}`
        originalRequest._retry = true
        return client(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      // refresh token 由 httpOnly cookie 自動附帶
      const { data } = await client.post('/auth/refresh/')
      const newToken: string = data.access

      // 更新 store 與 localStorage
      const { useAuthStore } = await import('@/stores/auth')
      useAuthStore().setAccessToken(newToken)

      flushQueue(null, newToken)

      originalRequest.headers = originalRequest.headers || {}
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return client(originalRequest)
    } catch (refreshError) {
      flushQueue(refreshError, null)
      await handleRefreshFailure()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

export default client
