import type { Router } from 'vue-router'
import NProgress from 'nprogress'
import { useAuthStore } from '@/stores/auth'
import { buildFullPath } from '@/router/menu'
import type { MenuRoutersOut } from '@/types/menu'

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

const isAdminRoute = (path: string) => path === '/admin' || path.startsWith('/admin/')

const flattenMenus = (items: MenuRoutersOut[], parentPath = '', basePath = '') => {
  const result: string[] = []
  items.forEach((item) => {
    if (item.type === 2) {
      result.push(buildFullPath(item, parentPath, basePath))
    }
    if (item.children?.length) {
      result.push(...flattenMenus(item.children, buildFullPath(item, parentPath, basePath), basePath))
    }
  })
  return result
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
      if (isAdminRoute(to.path)) {
        const candidates = flattenMenus(authStore.routers, '', '/admin')
        const fallback = candidates.find((path) => path && path !== to.path)
        if (fallback) {
          return fallback
        }
      }
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
