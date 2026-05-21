/**
 * Vue Router 設定 + Navigation Guard。
 *
 * 路由 meta：
 * - requiresAuth: boolean — 是否需要登入
 * - layout: 'auth' | 'app' — App.vue 用此決定外殼版型（.doc/taskflow_layout_design.md §9.1 / §5.3）
 *
 * Guard 行為：
 * 1. 首次導航時呼叫 `authStore.initAuth()` 驗證已存的 token
 * 2. 進入受保護頁但未登入 → 重導 /login（帶 redirect query 保留原目的地）
 * 3. 已登入時造訪公開頁（如 /login）→ 重導 /dashboard
 *
 * 規格：.doc/taskflow-frontend.md §4.5
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  // 公開頁面（AuthLayout）
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false, layout: 'auth' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresAuth: false, layout: 'auth' },
  },
  {
    path: '/oauth/callback',
    name: 'oauth-callback',
    component: () => import('@/views/OAuthCallbackView.vue'),
    meta: { requiresAuth: false, layout: 'auth' },
  },

  // 受保護頁面（AppLayout）
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },
  {
    path: '/workspaces',
    name: 'workspaces',
    component: () => import('@/views/WorkspaceListView.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },
  {
    path: '/workspaces/:id/projects',
    name: 'workspace-projects',
    component: () => import('@/views/ProjectListView.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },
  {
    path: '/project/:id/board',
    name: 'board',
    component: () => import('@/views/BoardView.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },
  {
    path: '/calendar',
    name: 'calendar',
    component: () => import('@/views/CalendarView.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },
  {
    path: '/ai',
    name: 'ai',
    component: () => import('@/views/AiCenterView.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },

  // Catch-all：未匹配路由轉到 dashboard（已登入）或 login（未登入由 guard 接手）
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 首次導航才執行 initAuth，後續請求由 store / interceptor 自行維護狀態
let authInitialized = false

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (!authInitialized) {
    await authStore.initAuth()
    authInitialized = true
  }

  // 受保護頁面但未登入：導向 login，並把原 path 存到 query 供登入後 redirect
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 已登入卻造訪登入 / 註冊頁：直接導 dashboard
  if (!to.meta.requiresAuth && authStore.isAuthenticated && to.path !== '/oauth/callback') {
    return { path: '/dashboard' }
  }
})

/** 測試用：重置 guard 狀態（讓 initAuth 能再次執行） */
export function _resetAuthInitialized() {
  authInitialized = false
}

export default router

/**
 * 對 vue-router 的 RouteMeta 進行 type augmentation，
 * 讓 to.meta.layout / to.meta.requiresAuth 在 TS 上有型別推斷。
 */
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    layout?: 'auth' | 'app'
  }
}
