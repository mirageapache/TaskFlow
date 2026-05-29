/**
 * AppLayout 測試
 * 規格：.doc/taskflow_layout_design.md §5.3 / .doc/taskflow-frontend.md §4.7
 *
 * 驗證：
 * - 渲染 slot 內容
 * - TopBar 顯示 Logo（連結回 /dashboard）
 * - Sidebar 包含主要導航項目（儀表板 / AI 助理 / 設定）
 * - 已登入：使用者選單顯示首字 / 名稱 / Email
 * - 點登出：呼叫 authStore.logout 後導 /login
 * - 即時通知：WS 推送 → Pinia store 更新 + Toast 顯示 + 未讀徽章
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import AppLayout from '@/layouts/AppLayout.vue'

vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

const toastAdd = vi.fn()
vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: toastAdd }),
}))

// useWebSocket：以 stub 暴露 connect / disconnect / on，並提供 emit 觸發 handler
const wsHandlers: Record<string, ((msg: unknown) => void) | undefined> = {}
const wsConnect = vi.fn()
const wsDisconnect = vi.fn()
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: { value: false },
    connect: wsConnect,
    disconnect: wsDisconnect,
    on: (type: string, handler: (msg: unknown) => void) => {
      wsHandlers[type] = handler
    },
  }),
}))

function emitWs(type: string, msg: unknown) {
  wsHandlers[type]?.(msg)
}

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
    toastAdd.mockReset()
    wsConnect.mockReset()
    wsDisconnect.mockReset()
    for (const k of Object.keys(wsHandlers)) delete wsHandlers[k]
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

  it('Sidebar 透過 flex 父層撐滿剩餘高度（lg:flex + 父層 flex-1 min-h-0）', async () => {
    const wrapper = await mountLayout(buildRouter())
    const sidebar = wrapper.find('[data-test="sidebar"]')
    expect(sidebar.exists()).toBe(true)

    // 新版改用 flex 撐高，sidebar 本身需是 flex column
    const cls = sidebar.classes()
    expect(cls).toContain('lg:flex')
    expect(cls).toContain('flex-col')

    // 父層需具備 flex-1 min-h-0 才能讓 sidebar 在 topbar 下方撐到底
    const parent = sidebar.element.parentElement
    expect(parent).not.toBeNull()
    expect(parent!.className).toContain('flex-1')
    expect(parent!.className).toContain('min-h-0')
  })

  it('Sidebar 上方顯示目前工作區名稱（workspace store 有資料時）', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'w1',
            name: '個人工作區',
            description: '',
            avatar_url: null,
            owner: 'u1',
            created_at: '',
            updated_at: '',
          },
        ],
      },
    })

    const wrapper = await mountLayout(buildRouter())
    await flushPromises()

    const header = wrapper.find('[data-test="workspace-header"]')
    expect(header.exists()).toBe(true)
    expect(header.text()).toContain('個人工作區')
  })

  it('Sidebar 上方在工作區尚未載入時顯示 placeholder', async () => {
    // 不設置 mock → fetchAll 會嘗試但失敗，store 維持空 list
    vi.mocked(client.get).mockRejectedValueOnce(new Error('not loaded'))
    const wrapper = await mountLayout(buildRouter())
    await flushPromises()

    const header = wrapper.find('[data-test="workspace-header"]')
    expect(header.exists()).toBe(true)
    // placeholder 文字
    expect(header.text()).toContain('工作區')
  })

  it('Sidebar 收合按鈕：點擊後 sidebar 變窄（w-16），再點變寬（w-60）', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { count: 0, next: null, previous: null, results: [] },
    })
    const wrapper = await mountLayout(buildRouter())
    await flushPromises()

    const sidebar = wrapper.find('[data-test="sidebar"]')
    expect(sidebar.classes()).toContain('w-60')

    await wrapper.find('[data-test="sidebar-toggle"]').trigger('click')
    expect(sidebar.classes()).toContain('w-16')
    expect(sidebar.classes()).not.toContain('w-60')

    // 收合狀態下按鈕仍存在（位置可能不同），再點展開
    await wrapper.find('[data-test="sidebar-toggle"]').trigger('click')
    expect(sidebar.classes()).toContain('w-60')
  })

  describe('即時通知（WebSocket + Toast + 未讀徽章）', () => {
    it('掛載時呼叫 ws.connect 並註冊 notification / unread_count handler', async () => {
      await mountLayout(buildRouter())
      await flushPromises()

      expect(wsConnect).toHaveBeenCalledTimes(1)
      expect(typeof wsHandlers.notification).toBe('function')
      expect(typeof wsHandlers.unread_count).toBe('function')
    })

    it('收到 type=notification → store.pushNotification + toast.add', async () => {
      await mountLayout(buildRouter())
      await flushPromises()

      const notifStore = useNotificationStore()
      expect(notifStore.unreadCount).toBe(0)

      emitWs('notification', {
        type: 'notification',
        data: {
          id: 'n1',
          recipient: 'u1',
          notif_type: 'task_assigned',
          title: '你被指派了一個任務',
          body: '請開始處理「設計資料庫」',
          payload: {},
          is_read: false,
          read_at: null,
          created_at: '2026-05-21T08:00:00Z',
        },
      })

      expect(notifStore.list).toHaveLength(1)
      expect(notifStore.list[0].id).toBe('n1')
      expect(notifStore.unreadCount).toBe(1)
      expect(toastAdd).toHaveBeenCalledTimes(1)
      expect(toastAdd).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'info',
          summary: '你被指派了一個任務',
          detail: '請開始處理「設計資料庫」',
        }),
      )
    })

    it('收到 type=unread_count → store.setUnreadCount', async () => {
      const wrapper = await mountLayout(buildRouter())
      await flushPromises()

      emitWs('unread_count', { type: 'unread_count', count: 7 })
      await flushPromises()

      const notifStore = useNotificationStore()
      expect(notifStore.unreadCount).toBe(7)

      // Badge 顯示在通知鈴鐺上
      const badge = wrapper.find('[data-test="notification-badge"]')
      expect(badge.exists()).toBe(true)
      expect(badge.text()).toBe('7')
    })

    it('未讀為 0：不顯示徽章', async () => {
      const wrapper = await mountLayout(buildRouter())
      await flushPromises()

      expect(wrapper.find('[data-test="notification-badge"]').exists()).toBe(false)
    })

    it('未讀超過 99：徽章顯示 99+', async () => {
      const wrapper = await mountLayout(buildRouter())
      await flushPromises()
      emitWs('unread_count', { type: 'unread_count', count: 150 })
      await flushPromises()
      expect(wrapper.find('[data-test="notification-badge"]').text()).toBe('99+')
    })

    it('卸載時呼叫 ws.disconnect', async () => {
      const wrapper = await mountLayout(buildRouter())
      await flushPromises()
      wrapper.unmount()
      expect(wsDisconnect).toHaveBeenCalledTimes(1)
    })
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
