<template>
  <component :is="layoutComponent">
    <RouterView />
  </component>
</template>

<script setup lang="ts">
/**
 * 應用根元件 — 依路由 meta.layout 動態決定外殼版型。
 *
 * - meta.layout === 'auth' → AuthLayout（登入 / 註冊 / OAuth Callback）
 * - 其餘 → AppLayout（已登入區）
 *
 * 規格：.doc/taskflow_layout_design.md §9.1（Auth）/ §5.3（App）
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

const route = useRoute()
const layoutComponent = computed(() =>
  route.meta.layout === 'auth' ? AuthLayout : AppLayout,
)
</script>
