/**
 * BoardView 看板測試（smoke）
 * 規格：.doc/taskflow_layout_design.md §9.3
 *
 * 涵蓋：
 * - 掛載時並行抓取 project 詳情、status 欄位、task
 * - 每個 status 渲染為一個欄；對應狀態的 task 出現在欄內
 * - 任務數量徽章
 * - 點 TaskCard 觸發抽屜（emit 'select' 或本地 state 切換）
 * - 拖曳使用 vuedraggable（jsdom 不支援實際拖曳，這裡只 stub 用以驗證骨架）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

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

// vuedraggable 在 jsdom 沒有實際拖曳能力；用簡單 stub 把 item 槽渲染出來
vi.mock('vuedraggable', () => ({
  default: {
    name: 'draggable',
    props: ['list', 'modelValue', 'group', 'itemKey'],
    emits: ['change', 'update:modelValue'],
    template: `
      <div data-test="draggable-zone">
        <slot
          v-for="el in (list || modelValue) || []"
          name="item"
          :element="el"
          :index="0"
        />
      </div>
    `,
  },
}))

import BoardView from '@/views/BoardView.vue'

const project = {
  id: 'p1',
  workspace: 'w1',
  name: '官網改版',
  description: '',
  color: '#F97316',
  created_at: '',
  updated_at: '',
}

const statuses = [
  {
    id: 's-todo',
    name: '待辦',
    color: '#A8A29E',
    order: 0,
    is_completed: false,
    created_at: '',
    updated_at: '',
  },
  {
    id: 's-doing',
    name: '進行中',
    color: '#2563EB',
    order: 1,
    is_completed: false,
    created_at: '',
    updated_at: '',
  },
  {
    id: 's-done',
    name: '完成',
    color: '#059669',
    order: 2,
    is_completed: true,
    created_at: '',
    updated_at: '',
  },
]

const tasks = [
  { id: 't1', project: 'p1', status: 's-todo', title: '寫文案', priority: 'high', order: 0 },
  { id: 't2', project: 'p1', status: 's-todo', title: '收集需求', priority: 'medium', order: 1 },
  { id: 't3', project: 'p1', status: 's-doing', title: '畫線稿', priority: 'urgent', order: 0 },
].map((t) => ({
  parent_task: null,
  creator: 'u1',
  description: '',
  start_date: null,
  due_date: null,
  estimated_hours: null,
  assignees: [],
  tags: [],
  created_at: '',
  updated_at: '',
  ...t,
}))

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

function buildRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/project/:id/board', name: 'board', component: BoardView },
      {
        path: '/workspaces',
        name: 'workspaces',
        component: { template: '<div>ws</div>' },
      },
      {
        path: '/workspaces/:id/projects',
        name: 'workspace-projects',
        component: { template: '<div>projects</div>' },
      },
    ],
  })
}

function setupMockResponses() {
  // Mock order matches BoardView's fetch sequence
  vi.mocked(client.get).mockImplementation((url: string) => {
    if (url === '/projects/p1/') return Promise.resolve({ data: project })
    if (url === '/projects/p1/statuses/') return Promise.resolve({ data: paginated(statuses) })
    if (url === '/tasks/') return Promise.resolve({ data: paginated(tasks) })
    return Promise.reject(new Error(`Unexpected URL: ${url}`))
  })
}

async function mountBoard(router: Router) {
  await router.push('/project/p1/board')
  await router.isReady()
  const wrapper = mount(BoardView, {
    global: { plugins: [router] },
  })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('BoardView', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
    vi.mocked(client.patch).mockReset()
    toastAdd.mockReset()
  })

  it('掛載時抓 project 詳情 / statuses / tasks', async () => {
    setupMockResponses()
    await mountBoard(buildRouter())

    expect(client.get).toHaveBeenCalledWith('/projects/p1/')
    expect(client.get).toHaveBeenCalledWith('/projects/p1/statuses/')
    expect(client.get).toHaveBeenCalledWith('/tasks/', { params: { project: 'p1' } })
  })

  it('顯示 project 名稱於頁面標題', async () => {
    setupMockResponses()
    const wrapper = await mountBoard(buildRouter())
    expect(wrapper.text()).toContain('官網改版')
  })

  it('每個 status 渲染為一欄、任務在對應欄', async () => {
    setupMockResponses()
    const wrapper = await mountBoard(buildRouter())

    const columns = wrapper.findAll('[data-test="kanban-column"]')
    expect(columns).toHaveLength(3)

    expect(columns[0].text()).toContain('待辦')
    expect(columns[0].text()).toContain('寫文案')
    expect(columns[0].text()).toContain('收集需求')

    expect(columns[1].text()).toContain('進行中')
    expect(columns[1].text()).toContain('畫線稿')

    expect(columns[2].text()).toContain('完成')
  })

  it('每欄 header 顯示任務數量徽章', async () => {
    setupMockResponses()
    const wrapper = await mountBoard(buildRouter())

    const columns = wrapper.findAll('[data-test="kanban-column"]')
    expect(columns[0].find('[data-test="task-count"]').text()).toBe('2')
    expect(columns[1].find('[data-test="task-count"]').text()).toBe('1')
    expect(columns[2].find('[data-test="task-count"]').text()).toBe('0')
  })

  it('點 TaskCard 開啟 TaskDrawer（顯示該 task 的標題）', async () => {
    setupMockResponses()
    const wrapper = await mountBoard(buildRouter())

    // 預設沒有抽屜
    expect(wrapper.find('[data-test="task-drawer"]').exists()).toBe(false)

    // 點第一張卡（'寫文案'）
    const cards = wrapper.findAll('[data-test="task-card-wrapper"]')
    expect(cards.length).toBeGreaterThan(0)
    await cards[0].trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="task-drawer"]').exists()).toBe(true)
    const titleInput = wrapper.find('[data-test="title-input"]')
    expect(titleInput.exists()).toBe(true)
    expect((titleInput.element as HTMLInputElement).value).toBe('寫文案')
  })
})
