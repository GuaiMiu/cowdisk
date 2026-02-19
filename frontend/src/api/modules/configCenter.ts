import { request } from '@/api/request'
import type { ConfigGroupKey, ConfigSpec } from '@/types/config-center'

export const getConfigGroup = (group: ConfigGroupKey) =>
  request<{ items: ConfigSpec[] } | ConfigSpec[]>({
    url: '/api/v1/admin/system/config',
    method: 'GET',
    params: { group },
  })

export const updateConfigGroup = (
  _group: ConfigGroupKey,
  payload: { items: Array<{ key: string; value: unknown }> },
) => {
  return request({
    url: '/api/v1/admin/system/config/batch',
    method: 'PUT',
    data: payload,
  })
}
