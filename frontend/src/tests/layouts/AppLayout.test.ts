/**
 * AppLayout 測試
 * 規格：.doc/taskflow_layout_design.md §5.3
 *
 * 驗證：
 * - 渲染 slot 內容
 * - TopBar 顯示 Logo（連結回 /dashboard）
 * - Sidebar 包含主要導航項目（儀表板 / AI 助理 / 設定）
 * - 已登入：使用者選單顯示首字 / 名稱 / Email
 * - 點登出：呼叫 authStore.logout 後導 /login
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/layouts/AppLayout.vue'

vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

function buildRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: { template: '<div>login</div>' } },
      { path: '/dashboard', name: 'dashboard', component: { template: '<div>dashboard</div>' } },
      { path: '/workspaces', name: 'workspaces', component: { template: '<div>ws</div>' } },
      { path: '/ai', name: 'ai', component: { template: '<div>ai</div>' } },
      { path: '/settings', name: 'settings', component: { template: '<div>settings</div>' } },
    ],
  })
}

async function mountLayout(router: Router) {
  await router.push('/dashboard')
  await router.isReady()
  return mount(AppLayout, {
    global: { plugins: [router] },
    slots: { default: '<div data-test="content">頁面內容</div>' },
  })
}

describe('AppLayout', () => {
  beforeEach(() => {
    vi.mocked(client.post).mockReset()
    vi.mocked(client.get).mockReset()
  })

  it('渲染 slot 內容', async () => {
    const wrapper = await mountLayout(buildRouter())
    expect(wrapper.find('[data-test="content"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('頁面內容')
  })

  it('TopBar 顯示 TaskFlow logo（連結到 /dashboard）', async () => {
    const wrapper = await mountLayout(buildRouter())
    const logo = wrapper.find('a[href="/dashboard"]')
    expect(logo.exists()).toBe(true)
    expect(logo.text()).toContain('TaskFlow')
  })

  it('Sidebar 顯示主要導航項目', async () => {
    const wrapper = await mountLayout(buildRouter())
    expect(wrapper.html()).toContain('儀表板')
    expect(wrapper.html()).toContain('工作區')
    expect(wrapper.html()).toContain('AI 助理')
    expect(wrapper.html()).toContain('設定')
  })

  it('已登入：Avatar 顯示使用者名稱首字、選單展開時顯示完整資訊', async () => {
    const wrapper = await mountLayout(buildRouter())
    const auth = useAuthStore()
    auth.user = { id: '1', email: 'alice@example.com', username: 'Alice' }
    await flushPromises()

    const toggle = wrapper.find('[data-test="user-menu-toggle"]')
    expect(toggle.text()).toBe('A')

    await toggle.trigger('click')
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('alice@example.com')
  })

  it('點登出：呼叫 authStore.logout 並導 /login', async () => {
    vi.mocked(client.post).mockResolvedValueOnce({})

    const router = buildRouter()
    const wrapper = await mountLayout(router)
    const pushSpy = vi.spyOn(router, 'push')

    const auth = useAuthStore()
    auth.user = { id: '1', email: 'alice@example.com', username: 'Alice' }
    auth.setAccessToken('tok')
    await flushPromises()

    await wrapper.find('[data-test="user-menu-toggle"]').trigger('click')
    await wrapper.find('[data-test="logout-btn"]').trigger('click')
    await flushPromises()

    expect(client.post).toHaveBeenCalledWith('/auth/logout/')
    expect(auth.accessToken).toBeNull()
    expect(auth.user).toBeNull()
    expect(pushSpy).toHaveBeenCalledWith('/login')
  })

  it('登出 API 失敗仍清除前端 session 並導 /login', async () => {
    vi.mocked(client.post).mockRejectedValueOnce(new Error('network'))

    const router = buildRouter()
    const wrapper = await mountLayout(router)
    const pushSpy = vi.spyOn(router, 'push')

    const auth = useAuthStore()
    auth.user = { id: '1', email: 'a@b.com', username: 'A' }
    auth.setAccessToken('tok')
    await flushPromises()

    await wrapper.find('[data-test="user-menu-toggle"]').trigger('click')
    await wrapper.find('[data-test="logout-btn"]').trigger('click')
    await flushPromises()

    expect(auth.accessToken).toBeNull()
    expect(pushSpy).toHaveBeenCalledWith('/login')
  })
})
