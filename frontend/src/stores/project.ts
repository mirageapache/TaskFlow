/**
 * Project Store — 專案列表（依 workspace 分桶快取）。
 *
 * 設計：
 * - 不同 workspace 各自獨立快取（key = workspaceId）
 * - `fetchByWorkspace(id)` 預設懶載入，已載入則跳過；force 可強制重抓
 * - `create({ workspace_id, ... })` 自動把新 project 加到對應 workspace 桶
 * - `getByWorkspace(id)` 永遠回 array（無資料時回 []）
 *
 * 規格：.doc/taskflow-frontend.md §4.4
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import client from '@/api/client'
import type { Paginated, Project } from '@/types'

interface CreateInput {
  workspace_id: string
  name: string
  description?: string
  color?: string
}

export const useProjectStore = defineStore('project', () => {
  const byWorkspace = ref<Record<string, Project[]>>({})
  const loadedWorkspaces = ref<Set<string>>(new Set())
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByWorkspace(workspaceId: string, opts: { force?: boolean } = {}) {
    if (loadedWorkspaces.value.has(workspaceId) && !opts.force) return
    loading.value = true
    error.value = null
    try {
      const { data } = await client.get<Paginated<Project>>('/projects/', {
        params: { workspace: workspaceId },
      })
      byWorkspace.value[workspaceId] = data.results
      loadedWorkspaces.value.add(workspaceId)
    } catch (err) {
      error.value = extractError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function create(input: CreateInput): Promise<Project> {
    const { data } = await client.post<Project>('/projects/', input)
    const wsId = input.workspace_id
    const existing = byWorkspace.value[wsId] ?? []
    byWorkspace.value[wsId] = [...existing, data]
    return data
  }

  function getByWorkspace(workspaceId: string): Project[] {
    return byWorkspace.value[workspaceId] ?? []
  }

  function $reset() {
    byWorkspace.value = {}
    loadedWorkspaces.value = new Set()
    loading.value = false
    error.value = null
  }

  return {
    byWorkspace,
    loadedWorkspaces,
    loading,
    error,
    fetchByWorkspace,
    create,
    getByWorkspace,
    $reset,
  }
})

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response
    if (r?.data?.detail) return r.data.detail
  }
  return '取得專案失敗，請稍後再試'
}
