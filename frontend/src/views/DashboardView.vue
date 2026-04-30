<template>
  <div>
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-50">
        {{ greeting }}<span v-if="user?.username">，{{ user.username }}</span> 👋
      </h1>
      <p class="mt-1 text-sm text-stone-600 dark:text-stone-400">
        歡迎回來，今天想推進哪個專案？
      </p>
    </div>

    <!-- 統計卡片（Phase 1 基礎，後續會引入即時計算） -->
    <div class="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
      <article
        data-test="stat-card"
        class="p-5 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-stone-500">待辦</span>
          <i class="pi pi-list text-stone-400"></i>
        </div>
        <div class="mt-3 text-3xl font-bold text-stone-900 dark:text-stone-50">—</div>
        <p class="mt-1 text-xs text-stone-500">尚未串接（Phase 2）</p>
      </article>

      <article
        data-test="stat-card"
        class="p-5 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-stone-500">本週到期</span>
          <i class="pi pi-calendar text-stone-400"></i>
        </div>
        <div class="mt-3 text-3xl font-bold text-stone-900 dark:text-stone-50">—</div>
        <p class="mt-1 text-xs text-stone-500">尚未串接（Phase 2）</p>
      </article>

      <article
        data-test="stat-card"
        data-card="workspaces"
        class="p-5 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-stone-500">工作區</span>
          <i class="pi pi-th-large text-orange-500"></i>
        </div>
        <div
          class="mt-3 text-3xl font-bold text-stone-900 dark:text-stone-50"
        >
          {{ workspaceStore.list.length }}
        </div>
        <p class="mt-1 text-xs text-stone-500">{{ workspaceStore.loaded ? '已載入' : '載入中…' }}</p>
      </article>

      <article
        data-test="stat-card"
        class="p-5 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-stone-500">完成率</span>
          <i class="pi pi-chart-line text-stone-400"></i>
        </div>
        <div class="mt-3 text-3xl font-bold text-stone-900 dark:text-stone-50">—</div>
        <p class="mt-1 text-xs text-stone-500">尚未串接（Phase 2）</p>
      </article>
    </div>

    <!-- 主要內容：左 8 / 右 4 -->
    <div class="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- 工作區捷徑 -->
      <section class="lg:col-span-8">
        <header class="flex items-center justify-between">
          <h2 class="text-xl font-semibold tracking-tight text-stone-900 dark:text-stone-50">
            你的工作區
          </h2>
          <RouterLink
            to="/workspaces"
            class="text-sm font-medium text-orange-600 hover:underline"
          >
            查看全部 →
          </RouterLink>
        </header>

        <div v-if="!workspaceStore.loaded" class="mt-4 text-stone-500 text-sm">
          <i class="pi pi-spinner pi-spin"></i> 載入中…
        </div>

        <div
          v-else-if="workspaceStore.list.length === 0"
          class="mt-4 p-6 rounded-xl border border-dashed border-stone-300 dark:border-stone-700 text-center"
        >
          <p class="text-sm text-stone-500 dark:text-stone-400">還沒有工作區</p>
          <RouterLink
            to="/workspaces"
            class="mt-3 inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium"
          >
            <i class="pi pi-plus"></i><span>建立第一個工作區</span>
          </RouterLink>
        </div>

        <ul v-else class="mt-4 space-y-2">
          <li v-for="ws in workspaceStore.list.slice(0, 5)" :key="ws.id">
            <RouterLink
              data-test="workspace-link"
              :to="`/workspaces/${ws.id}/projects`"
              class="flex items-center gap-3 p-4 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 hover:border-orange-500 hover:shadow-sm transition-all duration-150"
            >
              <span class="w-9 h-9 rounded-lg bg-orange-100 dark:bg-orange-950/40 text-orange-600 inline-flex items-center justify-center">
                <i class="pi pi-th-large"></i>
              </span>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-sm text-stone-900 dark:text-stone-50 truncate">
                  {{ ws.name }}
                </div>
                <div class="text-xs text-stone-500 truncate">{{ ws.description || '—' }}</div>
              </div>
              <i class="pi pi-arrow-right text-stone-400"></i>
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- 右側：Phase 2/3 placeholder -->
      <aside class="lg:col-span-4 space-y-4">
        <section
          class="p-5 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
        >
          <h3 class="text-sm font-semibold text-stone-900 dark:text-stone-50">
            <i class="pi pi-bell mr-1 text-stone-400"></i>通知
          </h3>
          <p class="mt-3 text-xs text-stone-500">
            即時通知將在 Phase 2（WebSocket）開放。
          </p>
        </section>

        <section
          class="p-5 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
        >
          <h3 class="text-sm font-semibold text-stone-900 dark:text-stone-50">
            <i class="pi pi-calendar mr-1 text-stone-400"></i>月曆
          </h3>
          <p class="mt-3 text-xs text-stone-500">
            行程整合（FullCalendar）將在 Phase 2 開放。
          </p>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * DashboardView — Phase 1 基礎儀表板。
 *
 * 內容：
 * - 個人化問候（依時段）
 * - 4 張統計卡（目前只有「工作區」串接，其餘待 Phase 2）
 * - 工作區捷徑列表（前 5 個）
 * - 通知 / 月曆 placeholder（Phase 2/3）
 *
 * 規格：.doc/taskflow_layout_design.md §9.2
 */
import { computed, onMounted } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { useWorkspaceStore } from '@/stores/workspace'

const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()

const user = computed(() => authStore.user)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 5) return '夜深了'
  if (h < 12) return '早安'
  if (h < 18) return '午安'
  return '晚安'
})

onMounted(() => {
  workspaceStore.fetchAll().catch(() => {})
})
</script>
