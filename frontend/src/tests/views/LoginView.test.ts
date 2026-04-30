/**
 * LoginView 元件測試
 * 規格：.doc/taskflow-frontend.md §4.6（vee-validate + Zod）+ §4.5（登入後導頁）
 *
 * 測試行為：
 * - 渲染 email / password / submit
 * - 不合法輸入 submit 不會呼叫 authStore.login，而是顯示驗證訊息
 * - 合法 submit 呼叫 authStore.login，成功時導頁
 * - 帶 ?redirect= 時導向該路徑，否則 /dashboard
 * - API 失敗時顯示錯誤訊息且仍可重試
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import LoginView from '@/views/LoginView.vue'

vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

function buildRouter(initialPath = '/login'): Router {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: LoginView },
      { path: '/register', name: 'register', component: { template: '<div>register</div>' } },
      { path: '/dashboard', name: 'dashboard', component: { template: '<div>dashboard</div>' } },
      { path: '/project/:id/board', name: 'board', component: { template: '<div>board</div>' } },
    ],
  })
  router.push(initialPath)
  return router
}

async function mountLogin(router: Router) {
  await router.isReady()
  const wrapper = mount(LoginView, {
    global: { plugins: [router] },
  })
  await flushPromises()
  return wrapper
}

/**
 * 提交表單後等待 vee-validate 的多階段 async：
 * 1. handleSubmit → 內部 validate 透過 debounceAsync(setTimeout 5ms) 延遲執行
 * 2. validate 完成 → fn() 執行 → 多個 await 鏈
 * 3. 最終 isSubmitting reset
 *
 * setTimeout(50ms) 確保超過 5ms debounce + 後續所有 microtask flush。
 */
async function submitAndFlush(wrapper: ReturnType<typeof mount>) {
  await wrapper.find('form').trigger('submit')
  await new Promise((r) => setTimeout(r, 50))
  await flushPromises()
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.mocked(client.post).mockReset()
    vi.mocked(client.get).mockReset()
  })

  it('渲染 email / password 欄位與送出按鈕', async () => {
    const router = buildRouter()
    const wrapper = await mountLogin(router)

    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('空欄位 submit：不呼叫 API、顯示驗證訊息', async () => {
    const router = buildRouter()
    const wrapper = await mountLogin(router)

    await submitAndFlush(wrapper)

    expect(client.post).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('請輸入有效的 Email')
    expect(wrapper.text()).toContain('密碼至少 8 個字元')
  })

  it('合法輸入 submit：呼叫 authStore.login 並導 /dashboard', async () => {
    vi.mocked(client.post).mockResolvedValueOnce({ data: { access: 'tok' } })
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { id: '1', email: 'u@e.com', username: 'u' },
    })

    const router = buildRouter()
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = await mountLogin(router)

    await wrapper.find('input[type="email"]').setValue('u@e.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await submitAndFlush(wrapper)

    expect(client.post).toHaveBeenCalledWith('/auth/login/', {
      email: 'u@e.com',
      password: 'password123',
    })
    expect(pushSpy).toHaveBeenCalledWith('/dashboard')
  })

  it('帶 ?redirect= 時導向該路徑', async () => {
    vi.mocked(client.post).mockResolvedValueOnce({ data: { access: 'tok' } })
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { id: '1', email: 'u@e.com', username: 'u' },
    })

    const router = buildRouter('/login?redirect=/project/abc/board')
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = await mountLogin(router)

    await wrapper.find('input[type="email"]').setValue('u@e.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await submitAndFlush(wrapper)

    expect(pushSpy).toHaveBeenCalledWith('/project/abc/board')
  })

  it('登入 API 失敗：顯示錯誤訊息、不導頁', async () => {
    const err = new Error('Invalid credentials') as Error & { response?: unknown }
    err.response = { status: 401, data: { detail: '帳號或密碼錯誤' } }
    vi.mocked(client.post).mockRejectedValueOnce(err)

    const router = buildRouter()
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = await mountLogin(router)

    await wrapper.find('input[type="email"]').setValue('u@e.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await submitAndFlush(wrapper)

    expect(wrapper.text()).toContain('帳號或密碼錯誤')
    expect(pushSpy).not.toHaveBeenCalledWith('/dashboard')
  })

  it('提供「前往註冊」連結指向 /register', async () => {
    const router = buildRouter()
    const wrapper = await mountLogin(router)

    const link = wrapper.find('a[href="/register"]')
    expect(link.exists()).toBe(true)
  })

  it('密碼顯示切換：預設 type=password，點眼睛切到 text，再點切回 password', async () => {
    const wrapper = await mountLogin(buildRouter())
    const passwordInput = wrapper.find('input#password')
    const toggle = wrapper.find('[data-test="toggle-password"]')

    expect(toggle.exists()).toBe(true)
    expect(passwordInput.attributes('type')).toBe('password')

    await toggle.trigger('click')
    expect(passwordInput.attributes('type')).toBe('text')

    await toggle.trigger('click')
    expect(passwordInput.attributes('type')).toBe('password')
  })
})
