export type UserAddIn = {
  username: string
  nickname?: string | null
  mail?: string | null
  is_superuser?: boolean
  total_space?: number
  used_space?: number
  status?: boolean
  password: string
  roles?: number[] | null
}

export type UserEditIn = {
  id?: number
  username?: string
  nickname?: string | null
  mail?: string | null
  is_superuser?: boolean
  total_space?: number
  used_space?: number
  status?: boolean
  password?: string | null
  roles?: number[] | null
}

export type UsersDeleteIn = {
  ids?: number[] | null
}
