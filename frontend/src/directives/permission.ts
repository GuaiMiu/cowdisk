import type { App, DirectiveBinding } from 'vue'
import { useAuthStore } from '@/stores/auth'

type PermissionValue = string | string[]

const hasPermission = (value: PermissionValue, authStore: ReturnType<typeof useAuthStore>) => {
  if (Array.isArray(value)) {
    return authStore.hasAnyPerm(value)
  }
  return authStore.hasPerm(value)
}

const applyPermission = (el: HTMLElement, binding: DirectiveBinding<PermissionValue>) => {
  const authStore = useAuthStore()
  if (!binding.value) {
    return
  }
  if (!authStore.me && authStore.token) {
    return
  }
  const allowed = hasPermission(binding.value, authStore)
  if (allowed) {
    if (el.dataset.originalDisplay !== undefined) {
      el.style.display = el.dataset.originalDisplay
      delete el.dataset.originalDisplay
    }
    return
  }
  if (el.dataset.originalDisplay === undefined) {
    el.dataset.originalDisplay = el.style.display || ''
  }
  el.style.display = 'none'
}

export const registerPermissionDirective = (app: App) => {
  app.directive('permission', {
    mounted(el, binding) {
      applyPermission(el, binding)
    },
    updated(el, binding) {
      applyPermission(el, binding)
    },
  })
}
