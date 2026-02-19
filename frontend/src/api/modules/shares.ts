import { downloadBlob, request } from '@/api/request'
import type {
  Share,
  ShareCreateIn,
  ShareListOut,
  ShareListQueryOut,
  SharePublicResult,
  ShareSaveIn,
  ShareUpdateIn,
  ShareUnlockIn,
} from '@/types/share'

export const createShare = (payload: ShareCreateIn) =>
  request<Share>({
    url: '/api/v1/me/shares',
    method: 'POST',
    data: payload,
  })

export const listShares = (params?: {
  keyword?: string
  status?: string
  page?: number
  size?: number
}) =>
  request<ShareListOut>({
    url: '/api/v1/me/shares',
    method: 'GET',
    params,
  })

export const batchUpdateShareStatus = (payload: { ids: string[]; status: number }) =>
  request<{ success: number; failed: string[] }>({
    url: '/api/v1/me/shares/batch/status',
    method: 'POST',
    data: payload,
  })

export const updateShare = (shareId: string, payload: ShareUpdateIn) =>
  request<Share>({
    url: `/api/v1/me/shares/${shareId}`,
    method: 'PUT',
    data: payload,
  })

export const batchDeleteShares = (payload: { ids: string[] }) =>
  request<{ success: number; failed: string[] }>({
    url: '/api/v1/me/shares/batch/delete',
    method: 'POST',
    data: payload,
  })

export const getPublicShare = (token: string, accessToken?: string) =>
  request<SharePublicResult>({
    url: `/api/v1/public/shares/${token}`,
    method: 'GET',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })

export const unlockShare = (token: string, payload: ShareUnlockIn) =>
  request<{ accessToken?: string; ok?: boolean }>({
    url: `/api/v1/public/shares/${token}/unlock`,
    method: 'POST',
    data: payload,
  })

export const listShareEntries = (
  token: string,
  params?: { parent_id?: number | null; cursor?: string; limit?: number },
  accessToken?: string,
) =>
  request<ShareListQueryOut>({
    url: `/api/v1/public/shares/${token}/entries`,
    method: 'GET',
    params,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })

export const getShareDownloadUrl = (
  token: string,
  params?: { file_id?: number | null },
  accessToken?: string,
) => {
  const base = import.meta.env.VITE_API_BASE_URL || ''
  const url = new URL(`/api/v1/public/shares/${token}/content`, base || window.location.origin)
  if (params?.file_id) {
    url.searchParams.set('file_id', String(params.file_id))
  }
  url.searchParams.set('disposition', 'attachment')
  if (accessToken) {
    url.searchParams.set('accessToken', accessToken)
  }
  const href = url.toString()
  return base ? href : href.replace(window.location.origin, '')
}

export const previewShare = (token: string, params?: { file_id?: number | null }, accessToken?: string) =>
  downloadBlob({
    url: `/api/v1/public/shares/${token}/content`,
    method: 'GET',
    params: { ...params, disposition: 'inline' },
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })

export const saveShare = (token: string, payload: ShareSaveIn) =>
  request<boolean>({
    url: `/api/v1/public/shares/${token}/save`,
    method: 'POST',
    data: payload,
  })
