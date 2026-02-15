export type DiskEntry = {
  id: number
  user_id: number
  parent_id: number | null
  name: string
  path: string
  is_dir: boolean
  size: number
  mime_type?: string | null
  etag?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type DiskListOut = {
  parent_id: number | null
  items: DiskEntry[]
  total: number
  nextCursor?: number | null
}

export type DiskSearchOut = {
  keyword: string
  items: DiskEntry[]
  total: number
  nextCursor?: number | null
}

export type DiskUploadOut = {
  items: DiskEntry[]
}

export type DiskUploadInitIn = {
  parent_id?: number | null
  name: string
  size: number
  mime_type?: string | null
  part_size: number
  overwrite?: boolean
}

export type DiskUploadInitOut = {
  upload_id: string
  part_size: number
  total_parts: number
  expires_in: number
  upload_config: DiskUploadPolicyOut
}

export type DiskUploadPolicyOut = {
  chunk_size_mb: number
  chunk_upload_threshold_mb: number
  max_parallel_chunks: number
  max_concurrency_per_user: number
  chunk_retry_max: number
  chunk_retry_base_ms: number
  chunk_retry_max_ms: number
  enable_resumable: boolean
  max_single_file_mb: number
}

export type DiskUploadStatusOut = {
  status: string
  total_parts: number
  uploaded_parts: number[]
  missing_parts: number[]
  uploaded_bytes: number
  expires_in: number
}

export type DiskUploadFinalizeIn = {
  parent_id?: number | null
  name: string
  overwrite?: boolean
  mime_type?: string | null
  total_parts?: number | null
}

export type DiskMkdirIn = {
  parent_id?: number | null
  name: string
}

export type DiskDeleteBatchOut = {
  success: number[]
  failed: Array<{ file_id: number; error: string }>
}

export type DiskRenameIn = {
  file_id: number
  new_name: string
}

export type DiskRenameBody = {
  new_name: string
}

export type DiskMoveIn = {
  file_id: number
  target_parent_id: number | null
  new_name?: string | null
}

export type DiskMoveBody = {
  target_parent_id: number | null
  new_name?: string | null
}

export type DiskDownloadTokenIn = {
  file_id?: number | null
  job_id?: string | null
}


export type DiskTrashEntry = {
  id: string
  name: string
  path: string
  is_dir: boolean
  size: number
  deleted_at: string
}

export type DiskTrashListOut = {
  items: DiskTrashEntry[]
}

export type DiskTrashBatchIdsIn = {
  ids: string[]
}

export type DiskTrashBatchOut = {
  success: number
  failed: string[]
}

export type DiskCompressIn = {
  file_id: number
  name?: string | null
}

export type DiskExtractIn = {
  file_id: number
}

export type DiskJobStatus = {
  status?: string
  message?: string
  usage_updated?: string
}

export type DiskEditReadOut = {
  file_id: number
  content: string
  size: number
  modified_time?: string | null
}

export type DiskEditSaveIn = {
  file_id: number
  content: string
  overwrite?: boolean
}

export type DiskEditSaveBody = {
  content: string
  overwrite?: boolean
}
