import { defineStore } from 'pinia'

export type MessageType = 'success' | 'error' | 'info' | 'warning'

export type MessageItem = {
  id: number
  type: MessageType
  title: string
  message?: string
  loading?: boolean
  duration: number
}

let messageSeed = 1

export const useMessage = defineStore('message', {
  state: () => ({
    items: [] as MessageItem[],
  }),
  actions: {
    push(payload: Omit<MessageItem, 'id'>) {
      const item = { ...payload, id: messageSeed++ }
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
