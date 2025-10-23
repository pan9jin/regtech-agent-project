import { createRouter, createWebHistory } from 'vue-router'
import AnalyzeView from '@/views/AnalyzeView.vue'
import ResultsView from '@/views/ResultsView.vue'
import DashboardView from '@/views/DashboardView.vue'

const routes = [
  {
    path: '/',
    redirect: '/analyze',
  },
  {
    path: '/analyze',
    name: 'analyze',
    component: AnalyzeView,
    meta: { title: '규제 분석' },
  },
  {
    path: '/results',
    name: 'results',
    component: ResultsView,
    meta: { title: '분석 결과' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: { title: '대시보드' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 페이지 제목 설정
router.beforeEach((to, from, next) => {
  const title = to.meta.title || '규제 준수 자동화 시스템'
  document.title = `${title} | RegTech Assistant`
  next()
})

export default router
