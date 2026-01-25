import { onBeforeUnmount, ref } from 'vue'

type PollOptions<T> = {
  interval?: number
  timeout?: number
  stopCondition: (data: T) => boolean
}

export const usePolling = () => {
  const isPolling = ref(false)
  const stopped = ref(false)

  const stop = () => {
    stopped.value = true
    isPolling.value = false
  }

  const poll = async <T>(task: () => Promise<T>, options: PollOptions<T>) => {
    const interval = options.interval ?? 1200
    const timeout = options.timeout ?? 10 * 60 * 1000
    const startedAt = Date.now()
    stopped.value = false
    isPolling.value = true

    return new Promise<T>((resolve, reject) => {
      const run = async () => {
        if (stopped.value) {
          reject(new Error('轮询已停止'))
          return
        }
        if (Date.now() - startedAt > timeout) {
          isPolling.value = false
          reject(new Error('任务超时'))
          return
        }
        try {
          const data = await task()
          if (options.stopCondition(data)) {
            isPolling.value = false
            resolve(data)
            return
          }
        } catch (error) {
          isPolling.value = false
          reject(error)
          return
        }
        window.setTimeout(run, interval)
      }
      void run()
    })
  }

  onBeforeUnmount(() => {
    stop()
  })

  return {
    isPolling,
    poll,
    stop,
  }
}
