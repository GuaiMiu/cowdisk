import { onBeforeUnmount, watch, type Ref } from 'vue'

let lockCount = 0

const applyBodyLock = () => {
  if (typeof document === 'undefined') {
    return
  }
  document.body.style.overflow = lockCount > 0 ? 'hidden' : ''
}

export const useBodyScrollLock = (enabled: Ref<boolean>) => {
  let locked = false

  const lock = () => {
    if (locked) {
      return
    }
    lockCount += 1
    locked = true
    applyBodyLock()
  }

  const unlock = () => {
    if (!locked) {
      return
    }
    lockCount = Math.max(0, lockCount - 1)
    locked = false
    applyBodyLock()
  }

  watch(
    enabled,
    (value) => {
      if (value) {
        lock()
      } else {
        unlock()
      }
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    unlock()
  })
}

