<template>
  <div class="h-dvh flex flex-col bg-stone-50 dark:bg-stone-900 text-stone-800 dark:text-stone-100">
    <!-- TopBar：sticky 56px -->
    <header
      class="shrink-0 sticky top-0 z-[1100] h-14 bg-white dark:bg-stone-800 border-b border-stone-200 dark:border-stone-700 flex items-center px-4 lg:px-6"
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

    <div class="flex flex-1 min-h-0">
      <!-- Sidebar (desktop, collapsible) -->
      <aside
        data-test="sidebar"
        class="hidden lg:flex flex-col bg-white dark:bg-stone-800 border-r border-stone-200 dark:border-stone-700 transition-[width] duration-200"
        :class="sidebarCollapsed ? 'w-16' : 'w-60'"
      >
        <!-- 工作區選擇 + 收合按鈕 -->
        <div
          ref="workspaceDropdownRef"
          data-test="workspace-header"
          class="relative px-3 py-3 border-b border-stone-200 dark:border-stone-700 flex items-center gap-2"
          :class="sidebarCollapsed ? 'justify-center' : ''"
        >
          <button
            class="flex items-center gap-2 min-w-0 flex-1 rounded-md p-1 -m-1 hover:bg-stone-100 dark:hover:bg-stone-700 transition-colors"
            :title="sidebarCollapsed ? currentWorkspaceName : undefined"
            @click="sidebarCollapsed ? (sidebarCollapsed = false) : (workspaceDropdownOpen = !workspaceDropdownOpen)"
          >
            <span
              class="w-7 h-7 rounded-md bg-orange-100 dark:bg-orange-950/40 text-orange-600 inline-flex items-center justify-center shrink-0"
            >
              <i class="pi pi-th-large text-sm"></i>
            </span>
            <span
              v-if="!sidebarCollapsed"
              class="flex-1 text-sm font-medium text-stone-900 dark:text-stone-50 truncate text-left"
            >
              {{ currentWorkspaceName }}
            </span>
            <i
              v-if="!sidebarCollapsed"
              :class="['pi text-xs text-stone-400 shrink-0', workspaceDropdownOpen ? 'pi-angle-up' : 'pi-angle-down']"
            ></i>
          </button>

          <button
            v-if="!sidebarCollapsed"
            data-test="sidebar-toggle"
            class="p-1.5 rounded text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700 shrink-0"
            title="收合"
            aria-label="收合側邊選單"
            @click="sidebarCollapsed = true"
          >
            <i class="pi pi-angle-double-left text-sm"></i>
          </button>

          <!-- 工作區下拉選單 -->
          <div
            v-if="workspaceDropdownOpen && !sidebarCollapsed"
            class="absolute top-full left-2 right-2 z-50 mt-1 bg-white dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-lg shadow-lg py-1"
          >
            <button
              v-for="workspace in workspaceStore.list"
              :key="workspace.id"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-stone-50 dark:hover:bg-stone-700 transition-colors"
              :class="
                workspace.id === workspaceStore.currentWorkspaceId
                  ? 'text-orange-600 font-medium'
                  : 'text-stone-700 dark:text-stone-200'
              "
              @click="switchWorkspace(workspace.id)"
            >
              <i class="pi pi-th-large text-xs shrink-0"></i>
              <span class="flex-1 truncate text-left">{{ workspace.name }}</span>
              <i
                v-if="workspace.id === workspaceStore.currentWorkspaceId"
                class="pi pi-check text-xs shrink-0"
              ></i>
            </button>
            <div class="border-t border-stone-200 dark:border-stone-700 mt-1 pt-1">
              <RouterLink
                to="/workspaces"
                class="flex items-center gap-2 px-3 py-2 text-sm text-orange-600 hover:bg-stone-50 dark:hover:bg-stone-700 transition-colors"
                @click="workspaceDropdownOpen = false"
              >
                <i class="pi pi-plus text-xs"></i>
                <span>新增工作區</span>
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- 收合狀態下的展開按鈕 -->
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
          <!-- 上方一般導覽 -->
          <RouterLink
            v-for="item in topNavItems"
            :key="item.to"
            :to="item.to"
            :title="sidebarCollapsed ? item.label : undefined"
            class="flex items-center gap-3 p-2 rounded-lg text-sm font-medium text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700 transition-colors"
            active-class="!bg-orange-50 dark:!bg-orange-950/40 !text-orange-600"
          >
            <i :class="['pi', item.icon, 'text-base shrink-0']"></i>
            <span v-if="!sidebarCollapsed" class="truncate">{{ item.label }}</span>
          </RouterLink>

          <!-- 專案列表（可摺疊） -->
          <div>
            <button
              :title="sidebarCollapsed ? '專案列表' : undefined"
              class="group w-full flex items-center gap-3 p-2 rounded-lg text-sm font-medium text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700 transition-colors"
              @click="toggleProjects"
            >
              <i class="pi pi-folder text-base shrink-0 group-hover:hidden"></i>
              <i
                class="pi pi-angle-right text-base shrink-0 hidden group-hover:block transition-transform duration-200"
                :class="projectsOpen ? 'rotate-90' : ''"
              ></i>
              <span v-if="!sidebarCollapsed" class="flex-1 truncate text-left">專案列表</span>
            </button>

            <Transition name="fade">
              <div v-if="projectsOpen && !sidebarCollapsed" class="mt-1 space-y-0.5">
                <div
                  v-if="projectStore.loading"
                  class="flex items-center gap-2 pl-7 pr-2 py-1.5 text-xs text-stone-400"
                >
                  <i class="pi pi-spinner pi-spin text-xs"></i>
                  <span>載入中…</span>
                </div>
                <div
                  v-else-if="!workspaceStore.currentWorkspaceId"
                  class="pl-7 pr-2 py-1.5 text-xs text-stone-400"
                >
                  請先選擇工作區
                </div>
                <div
                  v-else-if="currentProjects.length === 0"
                  class="pl-7 pr-2 py-1.5 text-xs text-stone-400"
                >
                  此工作區尚無專案
                </div>
                <RouterLink
                  v-for="project in currentProjects"
                  :key="project.id"
                  :to="`/project/${project.id}/board`"
                  class="flex items-center gap-2 pl-7 pr-2 py-1.5 rounded-md text-xs font-medium text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-700 transition-colors"
                  active-class="!bg-orange-50 dark:!bg-orange-950/40 !text-orange-600"
                >
                  <span
                    class="w-2 h-2 rounded-full shrink-0"
                    :style="{ backgroundColor: project.color || '#f97316' }"
                  ></span>
                  <span class="truncate">{{ project.name }}</span>
                </RouterLink>
              </div>
            </Transition>
          </div>

          <!-- 下方一般導覽 -->
          <RouterLink
            v-for="item in bottomNavItems"
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
      <Transition name="drawer">
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
              class="h-14 flex items-center px-4 border-b border-stone-200 dark:border-stone-700 gap-2"
            >
              <i class="pi pi-th-large text-orange-500 shrink-0"></i>
              <div class="min-w-0">
                <div class="font-bold text-sm truncate">{{ currentWorkspaceName }}</div>
              </div>
            </div>
            <nav class="p-3 space-y-1">
              <RouterLink
                v-for="item in topNavItems"
                :key="item.to"
                :to="item.to"
                class="flex items-center gap-3 p-2 rounded-lg text-sm font-medium text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700"
                active-class="!bg-orange-50 dark:!bg-orange-950/40 !text-orange-600"
                @click="mobileNavOpen = false"
              >
                <i :class="['pi', item.icon, 'text-base']"></i>
                <span>{{ item.label }}</span>
              </RouterLink>

              <!-- 行動版專案列表（可摺疊） -->
              <div>
                <button
                  class="w-full flex items-center gap-3 p-2 rounded-lg text-sm font-medium text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700"
                  @click="projectsOpen = !projectsOpen"
                >
                  <i class="pi pi-folder text-base"></i>
                  <span class="flex-1 text-left">專案列表</span>
                  <i
                    class="pi pi-angle-right text-xs text-stone-400 transition-transform duration-200"
                    :class="projectsOpen ? 'rotate-90' : ''"
                  ></i>
                </button>
                <div v-if="projectsOpen" class="mt-1 space-y-0.5">
                  <div
                    v-if="currentProjects.length === 0"
                    class="pl-7 py-1.5 text-xs text-stone-400"
                  >
                    此工作區尚無專案
                  </div>
                  <RouterLink
                    v-for="project in currentProjects"
                    :key="project.id"
                    :to="`/project/${project.id}/board`"
                    class="flex items-center gap-2 pl-7 pr-2 py-1.5 rounded-md text-xs font-medium text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-700"
                    active-class="!bg-orange-50 dark:!bg-orange-950/40 !text-orange-600"
                    @click="mobileNavOpen = false"
                  >
                    <span
                      class="w-2 h-2 rounded-full shrink-0"
                      :style="{ backgroundColor: project.color || '#f97316' }"
                    ></span>
                    <span class="truncate">{{ project.name }}</span>
                  </RouterLink>
                </div>
              </div>

              <RouterLink
                v-for="item in bottomNavItems"
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
      </Transition>

      <!-- Main content slot -->
      <main class="flex-1 min-w-0 min-h-0 overflow-y-auto">
        <div class="max-w-screen-xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 min-h-full flex flex-col">
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
 * - Sidebar：桌面 240px / 收合 64px；工作區下拉選單；專案列表可摺疊；行動版改為 Drawer
 * - Content：max-w-screen-xl(1280px) mx-auto，py-6
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'

