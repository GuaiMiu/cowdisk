import { request } from '@/api/request'
import type { MenuAddIn, MenuEditIn, MenusOut, MenusDeleteIn, MenuOut } from '@/types/menu'
import type { RoleAddIn, RoleEditIn, RolesOut, RolesDeleteIn, RoleOut } from '@/types/role'
import type { UserAddIn, UserEditIn, UsersDeleteIn } from '@/types/user'
import type { UserOut } from '@/types/auth'

export const getUserList = (params?: { page?: number; size?: number }) =>
  request<{ items: UserOut[]; total: number; page: number; size: number; pages: number }>({
    url: '/api/v1/admin/system/user/list',
    method: 'GET',
    params,
  })

export const getUserDetail = (userId: number) =>
  request<UserOut>({
    url: `/api/v1/admin/system/user/${userId}`,
    method: 'GET',
  })

export const addUser = (payload: UserAddIn) =>
  request<UserOut>({
    url: '/api/v1/admin/system/user',
    method: 'POST',
    data: payload,
  })

export const editUser = (payload: UserEditIn) =>
  request<UserOut>({
    url: '/api/v1/admin/system/user',
    method: 'PUT',
    data: payload,
  })

export const deleteUser = (userId: number) =>
  request<UsersDeleteIn>({
    url: `/api/v1/admin/system/user/${userId}`,
    method: 'DELETE',
  })

export const deleteUsers = (payload: UsersDeleteIn) =>
  request<UsersDeleteIn>({
    url: '/api/v1/admin/system/user/delete',
    method: 'POST',
    data: payload,
  })

export const getRoleList = (params?: { page?: number; size?: number }) =>
  request<RolesOut>({
    url: '/api/v1/admin/system/role/list',
    method: 'GET',
    params,
  })

export const getRoleDetail = (roleId: number) =>
  request<RoleOut>({
    url: `/api/v1/admin/system/role/${roleId}`,
    method: 'GET',
  })

export const addRole = (payload: RoleAddIn) =>
  request<RoleOut>({
    url: '/api/v1/admin/system/role',
    method: 'POST',
    data: payload,
  })

export const editRole = (payload: RoleEditIn) =>
  request<RoleOut>({
    url: '/api/v1/admin/system/role',
    method: 'PUT',
    data: payload,
  })

export const deleteRole = (roleId: number) =>
  request<RolesDeleteIn>({
    url: `/api/v1/admin/system/role/${roleId}`,
    method: 'DELETE',
  })

export const deleteRoles = (payload: RolesDeleteIn) =>
  request<RolesDeleteIn>({
    url: '/api/v1/admin/system/role/delete',
    method: 'POST',
    data: payload,
  })

export const getMenuList = (params?: { page?: number; size?: number }) =>
  request<MenusOut>({
    url: '/api/v1/admin/system/menu/list',
    method: 'GET',
    params,
  })

export const getMenuDetail = (menuId: number) =>
  request<MenuOut>({
    url: `/api/v1/admin/system/menu/${menuId}`,
    method: 'GET',
  })

export const addMenu = (payload: MenuAddIn) =>
  request<MenuOut>({
    url: '/api/v1/admin/system/menu',
    method: 'POST',
    data: payload,
  })

export const editMenu = (payload: MenuEditIn) =>
  request<MenuOut>({
    url: '/api/v1/admin/system/menu',
    method: 'PUT',
    data: payload,
  })

export const deleteMenu = (menuId: number) =>
  request<MenusDeleteIn>({
    url: `/api/v1/admin/system/menu/${menuId}`,
    method: 'DELETE',
  })

export const deleteMenus = (payload: MenusDeleteIn) =>
  request<MenusDeleteIn>({
    url: '/api/v1/admin/system/menu/delete',
    method: 'POST',
    data: payload,
  })
