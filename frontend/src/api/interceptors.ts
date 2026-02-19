import type { AxiosInstance } from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'

type TokenGetter = () => string | null | undefined
type UnauthorizedHandler = () => void
type TokenRefresher = () => Promise<string | null>

let tokenGetter: TokenGetter | null = null
let unauthorizedHandler: UnauthorizedHandler | null = null
let tokenRefresher: TokenRefresher | null = null
let refreshPromise: Promise<string | null> | null = null

export const setTokenGetter = (getter: TokenGetter) => {
  tokenGetter = getter
}

export const setUnauthorizedHandler = (handler: UnauthorizedHandler) => {
  unauthorizedHandler = handler
}

export const setTokenRefresher = (refresher: TokenRefresher) => {
  tokenRefresher = refresher
}

const redirectToLogin = () => {
  const redirect = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = `/login?redirect=${redirect}`
}

export const setupInterceptors = (instance: AxiosInstance) => {
  instance.interceptors.request.use((config) => {
    const token = tokenGetter?.()
    if (token) {
      config.headers = config.headers ?? {}
      const headers = config.headers as Record<string, string>
      if (!headers.Authorization && !headers.authorization) {
        headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  })

  const refreshAccessToken = async () => {
    if (!tokenRefresher) {
      return null
    }
    if (!refreshPromise) {
      refreshPromise = tokenRefresher().finally(() => {
        refreshPromise = null
      })
    }
    return refreshPromise
  }

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const status = error?.response?.status
      const originalConfig = error?.config as
        | (InternalAxiosRequestConfig & { _retry?: boolean })
        | undefined
      const requestUrl = String(originalConfig?.url || '')
      const isAuthEndpoint =
        requestUrl.includes('/auth/login') ||
        requestUrl.includes('/auth/refresh-token') ||
        requestUrl.includes('/auth/logout')

      if (status === 401 && originalConfig && !originalConfig._retry && !isAuthEndpoint) {
        originalConfig._retry = true
        const nextToken = await refreshAccessToken()
        if (nextToken) {
          originalConfig.headers = originalConfig.headers ?? {}
          ;(originalConfig.headers as Record<string, string>).Authorization = `Bearer ${nextToken}`
          return instance.request(originalConfig)
        }
      }

      if (status === 401) {
        if (unauthorizedHandler) {
          unauthorizedHandler()
        } else {
          redirectToLogin()
        }
      }
      return Promise.reject(error)
    },
  )
}
