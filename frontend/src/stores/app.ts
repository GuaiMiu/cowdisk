import { defineStore } from 'pinia'
import { getPublicConfig } from '@/api/modules/setup'

type AppState = {
  siteName: string
  siteLogoUrl: string
  siteFaviconUrl: string
  loginBackgroundUrl: string
  themeImageUrl: string
  officeEnabled: boolean
  runtimeLoaded: boolean
  runtimeLoading: boolean
}

const DEFAULT_SITE_NAME = 'CowDisk'
const RUNTIME_CACHE_KEY = 'cowdisk.runtime.config.v1'

type RuntimeCachePayload = {
  siteName: string
  siteLogoUrl: string
  siteFaviconUrl: string
  loginBackgroundUrl: string
  themeImageUrl: string
  officeEnabled: boolean
}

const readRuntimeCache = (): RuntimeCachePayload | null => {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    const raw = window.localStorage.getItem(RUNTIME_CACHE_KEY)
    if (!raw) {
      return null
    }
    const parsed = JSON.parse(raw) as Partial<RuntimeCachePayload> | null
    if (!parsed || typeof parsed !== 'object') {
      return null
    }
    return {
      siteName: typeof parsed.siteName === 'string' ? parsed.siteName : '',
      siteLogoUrl: typeof parsed.siteLogoUrl === 'string' ? parsed.siteLogoUrl : '',
      siteFaviconUrl: typeof parsed.siteFaviconUrl === 'string' ? parsed.siteFaviconUrl : '',
      loginBackgroundUrl:
        typeof parsed.loginBackgroundUrl === 'string' ? parsed.loginBackgroundUrl : '',
      themeImageUrl: typeof parsed.themeImageUrl === 'string' ? parsed.themeImageUrl : '',
      officeEnabled: typeof parsed.officeEnabled === 'boolean' ? parsed.officeEnabled : false,
    }
  } catch {
    return null
  }
}

const cachedRuntime = readRuntimeCache()

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    siteName: cachedRuntime?.siteName || DEFAULT_SITE_NAME,
    siteLogoUrl: cachedRuntime?.siteLogoUrl || '',
    siteFaviconUrl: cachedRuntime?.siteFaviconUrl || '',
    loginBackgroundUrl: cachedRuntime?.loginBackgroundUrl || '',
    themeImageUrl: cachedRuntime?.themeImageUrl || '',
    officeEnabled: cachedRuntime?.officeEnabled || false,
    runtimeLoaded: false,
    runtimeLoading: false,
  }),
  actions: {
    persistRuntimeCache() {
      if (typeof window === 'undefined') {
        return
      }
      const payload: RuntimeCachePayload = {
        siteName: this.siteName,
        siteLogoUrl: this.siteLogoUrl,
        siteFaviconUrl: this.siteFaviconUrl,
        loginBackgroundUrl: this.loginBackgroundUrl,
        themeImageUrl: this.themeImageUrl,
        officeEnabled: this.officeEnabled,
      }
      try {
        window.localStorage.setItem(RUNTIME_CACHE_KEY, JSON.stringify(payload))
      } catch {
        // Ignore write failures from private mode or quota limits.
      }
    },
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
        this.officeEnabled = !!payload?.office_enabled
        this.persistRuntimeCache()
      } catch {
        // Keep cached/runtime values when request fails.
      } finally {
        this.applyRuntimeTheme()
        this.runtimeLoaded = true
        this.runtimeLoading = false
      }
    },
  },
})
