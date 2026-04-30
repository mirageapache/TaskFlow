/**
 * useDragAndDrop composable 測試
 * 規格：.doc/taskflow-frontend.md §4.8（樂觀更新 + 失敗回滾）
 *
 * 流程驗證：
 * 1. 樂觀更新本地 store（在 API 之前）
 * 2. PATCH /tasks/:id/ 帶 status_id
 * 3. 成功：本地保持新狀態
 * 4. 失敗：回滾到原始 status，且觸發 toast
 * 5. 同 status drop：跳過（不發 API）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

import client from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const toastAdd = vi.fn()
vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAdd }),
}))

import { useTaskStore } from '@/stores/task'
import { useDragAndDrop } from '@/composables/useDragAndDrop'
import type { Task } from '@/types'

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    project: 'p1',
    parent_task: null,
    status: 'st-todo',
    creator: 'u1',
    title: '範例',
    description: '',
    priority: 'medium',
    start_date: null,
    due_date: null,
    estimated_hours: null,
    order: 0,
    assignees: [],
    tags: [],
    created_at: '',
    updated_at: '',
    ...overrides,
  }
}

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

async function seedStore(initialTasks: Task[]) {
  const projectId = initialTasks[0]?.project ?? 'p1'
  vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(initialTasks) })
  const store = useTaskStore()
  await store.fetchByProject(projectId)
  return store
}

describe('useDragAndDrop', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.patch).mockReset()
    toastAdd.mockReset()
  })

  it('成功：樂觀更新 → API → 保持新狀態', async () => {
    const store = await seedStore([makeTask({ id: 't1', status: 'st-todo' })])
    vi.mocked(client.patch).mockResolvedValueOnce({ data: { id: 't1' } })

    const { onTaskDropped } = useDragAndDrop()
    await onTaskDropped('t1', 'st-doing')

    expect(client.patch).toHaveBeenCalledWith('/tasks/t1/', { status_id: 'st-doing' })
    expect(store.getById('t1')?.status).toBe('st-doing')
    expect(toastAdd).not.toHaveBeenCalled()
  })

  it('樂觀：本地 store 在 API resolve 之前已更新', async () => {
    const store = await seedStore([makeTask({ id: 't1', status: 'st-todo' })])

    let resolvePatch: (v: unknown) => void = () => {}
    vi.mocked(client.patch).mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePatch = resolve
      }) as unknown as ReturnType<typeof client.patch>,
    )

    const { onTaskDropped } = useDragAndDrop()
    const promise = onTaskDropped('t1', 'st-doing')

    // 此時 patch 還沒 resolve，但 store 應該已經更新
    expect(store.getById('t1')?.status).toBe('st-doing')

    resolvePatch({ data: {} })
    await promise
  })

  it('失敗：回滾為原始 status 並 toast 提示', async () => {
    const store = await seedStore([makeTask({ id: 't1', status: 'st-todo' })])
    vi.mocked(client.patch).mockRejectedValueOnce(new Error('500'))

    const { onTaskDropped } = useDragAndDrop()
    await onTaskDropped('t1', 'st-doing')

    expect(store.getById('t1')?.status).toBe('st-todo')
    expect(toastAdd).toHaveBeenCalledTimes(1)
    expect(toastAdd.mock.calls[0][0]).toMatchObject({
      severity: 'error',
      summary: expect.stringContaining('更新失敗'),
    })
  })

  it('drop 到同一 status：跳過、不發 API、不 toast', async () => {
    await seedStore([makeTask({ id: 't1', status: 'st-todo' })])
    const { onTaskDropped } = useDragAndDrop()

    await onTaskDropped('t1', 'st-todo')

    expect(client.patch).not.toHaveBeenCalled()
    expect(toastAdd).not.toHaveBeenCalled()
  })

  it('找不到 task：跳過、不發 API（避免 stale state 副作用）', async () => {
    await seedStore([makeTask({ id: 't1' })])
    const { onTaskDropped } = useDragAndDrop()

    await onTaskDropped('not-exists', 'st-doing')

    expect(client.patch).not.toHaveBeenCalled()
  })
})
