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
    url: '/api/v1/shares',
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
    url: '/api/v1/shares',
    method: 'GET',
    params,
  })

export const revokeShare = (shareId: string) =>
  request<boolean>({
    url: `/api/v1/shares/${shareId}/revoke`,
    method: 'POST',
  })

export const updateShare = (shareId: string, payload: ShareUpdateIn) =>
  request<Share>({
    url: `/api/v1/shares/${shareId}`,
    method: 'PUT',
    data: payload,
  })

export const deleteShare = (shareId: string) =>
  request<boolean>({
    url: `/api/v1/shares/${shareId}`,
    method: 'DELETE',
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
  params?: { path?: string; cursor?: string; limit?: number },
  accessToken?: string,
) =>
  request<ShareListQueryOut>({
    url: `/api/v1/public/shares/${token}/list`,
    method: 'GET',
    params,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })

export const getShareDownloadUrl = (
  token: string,
  params?: { path?: string },
  accessToken?: string,
) => {
  const base = import.meta.env.VITE_API_BASE_URL || ''
  const url = new URL(`/api/v1/public/shares/${token}/download`, base || window.location.origin)
  if (params?.path) {
    url.searchParams.set('path', params.path)
  }
  if (accessToken) {
    url.searchParams.set('accessToken', accessToken)
  }
  const href = url.toString()
  return base ? href : href.replace(window.location.origin, '')
}

export const previewShare = (
  token: string,
  params?: { path?: string },
  accessToken?: string,
) =>
  downloadBlob({
    url: `/api/v1/public/shares/${token}/preview`,
    method: 'GET',
    params,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })

export const saveShare = (token: string, payload: ShareSaveIn) =>
  request<boolean>({
    url: `/api/v1/public/shares/${token}/save`,
    method: 'POST',
    data: payload,
  })
