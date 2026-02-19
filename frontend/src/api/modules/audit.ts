import { downloadBlob, request } from '@/api/request'
import type { AuditLogListOut } from '@/types/config-center'

export const getAuditLogs = (params?: Record<string, unknown>) =>
  request<AuditLogListOut>({
    url: '/api/v1/system/audit/logs',
    method: 'GET',
    params,
  })

export const exportAuditLogs = (params?: Record<string, unknown>) =>
  downloadBlob({
    url: '/api/v1/system/audit/logs/export',
    method: 'GET',
    params,
  })

export const cleanupAuditLogs = () =>
  request<{ deleted: number }>({
    url: '/api/v1/system/audit/cleanup',
    method: 'POST',
  })
