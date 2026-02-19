export type ConfigGroupKey =
  | 'system'
  | 'auth'
  | 'office'
  | 'storage'
  | 'upload'
  | 'preview'
  | 'download'
  | 'performance'
  | 'audit'
  | 'infra'

export type ConfigSpec = {
  key: string
  group?: ConfigGroupKey | string
  value: unknown
  default: unknown
  value_type: 'string' | 'int' | 'bool' | 'json'
  description?: string
  editable?: boolean
  source?: string
  rules?: {
    min?: number
    max?: number
    min_len?: number
    max_len?: number
    enum?: string[]
    regex?: string
  }
  is_secret?: boolean
}

export type AuditLogItem = {
  id?: number
  user_id?: number | null
  action: string
  resource_type?: string | null
  resource_id?: string | null
  path?: string | null
  ip?: string | null
  user_agent?: string | null
  status: string
  detail?: string | null
  created_at: string
}

export type AuditLogListOut = {
  total: number
  items: AuditLogItem[]
}
