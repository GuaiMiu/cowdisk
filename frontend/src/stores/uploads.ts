import { defineStore } from 'pinia'
import { markRaw } from 'vue'

export type UploadStatus = 'queued' | 'uploading' | 'success' | 'error' | 'cancelled'

export type UploadItem = {
  id: string
  file: File
  path: string
  status: UploadStatus
  progress: number
  error?: string
  createdAt: number
}

export const useUploadsStore = defineStore('uploads', {
  state: () => ({
    items: [] as UploadItem[],
  }),
  actions: {
    enqueue(files: File[], path: string) {
      const now = Date.now()
      const next = files.map((file, index) => ({
        id: `${now}-${index}-${file.name}`,
        file: markRaw(file),
        path,
        status: 'queued' as UploadStatus,
        progress: 0,
        createdAt: now,
      }))
      this.items.push(...next)
      return next
    },
    update(id: string, patch: Partial<UploadItem>) {
      const target = this.items.find((item) => item.id === id)
      if (target) {
        Object.assign(target, patch)
      }
    },
    remove(id: string) {
      this.items = this.items.filter((item) => item.id !== id)
    },
    clearDone() {
      this.items = this.items.filter((item) => !['success', 'cancelled'].includes(item.status))
    },
    clearAll() {
      this.items = []
    },
  },
})
