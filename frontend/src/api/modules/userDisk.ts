import { downloadBlob, request } from '@/api/request'
import type { AxiosRequestConfig } from 'axios'
import type {
  DiskCompressIn,
  DiskDeleteBatchOut,
  DiskEntry,
  DiskExtractIn,
  DiskListOut,
  DiskMkdirIn,
  DiskOfficeOpenOut,
  DiskMoveBody,
  DiskRenameBody,
  DiskSearchOut,
  DiskTrashBatchIdsIn,
  DiskTrashBatchOut,
  DiskTrashListOut,
  DiskUploadFinalizeIn,
  DiskUploadInitIn,
  DiskUploadInitOut,
  DiskUploadPolicyOut,
  DiskUploadStatusOut,
  DiskUploadOut,
  DiskEditReadOut,
  DiskEditSaveBody,
} from '@/types/disk'

export const listDir = (
  parent_id: number | null = null,
  options?: { signal?: AbortSignal; cursor?: number; limit?: number; order?: string },
) =>
  request<DiskListOut>(
    {
      url: '/api/v1/me/files',
      method: 'GET',
      params: {
        parent_id,
        cursor: options?.cursor ?? 0,
        limit: options?.limit ?? 200,
        order: options?.order ?? 'name',
      },
    },
    options,
  )

export const searchFiles = (
  keyword: string,
  options?: { signal?: AbortSignal; cursor?: number; limit?: number; order?: string },
) =>
  request<DiskSearchOut>(
    {
      url: '/api/v1/me/files/search',
      method: 'GET',
      params: {
        keyword,
        cursor: options?.cursor ?? 0,
        limit: options?.limit ?? 200,
        order: options?.order ?? 'name',
      },
    },
    options,
  )

export const mkdir = (payload: DiskMkdirIn) =>
  request<DiskEntry>({
    url: '/api/v1/me/files/dir',
    method: 'POST',
    data: payload,
  })

const uploadRequestTimeout = Number(import.meta.env.VITE_UPLOAD_TIMEOUT ?? 1800000)
const uploadChunkTimeout = Number(
  import.meta.env.VITE_UPLOAD_CHUNK_TIMEOUT ?? import.meta.env.VITE_UPLOAD_TIMEOUT ?? 1800000,
)

export const uploadFiles = (
  payload: {
    items: Array<{ file: File; filename?: string }>
    parent_id?: number | null
    name?: string | null
    overwrite?: boolean
  },
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
  if (payload.parent_id !== undefined && payload.parent_id !== null) {
    formData.append('parent_id', String(payload.parent_id))
  }
  if (payload.name) {
    formData.append('name', payload.name)
  }
  formData.append('overwrite', String(payload.overwrite ?? false))
  return request<DiskUploadOut>(
    {
      url: '/api/v1/me/files/upload',
      method: 'POST',
      data: formData,
      timeout: uploadRequestTimeout,
    },
    {
      onUploadProgress: options?.onUploadProgress,
      signal: options?.signal,
    },
  )
}

export const initChunkUpload = (payload: DiskUploadInitIn, options?: { signal?: AbortSignal }) =>
  request<DiskUploadInitOut>(
    {
      url: '/api/v1/me/uploads',
      method: 'POST',
      data: payload,
    },
    options,
  )

export const getUploadPolicy = (options?: { signal?: AbortSignal }) =>
  request<DiskUploadPolicyOut>(
    {
      url: '/api/v1/me/uploads/policy',
      method: 'GET',
    },
    options,
  )

export const uploadChunk = (
  payload: { upload_id: string; part_number: number; chunk: Blob },
  options?: { signal?: AbortSignal },
) => {
  const formData = new FormData()
  formData.append('chunk', payload.chunk)
  return request<boolean>(
    {
      url: `/api/v1/me/uploads/${payload.upload_id}/parts/${payload.part_number}`,
      method: 'PUT',
      data: formData,
      timeout: uploadChunkTimeout,
    },
    options,
  )
}

export const completeChunkUpload = (
  upload_id: string,
  payload: DiskUploadFinalizeIn,
  options?: { signal?: AbortSignal },
) =>
  request<DiskEntry>(
    {
      url: `/api/v1/me/uploads/${upload_id}/finalize`,
      method: 'POST',
      data: payload,
      timeout: uploadRequestTimeout,
    },
    options,
  )

