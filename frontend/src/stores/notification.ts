import { defineStore } from 'pinia'

export type NotificationType = 'success' | 'error' | 'info' | 'warning'

export type NotificationItem = {
  id: number
  type: NotificationType
  title: string
  message?: string
  duration: number
}

let notificationSeed = 1

export const useNotification = defineStore('notification', {
  state: () => ({
    items: [] as NotificationItem[],
  }),
  actions: {
    push(payload: Omit<NotificationItem, 'id'>) {
      const item = { ...payload, id: notificationSeed++ }
      this.items.push(item)
      if (item.duration > 0) {
        window.setTimeout(() => this.remove(item.id), item.duration)
      }
      return item.id
    },
    success(title: string, message?: string, duration = 3600) {
      return this.push({ type: 'success', title, message, duration })
    },
    error(title: string, message?: string, duration = 4200) {
      return this.push({ type: 'error', title, message, duration })
    },
    info(title: string, message?: string, duration = 3600) {
      return this.push({ type: 'info', title, message, duration })
    },
    warning(title: string, message?: string, duration = 3800) {
      return this.push({ type: 'warning', title, message, duration })
    },
    remove(id: number) {
      this.items = this.items.filter((item) => item.id !== id)
    },
    clear() {
      this.items = []
    },
  },
})
