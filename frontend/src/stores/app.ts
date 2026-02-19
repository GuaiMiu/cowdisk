import { defineStore } from 'pinia'
import { getPublicConfig } from '@/api/modules/setup'

type AppState = {
  siteName: string
  siteLogoUrl: string
  siteFaviconUrl: string
  loginBackgroundUrl: string
  themeImageUrl: string
  runtimeLoaded: boolean
  runtimeLoading: boolean
}

const DEFAULT_SITE_NAME = 'CowDisk'

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    siteName: DEFAULT_SITE_NAME,
    siteLogoUrl: '',
    siteFaviconUrl: '',
    loginBackgroundUrl: '',
    themeImageUrl: '',
    runtimeLoaded: false,
    runtimeLoading: false,
  }),
  actions: {
    applyRuntimeTheme() {
      const root = document.documentElement
      if (this.loginBackgroundUrl) {
        root.style.setProperty('--runtime-login-bg-image', `url("${this.loginBackgroundUrl}")`)
      } else {
        root.style.removeProperty('--runtime-login-bg-image')
      }
      if (this.themeImageUrl) {
        root.style.setProperty('--runtime-theme-image', `url("${this.themeImageUrl}")`)
      } else {
        root.style.removeProperty('--runtime-theme-image')
      }

      const faviconHref = this.siteFaviconUrl || '/favicon.ico'
      let favicon = document.querySelector("link[rel='icon']") as HTMLLinkElement | null
      if (!favicon) {
        favicon = document.createElement('link')
        favicon.rel = 'icon'
        document.head.appendChild(favicon)
      }
      favicon.href = faviconHref
    },
    async initRuntimeConfig(force = false) {
      if (this.runtimeLoaded && !force) {
        return
      }
      if (this.runtimeLoading) {
        return
      }
      this.runtimeLoading = true
      try {
        const payload = await getPublicConfig()
        const siteName = (payload?.site_name || '').trim()
        this.siteName = siteName || DEFAULT_SITE_NAME
        this.siteLogoUrl = (payload?.site_logo_url || '').trim()
        this.siteFaviconUrl = (payload?.site_favicon_url || '').trim()
        this.loginBackgroundUrl = (payload?.login_background_url || '').trim()
        this.themeImageUrl = (payload?.theme_image_url || '').trim()
      } catch {
        this.siteName = DEFAULT_SITE_NAME
        this.siteLogoUrl = ''
        this.siteFaviconUrl = ''
        this.loginBackgroundUrl = ''
        this.themeImageUrl = ''
      } finally {
        this.applyRuntimeTheme()
        this.runtimeLoaded = true
        this.runtimeLoading = false
      }
    },
  },
})
