/**
 * Task Store 單元測試
 *
 * 涵蓋：
 * - byProject 分桶快取（不同 project 各自獨立）
 * - fetchByProject / 已 loaded 跳過 / force 強制重抓
 * - CRUD：create / update / remove
 * - updateTaskStatus 是樂觀更新用的「純本地 mutation」（不打 API）→ 給 useDragAndDrop 用
 * - 過濾邏輯：getById / getByProjectAndStatus（依 order 排序） / filterByPriority
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

import client from '@/api/client'
import { useTaskStore } from '@/stores/task'
import type { Task } from '@/types'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    project: 'proj1',
    parent_task: null,
    status: 'st-todo',
    creator: 'u1',
    title: '範例任務',
    description: '',
    priority: 'medium',
    start_date: null,
    due_date: null,
    estimated_hours: null,
    order: 0,
    assignees: [],
    tags: [],
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
    ...overrides,
  }
}

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

describe('useTaskStore', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
    vi.mocked(client.patch).mockReset()
    vi.mocked(client.delete).mockReset()
  })

  describe('fetchByProject + cache', () => {
    it('初始狀態：byProject 為空、loading=false', () => {
      const store = useTaskStore()
      expect(store.byProject).toEqual({})
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('fetchByProject(id) 帶 ?project 並寫入快取', async () => {
      const tasks = [makeTask({ id: 't1' }), makeTask({ id: 't2', order: 1 })]
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(tasks) })

      const store = useTaskStore()
      await store.fetchByProject('proj1')

      expect(client.get).toHaveBeenCalledWith('/tasks/', { params: { project: 'proj1' } })
      expect(store.byProject.proj1).toEqual(tasks)
    })

    it('已 loaded 時不再打 API；force 重抓', async () => {
      vi.mocked(client.get)
        .mockResolvedValueOnce({ data: paginated([makeTask({ id: 't1' })]) })
        .mockResolvedValueOnce({
          data: paginated([makeTask({ id: 't1' }), makeTask({ id: 't2' })]),
        })

      const store = useTaskStore()
      await store.fetchByProject('proj1')
      await store.fetchByProject('proj1')
      expect(client.get).toHaveBeenCalledTimes(1)

      await store.fetchByProject('proj1', { force: true })
      expect(client.get).toHaveBeenCalledTimes(2)
      expect(store.byProject.proj1).toHaveLength(2)
    })

    it('不同 project 各自獨立快取', async () => {
      vi.mocked(client.get)
        .mockResolvedValueOnce({ data: paginated([makeTask({ id: 'a', project: 'p1' })]) })
        .mockResolvedValueOnce({ data: paginated([makeTask({ id: 'b', project: 'p2' })]) })

      const store = useTaskStore()
      await store.fetchByProject('p1')
      await store.fetchByProject('p2')

      expect(store.byProject.p1).toHaveLength(1)
      expect(store.byProject.p2).toHaveLength(1)
      expect(store.byProject.p1[0].id).toBe('a')
      expect(store.byProject.p2[0].id).toBe('b')
    })

    it('fetchByProject 失敗：error 有值、未寫入快取', async () => {
      vi.mocked(client.get).mockRejectedValueOnce(new Error('500'))
      const store = useTaskStore()
      await expect(store.fetchByProject('p1')).rejects.toThrow()
      expect(store.error).not.toBeNull()
      expect(store.byProject.p1).toBeUndefined()
    })
  })

  describe('create / update / remove', () => {
    it('create() POST 後加到對應 project 桶', async () => {
      const created = makeTask({ id: 't9', title: '新任務' })
      vi.mocked(client.post).mockResolvedValueOnce({ data: created })

      const store = useTaskStore()
      const result = await store.create({
        project: 'proj1',
        title: '新任務',
        status_id: 'st-todo',
      })

      expect(client.post).toHaveBeenCalledWith('/tasks/', {
        project: 'proj1',
        title: '新任務',
        status_id: 'st-todo',
      })
      expect(result).toEqual(created)
      expect(store.byProject.proj1).toEqual([created])
    })

    it('update() PATCH 後在快取中更新該筆', async () => {
      const original = makeTask({ id: 't1', title: '原本' })
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([original]) })

      const store = useTaskStore()
      await store.fetchByProject('proj1')

      const updated = { ...original, title: '改過' }
      vi.mocked(client.patch).mockResolvedValueOnce({ data: updated })

      const result = await store.update('t1', { title: '改過' })

      expect(client.patch).toHaveBeenCalledWith('/tasks/t1/', { title: '改過' })
      expect(result.title).toBe('改過')
      expect(store.byProject.proj1[0].title).toBe('改過')
    })

    it('remove() DELETE 後從快取拔除', async () => {
      const t1 = makeTask({ id: 't1' })
      const t2 = makeTask({ id: 't2' })
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([t1, t2]) })
      vi.mocked(client.delete).mockResolvedValueOnce({})

      const store = useTaskStore()
      await store.fetchByProject('proj1')
      await store.remove('t1')

      expect(client.delete).toHaveBeenCalledWith('/tasks/t1/')
      expect(store.byProject.proj1).toEqual([t2])
    })
  })

  describe('updateTaskStatus（樂觀更新用：純本地）', () => {
    it('就地改 task.status，不發 API', async () => {
      const t1 = makeTask({ id: 't1', status: 'st-todo' })
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([t1]) })

      const store = useTaskStore()
      await store.fetchByProject('proj1')
      vi.mocked(client.patch).mockClear()

      store.updateTaskStatus('t1', 'st-doing')

      expect(client.patch).not.toHaveBeenCalled()
      expect(store.byProject.proj1[0].status).toBe('st-doing')
    })

    it('找不到對應 task 時靜默忽略（不丟錯）', () => {
      const store = useTaskStore()
      expect(() => store.updateTaskStatus('non-exist', 'st-doing')).not.toThrow()
    })
  })

  describe('過濾邏輯', () => {
    const tasks = [
      makeTask({ id: 'a', project: 'p1', status: 's1', priority: 'high', order: 2 }),
      makeTask({ id: 'b', project: 'p1', status: 's1', priority: 'low', order: 0 }),
      makeTask({ id: 'c', project: 'p1', status: 's2', priority: 'high', order: 0 }),
      makeTask({ id: 'd', project: 'p1', status: 's1', priority: 'urgent', order: 1 }),
    ]

    async function setup() {
      vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(tasks) })
      const store = useTaskStore()
      await store.fetchByProject('p1')
      return store
    }

    it('getById 跨 project 桶查找', async () => {
      const store = await setup()
      expect(store.getById('c')?.id).toBe('c')
      expect(store.getById('not-exist')).toBeNull()
    })

    it('getByProject 回 array（無資料時空陣列）', async () => {
      const store = await setup()
      expect(store.getByProject('p1')).toHaveLength(4)
      expect(store.getByProject('p999')).toEqual([])
    })

    it('getByProjectAndStatus 過濾並依 order 升冪排序', async () => {
      const store = await setup()
      const s1 = store.getByProjectAndStatus('p1', 's1')
      expect(s1.map((t) => t.id)).toEqual(['b', 'd', 'a']) // order 0,1,2
    })

    it('filterByPriority 過濾出指定優先級', async () => {
      const store = await setup()
      expect(store.filterByPriority('p1', 'high').map((t) => t.id)).toEqual(['a', 'c'])
      expect(store.filterByPriority('p1', 'urgent').map((t) => t.id)).toEqual(['d'])
    })

    it('getSubtasks 找到指定 parent_task 的子任務（依 order 升冪）', async () => {
      const parent = makeTask({ id: 'parent', project: 'p1' })
      const sub1 = makeTask({ id: 'sub1', project: 'p1', parent_task: 'parent', order: 1 })
      const sub2 = makeTask({ id: 'sub2', project: 'p1', parent_task: 'parent', order: 0 })
      const other = makeTask({ id: 'other', project: 'p1', parent_task: 'something-else' })
      vi.mocked(client.get).mockResolvedValueOnce({
        data: paginated([parent, sub1, sub2, other]),
      })

      const store = useTaskStore()
      await store.fetchByProject('p1')

      expect(store.getSubtasks('parent').map((t) => t.id)).toEqual(['sub2', 'sub1'])
      expect(store.getSubtasks('no-children')).toEqual([])
    })
  })
})
