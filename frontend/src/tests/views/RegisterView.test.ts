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

  it('註冊 API 失敗（detail）：顯示後端通用錯誤訊息、不導頁', async () => {
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

  it('註冊 API 回傳欄位驗證錯誤：訊息顯示在對應欄位下、不顯示制式 banner', async () => {
    const err = new Error('400') as Error & { response?: unknown }
    err.response = { status: 400, data: { password: ['這個密碼太常見了。'] } }
    vi.mocked(client.post).mockRejectedValueOnce(err)

    const wrapper = await mountRegister(buildRouter())

    await wrapper.find('input[type="email"]').setValue('a@b.com')
    await wrapper.find('input[name="username"]').setValue('alice')
    await wrapper.find('input[name="password"]').setValue('password')
    await wrapper.find('input[name="confirmPassword"]').setValue('password')

    await submitAndFlush(wrapper)

    // 訊息應顯示
    expect(wrapper.text()).toContain('這個密碼太常見了。')
    // 不應該顯示制式 fallback 訊息
    expect(wrapper.text()).not.toContain('註冊失敗，請稍後再試')
  })

  it('註冊 API 多欄位錯誤：每個欄位下顯示對應訊息', async () => {
    const err = new Error('400') as Error & { response?: unknown }
    err.response = {
      status: 400,
      data: {
        email: ['Email 已存在'],
        username: ['此使用者名稱已被使用'],
      },
    }
    vi.mocked(client.post).mockRejectedValueOnce(err)

    const wrapper = await mountRegister(buildRouter())

    await wrapper.find('input[type="email"]').setValue('dup@b.com')
    await wrapper.find('input[name="username"]').setValue('taken')
    await wrapper.find('input[name="password"]').setValue('StrongPwd1')
    await wrapper.find('input[name="confirmPassword"]').setValue('StrongPwd1')

    await submitAndFlush(wrapper)

    expect(wrapper.text()).toContain('Email 已存在')
    expect(wrapper.text()).toContain('此使用者名稱已被使用')
  })

  it('提供「前往登入」連結指向 /login', async () => {
    const router = buildRouter()
    const wrapper = await mountRegister(router)

    const link = wrapper.find('a[href="/login"]')
    expect(link.exists()).toBe(true)
  })

  it('密碼欄顯示切換：預設 type=password，點眼睛切到 text 並切回', async () => {
    const wrapper = await mountRegister(buildRouter())
    const passwordInput = wrapper.find('input#password')
    const toggle = wrapper.find('[data-test="toggle-password"]')

    expect(passwordInput.attributes('type')).toBe('password')
    await toggle.trigger('click')
    expect(passwordInput.attributes('type')).toBe('text')
    await toggle.trigger('click')
    expect(passwordInput.attributes('type')).toBe('password')
  })

  it('確認密碼欄顯示切換：與密碼欄獨立切換', async () => {
    const wrapper = await mountRegister(buildRouter())
    const passwordInput = wrapper.find('input#password')
    const confirmInput = wrapper.find('input#confirmPassword')

    await wrapper.find('[data-test="toggle-confirm-password"]').trigger('click')

    // 確認密碼切到 text，但密碼欄仍為 password（兩個切換獨立）
    expect(confirmInput.attributes('type')).toBe('text')
    expect(passwordInput.attributes('type')).toBe('password')
  })
})
