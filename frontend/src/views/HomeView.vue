<template>
  <div class="min-h-screen bg-surface-50 dark:bg-surface-950 p-8">
    <div class="max-w-2xl mx-auto">
      <h1 class="text-4xl font-bold text-surface-900 dark:text-surface-0">
        TaskFlow
      </h1>
      <p class="text-surface-600 dark:text-surface-300 mt-2">
        跨平台任務管理系統 — Phase 1 開發環境已啟動
      </p>

      <div class="mt-8 p-6 rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900">
        <h2 class="text-xl font-semibold text-surface-900 dark:text-surface-0">
          前後端連通狀態
        </h2>
        <div class="mt-4 space-y-2 text-surface-700 dark:text-surface-200">
          <p>
            Backend:
            <span :class="healthClass" class="font-mono">{{ backendText }}</span>
          </p>
          <p v-if="dbStatus">
            Database:
            <span :class="dbClass" class="font-mono">{{ dbStatus }}</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import client from '@/api/client'

type Status = 'loading' | 'ok' | 'offline'

const backend = ref<Status>('loading')
const dbStatus = ref<string>('')

const backendText = computed(() => {
  switch (backend.value) {
    case 'loading':
      return 'checking...'
    case 'ok':
      return 'connected'
    case 'offline':
      return 'offline'
  }
})

const healthClass = computed(() => ({
  'text-yellow-500': backend.value === 'loading',
  'text-green-500': backend.value === 'ok',
  'text-red-500': backend.value === 'offline',
}))

const dbClass = computed(() => ({
  'text-green-500': dbStatus.value === 'ok',
  'text-red-500': dbStatus.value === 'unavailable',
}))

onMounted(async () => {
  try {
    const { data } = await client.get('/health/')
    backend.value = 'ok'
    dbStatus.value = data.db
  } catch {
    backend.value = 'offline'
  }
})
</script>
