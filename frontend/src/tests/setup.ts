import { createPinia, setActivePinia } from 'pinia'
import { beforeEach } from 'vitest'

// 每個測試前重設 Pinia，避免 Store 狀態汙染
beforeEach(() => {
  setActivePinia(createPinia())
})
