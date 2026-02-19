export type MonitorServiceStatus = 'up' | 'down' | 'degraded'

export type MonitorOnlineSession = {
  user_id: number
  username?: string | null
  session_id: string
  login_ip?: string | null
  user_agent?: string | null
  token_ttl_seconds?: number | null
}

export type ForceLogoutResult = {
  session_id: string
  user_id?: number | null
  success: boolean
}

export type MonitorOnlineUsers = {
  total_users: number
  total_sessions: number
  sessions: MonitorOnlineSession[]
}

export type MonitorService = {
  name: string
  status: MonitorServiceStatus
  latency_ms?: number | null
  detail?: string | null
}

export type MonitorServiceSummary = {
  total: number
  up: number
  down: number
  degraded: number
}

export type MonitorCpu = {
  usage_percent?: number | null
  logical_cores?: number | null
}

export type MonitorMemory = {
  total_bytes?: number | null
  used_bytes?: number | null
  available_bytes?: number | null
  usage_percent?: number | null
}

export type MonitorDisk = {
  path: string
  total_bytes?: number | null
  used_bytes?: number | null
  free_bytes?: number | null
  usage_percent?: number | null
  status: 'up' | 'down' | 'unknown'
}

export type MonitorServer = {
  hostname?: string | null
  os?: string | null
  os_release?: string | null
  machine?: string | null
  processor?: string | null
  app_start_time: string
}

export type MonitorPython = {
  status: string
  version?: string | null
  executable?: string | null
  implementation?: string | null
  process_id?: number | null
  process_cpu_percent?: number | null
}

export type SystemMonitorOverview = {
  generated_at: string
  app_uptime_seconds: number
  online_users: MonitorOnlineUsers
  cpu: MonitorCpu
  memory: MonitorMemory
  disk: MonitorDisk
  server: MonitorServer
  python: MonitorPython
  services: MonitorService[]
  services_summary: MonitorServiceSummary
}
