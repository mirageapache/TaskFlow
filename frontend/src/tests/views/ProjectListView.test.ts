/**
 * ProjectListView 元件測試
 * 規格：.doc/taskflow_layout_design.md §8.3 / §8.6
 *
 * 涵蓋：
 * - 從路由 :id 取 workspaceId 並 fetch
 * - 顯示 workspace 名稱（已載入過 workspace store 時）
 * - 空狀態 / 列表 / 失敗訊息
 * - 建立 project：表單送出後加入清單，導向 board 連結存在
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import { useWorkspaceStore } from '@/stores/workspace'
import ProjectListView from '@/views/ProjectListView.vue'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockProjects = [
  {
    id: 'p1',
    workspace: 'w1',
    name: '官網改版',
    description: '',
    color: '#F97316',
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'p2',
    workspace: 'w1',
    name: '客服自動化',
    description: 'Bot + 工單整合',
    color: '#2563EB',
    created_at: '2026-04-02T00:00:00Z',
    updated_at: '2026-04-02T00:00:00Z',
  },
]

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

function buildRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/workspaces', name: 'workspaces', component: { template: '<div>list</div>' } },
      {
        path: '/workspaces/:id/projects',
        name: 'projects',
        component: ProjectListView,
      },
      {
        path: '/project/:id/board',
        name: 'board',
        component: { template: '<div>board</div>' },
      },
    ],
  })
}

async function mountView(router: Router, path = '/workspaces/w1/projects') {
  await router.push(path)
  await router.isReady()
  const wrapper = mount(ProjectListView, {
    global: { plugins: [router] },
  })
  await flushPromises()
  return wrapper
}

describe('ProjectListView', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
  })

  it('掛載時依路由 :id 過濾抓 projects', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    await mountView(buildRouter())
    expect(client.get).toHaveBeenCalledWith('/projects/', {
      params: { workspace: 'w1' },
    })
  })

  it('顯示 workspace 名稱（從已快取的 workspace store）', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    const router = buildRouter()
    await router.push('/workspaces/w1/projects')
    await router.isReady()

    // 預先填快取
    const wsStore = useWorkspaceStore()
    wsStore.list = [
      {
        id: 'w1',
        name: '團隊 Alpha',
        description: '',
        avatar_url: null,
        owner: 'u1',
        created_at: '',
        updated_at: '',
      },
    ]
    wsStore.loaded = true

    const wrapper = mount(ProjectListView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('團隊 Alpha')
  })

  it('空狀態：顯示「還沒有專案」', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    const wrapper = await mountView(buildRouter())
    expect(wrapper.text()).toContain('還沒有專案')
  })

  it('已載入：顯示所有 project 名稱與通往看板的連結', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockProjects) })
    const wrapper = await mountView(buildRouter())

    expect(wrapper.text()).toContain('官網改版')
    expect(wrapper.text()).toContain('客服自動化')
    expect(wrapper.find('a[href="/project/p1/board"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/project/p2/board"]').exists()).toBe(true)
  })

  it('載入失敗：顯示後端錯誤訊息', async () => {
    const err = new Error('forbidden') as Error & { response?: unknown }
    err.response = { status: 403, data: { detail: '不是此工作區成員' } }
    vi.mocked(client.get).mockRejectedValueOnce(err)

    const wrapper = await mountView(buildRouter())
    expect(wrapper.text()).toContain('不是此工作區成員')
  })

  it('建立 project：送出後加入清單', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockProjects) })
    const newProject = {
      id: 'p9',
      workspace: 'w1',
      name: '新專案',
      description: '',
      color: '#F97316',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }
    vi.mocked(client.post).mockResolvedValueOnce({ data: newProject })

    const wrapper = await mountView(buildRouter())

    await wrapper.find('[data-test="toggle-create"]').trigger('click')
    await wrapper.find('input[name="name"]').setValue('新專案')
    await wrapper.find('[data-test="create-form"]').trigger('submit')
    await flushPromises()

    expect(client.post).toHaveBeenCalledWith('/projects/', {
      workspace_id: 'w1',
      name: '新專案',
      description: '',
    })
    expect(wrapper.text()).toContain('新專案')
  })
})
