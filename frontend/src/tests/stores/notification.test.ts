/**
 * Notification Store 單元測試
 *
 * 涵蓋：
 * - list / unreadCount 初始狀態
 * - fetchAll：GET /notifications/（含 ?is_read 過濾）
 * - markRead：PATCH /notifications/{id}/，更新本地 + 遞減 unreadCount
 * - markAllRead：POST /notifications/mark-all-read/，全部標已讀 + unreadCount = 0
 * - pushNotification（WS 收到 'notification' 時用）：prepend + 未讀則 ++unreadCount
 * - setUnreadCount（WS 收到 'unread_count' 時用）：直接覆寫
 * - $reset
 *
 * 規格：.doc/taskflow-frontend.md §4.7 / .doc/taskflow-backend.md（/api/v1/notifications/）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

import client from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import type { Notification } from '@/types'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

function makeNotif(overrides: Partial<Notification> = {}): Notification {
  return {
    id: 'n1',
    recipient: 'u1',
    notif_type: 'task_assigned',
    title: '你被指派了一個任務',
    body: '任務「設計資料庫」已指派給你',
    payload: { task_id: 't1' },
    is_read: false,
    read_at: null,
    created_at: '2026-05-21T08:00:00Z',
    ...overrides,
  }
}

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

describe('useNotificationStore', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
    vi.mocked(client.patch).mockReset()
  })

  describe('初始狀態', () => {
    it('list 為空、unreadCount = 0、loading = false', () => {
      const store = useNotificationStore()
      expect(store.list).toEqual([])
      expect(store.unreadCount).toBe(0)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('fetchAll()', () => {
    it('GET /notifications/ 並把結果寫入 list、unreadCount 取自未讀數', async () => {
      const data = [
        makeNotif({ id: 'n1', is_read: false }),
        makeNotif({ id: 'n2', is_read: true, read_at: '2026-05-20T00:00:00Z' }),
        makeNotif({ id: 'n3', is_read: false }),
      ]
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(data) })

      const store = useNotificationStore()
      await store.fetchAll()

      expect(client.get).toHaveBeenCalledWith('/notifications/', { params: {} })
      expect(store.list).toHaveLength(3)
      expect(store.unreadCount).toBe(2)
    })

    it('傳入 isRead 過濾：帶到 query string', async () => {
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })

      const store = useNotificationStore()
      await store.fetchAll({ isRead: false })

      expect(client.get).toHaveBeenCalledWith('/notifications/', {
        params: { is_read: false },
      })
    })

    it('失敗時 error 有值，list 維持原狀', async () => {
      vi.mocked(client.get).mockRejectedValueOnce(new Error('500'))
      const store = useNotificationStore()
      await expect(store.fetchAll()).rejects.toThrow()
      expect(store.error).not.toBeNull()
      expect(store.list).toEqual([])
    })
  })

  describe('markRead()', () => {
    it('PATCH /notifications/{id}/ is_read=true，本地該筆改成 read 並 --unreadCount', async () => {
      const n1 = makeNotif({ id: 'n1', is_read: false })
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([n1]) })

      const store = useNotificationStore()
      await store.fetchAll()
      expect(store.unreadCount).toBe(1)

      const updated = { ...n1, is_read: true, read_at: '2026-05-21T08:30:00Z' }
      vi.mocked(client.patch).mockResolvedValueOnce({ data: updated })

      await store.markRead('n1')

      expect(client.patch).toHaveBeenCalledWith('/notifications/n1/', { is_read: true })
      expect(store.list[0].is_read).toBe(true)
      expect(store.list[0].read_at).toBe('2026-05-21T08:30:00Z')
      expect(store.unreadCount).toBe(0)
    })

    it('對「已讀」的通知再 markRead：不重複扣 unreadCount', async () => {
      const n1 = makeNotif({ id: 'n1', is_read: true, read_at: '2026-05-20T00:00:00Z' })
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([n1]) })

      const store = useNotificationStore()
      await store.fetchAll()
      expect(store.unreadCount).toBe(0)

      vi.mocked(client.patch).mockResolvedValueOnce({ data: n1 })
      await store.markRead('n1')
      expect(store.unreadCount).toBe(0)
    })

    it('對 list 中不存在的 id markRead：不丟例外、不動 unreadCount', async () => {
      vi.mocked(client.patch).mockResolvedValueOnce({
        data: makeNotif({ id: 'nope', is_read: true }),
      })
      const store = useNotificationStore()
      await expect(store.markRead('nope')).resolves.not.toThrow()
      expect(store.unreadCount).toBe(0)
    })
  })

  describe('markAllRead()', () => {
    it('POST /notifications/mark-all-read/，list 全部 is_read=true、unreadCount=0', async () => {
      const list = [
        makeNotif({ id: 'n1', is_read: false }),
        makeNotif({ id: 'n2', is_read: false }),
        makeNotif({ id: 'n3', is_read: true, read_at: '2026-05-20T00:00:00Z' }),
      ]
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(list) })
      const store = useNotificationStore()
      await store.fetchAll()
      expect(store.unreadCount).toBe(2)

      vi.mocked(client.post).mockResolvedValueOnce({ data: { updated: 2 } })
      await store.markAllRead()

      expect(client.post).toHaveBeenCalledWith('/notifications/mark-all-read/')
      expect(store.list.every((n) => n.is_read)).toBe(true)
      expect(store.unreadCount).toBe(0)
    })
  })

  describe('pushNotification()（WS 收到 type=notification 時呼叫）', () => {
    it('新通知 prepend 到 list 開頭，且未讀時 unreadCount + 1', () => {
      const store = useNotificationStore()
      const a = makeNotif({ id: 'a', is_read: false })
      const b = makeNotif({ id: 'b', is_read: false, created_at: '2026-05-21T09:00:00Z' })

      store.pushNotification(a)
      store.pushNotification(b)

      expect(store.list.map((n) => n.id)).toEqual(['b', 'a'])
      expect(store.unreadCount).toBe(2)
    })

    it('已讀的推送：list 仍 prepend 但不 ++unreadCount', () => {
      const store = useNotificationStore()
      store.pushNotification(
        makeNotif({ id: 'a', is_read: true, read_at: '2026-05-21T00:00:00Z' }),
      )
      expect(store.list).toHaveLength(1)
      expect(store.unreadCount).toBe(0)
    })

    it('同 id 重複推送：去重（不重複加進 list、不再 ++unreadCount）', () => {
      const store = useNotificationStore()
      const a = makeNotif({ id: 'a', is_read: false })
      store.pushNotification(a)
      store.pushNotification(a)
      expect(store.list).toHaveLength(1)
      expect(store.unreadCount).toBe(1)
    })
  })

  describe('setUnreadCount()（WS 收到 type=unread_count 時呼叫）', () => {
    it('直接覆寫 unreadCount', () => {
      const store = useNotificationStore()
      store.setUnreadCount(5)
      expect(store.unreadCount).toBe(5)
      store.setUnreadCount(0)
      expect(store.unreadCount).toBe(0)
    })
  })

  describe('$reset()', () => {
    it('清空 list / unreadCount / error', async () => {
      vi.mocked(client.get).mockResolvedValueOnce({
        data: paginated([makeNotif({ is_read: false })]),
      })
      const store = useNotificationStore()
      await store.fetchAll()
      expect(store.list).toHaveLength(1)

      store.$reset()
      expect(store.list).toEqual([])
      expect(store.unreadCount).toBe(0)
      expect(store.error).toBeNull()
    })
  })
})
