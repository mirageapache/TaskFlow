/**
 * Vue Router 設定 + Navigation Guard。
 *
 * 路由分兩類：
 * - 公開頁（meta.requiresAuth = false）：login / register / oauth/callback
 * - 受保護頁（meta.requiresAuth = true）：dashboard / board / ai / settings
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
  // 公開頁面
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/oauth/callback',
    name: 'oauth-callback',
    component: () => import('@/views/OAuthCallbackView.vue'),
    meta: { requiresAuth: false },
  },

  // 受保護頁面
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/project/:id/board',
    name: 'board',
    component: () => import('@/views/BoardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/ai',
    name: 'ai',
    component: () => import('@/views/AiCenterView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true },
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
