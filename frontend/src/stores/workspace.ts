/**
 * Workspace Store — 工作區列表的取得與快取。
 *
 * - `fetchAll()` 預設懶載入：已 `loaded` 則直接返回；以 `{ force: true }` 強制重抓
 * - `create()` 成功後將新建 workspace 附加到 list
 * - `getById()` 從快取找單一筆（不會打 API）
 *
 * 規格：.doc/taskflow-frontend.md §4.4
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import client from '@/api/client'
import type { Paginated, Workspace } from '@/types'

interface CreateInput {
  name: string
  description?: string
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const list = ref<Workspace[]>([])
  const loaded = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll(opts: { force?: boolean } = {}) {
    if (loaded.value && !opts.force) return
    loading.value = true
    error.value = null
    try {
      const { data } = await client.get<Paginated<Workspace>>('/workspaces/')
      list.value = data.results
      loaded.value = true
    } catch (err) {
      error.value = extractError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function create(input: CreateInput): Promise<Workspace> {
    const { data } = await client.post<Workspace>('/workspaces/', input)
    list.value = [...list.value, data]
    return data
  }

  function getById(id: string): Workspace | null {
    return list.value.find((w) => w.id === id) ?? null
  }

  function $reset() {
    list.value = []
    loaded.value = false
    loading.value = false
    error.value = null
  }

  return { list, loaded, loading, error, fetchAll, create, getById, $reset }
})

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response
    if (r?.data?.detail) return r.data.detail
  }
  return '取得工作區失敗，請稍後再試'
}
