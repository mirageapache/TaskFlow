/**
 * Axios Client 攔截器測試
 * 規格：.doc/taskflow-frontend.md §4.3
 *
 * 透過 mock axios adapter 控制 HTTP 回應，驗證：
 * - Request interceptor 自動附 Authorization header
 * - 401 → refresh → retry 連鎖
 * - refresh 失敗時清除 session
 * - 並發 401 請求只觸發一次 refresh
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { AxiosAdapter, AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// router push 不應實際導航；mock 為 vitest spy
const routerPushMock = vi.fn()
vi.mock('@/router', () => ({
  default: { push: routerPushMock },
}))

import client from '@/api/client'

type AdapterImpl = (config: InternalAxiosRequestConfig) => Promise<AxiosResponse>

function makeResponse(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosResponse {
  return { status, data, statusText: '', headers: {}, config }
}

function makeAxiosError(
  config: InternalAxiosRequestConfig,
  status: number,
): AxiosError {
  const err = new Error(`Request failed with status code ${status}`) as AxiosError
  err.config = config
  err.response = {
    status,
    data: {},
    statusText: '',
    headers: {},
    config,
  }
  err.isAxiosError = true
  return err
}

describe('Axios client interceptors', () => {
  let originalAdapter: typeof client.defaults.adapter

  beforeEach(() => {
    originalAdapter = client.defaults.adapter
    routerPushMock.mockClear()
  })

  afterEach(() => {
    client.defaults.adapter = originalAdapter
  })

  function setAdapter(impl: AdapterImpl) {
    client.defaults.adapter = impl as unknown as AxiosAdapter
  }

  it('Request interceptor 自動帶 Authorization header（有 token 時）', async () => {
    localStorage.setItem('access_token', 'my-token')
    let captured: InternalAxiosRequestConfig | null = null
    setAdapter(async (config) => {
      captured = config
      return makeResponse(config, 200, 'ok')
    })

    await client.get('/something/')
    expect(captured!.headers.Authorization).toBe('Bearer my-token')
  })

  it('Request interceptor 無 token 時不帶 Authorization header', async () => {
    let captured: InternalAxiosRequestConfig | null = null
    setAdapter(async (config) => {
      captured = config
      return makeResponse(config, 200, 'ok')
    })

    await client.get('/public/')
    expect(captured!.headers.Authorization).toBeUndefined()
  })

  it('401 → refresh → retry：使用新 token 重送原請求', async () => {
    localStorage.setItem('access_token', 'expired')
    const seen: Array<{ url: string; auth: string | undefined }> = []
    let calls = 0

    setAdapter(async (config) => {
      calls++
      seen.push({
        url: config.url || '',
        auth: config.headers.Authorization as string | undefined,
      })

      // 1. 原始受保護請求 → 401
      if (calls === 1 && config.url === '/protected/') {
        throw makeAxiosError(config, 401)
      }
      // 2. refresh 端點 → 200 帶新 token
      if (config.url === '/auth/refresh/') {
        return makeResponse(config, 200, { access: 'fresh-token' })
      }
      // 3. 重試 → 200
      return makeResponse(config, 200, 'retried')
    })

    const result = await client.get('/protected/')
    expect(result.data).toBe('retried')
    expect(localStorage.getItem('access_token')).toBe('fresh-token')

    // 驗證重試時帶的是新 token
    const retryCall = seen.find((c) => c.url === '/protected/' && c.auth?.includes('fresh-token'))
    expect(retryCall).toBeDefined()
  })

  it('refresh 失敗：清除 session 並 push /login', async () => {
    localStorage.setItem('access_token', 'expired')
    // 設定路徑為非公開頁
    window.history.pushState({}, '', '/dashboard')

    setAdapter(async (config) => {
      if (config.url === '/protected/') {
        throw makeAxiosError(config, 401)
      }
      if (config.url === '/auth/refresh/') {
        throw makeAxiosError(config, 401)
      }
      return makeResponse(config, 200, 'should-not-reach')
    })

    await expect(client.get('/protected/')).rejects.toBeDefined()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(routerPushMock).toHaveBeenCalledWith('/login')
  })

  it('refresh 失敗 + 已在公開頁（/register、/login、/oauth/callback）：清除 session 但不 push /login', async () => {
    setAdapter(async (config) => {
      if (config.url === '/protected/') {
        throw makeAxiosError(config, 401)
      }
      if (config.url === '/auth/refresh/') {
        throw makeAxiosError(config, 401)
      }
      return makeResponse(config, 200, 'should-not-reach')
    })

    for (const publicPath of ['/register', '/login', '/oauth/callback']) {
      localStorage.setItem('access_token', 'expired')
      routerPushMock.mockClear()
      window.history.pushState({}, '', publicPath)

      await expect(client.get('/protected/')).rejects.toBeDefined()

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(routerPushMock).not.toHaveBeenCalled()
    }
  })

  it('/auth/refresh/ 自身回 401 不會觸發遞迴 refresh', async () => {
    localStorage.setItem('access_token', 'expired')
    let refreshCalls = 0

    setAdapter(async (config) => {
      if (config.url === '/auth/refresh/') {
        refreshCalls++
        throw makeAxiosError(config, 401)
      }
      return makeResponse(config, 200, 'ok')
    })

    await expect(client.post('/auth/refresh/')).rejects.toBeDefined()
    // 應該只試一次，不會自己呼叫自己造成無限迴圈
    expect(refreshCalls).toBe(1)
  })

  it('並發 401：只觸發一次 refresh，其餘請求排隊重試', async () => {
    localStorage.setItem('access_token', 'expired')
    let refreshCalls = 0
    const protectedHits: string[] = []

    setAdapter(async (config) => {
      if (config.url === '/auth/refresh/') {
        refreshCalls++
        // 模擬 refresh 需要時間
        await new Promise((r) => setTimeout(r, 10))
        return makeResponse(config, 200, { access: 'shared-fresh' })
      }
      // 帶舊 token 的請求 → 401；帶新 token 的請求 → 成功
      const auth = config.headers.Authorization as string
      if (auth?.includes('shared-fresh')) {
        protectedHits.push(config.url || '')
        return makeResponse(config, 200, config.url)
      }
      throw makeAxiosError(config, 401)
    })

    const [a, b, c] = await Promise.all([
      client.get('/a/'),
      client.get('/b/'),
      client.get('/c/'),
    ])

    expect(refreshCalls).toBe(1)
    expect(a.data).toBe('/a/')
    expect(b.data).toBe('/b/')
    expect(c.data).toBe('/c/')
    expect(localStorage.getItem('access_token')).toBe('shared-fresh')
  })

  it('非 401 錯誤直接拋出（不嘗試 refresh）', async () => {
    localStorage.setItem('access_token', 'valid')
    let refreshCalls = 0

    setAdapter(async (config) => {
      if (config.url === '/auth/refresh/') {
        refreshCalls++
        return makeResponse(config, 200, { access: 'new' })
      }
      throw makeAxiosError(config, 500)
    })

    await expect(client.get('/protected/')).rejects.toBeDefined()
    expect(refreshCalls).toBe(0)
  })
})