export const cancelChunkUpload = (
  upload_id: string,
  options?: { signal?: AbortSignal },
) =>
  request<boolean>(
    {
      url: `/api/v1/me/uploads/${upload_id}`,
      method: 'DELETE',
      timeout: uploadRequestTimeout,
    },
    options,
  )

export const getUploadStatus = (upload_id: string, options?: { signal?: AbortSignal }) =>
  request<DiskUploadStatusOut>(
    {
      url: `/api/v1/me/uploads/${upload_id}`,
      method: 'GET',
      timeout: uploadRequestTimeout,
    },
    options,
  )

export const deleteFiles = (file_ids: number[]) =>
  request<DiskDeleteBatchOut>({
    url: '/api/v1/me/files',
    method: 'DELETE',
    data: { file_ids },
  })

export const renameFile = (file_id: number, payload: DiskRenameBody) =>
  request<DiskEntry>({
    url: `/api/v1/me/files/${file_id}`,
    method: 'PATCH',
    data: { name: payload.new_name },
  })

export const moveFile = (file_id: number, payload: DiskMoveBody) =>
  request<DiskEntry>({
    url: `/api/v1/me/files/${file_id}`,
    method: 'PATCH',
    data: {
      parentId: payload.target_parent_id,
      name: payload.new_name ?? undefined,
    },
  })

export const previewFile = (file_id: number) =>
  downloadBlob({
    url: `/api/v1/me/files/${file_id}/content`,
    method: 'GET',
    params: { disposition: 'inline' },
  })

export const downloadFile = (file_id: number) =>
  downloadBlob({
    url: `/api/v1/me/files/${file_id}/content`,
    method: 'GET',
    params: { disposition: 'attachment' },
  })

export const getDownloadUrl = (file_id: number) =>
  request<{ url: string; expires_in: number }>({
    url: `/api/v1/files/${file_id}/download-url`,
    method: 'POST',
  })

export const getOfficeOpenUrl = (file_id: number, lang?: string, mode: 'view' | 'edit' = 'view') =>
  request<DiskOfficeOpenOut>({
    url: `/api/v1/files/${file_id}/office-url`,
    method: 'POST',
    params: { ...(lang ? { lang } : {}), mode },
  })

export const listTrash = () =>
  request<DiskTrashListOut>({
    url: '/api/v1/me/trash',
    method: 'GET',
  })

export const batchRestoreTrash = (payload: DiskTrashBatchIdsIn) =>
  request<DiskTrashBatchOut>({
    url: '/api/v1/me/trash/batch/restore',
    method: 'POST',
    data: payload,
  })

export const batchDeleteTrash = (payload: DiskTrashBatchIdsIn) =>
  request<DiskTrashBatchOut>({
    url: '/api/v1/me/trash/batch/delete',
    method: 'POST',
    data: payload,
  })

export const clearTrash = () =>
  request<{ cleared: number }>({
    url: '/api/v1/me/trash/clear',
    method: 'DELETE',
  })

export const prepareCompress = (payload: DiskCompressIn) =>
  request<{ job_id: string }>({
    url: '/api/v1/me/archives/compress',
    method: 'POST',
    data: payload,
  })

export const compressStatus = (jobId: string) =>
  request<{ status?: string; message?: string }>({
    url: '/api/v1/me/archives/compress/status',
    method: 'GET',
    params: { job_id: jobId },
  })

export const prepareExtract = (payload: DiskExtractIn) =>
  request<{ job_id: string }>({
    url: '/api/v1/me/archives/extract',
    method: 'POST',
    data: payload,
  })

export const extractStatus = (jobId: string) =>
  request<{ status?: string; message?: string }>({
    url: '/api/v1/me/archives/extract/status',
    method: 'GET',
    params: { job_id: jobId },
  })

export const readEditFile = (file_id: number) =>
  request<DiskEditReadOut>({
    url: `/api/v1/me/files/${file_id}/text`,
    method: 'GET',
  })

export const saveEditFile = (file_id: number, payload: DiskEditSaveBody) =>
  request<DiskEntry>({
    url: `/api/v1/me/files/${file_id}/text`,
    method: 'PUT',
    data: payload,
  })
