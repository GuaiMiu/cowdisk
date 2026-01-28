export type DiskEntry = {
  name: string
  path: string
  is_dir: boolean
  size: number
  modified_time?: string | null
}

export type DiskListOut = {
  path: string
  items: DiskEntry[]
}

export type DiskUploadOut = {
  items: DiskEntry[]
}

export type DiskUploadInitIn = {
  path: string
  filename: string
  size: number
  total_chunks: number
  overwrite?: boolean
}

export type DiskUploadCompleteIn = {
  upload_id: string
}

export type DiskMkdirIn = {
  path: string
}

export type DiskDeleteFailure = {
  path: string
  error: string
}

export type DiskDeleteBatchOut = {
  success: string[]
  failed: DiskDeleteFailure[]
}

export type DiskRenameItem = {
  src: string
  dst: string
  overwrite?: boolean
}

export type DiskRenameFailure = {
  src: string
  dst: string
  error: string
}

export type DiskRenameBatchOut = {
  success: DiskEntry[]
  failed: DiskRenameFailure[]
}

export type DiskDownloadTokenIn = {
  path?: string | null
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

export type DiskTrashRestoreIn = {
  id: string
}

export type DiskTrashDeleteIn = {
  id: string
}

export type DiskCompressIn = {
  path: string
  name?: string | null
}

export type DiskExtractIn = {
  path: string
}

export type DiskJobStatus = {
  status?: string
  message?: string
  usage_updated?: string
}

export type DiskEditReadOut = {
  path: string
  content: string
  size: number
  modified_time?: string | null
}

export type DiskEditSaveIn = {
  path: string
  content: string
  overwrite?: boolean
}
