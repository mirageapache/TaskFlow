/**
 * TaskDetailPanel 元件測試
 * 規格：.doc/taskflow_layout_design.md §9.5
 *
 * 涵蓋：
 * - 顯示傳入 task 的 title / description / priority
 * - 切換 Tab：描述 / 留言 / 附件 / 子任務
 * - 留言 Tab：載入留言、提交新留言
 * - 子任務 Tab：渲染 store 中 parent_task 為當前 task 的子任務
 * - 點關閉 emit close 事件
 * - 儲存：PATCH /tasks/:id/ 後 emit close
 *
 * 注意：TaskDrawer 是僅含動畫邏輯的殼層元件，內容測試以 TaskDetailPanel 為主。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import client from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

import { useTaskStore } from '@/stores/task'
import TaskDetailPanel from '@/components/task/TaskDetailPanel.vue'
import type { Task } from '@/types'

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    project: 'p1',
    parent_task: null,
    status: 's-todo',
    creator: 'u1',
    title: '主任務',
    description: '一段描述',
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

describe('TaskDetailPanel', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
    vi.mocked(client.patch).mockReset()
    vi.mocked(client.delete).mockReset()
  })

  it('顯示 task 的 title / description / priority（位於表單欄位中）', () => {
    const task = makeTask({ title: 'A', description: 'B', priority: 'high' })
    const wrapper = mount(TaskDetailPanel, { props: { task } })

    expect(
      (wrapper.find('[data-test="title-input"]').element as HTMLInputElement).value,
    ).toBe('A')
    expect(
      (wrapper.findAll('textarea')[0].element as HTMLTextAreaElement).value,
    ).toBe('B')
    expect(
      (wrapper.find('[data-test="priority-select"]').element as HTMLSelectElement).value,
    ).toBe('high')
  })

  it('預設顯示「描述」Tab', () => {
    const wrapper = mount(TaskDetailPanel, { props: { task: makeTask() } })
    expect(wrapper.find('[data-test="tab-description"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="tab-comments"]').exists()).toBe(false)
  })

  it('切到「留言」Tab：抓取留言、顯示列表', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({
      data: paginated([
        {
          id: 'c1',
          author: { id: 'u1', email: 'a@b.com', username: 'Alice' },
          content: '第一則留言',
          created_at: '2026-04-29T00:00:00Z',
          updated_at: '2026-04-29T00:00:00Z',
        },
      ]),
    })

    const wrapper = mount(TaskDetailPanel, { props: { task: makeTask({ id: 't1' }) } })
    await wrapper.find('[data-test="tab-btn-comments"]').trigger('click')
    await flushPromises()

    expect(client.get).toHaveBeenCalledWith('/tasks/t1/comments/')
    expect(wrapper.text()).toContain('第一則留言')
    expect(wrapper.text()).toContain('Alice')
  })

  it('提交留言：POST /tasks/:id/comments/、加入列表、清空輸入', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    vi.mocked(client.post).mockResolvedValueOnce({
      data: {
        id: 'c2',
        author: { id: 'u1', email: 'a@b.com', username: 'Me' },
        content: '我來回',
        created_at: '2026-04-29T00:00:00Z',
        updated_at: '2026-04-29T00:00:00Z',
      },
    })

    const wrapper = mount(TaskDetailPanel, { props: { task: makeTask({ id: 't1' }) } })
    await wrapper.find('[data-test="tab-btn-comments"]').trigger('click')
    await flushPromises()

    await wrapper.find('[data-test="comment-input"]').setValue('我來回')
    await wrapper.find('[data-test="comment-form"]').trigger('submit')
    await flushPromises()

    expect(client.post).toHaveBeenCalledWith('/tasks/t1/comments/', { content: '我來回' })
    expect(wrapper.text()).toContain('我來回')
    expect(
      (wrapper.find('[data-test="comment-input"]').element as HTMLTextAreaElement).value,
    ).toBe('')
  })

  it('「子任務」Tab：渲染 store 中 parent_task 為當前 task 的子任務', async () => {
    // 先把主任務 + 子任務塞入 task store
    const main = makeTask({ id: 'main', project: 'p1' })
    const subA = makeTask({ id: 'sub-a', project: 'p1', parent_task: 'main', title: '子 A' })
    const subB = makeTask({
      id: 'sub-b',
      project: 'p1',
      parent_task: 'main',
      title: '子 B',
      order: 1,
    })
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([main, subA, subB]) })

    const taskStore = useTaskStore()
    await taskStore.fetchByProject('p1')

    const wrapper = mount(TaskDetailPanel, { props: { task: main } })
    await wrapper.find('[data-test="tab-btn-subtasks"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('子 A')
    expect(wrapper.text()).toContain('子 B')
  })

  it('「附件」Tab：抓取附件列表並顯示檔名', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({
      data: paginated([
        {
          id: 'a1',
          file_name: 'spec.pdf',
          file_size: 12345,
          mime_type: 'application/pdf',
          uploaded_by: { id: 'u1', email: 'a@b.com', username: 'A' },
          created_at: '2026-04-29T00:00:00Z',
        },
      ]),
    })

    const wrapper = mount(TaskDetailPanel, { props: { task: makeTask({ id: 't1' }) } })
    await wrapper.find('[data-test="tab-btn-attachments"]').trigger('click')
    await flushPromises()

    expect(client.get).toHaveBeenCalledWith('/tasks/t1/attachments/')
    expect(wrapper.text()).toContain('spec.pdf')
  })

  it('儲存：PATCH /tasks/:id/，store 同步更新', async () => {
    // 先放任務到 store，update 才有目標可以 replace
    const task = makeTask({ id: 't1', title: '原' })
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([task]) })
    const taskStore = useTaskStore()
    await taskStore.fetchByProject('p1')

    const updated = { ...task, title: '改' }
    vi.mocked(client.patch).mockResolvedValueOnce({ data: updated })

    const wrapper = mount(TaskDetailPanel, { props: { task } })
    await wrapper.find('[data-test="title-input"]').setValue('改')
    await wrapper.find('[data-test="save-btn"]').trigger('click')
    await flushPromises()

    expect(client.patch).toHaveBeenCalledWith(
      '/tasks/t1/',
      expect.objectContaining({ title: '改' }),
    )
    expect(taskStore.getById('t1')?.title).toBe('改')
  })

  it('點關閉按鈕 emit close 事件', async () => {
    const wrapper = mount(TaskDetailPanel, { props: { task: makeTask() } })
    await wrapper.find('[data-test="close-btn"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
