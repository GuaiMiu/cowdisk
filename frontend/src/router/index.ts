import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import AdminLayout from '@/layouts/AdminLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/login/LoginView.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/login/RegisterView.vue'),
    },
    {
      path: '/403',
      name: 'forbidden',
      component: () => import('@/views/403.vue'),
    },
    {
      path: '/404',
      name: 'not-found',
      component: () => import('@/views/404.vue'),
    },
    {
      path: '/public/shares/:token',
      name: 'public-share',
      component: () => import('@/views/public/ShareView.vue'),
    },
    {
      path: '/app',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/app/files',
        },
        {
          path: 'files',
          name: 'app-files',
          component: () => import('@/views/app/FilesView.vue'),
          meta: { requiresAuth: true, permissions: ['disk:file:list'] },
        },
        {
          path: 'trash',
          name: 'app-trash',
          component: () => import('@/views/app/TrashView.vue'),
          meta: { requiresAuth: true, permissions: ['disk:file:delete'] },
        },
        {
          path: 'shares',
          name: 'app-shares',
          component: () => import('@/views/app/SharesView.vue'),
          meta: { requiresAuth: true, permissions: ['disk:file:download'] },
        },
        {
          path: 'settings',
          name: 'app-settings',
          component: () => import('@/views/app/SettingsView.vue'),
          meta: { requiresAuth: true },
        },
      ],
    },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/admin/system/user',
        },
        {
          path: 'system/user',
          name: 'admin-system-user',
          component: () => import('@/views/admin/system/UserView.vue'),
          meta: { requiresAuth: true, permissions: ['system:user:list'] },
        },
        {
          path: 'system/role',
          name: 'admin-system-role',
          component: () => import('@/views/admin/system/RoleView.vue'),
          meta: { requiresAuth: true, permissions: ['system:role:list'] },
        },
        {
          path: 'system/menu',
          name: 'admin-system-menu',
          component: () => import('@/views/admin/system/MenuView.vue'),
          meta: { requiresAuth: true, permissions: ['system:menu:list'] },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/404',
    },
  ],
})

export default router
