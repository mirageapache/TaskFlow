/**
 * Auth Store 單元測試
 * 規格：.doc/taskflow-frontend.md §4.4、.doc/taskflow-testing.md §4.1
 */
import { describe, it, expect, vi } from 'vitest'

import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

describe('useAuthStore', () => {
  it('初始狀態：未登入', () => {
    const store = useAuthStore()
    expect(store.accessToken).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('已存的 access token 從 localStorage 還原', () => {
    localStorage.setItem('access_token', 'persisted-token')
    const store = useAuthStore()
    expect(store.accessToken).toBe('persisted-token')
    expect(store.isAuthenticated).toBe(true)
  })

  it('login() 成功：儲存 token、抓 user、寫入 localStorage', async () => {
    vi.mocked(client.post).mockResolvedValueOnce({ data: { access: 'fake-token' } })
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { id: '1', email: 'test@test.com', username: 'testuser' },
    })

    const store = useAuthStore()
    await store.login('test@test.com', 'password123')

    expect(store.accessToken).toBe('fake-token')
    expect(store.isAuthenticated).toBe(true)
    expect(store.user).toEqual({ id: '1', email: 'test@test.com', username: 'testuser' })
    expect(localStorage.getItem('access_token')).toBe('fake-token')
    expect(client.post).toHaveBeenCalledWith('/auth/login/', {
      email: 'test@test.com',
      password: 'password123',
    })
  })

  it('login() 失敗：狀態保持未登入', async () => {
    vi.mocked(client.post).mockRejectedValueOnce(new Error('401'))

    const store = useAuthStore()
    await expect(store.login('bad@test.com', 'wrong')).rejects.toThrow()

    expect(store.accessToken).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('register() 註冊後自動觸發 login', async () => {
    vi.mocked(client.post)
      .mockResolvedValueOnce({}) // register
      .mockResolvedValueOnce({ data: { access: 'new-token' } }) // login
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { id: '2', email: 'new@test.com', username: 'new' },
    })

    const store = useAuthStore()
    await store.register('new@test.com', 'new', 'StrongPwd1!')

    expect(client.post).toHaveBeenCalledWith('/auth/register/', expect.any(Object))
    expect(store.accessToken).toBe('new-token')
    expect(store.user?.email).toBe('new@test.com')
  })

  it('logout() 清除 token / user / localStorage', async () => {
    vi.mocked(client.post).mockResolvedValueOnce({})
    const store = useAuthStore()
    store.setAccessToken('temp-token')

    await store.logout()

    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(client.post).toHaveBeenCalledWith('/auth/logout/')
  })

  it('logout() 即使 API 失敗仍清除前端狀態（透過 finally）', async () => {
    vi.mocked(client.post).mockRejectedValueOnce(new Error('network'))
    const store = useAuthStore()
    store.setAccessToken('temp-token')

    // logout 透過 finally 清除狀態，但 error 仍會拋給上層 caller
    await expect(store.logout()).rejects.toThrow('network')

    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('initAuth() 無 token 時直接結束，不發 API', async () => {
    const store = useAuthStore()
    await store.initAuth()
    expect(client.get).not.toHaveBeenCalled()
  })

  it('initAuth() 有 token 時呼叫 /me/ 還原使用者', async () => {
    localStorage.setItem('access_token', 'persisted')
    vi.mocked(client.get).mockResolvedValueOnce({
      data: { id: '3', email: 'persisted@test.com', username: 'p' },
    })

    const store = useAuthStore()
    await store.initAuth()

    expect(client.get).toHaveBeenCalledWith('/users/me/')
    expect(store.user?.email).toBe('persisted@test.com')
  })

  it('initAuth() /me/ 失敗時不拋例外', async () => {
    localStorage.setItem('access_token', 'invalid')
    vi.mocked(client.get).mockRejectedValueOnce(new Error('401'))

    const store = useAuthStore()
    // 不應拋出
    await expect(store.initAuth()).resolves.toBeUndefined()
  })

  it('clearSession() 直接清除狀態（不呼叫 API）', () => {
    const store = useAuthStore()
    store.setAccessToken('x')

    store.clearSession()

    expect(store.accessToken).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(client.post).not.toHaveBeenCalled()
  })
})
