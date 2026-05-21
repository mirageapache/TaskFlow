/**
 * useWebSocket composable 測試
 * 規格：.doc/taskflow-frontend.md §4.7
 *
 * 流程驗證：
 * 1. connect() 從 auth store 取 access token，組出含 token 的 ws URL
 * 2. 無 token 時不建立連線（避免握手就被後端 4401 close）
 * 3. onopen → isConnected = true；onclose / onerror → false
 * 4. onmessage 依照 data.type 分派到對應的 handler
 * 5. 沒註冊的 type / 解析失敗的訊息：不丟例外（解析失敗會 console.error）
 * 6. disconnect() 關閉 ws 並清掉內部參考，重複呼叫安全
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/auth'

// ── MockWebSocket：jsdom 不提供 WebSocket，需自訂 ────────────────────────
class MockWebSocket {
  static instances: MockWebSocket[] = []
  static last(): MockWebSocket {
    const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1]
    if (!ws) throw new Error('No MockWebSocket instance created')
    return ws
  }

  url: string
  readyState = 0
  onopen: ((ev: Event) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  close = vi.fn(() => {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close'))
  })

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  // ── 測試用觸發器 ──────────────────────────────────────────────────
  triggerOpen() {
    this.readyState = 1
    this.onopen?.(new Event('open'))
  }

  triggerMessage(data: unknown) {
    const payload = typeof data === 'string' ? data : JSON.stringify(data)
    this.onmessage?.(new MessageEvent('message', { data: payload }))
  }

  triggerError() {
    this.onerror?.(new Event('error'))
  }

  triggerClose() {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close'))
  }
}

beforeEach(() => {
  MockWebSocket.instances = []
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.stubEnv('VITE_WS_BASE_URL', 'ws://localhost:8000/ws')
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

// useAuthStore 需要在 stub 完成後再 import 進 composable，所以 dynamic import
async function loadComposable() {
  const mod = await import('@/composables/useWebSocket')
  return mod.useWebSocket
}

describe('useWebSocket', () => {
  describe('connect()', () => {
    it('用 auth store 的 token 組出 ws URL 並開啟連線', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('jwt-token-xyz')

      const useWebSocket = await loadComposable()
      const { connect } = useWebSocket()
      connect()

      expect(MockWebSocket.instances).toHaveLength(1)
      expect(MockWebSocket.last().url).toBe(
        'ws://localhost:8000/ws/notifications/?token=jwt-token-xyz',
      )
    })

    it('沒有 token 時不建立連線（避免握手就被後端 4401）', async () => {
      const useWebSocket = await loadComposable()
      const { connect, isConnected } = useWebSocket()
      connect()

      expect(MockWebSocket.instances).toHaveLength(0)
      expect(isConnected.value).toBe(false)
    })

    it('onopen 時 isConnected 變為 true', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect, isConnected } = useWebSocket()
      connect()
      expect(isConnected.value).toBe(false)

      MockWebSocket.last().triggerOpen()
      expect(isConnected.value).toBe(true)
    })

    it('onclose 與 onerror 時 isConnected 變回 false', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect, isConnected } = useWebSocket()
      connect()
      MockWebSocket.last().triggerOpen()
      expect(isConnected.value).toBe(true)

      MockWebSocket.last().triggerClose()
      expect(isConnected.value).toBe(false)

      // 重新連線後再測 onerror
      connect()
      MockWebSocket.last().triggerOpen()
      MockWebSocket.last().triggerError()
      expect(isConnected.value).toBe(false)
    })
  })

  describe('on() 訊息分派', () => {
    it('依 data.type 分派到對應的 handler', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect, on } = useWebSocket()
      const notifHandler = vi.fn()
      const countHandler = vi.fn()
      on('notification', notifHandler)
      on('unread_count', countHandler)
      connect()
      MockWebSocket.last().triggerOpen()

      const notifPayload = { type: 'notification', data: { id: 'n1', title: '新通知' } }
      MockWebSocket.last().triggerMessage(notifPayload)
      expect(notifHandler).toHaveBeenCalledTimes(1)
      expect(notifHandler).toHaveBeenCalledWith(notifPayload)
      expect(countHandler).not.toHaveBeenCalled()

      const countPayload = { type: 'unread_count', count: 3 }
      MockWebSocket.last().triggerMessage(countPayload)
      expect(countHandler).toHaveBeenCalledWith(countPayload)
    })

    it('沒註冊 handler 的 type：不丟例外', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect } = useWebSocket()
      connect()

      expect(() => {
        MockWebSocket.last().triggerMessage({ type: 'never_registered', foo: 1 })
      }).not.toThrow()
    })

    it('收到非 JSON 訊息：console.error 提示，不丟例外', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')
      const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const useWebSocket = await loadComposable()
      const { connect, on } = useWebSocket()
      const handler = vi.fn()
      on('notification', handler)
      connect()

      expect(() => {
        MockWebSocket.last().triggerMessage('not json{{')
      }).not.toThrow()
      expect(handler).not.toHaveBeenCalled()
      expect(errSpy).toHaveBeenCalled()

      errSpy.mockRestore()
    })

    it('on() 後註冊：對先前 connect 後到達的訊息一樣生效', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect, on } = useWebSocket()
      connect()

      // 先連、後註冊
      const handler = vi.fn()
      on('notification', handler)
      MockWebSocket.last().triggerMessage({ type: 'notification', x: 1 })
      expect(handler).toHaveBeenCalledTimes(1)
    })

    it('同 type 重新 on()：後者覆蓋前者（避免遺留舊 handler）', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect, on } = useWebSocket()
      const first = vi.fn()
      const second = vi.fn()
      on('notification', first)
      on('notification', second)
      connect()

      MockWebSocket.last().triggerMessage({ type: 'notification', v: 1 })
      expect(first).not.toHaveBeenCalled()
      expect(second).toHaveBeenCalledTimes(1)
    })
  })

  describe('disconnect()', () => {
    it('關閉 ws 並把內部 ws ref 清為 null', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect, disconnect, isConnected } = useWebSocket()
      connect()
      MockWebSocket.last().triggerOpen()
      expect(isConnected.value).toBe(true)

      const wsInstance = MockWebSocket.last()
      disconnect()

      expect(wsInstance.close).toHaveBeenCalledTimes(1)
      expect(isConnected.value).toBe(false)
    })

    it('未連線時呼叫 disconnect()：safe no-op', async () => {
      const useWebSocket = await loadComposable()
      const { disconnect } = useWebSocket()
      expect(() => disconnect()).not.toThrow()
    })

    it('重複呼叫 disconnect()：只關一次', async () => {
      const auth = useAuthStore()
      auth.setAccessToken('t')

      const useWebSocket = await loadComposable()
      const { connect, disconnect } = useWebSocket()
      connect()
      const wsInstance = MockWebSocket.last()

      disconnect()
      disconnect()
      expect(wsInstance.close).toHaveBeenCalledTimes(1)
    })
  })
})
