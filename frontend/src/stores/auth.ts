/**
 * Auth Store — 管理使用者登入狀態與 Access Token。
 *
 * Token 儲存策略（與後端 §4 對應）：
 * - Access Token：短時效（1h），存 localStorage，附在 Authorization header
 * - Refresh Token：後端以 httpOnly Cookie 寫入，前端不直接接觸（withCredentials 自動帶上）
 *
 * 規格：.doc/taskflow-frontend.md §4.4
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import client from '@/api/client'

interface User {
  id: string
  email: string
  username: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const isAuthenticated = computed(() => !!accessToken.value)

  /** 寫入 token 到 state + localStorage（由 login / refresh 呼叫） */
  function setAccessToken(token: string) {
    accessToken.value = token
    localStorage.setItem('access_token', token)
  }

  /** 清除狀態（logout 與 refresh 失敗時呼叫） */
  function clearSession() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('access_token')
  }

  /** 帳密登入：成功後僅儲 access；refresh 由後端設 httpOnly cookie */
  async function login(email: string, password: string) {
    const { data } = await client.post('/auth/login/', { email, password })
    setAccessToken(data.access)
    await fetchUser()
  }

  /** 註冊後自動執行登入流程 */
  async function register(email: string, username: string, password: string) {
    await client.post('/auth/register/', { email, username, password })
    await login(email, password)
  }

  /** 取得當前使用者資料；token 失效時 axios interceptor 會自動處理 401 */
  async function fetchUser() {
    const { data } = await client.get('/users/me/')
    user.value = data
  }

  /** 登出：通知後端黑名單該 refresh token，再清前端狀態（無論後端是否成功） */
  async function logout() {
    try {
      await client.post('/auth/logout/')
    } finally {
      clearSession()
    }
  }

  /**
   * 應用啟動時呼叫一次：若 localStorage 有 token，嘗試以它取得 /me/。
   * 若 token 已過期，axios interceptor 會嘗試 refresh；
   * refresh 也失敗則 interceptor 呼叫 logout()，此處 catch 後靜默結束。
   */
  async function initAuth() {
    if (!accessToken.value) return
    try {
      await fetchUser()
    } catch {
      // 失敗時 interceptor 已清除狀態，不需在此處理
    }
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    setAccessToken,
    clearSession,
    login,
    register,
    fetchUser,
    logout,
    initAuth,
  }
})
