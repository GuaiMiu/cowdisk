import type { App } from 'vue'
import { createPinia } from 'pinia'
import router from '@/router'
import { setupRouterGuards } from '@/router/guard'
import { setTokenGetter, setUnauthorizedHandler } from '@/api/interceptors'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { registerPermissionDirective } from '@/directives/permission'
import Can from '@/components/common/Can.vue'
import { i18n, initI18n } from '@/i18n'

export async function setupApp(app: App) {
  await initI18n()
  const pinia = createPinia()
  app.use(pinia)

  const appStore = useAppStore(pinia)
  const authStore = useAuthStore(pinia)
  await appStore.initRuntimeConfig()
  setTokenGetter(() => authStore.token)
  setUnauthorizedHandler(() => authStore.handleUnauthorized())

  setupRouterGuards(router)
  app.use(router)
  app.use(i18n)

  registerPermissionDirective(app)
  app.component('Can', Can)
}
