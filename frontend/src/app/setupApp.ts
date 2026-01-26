import type { App } from 'vue'
import { createPinia } from 'pinia'
import router from '@/router'
import { setupRouterGuards } from '@/router/guard'
import { setTokenGetter, setUnauthorizedHandler } from '@/api/interceptors'
import { useAuthStore } from '@/stores/auth'
import { registerPermissionDirective } from '@/directives/permission'
import Can from '@/components/common/Can.vue'
import { i18n, initI18n } from '@/i18n'

export async function setupApp(app: App) {
  await initI18n()
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)
  app.use(i18n)

  const authStore = useAuthStore(pinia)
  setTokenGetter(() => authStore.token)
  setUnauthorizedHandler(() => authStore.handleUnauthorized())

  registerPermissionDirective(app)
  app.component('Can', Can)
  setupRouterGuards(router)
}
