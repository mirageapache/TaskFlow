/**
 * Project Store — 專案 + 看板狀態的取得與快取。
 *
 * 設計：
 * - 專案以 workspaceId 分桶快取（不同 workspace 各自獨立）
 * - 看板狀態（ProjectStatus）以 projectId 分桶快取
 * - 列表 API 採懶載入；`force` 可強制重抓
 * - 單筆 fetch（fetchById）做為直接 deep-link 進 BoardView 時的 fallback
 *
 * 規格：.doc/taskflow-frontend.md §4.4
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import client from '@/api/client'
import type { Paginated, Project, ProjectStatus } from '@/types'

interface CreateInput {
  workspace_id: string
  name: string
  description?: string
  color?: string
}

export const useProjectStore = defineStore('project', () => {
  const byWorkspace = ref<Record<string, Project[]>>({})
  const loadedWorkspaces = ref<Set<string>>(new Set())
  const detailById = ref<Record<string, Project>>({})
  const statusesByProject = ref<Record<string, ProjectStatus[]>>({})
  const loadedStatuses = ref<Set<string>>(new Set())
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

  async function fetchById(projectId: string, opts: { force?: boolean } = {}): Promise<Project> {
    if (!opts.force) {
      const cached = getById(projectId)
      if (cached) return cached
    }
    const { data } = await client.get<Project>(`/projects/${projectId}/`)
    detailById.value[data.id] = data
    return data
  }

  async function fetchStatuses(projectId: string, opts: { force?: boolean } = {}) {
    if (loadedStatuses.value.has(projectId) && !opts.force) return
    const { data } = await client.get<Paginated<ProjectStatus>>(
      `/projects/${projectId}/statuses/`,
    )
    statusesByProject.value[projectId] = data.results.sort((a, b) => a.order - b.order)
    loadedStatuses.value.add(projectId)
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

  function getById(projectId: string): Project | null {
    if (detailById.value[projectId]) return detailById.value[projectId]
    for (const list of Object.values(byWorkspace.value)) {
      const found = list.find((p) => p.id === projectId)
      if (found) return found
    }
    return null
  }

  function getStatuses(projectId: string): ProjectStatus[] {
    return statusesByProject.value[projectId] ?? []
  }

  function $reset() {
    byWorkspace.value = {}
    loadedWorkspaces.value = new Set()
    detailById.value = {}
    statusesByProject.value = {}
    loadedStatuses.value = new Set()
    loading.value = false
    error.value = null
  }

  return {
    byWorkspace,
    loadedWorkspaces,
    detailById,
    statusesByProject,
    loadedStatuses,
    loading,
    error,
    fetchByWorkspace,
    fetchById,
    fetchStatuses,
    create,
    getByWorkspace,
    getById,
    getStatuses,
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
