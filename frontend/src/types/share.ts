export type Share = {
  id: string
  resourceType: string
  path: string
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
  resourceType: string
  path: string
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
  targetPath: string
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

export type ShareListQueryOut = {
  items: Record<string, unknown>[]
  nextCursor?: string | null
}

export type ShareBatchResult = {
  success: number
  failed: string[]
}
