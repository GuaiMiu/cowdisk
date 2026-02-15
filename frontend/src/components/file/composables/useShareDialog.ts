import { computed, ref } from 'vue'
import { copyToClipboard } from '@/utils/clipboard'
import type { DiskEntry } from '@/types/disk'
import type { Share } from '@/types/share'

export type ShareFormValue = {
  expiresInDays: number | null
  expiresAt: string | null
  requiresCode: boolean
  code: string
}

type CreateSharePayload = {
  fileId: number
  expiresInDays: number | null
  expiresAt: number | null
  code: string | null
}

type UseShareDialogOptions = {
  t: (key: string, params?: Record<string, unknown>) => string
  createShare: (payload: CreateSharePayload) => Promise<Share | null>
  message: {
    success: (title: string, message?: string) => number
    error: (title: string, message?: string) => number
  }
}

const createDefaultShareForm = (): ShareFormValue => ({
  expiresInDays: 7,
  expiresAt: null,
  requiresCode: true,
  code: '',
})

const buildShareUrl = (token: string, code?: string | null) => {
  const url = new URL(`/s/${token}`, window.location.origin)
  if (code) {
    url.searchParams.set('code', code)
  }
  return url.toString()
}

export const useShareDialog = (options: UseShareDialogOptions) => {
  const shareModal = ref(false)
  const shareEntry = ref<DiskEntry | null>(null)
  const shareLink = ref('')
  const shareLinkWithCode = ref('')
  const shareCode = ref('')
  const shareIncludeCode = ref(true)
  const shareResult = ref<Share | null>(null)
  const shareSubmitting = ref(false)
  const lastShareSignature = ref<string | null>(null)
  const shareForm = ref<ShareFormValue>(createDefaultShareForm())

  const buildShareSignature = () => {
    const expiresAt =
      shareForm.value.expiresAt && Number.isFinite(Date.parse(shareForm.value.expiresAt))
        ? Date.parse(shareForm.value.expiresAt)
        : null
    return JSON.stringify({
      fileId: shareEntry.value?.id ?? null,
      expiresInDays: shareForm.value.expiresInDays ?? null,
      expiresAt,
      code:
        shareForm.value.requiresCode && shareForm.value.code.trim()
          ? shareForm.value.code.trim()
          : null,
    })
  }

  const canRegenerateShare = computed(() => {
    if (!shareResult.value) {
      return true
    }
    return buildShareSignature() !== lastShareSignature.value
  })

  const openShareModal = (entry: DiskEntry) => {
    shareEntry.value = entry
    shareForm.value = createDefaultShareForm()
    shareLink.value = ''
    shareLinkWithCode.value = ''
    shareCode.value = ''
    shareIncludeCode.value = true
    shareResult.value = null
    lastShareSignature.value = null
    shareModal.value = true
  }

  const closeShareModal = () => {
    shareModal.value = false
  }

  const submitShare = async () => {
    if (!shareEntry.value || shareSubmitting.value || !canRegenerateShare.value) {
      return
    }
    shareSubmitting.value = true
    const expiresAt =
      shareForm.value.expiresAt && Number.isFinite(Date.parse(shareForm.value.expiresAt))
        ? Date.parse(shareForm.value.expiresAt)
        : null
    const payload: CreateSharePayload = {
      fileId: shareEntry.value.id,
      expiresInDays: shareForm.value.expiresInDays ?? null,
      expiresAt,
      code:
        shareForm.value.requiresCode && shareForm.value.code.trim()
          ? shareForm.value.code.trim()
          : null,
    }
    const share = await options.createShare(payload)
    shareSubmitting.value = false
    if (!share) {
      return
    }
    shareResult.value = share
    shareCode.value = share.code ?? ''
    shareLink.value = buildShareUrl(share.token)
    shareLinkWithCode.value = buildShareUrl(share.token, share.code)
    lastShareSignature.value = buildShareSignature()
  }

  const handleCopyLink = async () => {
    const link =
      shareIncludeCode.value && shareCode.value ? shareLinkWithCode.value : shareLink.value
    const text = shareCode.value
      ? `${options.t('fileExplorer.modals.copyLinkPrefix')}: ${link} ${options.t('fileExplorer.modals.copyCodePrefix')}: ${shareCode.value}`
      : link
    const ok = await copyToClipboard(text)
    if (ok) {
      options.message.success(options.t('fileExplorer.toasts.linkCopied'))
    } else {
      options.message.error(
        options.t('fileExplorer.toasts.copyFailTitle'),
        options.t('fileExplorer.toasts.copyFailMessage'),
      )
    }
  }

  return {
    shareModal,
    shareEntry,
    shareForm,
    shareResult,
    shareSubmitting,
    shareIncludeCode,
    shareCode,
    shareLink,
    shareLinkWithCode,
    canRegenerateShare,
    openShareModal,
    closeShareModal,
    submitShare,
    handleCopyLink,
  }
}

