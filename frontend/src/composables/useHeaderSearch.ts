import { ref, watch, type Ref } from 'vue'
import type { LocationQueryRaw, RouteLocationNormalizedLoaded, Router } from 'vue-router'

const normalizeQueryValue = (value: unknown) => {
  if (Array.isArray(value)) {
    return value[0] || ''
  }
  return typeof value === 'string' ? value : ''
}

export const getRouteSearchKeyword = (
  route: RouteLocationNormalizedLoaded,
  queryKey = 'q',
) => normalizeQueryValue(route.query[queryKey]).trim()

export const useHeaderSearchQuery = (options: {
  route: RouteLocationNormalizedLoaded
  router: Router
  enabled: Ref<boolean>
  queryKey?: string
}) => {
  const queryKey = options.queryKey || 'q'
  const modelValue = ref('')

  const syncFromRoute = () => {
    modelValue.value = normalizeQueryValue(options.route.query[queryKey])
  }

  const commit = async (raw: string) => {
    const value = raw.trim()
    const current = getRouteSearchKeyword(options.route, queryKey)
    if (value === current) {
      return
    }
    const nextQuery: LocationQueryRaw = { ...options.route.query }
    if (value) {
      nextQuery[queryKey] = value
    } else {
      delete nextQuery[queryKey]
    }
    await options.router.replace({ query: nextQuery })
  }

  watch(
    () => options.route.query[queryKey],
    () => {
      syncFromRoute()
    },
    { immediate: true },
  )

  watch(
    () => options.enabled.value,
    (enabled) => {
      if (!enabled) {
        return
      }
      syncFromRoute()
    },
    { immediate: true },
  )

  const submit = () => {
    if (!options.enabled.value) {
      return
    }
    void commit(modelValue.value)
  }

  return {
    modelValue,
    submit,
  }
}
