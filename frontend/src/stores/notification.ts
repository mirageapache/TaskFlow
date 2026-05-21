/**
 * Notification Store — 通知列表與未讀計數。
 *
 * 設計：
 * - HTTP API：fetchAll / markRead / markAllRead 對應 /api/v1/notifications/
 * - WebSocket 推送入口：
 *   - pushNotification(notif)：收到 type='notification' 時呼叫，prepend 並更新未讀
 *   - setUnreadCount(n)：收到 type='unread_count' 時呼叫，直接覆寫
 * - 來源去重：pushNotification 對相同 id 不重複加入（後端 group_send 與 connect 推送可能重疊）
 * - unreadCount 為衍生狀態但獨立儲存：WS 的 unread_count 事件是後端權威來源，
 *   不必每次重算；本地 mutation（markRead）也直接調整避免 list 與計數脫節。
 *
 * 規格：.doc/taskflow-frontend.md §4.7 / .doc/taskflow-backend.md（/api/v1/notifications/）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import client from '@/api/client'
import type { Notification, Paginated } from '@/types'

export const useNotificationStore = defineStore('notification', () => {
  const list = ref<Notification[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll(opts: { isRead?: boolean } = {}) {
    loading.value = true
    error.value = null
    try {
      const params: Record<string, boolean> = {}
      if (opts.isRead !== undefined) params.is_read = opts.isRead
      const { data } = await client.get<Paginated<Notification>>('/notifications/', {
        params,
      })
      list.value = data.results
      unreadCount.value = data.results.filter((n) => !n.is_read).length
    } catch (err) {
      error.value = extractError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function markRead(id: string) {
    const { data } = await client.patch<Notification>(`/notifications/${id}/`, {
      is_read: true,
    })
    const idx = list.value.findIndex((n) => n.id === id)
    if (idx >= 0) {
      const wasUnread = !list.value[idx].is_read
      list.value = [...list.value.slice(0, idx), data, ...list.value.slice(idx + 1)]
      if (wasUnread && unreadCount.value > 0) unreadCount.value -= 1
    }
  }

  async function markAllRead() {
    await client.post('/notifications/mark-all-read/')
    const now = new Date().toISOString()
    list.value = list.value.map((n) =>
      n.is_read ? n : { ...n, is_read: true, read_at: now },
    )
    unreadCount.value = 0
  }

  /** WS 收到 type='notification' 時呼叫；同 id 去重。 */
  function pushNotification(notif: Notification) {
    if (list.value.some((n) => n.id === notif.id)) return
    list.value = [notif, ...list.value]
    if (!notif.is_read) unreadCount.value += 1
  }

  /** WS 收到 type='unread_count' 時呼叫；後端權威來源。 */
  function setUnreadCount(count: number) {
    unreadCount.value = count
  }

  function $reset() {
    list.value = []
    unreadCount.value = 0
    loading.value = false
    error.value = null
  }

  return {
    list,
    unreadCount,
    loading,
    error,
    fetchAll,
    markRead,
    markAllRead,
    pushNotification,
    setUnreadCount,
    $reset,
  }
})

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response
    if (r?.data?.detail) return r.data.detail
  }
  return '取得通知失敗，請稍後再試'
}
