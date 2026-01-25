import type { Router } from 'vue-router'
import NProgress from 'nprogress'
import { useAuthStore } from '@/stores/auth'

const normalizePerms = (perms: unknown) => {
  if (!perms) {
    return []
  }
  if (Array.isArray(perms)) {
    return perms
  }
  if (typeof perms === 'string') {
    return [perms]
  }
  return []
}

export const setupRouterGuards = (router: Router) => {
  NProgress.configure({ showSpinner: false, trickleSpeed: 180, minimum: 0.08 })

  router.beforeEach(async (to, from) => {
    if (to.fullPath !== from.fullPath) {
      NProgress.start()
    }
    const authStore = useAuthStore()
    if (!to.meta.requiresAuth) {
      return true
    }

    if (!authStore.token) {
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      }
    }

    if (!authStore.me && !authStore.loading) {
      try {
        await authStore.bootstrap()
      } catch {
        await authStore.handleUnauthorized()
        return false
      }
    }

    const requiredPerms = normalizePerms(to.meta.permissions)
    if (requiredPerms.length && !authStore.hasAnyPerm(requiredPerms)) {
      return '/403'
    }

    return true
  })

  router.afterEach(() => {
    NProgress.done()
  })

  router.onError(() => {
    NProgress.done()
  })
}
