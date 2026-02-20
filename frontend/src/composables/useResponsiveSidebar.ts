import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useBodyScrollLock } from './useBodyScrollLock'

type ResponsiveSidebarOptions = {
  mobileQuery?: string
  compactQuery?: string
}

export const useResponsiveSidebar = (options: ResponsiveSidebarOptions = {}) => {
  const sidebarOpen = ref(true)
  const isMobile = ref(false)
  let mobileQuery: MediaQueryList | null = null
  let compactQuery: MediaQueryList | null = null
  let viewportMode: 'mobile' | 'compact' | 'desktop' | null = null

  const getViewportMode = () => {
    if (isMobile.value) {
      return 'mobile' as const
    }
    if (compactQuery?.matches) {
      return 'compact' as const
    }
    return 'desktop' as const
  }

  const applyDefaultByMode = (mode: 'mobile' | 'compact' | 'desktop') => {
    sidebarOpen.value = mode === 'desktop'
  }

  const syncSidebarWithViewport = () => {
    const nextMode = getViewportMode()
    if (viewportMode === nextMode) {
      return
    }
    viewportMode = nextMode
    applyDefaultByMode(nextMode)
  }

  const handleViewportChange = () => {
    isMobile.value = !!mobileQuery?.matches
    syncSidebarWithViewport()
  }

  const handleNavItemClick = () => {
    if (isMobile.value) {
      sidebarOpen.value = false
    }
  }

  const shouldLockBody = computed(() => isMobile.value && sidebarOpen.value)
  useBodyScrollLock(shouldLockBody)

  onMounted(() => {
    mobileQuery = window.matchMedia(options.mobileQuery ?? '(max-width: 768px)')
    compactQuery = window.matchMedia(options.compactQuery ?? '(max-width: 1440px)')
    isMobile.value = mobileQuery.matches
    syncSidebarWithViewport()
    mobileQuery.addEventListener('change', handleViewportChange)
    compactQuery.addEventListener('change', handleViewportChange)
  })

  onBeforeUnmount(() => {
    if (mobileQuery) {
      mobileQuery.removeEventListener('change', handleViewportChange)
    }
    if (compactQuery) {
      compactQuery.removeEventListener('change', handleViewportChange)
    }
  })

  return {
    sidebarOpen,
    handleNavItemClick,
  }
}
