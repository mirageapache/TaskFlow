/**
 * Sentry 前端整合
 * 規格：.doc/taskflow-backend.md §9.2
 *
 * 設計原則（與後端一致）：
 * - VITE_SENTRY_DSN 為空時不初始化，避免本地 / CI 噪音
 * - sendDefaultPii=false 避免送出使用者 cookies / headers
 * - tracesSampleRate 與 environment 從環境變數讀取
 */
import * as Sentry from '@sentry/vue'
import type { App } from 'vue'
import type { Router } from 'vue-router'

export interface SentryInitOptions {
  app: App
  router?: Router
  dsn?: string
  environment?: string
  tracesSampleRate?: number
}

export function initSentry(options: SentryInitOptions): boolean {
  const dsn = options.dsn ?? import.meta.env.VITE_SENTRY_DSN ?? ''
  if (!dsn) return false

  const environment =
    options.environment ?? import.meta.env.VITE_SENTRY_ENVIRONMENT ?? 'development'
  const tracesSampleRate =
    options.tracesSampleRate ?? Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0.2)

  Sentry.init({
    app: options.app,
    dsn,
    environment,
    tracesSampleRate,
    sendDefaultPii: false,
    integrations: options.router
      ? [Sentry.browserTracingIntegration({ router: options.router })]
      : [],
  })
  return true
}
