import { request } from '@/api/request'
import type { MenuAddIn, MenuEditIn, MenusDeleteIn, MenuOut } from '@/types/menu'
import type { RoleAddIn, RoleEditIn, RolesDeleteIn, RoleOut } from '@/types/role'
import type { UserAddIn, UserEditIn, UsersDeleteIn } from '@/types/user'
import type { UserOut } from '@/types/auth'
import type { CursorPageResult } from '@/types/pagination'

export const getUserList = (params?: { cursor?: string | null; size?: number }) =>
  request<CursorPageResult<UserOut>>({
    url: '/api/v1/admin/users',
    method: 'GET',
    params,
  })

export const getUserDetail = (userId: number) =>
  request<UserOut>({
    url: `/api/v1/admin/users/${userId}`,
    method: 'GET',
  })

export const addUser = (payload: UserAddIn) =>
  request<UserOut>({
    url: '/api/v1/admin/users',
    method: 'POST',
    data: payload,
  })

export const editUser = (payload: UserEditIn) =>
  request<UserOut>({
    url: `/api/v1/admin/users/${payload.id}`,
    method: 'PATCH',
    data: payload,
  })

export const deleteUser = (userId: number) =>
  request<UsersDeleteIn>({
    url: `/api/v1/admin/users/${userId}`,
    method: 'DELETE',
  })

export const deleteUsers = (payload: UsersDeleteIn) =>
  request<UsersDeleteIn>({
    url: '/api/v1/admin/users',
    method: 'DELETE',
    data: payload,
  })

export const getRoleList = (params?: { cursor?: string | null; size?: number }) =>
  request<CursorPageResult<RoleOut>>({
    url: '/api/v1/admin/roles',
    method: 'GET',
    params,
  })

export const getRoleDetail = (roleId: number) =>
  request<RoleOut>({
    url: `/api/v1/admin/roles/${roleId}`,
    method: 'GET',
  })

export const addRole = (payload: RoleAddIn) =>
  request<RoleOut>({
    url: '/api/v1/admin/roles',
    method: 'POST',
    data: payload,
  })

export const editRole = (payload: RoleEditIn) =>
  request<RoleOut>({
    url: `/api/v1/admin/roles/${payload.id}`,
    method: 'PATCH',
    data: payload,
  })

export const deleteRole = (roleId: number) =>
  request<RolesDeleteIn>({
    url: `/api/v1/admin/roles/${roleId}`,
    method: 'DELETE',
  })

export const deleteRoles = (payload: RolesDeleteIn) =>
  request<RolesDeleteIn>({
    url: '/api/v1/admin/roles',
    method: 'DELETE',
    data: payload,
  })

export const getMenuList = (params?: { cursor?: string | null; size?: number }) =>
  request<CursorPageResult<MenuOut>>({
    url: '/api/v1/admin/menus',
    method: 'GET',
    params,
  })

export const getMenuDetail = (menuId: number) =>
  request<MenuOut>({
    url: `/api/v1/admin/menus/${menuId}`,
    method: 'GET',
  })

export const addMenu = (payload: MenuAddIn) =>
  request<MenuOut>({
    url: '/api/v1/admin/menus',
    method: 'POST',
    data: payload,
  })

export const editMenu = (payload: MenuEditIn) =>
  request<MenuOut>({
    url: `/api/v1/admin/menus/${payload.id}`,
    method: 'PATCH',
    data: payload,
  })

export const deleteMenu = (menuId: number) =>
  request<MenusDeleteIn>({
    url: `/api/v1/admin/menus/${menuId}`,
    method: 'DELETE',
  })

export const deleteMenus = (payload: MenusDeleteIn) =>
  request<MenusDeleteIn>({
    url: '/api/v1/admin/menus',
    method: 'DELETE',
    data: payload,
  })
