import { computed, onBeforeUnmount, ref, watch, type Ref } from 'vue'

type AvatarResponse = {
  blob: Blob
}

type UseUserAvatarOptions = {
  label: Ref<string>
  avatarPath: Ref<string | null | undefined>
  token: Ref<string | null | undefined>
  loadAvatar: () => Promise<AvatarResponse>
}

export const useUserAvatar = (options: UseUserAvatarOptions) => {
  const avatarFailed = ref(false)
  const avatarSrc = ref<string | null>(null)

  const initials = computed(() => {
    const label = options.label.value || ''
    if (!label) {
      return '?'
    }
    return label.trim().slice(0, 1).toUpperCase()
  })

  const hasAvatar = computed(() => !!options.avatarPath.value)

  const onAvatarError = () => {
    avatarFailed.value = true
  }

  const clearAvatar = () => {
    if (avatarSrc.value) {
      URL.revokeObjectURL(avatarSrc.value)
    }
    avatarSrc.value = null
    avatarFailed.value = false
  }

  const fetchAvatar = async () => {
    if (!hasAvatar.value) {
      clearAvatar()
      return
    }
    try {
      const result = await options.loadAvatar()
      if (avatarSrc.value) {
        URL.revokeObjectURL(avatarSrc.value)
      }
      avatarSrc.value = URL.createObjectURL(result.blob)
      avatarFailed.value = false
    } catch {
      clearAvatar()
    }
  }

  watch(
    [options.avatarPath, options.token],
    () => {
      void fetchAvatar()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    clearAvatar()
  })

  return {
    avatarFailed,
    avatarSrc,
    initials,
    onAvatarError,
    fetchAvatar,
    clearAvatar,
  }
}
