/**
 * DashboardView 測試（smoke）
 * 規格：.doc/taskflow_layout_design.md §9.2
 *
 * Phase 1 基礎頁：歡迎訊息 + 統計卡 + 工作區捷徑
 * 完整今日任務 / 通知 feed / 月曆留待 Phase 2/3
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import DashboardView from '@/views/DashboardView.vue'

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

const workspaces = [
  {
    id: 'w1',
    name: '個人',
    description: '私人空間',
    avatar_url: null,
    owner: 'u1',
    created_at: '',
    updated_at: '',
  },
  {
    id: 'w2',
    name: '團隊 Alpha',
    description: '產品團隊',
    avatar_url: null,
    owner: 'u1',
    created_at: '',
    updated_at: '',
  },
]

const projects = [
  {
    id: 'p1',
    workspace: 'w1',
    name: '官網改版',
    description: '',
    color: '#F97316',
    created_at: '',
    updated_at: '',
  },
  {
    id: 'p2',
    workspace: 'w1',
    name: '行銷活動',
    description: '',
    color: '#3B82F6',
    created_at: '',
    updated_at: '',
  },
]

function mockWorkspacesAndProjects() {
  vi.mocked(client.get).mockImplementation((url: string) => {
    if (url === '/workspaces/') return Promise.resolve({ data: paginated(workspaces) })
    if (url === '/projects/') return Promise.resolve({ data: paginated(projects) })
    return Promise.reject(new Error(`Unexpected URL: ${url}`))
  })
}

function buildRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/dashboard', name: 'dashboard', component: DashboardView },
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

async function mountView(router: Router) {
  await router.push('/dashboard')
  await router.isReady()
  const wrapper = mount(DashboardView, {
    global: { plugins: [router] },
  })
  // 兩次 flush：先讓 workspaceStore.fetchAll() resolve，再讓接著鏈式呼叫的
  // projectStore.fetchByWorkspace() 與後續 DOM patch 完成
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('DashboardView', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
  })

  it('歡迎訊息含使用者名稱', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    const router = buildRouter()
    await router.push('/dashboard')
    await router.isReady()

    const auth = useAuthStore()
    auth.user = { id: 'u1', email: 'alice@e.com', username: 'Alice' }

    const wrapper = mount(DashboardView, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Alice')
  })

  it('渲染 4 張統計卡片', async () => {
    mockWorkspacesAndProjects()
    const wrapper = await mountView(buildRouter())

    const cards = wrapper.findAll('[data-test="stat-card"]')
    expect(cards).toHaveLength(4)
  })

  it('「專案」統計卡顯示當前工作區的專案數', async () => {
    mockWorkspacesAndProjects()
    const wrapper = await mountView(buildRouter())

    const projCard = wrapper.find('[data-card="projects"]')
    expect(projCard.exists()).toBe(true)
    expect(projCard.text()).toContain('2')
  })

  it('已載入專案：列表顯示專案捷徑（連到看板）', async () => {
    mockWorkspacesAndProjects()
    const wrapper = await mountView(buildRouter())

    const links = wrapper.findAll('[data-test="project-link"]')
    expect(links).toHaveLength(2)
    expect(links[0].text()).toContain('官網改版')
    expect(links[0].attributes('href')).toBe('/project/p1/board')
  })

  it('沒有工作區：顯示提示，連結到 /workspaces 建立', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    const wrapper = await mountView(buildRouter())

    expect(wrapper.text()).toContain('尚未選擇工作區')
    expect(wrapper.find('a[href="/workspaces"]').exists()).toBe(true)
  })
})
