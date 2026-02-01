import { downloadBlob, request } from '@/api/request'
import type { AxiosRequestConfig } from 'axios'
import type {
  DiskCompressIn,
  DiskDeleteBatchOut,
  DiskDownloadTokenIn,
  DiskEntry,
  DiskExtractIn,
  DiskJobStatus,
  DiskListOut,
  DiskMkdirIn,
  DiskRenameBatchOut,
  DiskRenameItem,
  DiskTrashBatchIdsIn,
  DiskTrashBatchOut,
  DiskTrashListOut,
  DiskUploadCompleteIn,
  DiskUploadInitIn,
  DiskUploadOut,
  DiskEditReadOut,
  DiskEditSaveIn,
} from '@/types/disk'

export const listDir = (path = '', options?: { signal?: AbortSignal }) =>
  request<DiskListOut>(
    {
      url: '/api/v1/user/disk/list',
      method: 'GET',
      params: { path },
    },
    options,
  )

export const mkdir = (payload: DiskMkdirIn) =>
  request<DiskEntry>({
    url: '/api/v1/user/disk/mkdir',
    method: 'POST',
    data: payload,
  })

const uploadTimeout = Number(import.meta.env.VITE_UPLOAD_TIMEOUT ?? 1800000)

export const uploadFiles = (
  payload: { items: Array<{ file: File; filename?: string }>; path?: string; overwrite?: boolean },
  options?: { onUploadProgress?: AxiosRequestConfig['onUploadProgress']; signal?: AbortSignal },
) => {
  const formData = new FormData()
  payload.items.forEach((item) => {
    if (item.filename) {
      formData.append('files', item.file, item.filename)
    } else {
      formData.append('files', item.file)
    }
  })
  formData.append('path', payload.path ?? '')
  formData.append('overwrite', String(payload.overwrite ?? false))
  return request<DiskUploadOut>(
    {
      url: '/api/v1/user/disk/upload',
      method: 'POST',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: uploadTimeout,
    },
    {
      onUploadProgress: options?.onUploadProgress,
      signal: options?.signal,
    },
  )
}

export const initChunkUpload = (payload: DiskUploadInitIn, options?: { signal?: AbortSignal }) =>
  request<{ upload_id: string }>(
    {
      url: '/api/v1/user/disk/upload/init',
      method: 'POST',
      data: payload,
    },
    options,
  )

export const uploadChunk = (
  payload: { upload_id: string; index: number; chunk: Blob },
  options?: { signal?: AbortSignal },
) => {
  const formData = new FormData()
  formData.append('upload_id', payload.upload_id)
  formData.append('index', String(payload.index))
  formData.append('chunk', payload.chunk)
  return request<boolean>(
    {
      url: '/api/v1/user/disk/upload/chunk',
      method: 'POST',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
    },
    options,
  )
}

export const completeChunkUpload = (
  payload: DiskUploadCompleteIn,
  options?: { signal?: AbortSignal },
) =>
  request<DiskEntry>(
    {
      url: '/api/v1/user/disk/upload/complete',
      method: 'POST',
      data: payload,
    },
    options,
  )

export const cancelChunkUpload = (
  payload: { upload_id: string },
  options?: { signal?: AbortSignal },
) =>
  request<boolean>(
    {
      url: '/api/v1/user/disk/upload/cancel',
      method: 'POST',
      data: payload,
    },
    options,
  )

export const deletePaths = (paths: string[], recursive = false) =>
  request<DiskDeleteBatchOut>({
    url: '/api/v1/user/disk',
    method: 'DELETE',
    data: { paths, recursive },
  })

export const renamePaths = (items: DiskRenameItem[]) =>
  request<DiskRenameBatchOut>({
    url: '/api/v1/user/disk/rename',
    method: 'POST',
    data: { items },
  })

export const prepareDownload = (payload: DiskMkdirIn) =>
  request<{ job_id: string }>({
    url: '/api/v1/user/disk/download/prepare',
    method: 'POST',
    data: payload,
  })

export const downloadStatus = (jobId: string) =>
  request<DiskJobStatus>({
    url: '/api/v1/user/disk/download/status',
    method: 'GET',
    params: { job_id: jobId },
  })

export const createDownloadToken = (payload: DiskDownloadTokenIn) =>
  request<{ token: string }>({
    url: '/api/v1/user/disk/download/token',
    method: 'POST',
    data: payload,
  })

const getBaseUrl = () => import.meta.env.VITE_API_BASE_URL || window.location.origin

const buildUrl = (path: string, params: Record<string, string>) => {
  const url = new URL(path, getBaseUrl())
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value))
  return url.toString()
}

export const getDownloadFileUrl = (token: string) =>
  buildUrl('/api/v1/user/disk/download', { token })

export const getDownloadJobUrl = (token: string) =>
  buildUrl('/api/v1/user/disk/download/job', { token })

export const getPreviewFileUrl = (token: string) => buildUrl('/api/v1/user/disk/preview', { token })

export const previewFileByToken = (token: string) =>
  downloadBlob({
    url: '/api/v1/user/disk/preview',
    method: 'GET',
    params: { token },
  })

export const listTrash = () =>
  request<DiskTrashListOut>({
    url: '/api/v1/user/disk/trash',
    method: 'GET',
  })

export const batchRestoreTrash = (payload: DiskTrashBatchIdsIn) =>
  request<DiskTrashBatchOut>({
    url: '/api/v1/user/disk/trash/batch/restore',
    method: 'POST',
    data: payload,
  })

export const batchDeleteTrash = (payload: DiskTrashBatchIdsIn) =>
  request<DiskTrashBatchOut>({
    url: '/api/v1/user/disk/trash/batch/delete',
    method: 'POST',
    data: payload,
  })

export const clearTrash = () =>
  request<{ cleared: number }>({
    url: '/api/v1/user/disk/trash/clear',
    method: 'DELETE',
  })

export const prepareCompress = (payload: DiskCompressIn) =>
  request<{ job_id: string }>({
    url: '/api/v1/user/disk/compress/prepare',
    method: 'POST',
    data: payload,
  })

export const compressStatus = (jobId: string) =>
  request<{ status?: string; message?: string }>({
    url: '/api/v1/user/disk/compress/status',
    method: 'GET',
    params: { job_id: jobId },
  })

export const prepareExtract = (payload: DiskExtractIn) =>
  request<{ job_id: string }>({
    url: '/api/v1/user/disk/extract/prepare',
    method: 'POST',
    data: payload,
  })

export const extractStatus = (jobId: string) =>
  request<{ status?: string; message?: string }>({
    url: '/api/v1/user/disk/extract/status',
    method: 'GET',
    params: { job_id: jobId },
  })

export const readEditFile = (path: string) =>
  request<DiskEditReadOut>({
    url: '/api/v1/user/disk/edit',
    method: 'GET',
    params: { path },
  })

export const saveEditFile = (payload: DiskEditSaveIn) =>
  request<DiskEntry>({
    url: '/api/v1/user/disk/edit',
    method: 'POST',
    data: payload,
  })
