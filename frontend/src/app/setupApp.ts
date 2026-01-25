import type { App } from 'vue'
import { createPinia } from 'pinia'
import router from '@/router'
import { setupRouterGuards } from '@/router/guard'
import { setTokenGetter, setUnauthorizedHandler } from '@/api/interceptors'
import { useAuthStore } from '@/stores/auth'
import { registerPermissionDirective } from '@/directives/permission'
import Can from '@/components/common/Can.vue'

export function setupApp(app: App) {
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)

  const authStore = useAuthStore(pinia)
  setTokenGetter(() => authStore.token)
  setUnauthorizedHandler(() => authStore.handleUnauthorized())

  registerPermissionDirective(app)
  app.component('Can', Can)
  setupRouterGuards(router)
}
