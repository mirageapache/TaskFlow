/**
 * TaskCard 元件測試
 * 規格：.doc/taskflow_layout_design.md §9.3 Kanban 卡片
 *
 * 涵蓋：
 * - 渲染 title
 * - 優先級 dot 顏色（urgent/high/medium/low 各對應 §1.4 色票）
 * - 截止日：未設定時不顯示；逾期時加紅色 class
 * - 多 assignee 時最多顯示 3 個 avatar，超過顯示 +N
 * - 有 tags 時顯示數量徽章
 * - 點擊發出 'click' 事件帶 task
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import dayjs from 'dayjs'

import TaskCard from '@/components/task/TaskCard.vue'
import type { Task, TaskPriority, User } from '@/types'

function makeUser(id: string, username: string): User {
  return { id, username, email: `${username}@e.com`, avatar_url: null }
}

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    project: 'p1',
    parent_task: null,
    status: 's1',
    creator: 'u1',
    title: '預設任務標題',
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

describe('TaskCard', () => {
  it('渲染 title', () => {
    const wrapper = mount(TaskCard, { props: { task: makeTask({ title: '寫測試' }) } })
    expect(wrapper.text()).toContain('寫測試')
  })

  it.each([
    ['urgent', 'bg-red-700'],
    ['high', 'bg-rose-600'],
    ['medium', 'bg-blue-600'],
    ['low', 'bg-stone-500'],
  ] as [TaskPriority, string][])(
    '優先級 %s dot 帶 %s class',
    (priority, expectedClass) => {
      const wrapper = mount(TaskCard, { props: { task: makeTask({ priority }) } })
      const dot = wrapper.find('[data-test="priority-dot"]')
      expect(dot.exists()).toBe(true)
      expect(dot.classes()).toContain(expectedClass)
    },
  )

  it('未設定 due_date 時不顯示截止日區塊', () => {
    const wrapper = mount(TaskCard, { props: { task: makeTask({ due_date: null }) } })
    expect(wrapper.find('[data-test="due-date"]').exists()).toBe(false)
  })

  it('已設定 due_date 顯示日期（M/D 格式）', () => {
    const wrapper = mount(TaskCard, {
      props: { task: makeTask({ due_date: '2026-12-25T00:00:00Z' }) },
    })
    const due = wrapper.find('[data-test="due-date"]')
    expect(due.exists()).toBe(true)
    expect(due.text()).toContain('12/25')
  })

  it('逾期 due_date 套用紅色 class', () => {
    const yesterday = dayjs().subtract(1, 'day').toISOString()
    const wrapper = mount(TaskCard, { props: { task: makeTask({ due_date: yesterday }) } })
    const due = wrapper.find('[data-test="due-date"]')
    expect(due.classes().some((c) => c.includes('text-red'))).toBe(true)
  })

  it('未來 due_date 不套用紅色', () => {
    const tomorrow = dayjs().add(1, 'day').toISOString()
    const wrapper = mount(TaskCard, { props: { task: makeTask({ due_date: tomorrow }) } })
    const due = wrapper.find('[data-test="due-date"]')
    expect(due.classes().some((c) => c.includes('text-red'))).toBe(false)
  })

  it('assignees 1-3 個全部顯示首字 avatar', () => {
    const wrapper = mount(TaskCard, {
      props: {
        task: makeTask({
          assignees: [
            makeUser('u1', 'Alice'),
            makeUser('u2', 'Bob'),
          ],
        }),
      },
    })
    const avatars = wrapper.findAll('[data-test="assignee-avatar"]')
    expect(avatars).toHaveLength(2)
    expect(avatars[0].text()).toBe('A')
    expect(avatars[1].text()).toBe('B')
  })

  it('assignees > 3：顯示前 3 個 + "+N" 溢位', () => {
    const wrapper = mount(TaskCard, {
      props: {
        task: makeTask({
          assignees: [
            makeUser('u1', 'Alice'),
            makeUser('u2', 'Bob'),
            makeUser('u3', 'Carol'),
            makeUser('u4', 'Dave'),
            makeUser('u5', 'Eve'),
          ],
        }),
      },
    })
    expect(wrapper.findAll('[data-test="assignee-avatar"]')).toHaveLength(3)
    expect(wrapper.find('[data-test="assignee-overflow"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="assignee-overflow"]').text()).toBe('+2')
  })

  it('沒有 tags 時不顯示徽章；有 tags 時顯示數量', () => {
    const noTags = mount(TaskCard, { props: { task: makeTask({ tags: [] }) } })
    expect(noTags.find('[data-test="tag-badge"]').exists()).toBe(false)

    const withTags = mount(TaskCard, {
      props: { task: makeTask({ tags: ['tag1', 'tag2', 'tag3'] }) },
    })
    const badge = withTags.find('[data-test="tag-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('3')
  })

  it('點擊卡片發出 click 事件帶 task', async () => {
    const task = makeTask({ id: 'click-me' })
    const wrapper = mount(TaskCard, { props: { task } })

    await wrapper.trigger('click')

    expect(wrapper.emitted('click')).toBeTruthy()
    expect(wrapper.emitted('click')![0]).toEqual([task])
  })
})
