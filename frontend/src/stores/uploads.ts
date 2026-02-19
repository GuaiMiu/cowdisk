import { defineStore } from 'pinia'
import { markRaw } from 'vue'

export type UploadStatus = 'queued' | 'uploading' | 'paused' | 'success' | 'error' | 'cancelled'

export type UploadItem = {
  id: string
  file: File
  path: string
  parent_id: number | null
  status: UploadStatus
  progress: number
  speed?: number
  uploadId?: string
  totalChunks?: number
  uploadedChunks?: number[]
  error?: string
  createdAt: number
}

export const useUploadsStore = defineStore('uploads', {
  state: () => ({
    items: [] as UploadItem[],
    queueCursor: 0,
  }),
  actions: {
    enqueue(files: File[], path: string, parent_id: number | null) {
      const now = Date.now()
      const next = files.map((file, index) => ({
        id: `${now}-${index}-${file.name}`,
        file: markRaw(file),
        path,
        parent_id,
        status: 'queued' as UploadStatus,
        progress: 0,
        speed: 0,
        uploadId: undefined,
        totalChunks: undefined,
        uploadedChunks: [],
        createdAt: now,
      }))
      this.items.push(...next)
      return next
    },
    async enqueueBatched(files: File[], path: string, parent_id: number | null, batchSize = 200) {
      const items: UploadItem[] = []
      for (let start = 0; start < files.length; start += batchSize) {
        const batch = files.slice(start, start + batchSize)
        items.push(...this.enqueue(batch, path, parent_id))
        // 让出主线程，避免一次性入队导致 UI 假死
        await yieldToMain()
      }
      return items
    },
    update(id: string, patch: Partial<UploadItem>) {
      const target = this.items.find((item) => item.id === id)
      if (target) {
        Object.assign(target, patch)
      }
      if (patch.status === 'queued') {
        this.queueCursor = 0
      }
    },
    markChunkUploaded(id: string, index: number) {
      const target = this.items.find((item) => item.id === id)
      if (!target || target.totalChunks === undefined) {
        return
      }
      const existing = target.uploadedChunks ?? []
      if (!existing.includes(index)) {
        target.uploadedChunks = [...existing, index]
      }
    },
    resetChunkState(id: string) {
      const target = this.items.find((item) => item.id === id)
      if (!target) {
        return
      }
      target.uploadId = undefined
      target.totalChunks = undefined
      target.uploadedChunks = []
    },
    takeNextQueued() {
      for (let index = this.queueCursor; index < this.items.length; index += 1) {
        const item = this.items[index]
        if (item?.status === 'queued') {
          this.queueCursor = index + 1
          return item
        }
      }
      return undefined
    },
    hasQueued() {
      for (let index = this.queueCursor; index < this.items.length; index += 1) {
        if (this.items[index]?.status === 'queued') {
          return true
        }
      }
      for (let index = 0; index < this.queueCursor; index += 1) {
        if (this.items[index]?.status === 'queued') {
          return true
        }
      }
      return false
    },
    remove(id: string) {
      this.items = this.items.filter((item) => item.id !== id)
      this.queueCursor = Math.min(this.queueCursor, this.items.length)
    },
    clearDone() {
      this.items = this.items.filter((item) => !['success', 'cancelled'].includes(item.status))
      this.queueCursor = 0
    },
    clearAll() {
      this.items = []
      this.queueCursor = 0
    },
  },
})

const yieldToMain = () =>
  new Promise<void>((resolve) => {
    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      ;(window as Window & { requestIdleCallback: (cb: () => void) => number }).requestIdleCallback(
        () => resolve(),
      )
      return
    }
    setTimeout(resolve, 0)
  })
