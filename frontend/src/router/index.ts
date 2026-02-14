import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import AdminLayout from '@/layouts/AdminLayout.vue'
import {
  ADMIN_FULL_ACCESS_USER,
} from '@/router/adminPaths'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/app',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/login/LoginView.vue'),
      meta: { titleKey: 'auth.login.title' },
    },
    {
      path: '/setup',
      name: 'setup',
      component: () => import('@/views/setup/SetupView.vue'),
      meta: { titleKey: 'pageTitle.setup' },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/login/RegisterView.vue'),
      meta: { titleKey: 'auth.register.title' },
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('@/views/login/ForgotPasswordView.vue'),
      meta: { titleKey: 'auth.forgot.title' },
    },
    {
      path: '/403',
      name: 'forbidden',
      component: () => import('@/views/403.vue'),
      meta: { titleKey: 'pageTitle.forbidden' },
    },
    {
      path: '/404',
      name: 'not-found',
      component: () => import('@/views/404.vue'),
      meta: { titleKey: 'pageTitle.notFound' },
    },
    {
      path: '/public/shares/:token',
      name: 'public-share',
      component: () => import('@/views/public/ShareView.vue'),
      meta: { titleKey: 'shares.title' },
    },
    {
      path: '/s/:token',
      name: 'public-share-short',
      component: () => import('@/views/public/ShareView.vue'),
      meta: { titleKey: 'shares.title' },
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
          meta: { requiresAuth: true, permissions: ['disk:file:view'], titleKey: 'layout.nav.files' },
        },
        {
          path: 'trash',
          name: 'app-trash',
          component: () => import('@/views/app/TrashView.vue'),
          meta: { requiresAuth: true, permissions: ['disk:trash:view'], titleKey: 'layout.nav.trash' },
        },
        {
          path: 'shares',
          name: 'app-shares',
          component: () => import('@/views/app/SharesView.vue'),
          meta: { requiresAuth: true, permissions: ['disk:share:view'], titleKey: 'layout.nav.shares' },
        },
        {
          path: 'settings',
          name: 'app-settings',
          component: () => import('@/views/app/SettingsView.vue'),
          meta: { requiresAuth: true, titleKey: 'settings.title' },
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
          redirect: ADMIN_FULL_ACCESS_USER,
        },
        {
          path: ':pathMatch(.*)*',
          name: 'admin-dynamic-entry',
          component: () => import('@/views/admin/AdminDynamicView.vue'),
          meta: { requiresAuth: true, isAdminDynamic: true },
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

