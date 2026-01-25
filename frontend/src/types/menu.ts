export type MenuOut = {
  id?: number
  name?: string
  route_name?: string | null
  pid?: number | null
  icon?: string | null
  type?: number | null
  permission_char?: string | null
  sort?: number | null
  redirect?: string | null
  router_path?: string | null
  keep_alive?: boolean
  component_path?: string | null
  status?: boolean
  is_frame?: boolean
  description?: string | null
  create_by?: string | null
  create_time?: string | null
  update_by?: string | null
  update_time?: string | null
}

export type MenuRoutersOut = MenuOut & {
  children?: MenuRoutersOut[] | null
}

export type MenusOut = {
  items: MenuOut[]
  total: number
  page: number
  size: number
  pages: number
}

export type MenuAddIn = Omit<MenuOut, 'id' | 'create_by' | 'create_time' | 'update_by' | 'update_time'>

export type MenuEditIn = MenuOut

export type MenusDeleteIn = {
  ids?: number[] | null
}
