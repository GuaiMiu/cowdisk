export type SetupStatusOut = {
  phase: 'PENDING' | 'RUNNING' | 'FAILED' | 'DONE'
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
  database_type: string
  database_host: string
  database_port: number
  database_user: string
  database_name: string
  database_url: string
  superuser_name: string
  superuser_mail: string
  allow_register: boolean
  redis_enable: boolean
  redis_host: string
  redis_port: number
  redis_db: number
  storage_path: string
}

export type SetupPayload = {
  database_type: string
  app_name?: string | null
  database_host?: string | null
  database_port?: number | null
  database_user?: string | null
  database_password?: string | null
  database_name?: string | null
  database_url?: string | null
  superuser_name: string
  superuser_password: string
  superuser_mail: string
  allow_register?: boolean
  redis_enable?: boolean
  redis_host?: string | null
  redis_port?: number | null
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
