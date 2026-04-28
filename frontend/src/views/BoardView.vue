<template>
  <div class="min-h-screen bg-surface-50 dark:bg-surface-950 p-8">
    <div class="max-w-7xl mx-auto">
      <h1 class="text-3xl font-bold text-surface-900 dark:text-surface-0">
        Project Board
      </h1>
      <p class="mt-2 text-surface-600 dark:text-surface-300">
        Project ID: <code>{{ projectId }}</code>
      </p>
      <p class="mt-1 text-surface-500 dark:text-surface-400">
        Phase 1 — 看板拖曳介面待實作
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

// Phase 1 後續迭代：vuedraggable 拖曳卡片、樂觀更新
const route = useRoute()
const projectId = computed(() => route.params.id as string)
</script>
