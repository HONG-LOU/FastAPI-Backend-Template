import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: () => import('@/views/Chat.vue') },
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
  { path: '/register', name: 'register', component: () => import('@/views/Register.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const publicPages = new Set(['login', 'register'])
  if (!publicPages.has(to.name as string) && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router


