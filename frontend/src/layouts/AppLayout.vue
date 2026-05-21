<template>
  <div class="min-h-screen bg-stone-50 dark:bg-stone-900 text-stone-800 dark:text-stone-100">
    <!-- TopBar：sticky 56px -->
    <header
      class="sticky top-0 z-[1100] h-14 bg-white dark:bg-stone-800 border-b border-stone-200 dark:border-stone-700 flex items-center px-4 lg:px-6"
    >
      <button
        class="lg:hidden mr-2 -ml-2 p-2 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-700"
        aria-label="開啟側邊選單"
        @click="mobileNavOpen = true"
      >
        <i class="pi pi-bars"></i>
      </button>

      <RouterLink
        to="/dashboard"
        class="inline-flex items-center gap-2 text-lg font-bold text-stone-900 dark:text-stone-50"
      >
        <i class="pi pi-th-large text-orange-500 text-xl"></i>
        <span>TaskFlow</span>
      </RouterLink>

      <div class="ml-auto flex items-center gap-1">
        <button
          data-test="notification-bell"
          class="relative p-2 rounded-lg text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700"
          aria-label="通知"
        >
          <i class="pi pi-bell"></i>
          <span
            v-if="unreadCount > 0"
            data-test="notification-badge"
            class="absolute -top-0.5 -right-0.5 min-w-[1.125rem] h-[1.125rem] px-1 rounded-full bg-orange-500 text-white text-[10px] font-semibold inline-flex items-center justify-center"
          >
            {{ unreadCount > 99 ? '99+' : unreadCount }}
          </span>
        </button>

        <div ref="userMenuRef" class="relative">
          <button
            data-test="user-menu-toggle"
            class="ml-1 inline-flex items-center p-1 rounded-full hover:bg-stone-100 dark:hover:bg-stone-700"
            aria-label="使用者選單"
            @click="userMenuOpen = !userMenuOpen"
          >
            <span
              class="w-8 h-8 rounded-full bg-orange-500 text-white inline-flex items-center justify-center text-sm font-medium"
            >
              {{ userInitial }}
            </span>
          </button>
          <div
            v-if="userMenuOpen"
            class="absolute right-0 mt-2 w-56 bg-white dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-lg shadow-md py-1 z-[1100]"
          >
            <div class="px-3 py-2 border-b border-stone-200 dark:border-stone-700">
              <div class="text-sm font-medium text-stone-900 dark:text-stone-50">
                {{ user?.username ?? '使用者' }}
              </div>
              <div class="text-xs text-stone-500 dark:text-stone-400 truncate">
                {{ user?.email }}
              </div>
            </div>
            <RouterLink
              to="/settings"
              class="flex items-center gap-2 px-3 py-2 text-sm text-stone-700 dark:text-stone-200 hover:bg-stone-50 dark:hover:bg-stone-700"
              @click="userMenuOpen = false"
            >
              <i class="pi pi-cog"></i>
              <span>設定</span>
            </RouterLink>
            <button
              data-test="logout-btn"
              class="w-full inline-flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-stone-50 dark:hover:bg-stone-700"
              @click="handleLogout"
            >
              <i class="pi pi-sign-out"></i>
              <span>登出</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <div class="flex">
      <!-- Sidebar (desktop, collapsible, sticky 撐滿 viewport) -->
      <aside
        data-test="sidebar"
        class="hidden lg:flex flex-col sticky top-14 h-[calc(100vh-3.5rem)] bg-white dark:bg-stone-800 border-r border-stone-200 dark:border-stone-700 transition-[width] duration-200"
        :class="sidebarCollapsed ? 'w-16' : 'w-60'"
      >
        <!-- 工作區資訊 + 收合按鈕 -->
        <div
          data-test="workspace-header"
          class="px-3 py-3 border-b border-stone-200 dark:border-stone-700 flex items-center gap-2"
          :class="sidebarCollapsed ? 'justify-center' : ''"
        >
          <span
            class="w-7 h-7 rounded-md bg-orange-100 dark:bg-orange-950/40 text-orange-600 inline-flex items-center justify-center shrink-0"
          >
            <i class="pi pi-th-large text-sm"></i>
          </span>
          <span
            v-if="!sidebarCollapsed"
            class="flex-1 text-sm font-medium text-stone-900 dark:text-stone-50 truncate"
            :title="currentWorkspaceName"
          >
            {{ currentWorkspaceName }}
          </span>
          <button
            v-if="!sidebarCollapsed"
            data-test="sidebar-toggle"
            class="p-1.5 rounded text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700"
            title="收合"
            aria-label="收合側邊選單"
            @click="sidebarCollapsed = true"
          >
            <i class="pi pi-angle-double-left text-sm"></i>
          </button>
        </div>
        <!-- 收合狀態下的展開按鈕（占位於工作區圖示下方） -->
        <button
          v-if="sidebarCollapsed"
          data-test="sidebar-toggle"
          class="mx-2 mt-2 p-1.5 rounded text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700 inline-flex justify-center"
          title="展開"
          aria-label="展開側邊選單"
          @click="sidebarCollapsed = false"
        >
          <i class="pi pi-angle-double-right text-sm"></i>
        </button>

        <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            :title="sidebarCollapsed ? item.label : undefined"
            class="flex items-center gap-3 p-2 rounded-lg text-sm font-medium text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700 transition-colors"
            active-class="!bg-orange-50 dark:!bg-orange-950/40 !text-orange-600"
          >
            <i :class="['pi', item.icon, 'text-base shrink-0']"></i>
            <span v-if="!sidebarCollapsed" class="truncate">{{ item.label }}</span>
          </RouterLink>
        </nav>
      </aside>

      <!-- Mobile drawer -->
      <div
        v-if="mobileNavOpen"
        class="lg:hidden fixed inset-0 z-[1200] bg-black/40"
        @click="mobileNavOpen = false"
      >
        <aside
          class="absolute inset-y-0 left-0 w-64 bg-white dark:bg-stone-800 border-r border-stone-200 dark:border-stone-700"
          @click.stop
        >
          <div
            class="h-14 flex items-center px-4 border-b border-stone-200 dark:border-stone-700"
          >
            <i class="pi pi-th-large text-orange-500 mr-2"></i>
            <span class="font-bold">TaskFlow</span>
          </div>
          <nav class="p-3 space-y-1">
            <RouterLink
              v-for="item in navItems"
              :key="item.to"
              :to="item.to"
              class="flex items-center gap-3 p-2 rounded-lg text-sm font-medium text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700"
              active-class="!bg-orange-50 dark:!bg-orange-950/40 !text-orange-600"
              @click="mobileNavOpen = false"
            >
              <i :class="['pi', item.icon, 'text-base']"></i>
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
        </aside>
      </div>

      <!-- Main content slot -->
      <main class="flex-1 min-w-0">
        <div class="max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AppLayout — 已登入後的主版型（TopBar + Sidebar + Content）。
 *
 * 規格：.doc/taskflow_layout_design.md §5.3
 * - TopBar：56px sticky，logo + 通知 + 使用者選單
 * - Sidebar：桌面 240px / 收合 64px；行動版改為 Drawer
 * - Content：max-w-screen-xl(1280px) mx-auto，py-6
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'

