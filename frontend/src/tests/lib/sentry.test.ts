/**
 * Sentry 前端整合 TDD 測試
 * 規格：.doc/taskflow-backend.md §9.2
 *
 * 測試範圍：
 * - VITE_SENTRY_DSN 為空時不呼叫 Sentry.init
 * - 有 DSN 時 Sentry.init 被呼叫並帶入 dsn / environment / sampleRate
 * - sendDefaultPii=false（避免外洩使用者 cookies / headers）
 * - 提供 router 時加入 browserTracingIntegration
 */
import { createApp } from 'vue'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { initSentry } from '@/lib/sentry'

vi.mock('@sentry/vue', () => ({
  init: vi.fn(),
  browserTracingIntegration: vi.fn(() => ({ name: 'BrowserTracing' })),
}))

import * as Sentry from '@sentry/vue'

const App = { template: '<div />' }

describe('initSentry — disabled', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns false and skips init when dsn is empty', () => {
    const app = createApp(App)
    const result = initSentry({ app, dsn: '' })
    expect(result).toBe(false)
    expect(Sentry.init).not.toHaveBeenCalled()
  })
})

describe('initSentry — enabled', () => {
  const FAKE_DSN = 'https://abc123@o12345.ingest.sentry.io/67890'

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls Sentry.init with the provided dsn', () => {
    const app = createApp(App)
    const result = initSentry({ app, dsn: FAKE_DSN })
    expect(result).toBe(true)
    expect(Sentry.init).toHaveBeenCalledOnce()
    const call = vi.mocked(Sentry.init).mock.calls[0][0]!
    expect(call.dsn).toBe(FAKE_DSN)
    expect(call.app).toBe(app)
  })

  it('sets sendDefaultPii to false to avoid leaking PII', () => {
    const app = createApp(App)
    initSentry({ app, dsn: FAKE_DSN })
    const call = vi.mocked(Sentry.init).mock.calls[0][0]!
    expect(call.sendDefaultPii).toBe(false)
  })

  it('passes environment and tracesSampleRate through', () => {
    const app = createApp(App)
    initSentry({
      app,
      dsn: FAKE_DSN,
      environment: 'production',
      tracesSampleRate: 0.5,
    })
    const call = vi.mocked(Sentry.init).mock.calls[0][0]!
    expect(call.environment).toBe('production')
    expect(call.tracesSampleRate).toBe(0.5)
  })

  it('attaches browserTracingIntegration when router is provided', () => {
    const app = createApp(App)
    const fakeRouter = {} as never
    initSentry({ app, dsn: FAKE_DSN, router: fakeRouter })
    expect(Sentry.browserTracingIntegration).toHaveBeenCalledWith({ router: fakeRouter })
    const call = vi.mocked(Sentry.init).mock.calls[0][0]!
    expect(call.integrations).toHaveLength(1)
  })

  it('omits browserTracingIntegration when router is not provided', () => {
    const app = createApp(App)
    initSentry({ app, dsn: FAKE_DSN })
    expect(Sentry.browserTracingIntegration).not.toHaveBeenCalled()
    const call = vi.mocked(Sentry.init).mock.calls[0][0]!
    expect(call.integrations).toEqual([])
  })
})
