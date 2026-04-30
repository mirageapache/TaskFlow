/**
 * Router Navigation Guard 測試
 * 規格：.doc/taskflow-frontend.md §4.5
 *
 * 用獨立的 router 實例（同樣 routes + 同樣 guard）測試導航行為，
 * 避免污染應用的全域 router 狀態。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

// 與 src/router/index.ts 同步的路由表（測試用獨立實例）
function buildRouter(): Router {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: { template: '<div>login</div>' }, meta: { requiresAuth: false } },
      { path: '/register', name: 'register', component: { template: '<div>register</div>' }, meta: { requiresAuth: false } },
      { path: '/dashboard', name: 'dashboard', component: { template: '<div>dashboard</div>' }, meta: { requiresAuth: true } },
      { path: '/settings', name: 'settings', component: { template: '<div>settings</div>' }, meta: { requiresAuth: true } },
      { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
    ],
  })

  let initialized = false
  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    if (!initialized) {
      await auth.initAuth()
      initialized = true
    }
    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    if (!to.meta.requiresAuth && auth.isAuthenticated) {
      return { path: '/dashboard' }
    }
  })

  return router
}

describe('Router navigation guard', () => {
  let router: Router

  beforeEach(() => {
    router = buildRouter()
  })

  it('未登入造訪受保護頁 → 重導 /login 並帶 redirect query', async () => {
    await router.push('/dashboard')
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/dashboard')
  })

  it('未登入可正常瀏覽 /login', async () => {
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('已登入造訪受保護頁 → 正常進入', async () => {
    localStorage.setItem('access_token', 'logged-in')
    vi.mocked(client.get).mockResolvedValueOnce({ data: { id: '1', email: 'x@x.com', username: 'x' } })

    await router.push('/dashboard')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('已登入造訪 /login → 重導 /dashboard', async () => {
    localStorage.setItem('access_token', 'logged-in')
    vi.mocked(client.get).mockResolvedValueOnce({ data: { id: '1', email: 'x@x.com', username: 'x' } })

    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('未匹配路由 fallback 到 /dashboard（再被 guard 重導 /login 因未登入）', async () => {
    await router.push('/no-such-page')
    // 未登入時 fallback /dashboard 後再被導 /login
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('initAuth 只在首次導航執行一次', async () => {
    localStorage.setItem('access_token', 'persisted')
    vi.mocked(client.get).mockResolvedValueOnce({ data: { id: '1', email: 'a@a.com', username: 'a' } })

    await router.push('/dashboard')
    await router.push('/settings')
    await router.push('/dashboard')

    // 三次導航中只第一次呼叫 /me/
    expect(client.get).toHaveBeenCalledTimes(1)
  })
})
