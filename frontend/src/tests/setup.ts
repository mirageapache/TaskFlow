/**
 * Vitest 全域 setup：每個測試前重置共享狀態，避免測試間互相污染。
 *
 * 重置項目：
 * - Pinia：避免 store 狀態跨測試殘留
 * - localStorage：避免上個測試寫入的 token 影響下個測試
 * - vi.clearAllMocks：避免 mock 計數累計
 */
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})