import { useWebSocket } from '@/composables/useWebSocket'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import { useProjectStore } from '@/stores/project'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Notification } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const projectStore = useProjectStore()
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
const workspaceDropdownOpen = ref(false)
const workspaceDropdownRef = ref<HTMLElement | null>(null)
const projectsOpen = ref(false)

const user = computed(() => authStore.user)
const userInitial = computed(() => user.value?.username?.[0]?.toUpperCase() ?? '?')
const currentWorkspaceName = computed(() => workspaceStore.currentWorkspace?.name ?? '選擇工作區')
const currentProjects = computed(() => {
  const wsId = workspaceStore.currentWorkspaceId
  if (!wsId) return []
  return projectStore.getByWorkspace(wsId)
})

const topNavItems = [{ to: '/dashboard', label: '儀表板', icon: 'pi-home' }]
const bottomNavItems = [
  { to: '/calendar', label: '行事曆', icon: 'pi-calendar' },
  { to: '/ai', label: 'AI 助理', icon: 'pi-sparkles' },
  { to: '/settings', label: '設定', icon: 'pi-cog' },
]

async function switchWorkspace(id: string) {
  workspaceStore.setCurrentWorkspace(id)
  workspaceDropdownOpen.value = false
  await projectStore.fetchByWorkspace(id).catch(() => {})
}

