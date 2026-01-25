import { defineStore } from 'pinia'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export type ToastItem = {
  id: number
  type: ToastType
  title: string
  message?: string
  loading?: boolean
  duration: number
}

let toastSeed = 1

export const useToastStore = defineStore('toast', {
  state: () => ({
    items: [] as ToastItem[],
  }),
  actions: {
    push(payload: Omit<ToastItem, 'id'>) {
      const item = { ...payload, id: toastSeed++ }
      this.items.push(item)
      if (item.duration > 0) {
        window.setTimeout(() => this.remove(item.id), item.duration)
      }
      return item.id
    },
    success(title: string, message?: string, duration = 2400) {
      return this.push({ type: 'success', title, message, duration })
    },
    error(title: string, message?: string, duration = 3200) {
      return this.push({ type: 'error', title, message, duration })
    },
    info(title: string, message?: string, duration = 2400) {
      return this.push({ type: 'info', title, message, duration })
    },
    warning(title: string, message?: string, duration = 2800) {
      return this.push({ type: 'warning', title, message, duration })
    },
    loading(title: string, message?: string) {
      return this.push({ type: 'info', title, message, duration: 0, loading: true })
    },
    remove(id: number) {
      this.items = this.items.filter((item) => item.id !== id)
    },
    clear() {
      this.items = []
    },
  },
})
