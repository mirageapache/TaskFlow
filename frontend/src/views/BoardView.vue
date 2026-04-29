<template>
  <div>
    <h1 class="text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-50">
      專案看板
    </h1>
    <p class="mt-2 text-sm text-stone-600 dark:text-stone-400">
      Project ID: <code class="font-mono">{{ projectId }}</code>
    </p>
    <p class="mt-1 text-sm text-stone-500 dark:text-stone-500">
      Phase 1 — 看板拖曳介面待實作
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

// Phase 1 後續迭代：vuedraggable 拖曳卡片、樂觀更新
const route = useRoute()
const projectId = computed(() => route.params.id as string)
</script>
