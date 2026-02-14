export type Share = {
  id: string
  resourceType: string
  fileId: number
  token: string
  name: string
  ownerName?: string | null
  createdAt: number
  expiresAt?: number | null
  hasCode: boolean
  code?: string | null
  status: number
  missing?: boolean
}

export type ShareCreateIn = {
  fileId: number
  expiresInDays?: number | null
  expiresAt?: number | null
  code?: string | null
}

export type ShareUpdateIn = {
  expiresInDays?: number | null
  expiresAt?: number | null
  code?: string | null
  status?: number | null
}

export type ShareListOut = {
  items: Share[]
  total: number
  page: number
  size: number
  pages: number
}

export type ShareUnlockIn = {
  code: string
}

export type ShareSaveIn = {
  targetParentId: number | null
}

export type SharePublicResult = {
  locked: boolean
  share:
    | Share
    | {
        name?: string
        resourceType?: string
        expiresAt?: number | null
        ownerName?: string | null
      }
  fileMeta?: { size?: number; mime?: string } | null
}

export type ShareEntry = {
  id: number
  name: string
  parent_id: number | null
  is_dir: boolean
  size: number
  mime_type?: string | null
  updated_at?: string | null
  path?: string
}

export type ShareListQueryOut = {
  items: ShareEntry[]
  nextCursor?: string | null
}

export type ShareBatchResult = {
  success: number
  failed: string[]
}
