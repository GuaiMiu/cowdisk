import { downloadBlob, request, requestForm } from '@/api/request'
import type { MenuRoutersOut } from '@/types/menu'
import type { TokenOut, UserOut } from '@/types/auth'

export const login = (payload: { username: string; password: string }) =>
  requestForm<TokenOut>({
    url: '/api/v1/auth/login',
    method: 'POST',
    data: payload,
  })

export const register = (payload: { username: string; password: string; mail: string }) =>
  request<UserOut>({
    url: '/api/v1/auth/register',
    method: 'POST',
    data: payload,
  })

export const getMe = () =>
  request<UserOut>({
    url: '/api/v1/auth/me',
    method: 'GET',
  })

export const getPermissions = () =>
  request<string[]>({
    url: '/api/v1/auth/permissions',
    method: 'GET',
  })

export const getRouters = () =>
  request<MenuRoutersOut>({
    url: '/api/v1/auth/routers',
    method: 'GET',
  })

export const logout = () =>
  request<boolean>({
    url: '/api/v1/auth/logout',
    method: 'GET',
  })

export const getAvatar = () =>
  downloadBlob({
    url: '/api/v1/user/avatar',
    method: 'GET',
  })
