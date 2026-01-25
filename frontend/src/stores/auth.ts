import { defineStore } from 'pinia'
import { login as loginApi, getMe, getPermissions, getRouters, logout as logoutApi } from '@/api/modules/auth'
import type { MenuRoutersOut } from '@/types/menu'
import type { UserOut } from '@/types/auth'
import router from '@/router'
import { useToastStore } from './toast'

type AuthState = {
  token: string | null
  me: UserOut | null
  permissions: Set<string>
  routers: MenuRoutersOut[]
  loading: boolean
}

const TOKEN_KEY = 'cowdisk_token'

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY),
    me: null,
    permissions: new Set(),
    routers: [],
    loading: false,
  }),
  actions: {
    async login(payload: { username: string; password: string }) {
      const toast = useToastStore()
      this.loading = true
      try {
        const tokenOut = await loginApi(payload)
        const token = tokenOut?.access_token
        if (!token) {
          throw new Error('登录失败')
        }
        this.token = token
        localStorage.setItem(TOKEN_KEY, token)
        await this.bootstrap()
      } catch (error) {
        toast.error('登录失败', error instanceof Error ? error.message : '请稍后重试')
        throw error
      } finally {
        this.loading = false
      }
    },
    async bootstrap() {
      this.loading = true
      try {
        const [me, permissions, routers] = await Promise.all([getMe(), getPermissions(), getRouters()])
        this.me = me
        this.permissions = new Set(Array.isArray(permissions) ? permissions : [])
        if (Array.isArray(routers)) {
          this.routers = routers
        } else if (routers && Object.keys(routers).length) {
          this.routers = [routers]
        } else {
          this.routers = []
        }
      } finally {
        this.loading = false
      }
    },
    async logout(options?: { redirect?: boolean; silent?: boolean }) {
      const toast = useToastStore()
      try {
        if (!options?.silent) {
          await logoutApi()
        }
      } catch (error) {
        if (!options?.silent) {
          toast.error('退出失败', error instanceof Error ? error.message : '请稍后重试')
        }
      } finally {
        this.token = null
        this.me = null
        this.permissions = new Set()
        this.routers = []
        localStorage.removeItem(TOKEN_KEY)
        if (options?.redirect !== false) {
          router.replace('/login')
        }
      }
    },
    handleUnauthorized() {
      return this.logout({ silent: true, redirect: true })
    },
    hasPerm(permission?: string) {
      if (!permission) {
        return false
      }
      if (this.me?.is_superuser) {
        return true
      }
      return this.permissions.has(permission)
    },
    hasAnyPerm(perms?: string[] | string) {
      if (!perms) {
        return false
      }
      if (this.me?.is_superuser) {
        return true
      }
      const list = Array.isArray(perms) ? perms : [perms]
      return list.some((perm) => this.permissions.has(perm))
    },
    landingPath() {
      const hasSystem = Array.from(this.permissions).some((perm) => perm.startsWith('system:'))
      return hasSystem ? '/admin' : '/app'
    },
  },
})
