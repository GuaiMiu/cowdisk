export type SetupStatusOut = {
  installed: boolean
  phase: 'PENDING' | 'RUNNING' | 'FAILED' | 'DONE'
  message?: string | null
  updated_at?: string | null
}

export type PublicConfigOut = {
  site_name: string
  site_logo_url?: string
  site_favicon_url?: string
  login_background_url?: string
  theme_image_url?: string
}

export type SetupDefaultsOut = {
  app_name: string
  database_url: string
  superuser_name: string
  superuser_mail: string
  allow_register: boolean
  redis_enable: boolean
  redis_host: string
  redis_port: number
  redis_auth_mode: 'none' | 'password' | 'username_password'
  redis_username: string
  redis_db: number
  storage_path: string
}

export type SetupPayload = {
  database_url: string
  app_name?: string | null
  superuser_name: string
  superuser_password: string
  superuser_mail: string
  allow_register?: boolean
  redis_enable?: boolean
  redis_auth_mode?: 'none' | 'password' | 'username_password' | null
  redis_host?: string | null
  redis_port?: number | null
  redis_username?: string | null
  redis_password?: string | null
  redis_db?: number | null
  storage_path: string
}

export type SetupCheckOut = {
  ok: boolean
  message: string
  skipped?: boolean
}

export type SetupResultOut = {
  env_path: string
  system: SetupCheckOut
  database: SetupCheckOut
  superuser: SetupCheckOut
  redis: SetupCheckOut
}

export type SetupProgressItem = {
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  message: string
  skipped?: boolean
}

export type SetupProgressOut = {
  steps: Record<string, SetupProgressItem>
}
