import { computed, ref } from 'vue'

export type ThemeMode = 'system' | 'light' | 'dark'
type ResolvedTheme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'cowdisk.theme.mode'

const themeMode = ref<ThemeMode>('system')
const systemDark = ref(false)
let mediaQuery: MediaQueryList | null = null
let initialized = false

const readStoredMode = (): ThemeMode => {
  if (typeof window === 'undefined') {
    return 'system'
  }
  const value = window.localStorage.getItem(THEME_STORAGE_KEY)
  if (value === 'light' || value === 'dark' || value === 'system') {
    return value
  }
  return 'system'
}

const getResolvedTheme = (): ResolvedTheme =>
  themeMode.value === 'system' ? (systemDark.value ? 'dark' : 'light') : themeMode.value

const applyTheme = () => {
  if (typeof document === 'undefined') {
    return
  }
  document.documentElement.setAttribute('data-theme', getResolvedTheme())
}

const handleSystemChange = (event: MediaQueryListEvent) => {
  systemDark.value = event.matches
  if (themeMode.value === 'system') {
    applyTheme()
  }
}

export const initTheme = () => {
  if (initialized || typeof window === 'undefined') {
    return
  }
  initialized = true
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = mediaQuery.matches
  themeMode.value = readStoredMode()
  if (typeof mediaQuery.addEventListener === 'function') {
    mediaQuery.addEventListener('change', handleSystemChange)
  } else {
    mediaQuery.addListener(handleSystemChange)
  }
  applyTheme()
}

export const setThemeMode = (mode: ThemeMode) => {
  themeMode.value = mode
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode)
  }
  applyTheme()
}

export const useTheme = () => {
  initTheme()
  const resolvedTheme = computed<ResolvedTheme>(() => getResolvedTheme())
  return {
    themeMode,
    resolvedTheme,
    isDark: computed(() => resolvedTheme.value === 'dark'),
    setThemeMode,
  }
}

