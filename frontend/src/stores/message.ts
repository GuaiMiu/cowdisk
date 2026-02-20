import { defineStore } from 'pinia'

export type MessageType = 'success' | 'error' | 'info' | 'warn'

export type MessageAction = {
  label: string
  onClick?: () => void
  dismissOnClick?: boolean
}

export type MessageItem = {
  id: number
  type: MessageType
  title: string
  message?: string
  loading?: boolean
  duration: number
  action?: MessageAction
}

type MessageOptions = {
  duration?: number
  loading?: boolean
  action?: MessageAction
}

let messageSeed = 1
const timerMap = new Map<number, number>()

export const useMessage = defineStore('message', {
  state: () => ({
    items: [] as MessageItem[],
  }),
  actions: {
    push(payload: Omit<MessageItem, 'id'>) {
      const item = { ...payload, id: messageSeed++ }
      this.items.push(item)
      if (item.duration > 0) {
        const timerId = window.setTimeout(() => this.remove(item.id), item.duration)
        timerMap.set(item.id, timerId)
      }
      return item.id
    },
    success(title: string, message?: string, options: MessageOptions = {}) {
      return this.push({
        type: 'success',
        title,
        message,
        duration: options.duration ?? 2400,
        action: options.action,
        loading: options.loading,
      })
    },
    error(title: string, message?: string, options: MessageOptions = {}) {
      return this.push({
        type: 'error',
        title,
        message,
        duration: options.duration ?? 3200,
        action: options.action,
        loading: options.loading,
      })
    },
    info(title: string, message?: string, options: MessageOptions = {}) {
      return this.push({
        type: 'info',
        title,
        message,
        duration: options.duration ?? 2400,
        action: options.action,
        loading: options.loading,
      })
    },
    warn(title: string, message?: string, options: MessageOptions = {}) {
      return this.push({
        type: 'warn',
        title,
        message,
        duration: options.duration ?? 2800,
        action: options.action,
        loading: options.loading,
      })
    },
    warning(title: string, message?: string, options: MessageOptions = {}) {
      return this.warn(title, message, options)
    },
    loading(title: string, message?: string, options: MessageOptions = {}) {
      return this.push({
        type: 'info',
        title,
        message,
        duration: options.duration ?? 0,
        loading: true,
        action: options.action,
      })
    },
    update(id: number, patch: Partial<Omit<MessageItem, 'id'>>) {
      const target = this.items.find((item) => item.id === id)
      if (!target) {
        return
      }
      Object.assign(target, patch)
    },
    triggerAction(id: number) {
      const target = this.items.find((item) => item.id === id)
      if (!target?.action?.onClick) {
        return
      }
      target.action.onClick()
      if (target.action.dismissOnClick !== false) {
        this.remove(id)
      }
    },
    remove(id: number) {
      const timerId = timerMap.get(id)
      if (timerId) {
        window.clearTimeout(timerId)
        timerMap.delete(id)
      }
      this.items = this.items.filter((item) => item.id !== id)
    },
    clear() {
      timerMap.forEach((timerId) => {
        window.clearTimeout(timerId)
      })
      timerMap.clear()
      this.items = []
    },
  },
})
