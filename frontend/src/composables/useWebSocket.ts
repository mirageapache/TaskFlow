/**
 * useWebSocket — 即時通知 WebSocket 連線與訊息分派。
 *
 * 規格：.doc/taskflow-frontend.md §4.7
 *
 * 設計：
 * - 後端走 Django Channels，路徑為 /ws/notifications/，
 *   無法走 Authorization header → access token 改放 querystring，
 *   由後端 JWTAuthMiddleware 從 scope.query_string 取出驗證。
 * - 訊息由後端統一帶 `type` 欄位（'notification' / 'unread_count' …），
 *   composable 內以 Map 對應 handler，呼叫端用 on(type, handler) 訂閱。
 * - onUnmounted 自動關閉連線；測試 / 非 component 環境呼叫時跳過 lifecycle 註冊，
 *   避免 Vue 噴 "onUnmounted is called when there is no active component instance"。
 */
import { getCurrentInstance, onUnmounted, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

export type WsMessage = { type: string; [key: string]: unknown }
type Handler = (data: WsMessage) => void

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const handlers = new Map<string, Handler>()

  function connect() {
    // 已有連線就不重開（避免使用者誤呼叫造成雙連線）
    if (ws.value) return

    const authStore = useAuthStore()
    const token = authStore.accessToken
    if (!token) return

    const base = import.meta.env.VITE_WS_BASE_URL
    const url = `${base}/notifications/?token=${token}`
    const socket = new WebSocket(url)
    ws.value = socket

    socket.onopen = () => {
      isConnected.value = true
    }
    socket.onclose = () => {
      isConnected.value = false
    }
    socket.onerror = () => {
      isConnected.value = false
    }
    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as WsMessage
        handlers.get(data.type)?.(data)
      } catch {
        console.error('WebSocket 訊息解析失敗', event.data)
      }
    }
  }

  function on(type: string, handler: Handler) {
    handlers.set(type, handler)
  }

  function disconnect() {
    if (!ws.value) return
    ws.value.close()
    ws.value = null
    isConnected.value = false
  }

  if (getCurrentInstance()) {
    onUnmounted(disconnect)
  }

  return { isConnected, connect, disconnect, on }
}
