/**
 * useDragAndDrop — 看板任務拖曳的樂觀更新流程。
 *
 * 規格：.doc/taskflow-frontend.md §4.8
 *
 * 流程：
 *   1. 讀取原始 status 作為回滾用快照
 *   2. 立即更新本地 store（樂觀）
 *   3. PATCH /tasks/:id/ { status_id }
 *   4. 失敗則回滾本地 + toast 提示
 *
 * 邊界：
 *   - drop 到同一 status：no-op（避免無謂 API）
 *   - 找不到 task：no-op（避免在 stale state 上產生副作用）
 */
import { useToast } from 'primevue/usetoast'

import client from '@/api/client'
import { useTaskStore } from '@/stores/task'

export function useDragAndDrop() {
  const taskStore = useTaskStore()
  const toast = useToast()

  async function onTaskDropped(taskId: string, newStatusId: string) {
    const task = taskStore.getById(taskId)
    if (!task) return
    const previousStatusId = task.status
    if (previousStatusId === newStatusId) return

    // 樂觀更新（先動 UI 再打 API）
    taskStore.updateTaskStatus(taskId, newStatusId)

    try {
      await client.patch(`/tasks/${taskId}/`, { status_id: newStatusId })
    } catch {
      // 回滾
      taskStore.updateTaskStatus(taskId, previousStatusId)
      toast.add({
        severity: 'error',
        summary: '更新失敗',
        detail: '任務狀態更新失敗，已復原',
        life: 3000,
      })
    }
  }

  return { onTaskDropped }
}
