/**
 * WorkspaceListView 元件測試
 * 規格：.doc/taskflow_layout_design.md §8.3 Card / §8.6 Empty State
 *
 * 涵蓋：
 * - 掛載時自動 fetch
 * - 空狀態顯示提示文字
 * - 已載入：顯示所有 workspace 名稱與「進入」連結
 * - 失敗：顯示錯誤訊息
 * - 建立流程：展開表單、送出後加入清單
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import WorkspaceListView from '@/views/WorkspaceListView.vue'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockItems = [
  {
    id: 'w1',
    name: '個人',
    description: '私人空間',
    avatar_url: null,
    owner: 'u1',
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'w2',
    name: '團隊 Alpha',
    description: '產品團隊',
    avatar_url: null,
    owner: 'u1',
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
      { path: '/workspaces', name: 'workspaces', component: WorkspaceListView },
      {
        path: '/workspaces/:id/projects',
        name: 'projects',
        component: { template: '<div>projects</div>' },
      },
    ],
  })
}

async function mountView(router: Router) {
  await router.push('/workspaces')
  await router.isReady()
  const wrapper = mount(WorkspaceListView, {
    global: { plugins: [router] },
  })
  await flushPromises()
  return wrapper
}

describe('WorkspaceListView', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
  })

  it('掛載時自動取列表', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    await mountView(buildRouter())
    expect(client.get).toHaveBeenCalledWith('/workspaces/')
  })

  it('空狀態：顯示「還沒有工作區」', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated([]) })
    const wrapper = await mountView(buildRouter())
    expect(wrapper.text()).toContain('還沒有工作區')
  })

  it('已載入：顯示所有 workspace 名稱與進入連結', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockItems) })
    const wrapper = await mountView(buildRouter())

    expect(wrapper.text()).toContain('個人')
    expect(wrapper.text()).toContain('團隊 Alpha')
    expect(wrapper.find('a[href="/workspaces/w1/projects"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/workspaces/w2/projects"]').exists()).toBe(true)
  })

  it('載入失敗：顯示後端錯誤訊息', async () => {
    const err = new Error('forbidden') as Error & { response?: unknown }
    err.response = { status: 403, data: { detail: '無權限存取' } }
    vi.mocked(client.get).mockRejectedValueOnce(err)

    const wrapper = await mountView(buildRouter())
    expect(wrapper.text()).toContain('無權限存取')
  })

  it('點「建立工作區」展開表單，送出後新項目加入清單', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockItems) })
    const newWs = {
      id: 'w3',
      name: '新空間',
      description: '描述',
      avatar_url: null,
      owner: 'u1',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }
    vi.mocked(client.post).mockResolvedValueOnce({ data: newWs })

    const wrapper = await mountView(buildRouter())

    // 展開
    await wrapper.find('[data-test="toggle-create"]').trigger('click')
    await wrapper.find('input[name="name"]').setValue('新空間')
    await wrapper.find('textarea[name="description"]').setValue('描述')
    await wrapper.find('[data-test="create-form"]').trigger('submit')
    await flushPromises()

    expect(client.post).toHaveBeenCalledWith('/workspaces/', {
      name: '新空間',
      description: '描述',
    })
    expect(wrapper.text()).toContain('新空間')
  })
})
