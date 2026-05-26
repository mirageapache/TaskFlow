/**
 * Calendar Store 單元測試
 *
 * 涵蓋：
 * - 初始狀態
 * - fetchByRange：GET /calendar/?workspace=&start=&end=&expand=true（後端展開重複事件）
 *   - 注意：expand=true 回傳「純陣列」而非分頁包裝（見 backend/apps/calendar_events/views.py::_list_expanded）
 * - CRUD：create / update / remove
 * - $reset
 *
 * 規格：.doc/taskflow-frontend.md §10 / backend /api/v1/calendar/
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

import client from '@/api/client'
import { useCalendarStore } from '@/stores/calendar'
import type { CalendarEvent } from '@/types'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

function makeEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: 'e1',
    workspace: 'w1',
    creator: 'u1',
    title: '專案開工',
    description: '',
    start_at: '2026-05-21T09:00:00Z',
    end_at: '2026-05-21T10:00:00Z',
    is_all_day: false,
    recurrence_rule: '',
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
    ...overrides,
  }
}

describe('useCalendarStore', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
    vi.mocked(client.patch).mockReset()
    vi.mocked(client.delete).mockReset()
  })

  describe('初始狀態', () => {
    it('events 為空、loading=false、error=null', () => {
      const store = useCalendarStore()
      expect(store.events).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('fetchByRange()', () => {
    it('GET /calendar/?workspace=&start=&end=&expand=true，寫入展開後的事件陣列', async () => {
      const list = [
        makeEvent({ id: 'e1', start_at: '2026-05-21T09:00:00Z' }),
        makeEvent({ id: 'e2', start_at: '2026-05-22T14:00:00Z' }),
      ]
      // expand=true 回傳純陣列（非分頁）
      vi.mocked(client.get).mockResolvedValueOnce({ data: list })

      const store = useCalendarStore()
      await store.fetchByRange({
        workspaceId: 'w1',
        start: '2026-05-01T00:00:00Z',
        end: '2026-05-31T23:59:59Z',
      })

      expect(client.get).toHaveBeenCalledWith('/calendar/', {
        params: {
          workspace: 'w1',
          start: '2026-05-01T00:00:00Z',
          end: '2026-05-31T23:59:59Z',
          expand: 'true',
        },
      })
      expect(store.events).toEqual(list)
    })

    it('每次 fetch 都覆寫 events（FullCalendar 切換月份時要重新讀整個範圍）', async () => {
      const first = [makeEvent({ id: 'e1' })]
      const second = [makeEvent({ id: 'e2' })]
      vi.mocked(client.get)
        .mockResolvedValueOnce({ data: first })
        .mockResolvedValueOnce({ data: second })

      const store = useCalendarStore()
      await store.fetchByRange({
        workspaceId: 'w1',
        start: '2026-05-01T00:00:00Z',
        end: '2026-05-31T23:59:59Z',
      })
      expect(store.events).toEqual(first)

      await store.fetchByRange({
        workspaceId: 'w1',
        start: '2026-06-01T00:00:00Z',
        end: '2026-06-30T23:59:59Z',
      })
      expect(store.events).toEqual(second)
    })

    it('失敗時 error 有值、events 維持原狀', async () => {
      const seed = [makeEvent({ id: 'e1' })]
      vi.mocked(client.get).mockResolvedValueOnce({ data: seed })
      const store = useCalendarStore()
      await store.fetchByRange({
        workspaceId: 'w1',
        start: '2026-05-01T00:00:00Z',
        end: '2026-05-31T23:59:59Z',
      })

      vi.mocked(client.get).mockRejectedValueOnce(new Error('500'))
      await expect(
        store.fetchByRange({
          workspaceId: 'w1',
          start: '2026-06-01T00:00:00Z',
          end: '2026-06-30T23:59:59Z',
        }),
      ).rejects.toThrow()
      expect(store.error).not.toBeNull()
      expect(store.events).toEqual(seed)
    })
  })

  describe('create()', () => {
    it('POST /calendar/ 並把回傳事件加進 events', async () => {
      const created = makeEvent({ id: 'e9', title: '新事件' })
      vi.mocked(client.post).mockResolvedValueOnce({ data: created })

      const store = useCalendarStore()
      const result = await store.create({
        workspace_id: 'w1',
        title: '新事件',
        start_at: '2026-05-21T09:00:00Z',
        end_at: '2026-05-21T10:00:00Z',
      })

      expect(client.post).toHaveBeenCalledWith('/calendar/', {
        workspace_id: 'w1',
        title: '新事件',
        start_at: '2026-05-21T09:00:00Z',
        end_at: '2026-05-21T10:00:00Z',
      })
      expect(result).toEqual(created)
      expect(store.events).toContainEqual(created)
    })
  })

  describe('update()', () => {
    it('PATCH /calendar/{id}/ 並在 events 中以新版取代', async () => {
      const original = makeEvent({ id: 'e1', title: '原本' })
      vi.mocked(client.get).mockResolvedValueOnce({ data: [original] })
      const store = useCalendarStore()
      await store.fetchByRange({
        workspaceId: 'w1',
        start: '2026-05-01T00:00:00Z',
        end: '2026-05-31T23:59:59Z',
      })

      const updated = { ...original, title: '改過' }
      vi.mocked(client.patch).mockResolvedValueOnce({ data: updated })
      const result = await store.update('e1', { title: '改過' })

      expect(client.patch).toHaveBeenCalledWith('/calendar/e1/', { title: '改過' })
      expect(result.title).toBe('改過')
      expect(store.events[0].title).toBe('改過')
    })
  })

  describe('remove()', () => {
    it('DELETE /calendar/{id}/ 並從 events 中拔除（同 id 的所有 occurrences）', async () => {
      const e1a = makeEvent({ id: 'e1', start_at: '2026-05-21T09:00:00Z' })
      const e1b = makeEvent({ id: 'e1', start_at: '2026-05-28T09:00:00Z' })
      const e2 = makeEvent({ id: 'e2' })
      vi.mocked(client.get).mockResolvedValueOnce({ data: [e1a, e1b, e2] })
      const store = useCalendarStore()
      await store.fetchByRange({
        workspaceId: 'w1',
        start: '2026-05-01T00:00:00Z',
        end: '2026-05-31T23:59:59Z',
      })

      vi.mocked(client.delete).mockResolvedValueOnce({})
      await store.remove('e1')

      expect(client.delete).toHaveBeenCalledWith('/calendar/e1/')
      expect(store.events).toEqual([e2])
    })
  })

  describe('$reset()', () => {
    it('清空 events / error', async () => {
      vi.mocked(client.get).mockResolvedValueOnce({ data: [makeEvent()] })
      const store = useCalendarStore()
      await store.fetchByRange({
        workspaceId: 'w1',
        start: '2026-05-01T00:00:00Z',
        end: '2026-05-31T23:59:59Z',
      })
      expect(store.events).toHaveLength(1)
      store.$reset()
      expect(store.events).toEqual([])
      expect(store.error).toBeNull()
    })
  })
})
