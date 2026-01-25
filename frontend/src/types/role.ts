import type { MenuOut } from './menu'

export type RoleOut = {
  id?: number
  name?: string | null
  permission_char?: string | null
  status?: boolean | null
  create_by?: string | null
  create_time?: string | null
  update_by?: string | null
  update_time?: string | null
  description?: string | null
  menus?: MenuOut[] | null
}

export type RolesOut = {
  items: RoleOut[]
  total: number
  page: number
  size: number
  pages: number
}

export type RoleAddIn = {
  name: string
  permission_char?: string | null
  status?: boolean
  description?: string | null
  menus?: number[] | null
}

export type RoleEditIn = {
  id?: number
  name?: string
  permission_char?: string | null
  status?: boolean
  description?: string | null
  menus?: number[] | null
}

export type RolesDeleteIn = {
  ids?: number[] | null
}
