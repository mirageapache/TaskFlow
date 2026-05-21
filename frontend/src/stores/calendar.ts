/**
 * Calendar Store — 行程事件列表與 CRUD。
 *
 * 設計：
 * - fetchByRange 使用後端 `expand=true`：把 RRULE 重複事件展開為多個 occurrences；
 *   回傳是「純陣列」而非 PageNumberPagination 包裝（見 backend views.py::_list_expanded）。
 * - 每次 fetchByRange 完整覆寫 events：FullCalendar 切換月／週／日視圖時會帶新的範圍，
 *   分頁式快取會把同一事件的不同 occurrences 切到不同頁，治理成本高，乾脆每次重抓。
 * - remove(id) 從快取拔除「同 id 的所有 occurrences」（同 RRULE 事件在 events 中可能出現多筆）。
 *
 * 規格：.doc/taskflow-frontend.md §10 / .doc/taskflow-backend.md（/api/v1/calendar/）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import client from '@/api/client'
import type { CalendarEvent } from '@/types'

interface FetchRangeInput {
  workspaceId: string
  /** ISO 8601 */
  start: string
  /** ISO 8601 */
  end: string
}

interface CreateInput {
  workspace_id: string
  title: string
  start_at: string
  end_at: string
  description?: string
  is_all_day?: boolean
  recurrence_rule?: string
}

type UpdateInput = Partial<Omit<CreateInput, 'workspace_id'>>

export const useCalendarStore = defineStore('calendar', () => {
  const events = ref<CalendarEvent[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByRange(input: FetchRangeInput) {
    loading.value = true
    error.value = null
    try {
      const { data } = await client.get<CalendarEvent[]>('/calendar/', {
        params: {
          workspace: input.workspaceId,
          start: input.start,
          end: input.end,
          expand: 'true',
        },
      })
      events.value = data
    } catch (err) {
      error.value = extractError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function create(input: CreateInput): Promise<CalendarEvent> {
    const { data } = await client.post<CalendarEvent>('/calendar/', input)
    events.value = [...events.value, data]
    return data
  }

  async function update(id: string, patch: UpdateInput): Promise<CalendarEvent> {
    const { data } = await client.patch<CalendarEvent>(`/calendar/${id}/`, patch)
    events.value = events.value.map((e) => (e.id === id ? data : e))
    return data
  }

  async function remove(id: string): Promise<void> {
    await client.delete(`/calendar/${id}/`)
    events.value = events.value.filter((e) => e.id !== id)
  }

  function $reset() {
    events.value = []
    loading.value = false
    error.value = null
  }

  return {
    events,
    loading,
    error,
    fetchByRange,
    create,
    update,
    remove,
    $reset,
  }
})

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response
    if (r?.data?.detail) return r.data.detail
  }
  return '取得行程失敗，請稍後再試'
}
