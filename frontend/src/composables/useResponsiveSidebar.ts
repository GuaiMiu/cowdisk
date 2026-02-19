import { onBeforeUnmount, onMounted, ref } from 'vue'

type ResponsiveSidebarOptions = {
  mobileQuery?: string
  compactQuery?: string
}

export const useResponsiveSidebar = (options: ResponsiveSidebarOptions = {}) => {
  const sidebarOpen = ref(true)
  let mobileQuery: MediaQueryList | null = null
  let compactQuery: MediaQueryList | null = null
  let viewportMode: 'mobile' | 'compact' | 'desktop' | null = null

  const getViewportMode = () => {
    if (mobileQuery?.matches) {
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
    syncSidebarWithViewport()
  }

  const handleNavItemClick = () => {
    if (mobileQuery?.matches) {
      sidebarOpen.value = false
    }
  }

  onMounted(() => {
    mobileQuery = window.matchMedia(options.mobileQuery ?? '(max-width: 768px)')
    compactQuery = window.matchMedia(options.compactQuery ?? '(max-width: 1440px)')
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
