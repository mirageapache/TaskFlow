/**
 * RegisterView 元件測試
 * 規格：.doc/taskflow-frontend.md §4.6（vee-validate + Zod）
 *
 * 測試行為：
 * - 渲染 email / username / password / confirmPassword / submit
 * - 不合法輸入 submit 不會呼叫 API
 * - 密碼不一致顯示錯誤
 * - 合法 submit 呼叫 authStore.register（自動 login）並導 /dashboard
 * - API 失敗時顯示後端錯誤訊息
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'

import client from '@/api/client'
import RegisterView from '@/views/RegisterView.vue'

vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

function buildRouter(initialPath = '/register'): Router {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: { template: '<div>login</div>' } },
      { path: '/register', name: 'register', component: RegisterView },
      { path: '/dashboard', name: 'dashboard', component: { template: '<div>dashboard</div>' } },
    ],
  })
  router.push(initialPath)
  return router
}

async function mountRegister(router: Router) {
  await router.isReady()
  const wrapper = mount(RegisterView, {
    global: { plugins: [router] },
  })
  await flushPromises()
  return wrapper
}

/** vee-validate validate 內部用 5ms debounce，必須等實際時間流逝 */
async function submitAndFlush(wrapper: ReturnType<typeof mount>) {
  await wrapper.find('form').trigger('submit')
  await new Promise((r) => setTimeout(r, 50))
  await flushPromises()
}

describe('RegisterView', () => {
  beforeEach(() => {
    vi.mocked(client.post).mockReset()
    vi.mocked(client.get).mockReset()
  })

  it('渲染 email / username / password / confirmPassword 欄位', async () => {
    const router = buildRouter()
    const wrapper = await mountRegister(router)

    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[name="username"]').exists()).toBe(true)
    expect(wrapper.find('input[name="password"]').exists()).toBe(true)
    expect(wrapper.find('input[name="confirmPassword"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('空欄位 submit：不呼叫 API、顯示驗證訊息', async () => {
    const router = buildRouter()
    const wrapper = await mountRegister(router)

    await submitAndFlush(wrapper)

    expect(client.post).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('請輸入有效的 Email')
    expect(wrapper.text()).toContain('使用者名至少 3 個字元')
    expect(wrapper.text()).toContain('密碼至少 8 個字元')
  })

  it('密碼與確認密碼不一致：顯示「密碼不一致」、不呼叫 API', async () => {
    const router = buildRouter()
    const wrapper = await mountRegister(router)

    await wrapper.find('input[type="email"]').setValue('a@b.com')
    await wrapper.find('input[name="username"]').setValue('alice')
    await wrapper.find('input[name="password"]').setValue('StrongPwd1')
    await wrapper.find('input[name="confirmPassword"]').setValue('Different1')

    await submitAndFlush(wrapper)

    expect(client.post).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('密碼不一致')
  })

  it('合法 submit：呼叫 register → login → 導 /dashboard', async () => {
    // register API 一次、login API 一次、me API 一次
    vi.mocked(client.post)
      .mockResolvedValueOnce({}) // /auth/register/
      .mockResolvedValueOnce({ data: { access: 'tok' } }) // /auth/login/
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { id: '1', email: 'a@b.com', username: 'alice' },
    })

    const router = buildRouter()
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = await mountRegister(router)

    await wrapper.find('input[type="email"]').setValue('a@b.com')
    await wrapper.find('input[name="username"]').setValue('alice')
    await wrapper.find('input[name="password"]').setValue('StrongPwd1')
    await wrapper.find('input[name="confirmPassword"]').setValue('StrongPwd1')

    await submitAndFlush(wrapper)

    expect(client.post).toHaveBeenNthCalledWith(1, '/auth/register/', {
      email: 'a@b.com',
      username: 'alice',
      password: 'StrongPwd1',
    })
    expect(pushSpy).toHaveBeenCalledWith('/dashboard')
  })

  it('註冊 API 失敗：顯示後端錯誤訊息、不導頁', async () => {
    const err = new Error('Email taken') as Error & { response?: unknown }
    err.response = { status: 400, data: { detail: '此 Email 已註冊' } }
    vi.mocked(client.post).mockRejectedValueOnce(err)

    const router = buildRouter()
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = await mountRegister(router)

    await wrapper.find('input[type="email"]').setValue('dup@b.com')
    await wrapper.find('input[name="username"]').setValue('alice')
    await wrapper.find('input[name="password"]').setValue('StrongPwd1')
    await wrapper.find('input[name="confirmPassword"]').setValue('StrongPwd1')

    await submitAndFlush(wrapper)

    expect(wrapper.text()).toContain('此 Email 已註冊')
    expect(pushSpy).not.toHaveBeenCalledWith('/dashboard')
  })

  it('提供「前往登入」連結指向 /login', async () => {
    const router = buildRouter()
    const wrapper = await mountRegister(router)

    const link = wrapper.find('a[href="/login"]')
    expect(link.exists()).toBe(true)
  })
})
