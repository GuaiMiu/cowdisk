import type { RoleOut } from './role'

export type TokenOut = {
  access_token: string
  token_type: string
}

export type UserOut = {
  id?: number
  username?: string
  nickname?: string | null
  mail?: string | null
  is_superuser?: boolean | null
  total_space?: number
  used_space?: number
  status?: boolean
  create_by?: string | null
  create_time?: string | null
  update_by?: string | null
  update_time?: string | null
  last_login_ip?: string | null
  last_login_time?: string | null
  avatar_path?: string | null
  roles?: RoleOut[] | null
}