async function toggleProjects() {
  if (sidebarCollapsed.value) {
    sidebarCollapsed.value = false
  }
  projectsOpen.value = !projectsOpen.value
  if (projectsOpen.value && workspaceStore.currentWorkspaceId) {
    await projectStore.fetchByWorkspace(workspaceStore.currentWorkspaceId).catch(() => {})
  }
}

// 切換工作區後，若專案列表已開啟，自動重抓新工作區的專案
watch(
  () => workspaceStore.currentWorkspaceId,
  async (newId) => {
    if (newId && projectsOpen.value) {
      await projectStore.fetchByWorkspace(newId).catch(() => {})
    }
  },
)

async function handleLogout() {
  userMenuOpen.value = false
  try {
    await authStore.logout()
  } catch {
    // logout 內 finally 已清除前端 session，網路錯誤可忽略
  }
  await router.push('/login')
}

function handleDocClick(e: MouseEvent) {
  const target = e.target as Node | null
  if (userMenuOpen.value && userMenuRef.value && target && !userMenuRef.value.contains(target)) {
    userMenuOpen.value = false
  }
  if (
    workspaceDropdownOpen.value &&
    workspaceDropdownRef.value &&
    target &&
    !workspaceDropdownRef.value.contains(target)
  ) {
    workspaceDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocClick)

  workspaceStore.fetchAll().then(() => {
    const wsId = workspaceStore.currentWorkspaceId
    if (wsId) {
      projectStore.fetchByWorkspace(wsId).catch(() => {})
    }
  }).catch(() => {})

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

<style scoped>
/* backdrop fade */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.25s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

/* aside slide from left */
.drawer-enter-active :deep(aside),
.drawer-leave-active :deep(aside) {
  transition: transform 0.25s ease;
}
.drawer-enter-from :deep(aside),
.drawer-leave-to :deep(aside) {
  transform: translateX(-100%);
}

/* 專案列表 fade */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
