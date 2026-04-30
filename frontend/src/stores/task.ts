/**
 * Task Store — 任務 CRUD + 過濾邏輯。
 *
 * 設計：
 * - 以 projectId 分桶快取（看板永遠在單一 project 範圍內操作）
 * - `fetchByProject` 懶載入；`force` 強制重抓
 * - CRUD：create / update / remove 均同步維護快取
 * - `updateTaskStatus(id, newStatusId)` 為「純本地 mutation」，不發 API；給 useDragAndDrop 做樂觀更新
 * - 過濾：getById（跨桶查找）/ getByProjectAndStatus（依 order 升冪）/ filterByPriority
 *
 * 規格：.doc/taskflow-frontend.md §4.4 / §4.8
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import client from '@/api/client'
import type { Paginated, Task, TaskPriority } from '@/types'

interface CreateInput {
  project: string
  title: string
  status_id: string
  description?: string
  priority?: TaskPriority
  start_date?: string | null
  due_date?: string | null
  estimated_hours?: number | null
  parent_task?: string | null
  assignee_ids?: string[]
  tag_ids?: string[]
}

type UpdateInput = Partial<CreateInput> & {
  /** 寫入時用 status_id（後端 read 是 status: UUID） */
  status_id?: string
}

export const useTaskStore = defineStore('task', () => {
  const byProject = ref<Record<string, Task[]>>({})
  const loadedProjects = ref<Set<string>>(new Set())
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByProject(projectId: string, opts: { force?: boolean } = {}) {
    if (loadedProjects.value.has(projectId) && !opts.force) return
    loading.value = true
    error.value = null
    try {
      const { data } = await client.get<Paginated<Task>>('/tasks/', {
        params: { project: projectId },
      })
      byProject.value[projectId] = data.results
      loadedProjects.value.add(projectId)
    } catch (err) {
      error.value = extractError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function create(input: CreateInput): Promise<Task> {
    const { data } = await client.post<Task>('/tasks/', input)
    const bucket = byProject.value[data.project] ?? []
    byProject.value[data.project] = [...bucket, data]
    return data
  }

  async function update(id: string, patch: UpdateInput): Promise<Task> {
    const { data } = await client.patch<Task>(`/tasks/${id}/`, patch)
    replaceInCache(data)
    return data
  }

  async function remove(id: string): Promise<void> {
    await client.delete(`/tasks/${id}/`)
    for (const projectId of Object.keys(byProject.value)) {
      byProject.value[projectId] = byProject.value[projectId].filter((t) => t.id !== id)
    }
  }

  /**
   * 純本地 mutation：更新任務的 status 欄位，不發 API。
   * 用於 useDragAndDrop 的樂觀更新流程；API 由呼叫端自行送出。
   */
  function updateTaskStatus(id: string, newStatusId: string) {
    for (const projectId of Object.keys(byProject.value)) {
      const list = byProject.value[projectId]
      const idx = list.findIndex((t) => t.id === id)
      if (idx >= 0) {
        const updated = { ...list[idx], status: newStatusId }
        byProject.value[projectId] = [...list.slice(0, idx), updated, ...list.slice(idx + 1)]
        return
      }
    }
  }

  function replaceInCache(task: Task) {
    const bucket = byProject.value[task.project]
    if (!bucket) return
    const idx = bucket.findIndex((t) => t.id === task.id)
    if (idx >= 0) {
      byProject.value[task.project] = [...bucket.slice(0, idx), task, ...bucket.slice(idx + 1)]
    }
  }

  function getById(id: string): Task | null {
    for (const list of Object.values(byProject.value)) {
      const found = list.find((t) => t.id === id)
      if (found) return found
    }
    return null
  }

  function getByProject(projectId: string): Task[] {
    return byProject.value[projectId] ?? []
  }

  function getByProjectAndStatus(projectId: string, statusId: string): Task[] {
    return getByProject(projectId)
      .filter((t) => t.status === statusId)
      .sort((a, b) => a.order - b.order)
  }

  function filterByPriority(projectId: string, priority: TaskPriority): Task[] {
    return getByProject(projectId).filter((t) => t.priority === priority)
  }

  function getSubtasks(parentTaskId: string): Task[] {
    const result: Task[] = []
    for (const list of Object.values(byProject.value)) {
      for (const t of list) {
        if (t.parent_task === parentTaskId) result.push(t)
      }
    }
    return result.sort((a, b) => a.order - b.order)
  }

  function $reset() {
    byProject.value = {}
    loadedProjects.value = new Set()
    loading.value = false
    error.value = null
  }

  return {
    byProject,
    loadedProjects,
    loading,
    error,
    fetchByProject,
    create,
    update,
    remove,
    updateTaskStatus,
    getById,
    getByProject,
    getByProjectAndStatus,
    filterByPriority,
    getSubtasks,
    $reset,
  }
})

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response
    if (r?.data?.detail) return r.data.detail
  }
  return '取得任務失敗，請稍後再試'
}