import { useWebSocket } from '@/composables/useWebSocket'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Notification } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const notificationStore = useNotificationStore()
const toast = useToast()
const ws = useWebSocket()

const unreadCount = computed(() => notificationStore.unreadCount)

/** notif_type → Toast severity 對應；mention 醒目用 warn，其餘走 info。 */
const NOTIF_SEVERITY: Record<string, 'info' | 'warn' | 'success'> = {
  task_assigned: 'info',
  task_comment: 'info',
  task_status_changed: 'success',
  mention: 'warn',
  workspace_invite: 'info',
}

const sidebarCollapsed = ref(false)
const mobileNavOpen = ref(false)
const userMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

const user = computed(() => authStore.user)
const userInitial = computed(() => user.value?.username?.[0]?.toUpperCase() ?? '?')

/**
 * 目前工作區名稱：取 store 中第一個 workspace；尚未載入或為空時顯示 placeholder。
 * 後續若實作「使用者預設工作區」可改為讀 user.default_workspace_id 對應項目。
 */
const currentWorkspaceName = computed(() => workspaceStore.list[0]?.name ?? '個人工作區')

const navItems = [
  { to: '/dashboard', label: '儀表板', icon: 'pi-home' },
  { to: '/workspaces', label: '工作區', icon: 'pi-th-large' },
  { to: '/ai', label: 'AI 助理', icon: 'pi-sparkles' },
  { to: '/settings', label: '設定', icon: 'pi-cog' },
]

async function handleLogout() {
  userMenuOpen.value = false
  try {
    await authStore.logout()
  } catch {
    // logout 內 finally 已清除前端 session，網路錯誤可忽略
  }
  await router.push('/login')
}

// 點選單外部時自動關閉
function handleDocClick(e: MouseEvent) {
  if (!userMenuOpen.value) return
  const target = e.target as Node | null
  if (userMenuRef.value && target && !userMenuRef.value.contains(target)) {
    userMenuOpen.value = false
  }
}
onMounted(() => {
  document.addEventListener('click', handleDocClick)
  // 確保 sidebar 上的工作區名稱可顯示；錯誤交給 store.error，不阻塞 UI
  workspaceStore.fetchAll().catch(() => {})

  // 即時通知：WS 推送 → Pinia Store 更新 + Toast 顯示
  ws.on('notification', (msg) => {
    const notif = (msg as unknown as { data: Notification }).data
    notificationStore.pushNotification(notif)
    toast.add({
      severity: NOTIF_SEVERITY[notif.notif_type] ?? 'info',
      summary: notif.title,
      detail: notif.body,
      life: 4000,
    })
  })
  ws.on('unread_count', (msg) => {
    notificationStore.setUnreadCount((msg as unknown as { count: number }).count)
  })
  ws.connect()
})
onUnmounted(() => {
  document.removeEventListener('click', handleDocClick)
  ws.disconnect()
})
</script>
