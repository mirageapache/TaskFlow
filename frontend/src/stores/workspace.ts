/**
 * Workspace Store — 工作區列表的取得與快取。
 *
 * - `fetchAll()` 預設懶載入：已 `loaded` 則直接返回；以 `{ force: true }` 強制重抓
 * - `create()` 成功後將新建 workspace 附加到 list
 * - `getById()` 從快取找單一筆（不會打 API）
 * - `currentWorkspaceId` 持久化到 localStorage，跨 session 記憶最後瀏覽的工作區
 *
 * 規格：.doc/taskflow-frontend.md §4.4
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import client from '@/api/client'
import type { Paginated, Workspace } from '@/types'

interface CreateInput {
  name: string
  description?: string
}

const STORAGE_KEY = 'taskflow:currentWorkspaceId'

export const useWorkspaceStore = defineStore('workspace', () => {
  const list = ref<Workspace[]>([])
  const loaded = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentWorkspaceId = ref<string | null>(localStorage.getItem(STORAGE_KEY))

  const currentWorkspace = computed(() =>
    list.value.find((w) => w.id === currentWorkspaceId.value) ?? null,
  )

  async function fetchAll(opts: { force?: boolean } = {}) {
    if (loaded.value && !opts.force) return
    loading.value = true
    error.value = null
    try {
      const { data } = await client.get<Paginated<Workspace>>('/workspaces/')
      list.value = data.results
      loaded.value = true
      // 若快取的 id 已不存在（被刪除），或尚未設定，則預設第一個工作區
      const valid = currentWorkspaceId.value && list.value.find((w) => w.id === currentWorkspaceId.value)
      if (!valid && list.value.length > 0) {
        setCurrentWorkspace(list.value[0].id)
      }
    } catch (err) {
      error.value = extractError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function setCurrentWorkspace(id: string) {
    currentWorkspaceId.value = id
    localStorage.setItem(STORAGE_KEY, id)
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
    currentWorkspaceId.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    list,
    loaded,
    loading,
    error,
    currentWorkspaceId,
    currentWorkspace,
    fetchAll,
    setCurrentWorkspace,
    create,
    getById,
    $reset,
  }
})

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response
    if (r?.data?.detail) return r.data.detail
  }
  return '取得工作區失敗，請稍後再試'
}
