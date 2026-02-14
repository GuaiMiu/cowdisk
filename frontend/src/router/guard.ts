import type { Router, RouteLocationNormalizedLoaded } from 'vue-router'
import NProgress from 'nprogress'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useSetupStore } from '@/stores/setup'
import { useMessage } from '@/stores/message'
import { buildFullPath } from '@/router/menu'
import { findAdminMenuByPath } from '@/router/adminDynamic'
import type { MenuRoutersOut } from '@/types/menu'
import { i18n } from '@/i18n'

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
let notifiedLoggedIn = false

const setDocumentTitle = (to: RouteLocationNormalizedLoaded) => {
  const appStore = useAppStore()
  const siteName = appStore.siteName || 'CowDisk'
  const dynamicTitle = typeof to.meta.dynamicTitle === 'string' ? to.meta.dynamicTitle : ''
  const titleKey = typeof to.meta.titleKey === 'string' ? to.meta.titleKey : ''
  const pageTitle = dynamicTitle || (titleKey ? i18n.global.t(titleKey) : '')
  document.title = pageTitle && pageTitle !== titleKey ? `${pageTitle} - ${siteName}` : siteName
}

const flattenMenus = (items: MenuRoutersOut[], parentPath = '', basePath = '') => {
  const result: Array<{ path: string; permission: string }> = []
  items.forEach((item) => {
    if (item.type === 2) {
      result.push({
        path: buildFullPath(item, parentPath, basePath),
        permission: item.permission_char || '',
      })
    }
    if (item.children?.length) {
      result.push(
        ...flattenMenus(item.children, buildFullPath(item, parentPath, basePath), basePath),
      )
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
    const setupStore = useSetupStore()
    if (!setupStore.checked && !setupStore.loading) {
      await setupStore.fetchStatus()
    }
    if (setupStore.phase !== 'DONE' && to.path !== '/setup') {
      return '/setup'
    }
    if (setupStore.phase === 'DONE' && to.path === '/setup') {
      return authStore.token ? authStore.landingPath() : '/login'
    }
    if (!authStore.token) {
      notifiedLoggedIn = false
    }
    if (!to.meta.requiresAuth) {
      if (to.path === '/login' && authStore.token) {
        const message = useMessage()
        if (!notifiedLoggedIn) {
          message.info(i18n.global.t('auth.toasts.alreadyLoggedIn'))
          notifiedLoggedIn = true
        }
        return authStore.landingPath()
      }
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

    const toMeta = to.meta as Record<string, unknown>
    delete toMeta.dynamicTitle

    let requiredPerms = normalizePerms(to.meta.permissions)
    if (isAdminRoute(to.path) && to.path !== '/admin') {
      const matchedMenu = findAdminMenuByPath(to.path, authStore.routers)
      if (!matchedMenu) {
        return '/404'
      }
      toMeta.dynamicTitle = matchedMenu.name || ''
      if (!requiredPerms.length) {
        requiredPerms = normalizePerms(matchedMenu.permission)
      }
    }

    if (requiredPerms.length && !authStore.hasAnyPerm(requiredPerms)) {
      if (isAdminRoute(to.path)) {
        const candidates = flattenMenus(authStore.routers, '', '/admin')
        const fallback = candidates.find(({ path, permission }) => {
          if (!path || path === to.path) {
            return false
          }
          return !permission || authStore.hasPerm(permission)
        })
        if (fallback) {
          return fallback.path
        }
      }
      return '/403'
    }

    return true
  })

  router.afterEach((to) => {
    setDocumentTitle(to)
    NProgress.done()
  })

  router.onError(() => {
    NProgress.done()
  })
}
