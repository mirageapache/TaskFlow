import { createRouter, createWebHistory } from 'vue-router'

// Phase 1 TDD 階段會擴充為 Login / Register / Dashboard / Board 等路由
// 並加上 Navigation Guard（詳見 .doc/taskflow-frontend.md §4.5）
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/HomeView.vue'),
    },
  ],
})

export default router
