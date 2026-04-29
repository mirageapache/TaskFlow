<template>
  <div class="min-h-screen flex bg-stone-50 dark:bg-stone-900 text-stone-800 dark:text-stone-100">
    <!-- 左側品牌（桌面顯示，行動版隱藏） -->
    <aside
      class="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-orange-500 to-orange-700 p-12 items-center justify-center text-white"
    >
      <div class="max-w-md">
        <div class="inline-flex items-center gap-2">
          <i class="pi pi-th-large text-2xl"></i>
          <span class="text-2xl font-bold tracking-tight">TaskFlow</span>
        </div>
        <h2 class="mt-8 text-4xl font-bold tracking-tight leading-tight">
          讓任務管理<br />像在咖啡廳工作般舒適。
        </h2>
        <p class="mt-4 text-base text-white/85 leading-relaxed">
          團隊協作的任務管理工具 — 看板拖曳、留言、AI 助理排程，
          讓你的工作流程清晰且溫暖。
        </p>
      </div>
    </aside>

    <!-- 右側內容（slot） -->
    <main class="flex-1 flex items-center justify-center p-4 sm:p-8">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * AuthLayout — 認證流程（Login / Register / OAuth Callback）共用佈局。
 *
 * 桌面：左側暖橘漸層品牌面板 + 右側表單卡片（slot）
 * 行動版：品牌面板隱藏，只顯示表單
 *
 * 規格：.doc/taskflow_layout_design.md §9.1
 */
</script>
