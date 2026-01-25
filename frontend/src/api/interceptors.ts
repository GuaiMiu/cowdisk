import type { AxiosInstance } from 'axios'

type TokenGetter = () => string | null | undefined
type UnauthorizedHandler = () => void

let tokenGetter: TokenGetter | null = null
let unauthorizedHandler: UnauthorizedHandler | null = null

export const setTokenGetter = (getter: TokenGetter) => {
  tokenGetter = getter
}

export const setUnauthorizedHandler = (handler: UnauthorizedHandler) => {
  unauthorizedHandler = handler
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

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error?.response?.status === 401) {
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
