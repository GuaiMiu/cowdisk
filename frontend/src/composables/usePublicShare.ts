import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getPublicShare,
  getShareDownloadUrl,
  listShareEntries,
  previewShare,
  saveShare,
  unlockShare,
} from '@/api/modules/shares'
import { useMessage } from '@/stores/message'
import type { ShareEntry, SharePublicResult } from '@/types/share'
import { openBlob } from '@/utils/download'

export const usePublicShare = (token: string) => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const loading = ref(false)
  const accessToken = ref<string | null>(null)
  const share = ref<SharePublicResult['share'] | null>(null)
  const locked = ref(true)
  const unlockError = ref('')
  const errorMessage = ref('')
  const fileMeta = ref<SharePublicResult['fileMeta'] | null>(null)
  const items = ref<ShareEntry[]>([])
  const currentParentId = ref<number | null>(null)
  const pendingCount = ref(0)
  let shareRequestId = 0
  let entryRequestId = 0

  const withLoading = async <T>(task: () => Promise<T>) => {
    pendingCount.value += 1
    loading.value = true
    try {
      return await task()
    } finally {
      pendingCount.value = Math.max(0, pendingCount.value - 1)
      loading.value = pendingCount.value > 0
    }
  }

  const isFile = computed(() => {
    const resourceType = (share.value as { resourceType?: string } | null)?.resourceType
    return resourceType === 'FILE'
  })

  const loadShare = async () => {
    const requestId = ++shareRequestId
    return withLoading(async () => {
      const data = await getPublicShare(token, accessToken.value ?? undefined)
      if (requestId !== shareRequestId) {
        return
      }
      locked.value = data.locked
      share.value = data.share
      fileMeta.value = data.fileMeta ?? null
      errorMessage.value = ''
      if (!data.locked && !isFile.value) {
        currentParentId.value = null
      }
    }).catch((error) => {
      if (requestId !== shareRequestId) {
        return
      }
      const detail =
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage')
      errorMessage.value = detail
      message.error(t('sharePublic.toasts.loadFailTitle'), detail)
    })
  }

  const unlock = async (code: string) => {
    return withLoading(async () => {
      const data = await unlockShare(token, { code })
      if (!data.accessToken && !data.ok) {
        const detail = t('sharePublic.toasts.unlockWrongCode')
        unlockError.value = detail
        message.error(t('sharePublic.toasts.unlockFailTitle'), detail)
        return false
      }
      accessToken.value = data.accessToken ?? null
      await loadShare()
      unlockError.value = ''
      message.success(t('sharePublic.toasts.unlockSuccessTitle'))
      return true
    }).catch((error) => {
      const detail =
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage')
      unlockError.value = detail
      message.error(t('sharePublic.toasts.unlockFailTitle'), detail)
      return false
    })
  }

  const loadEntries = async (parent_id?: number | null) => {
    const requestId = ++entryRequestId
    try {
      const data = await listShareEntries(
        token,
        { parent_id: parent_id ?? null },
        accessToken.value ?? undefined,
      )
      if (requestId !== entryRequestId) {
        return
      }
      items.value = data.items || []
      currentParentId.value = parent_id ?? null
    } catch (error) {
      message.error(
        t('sharePublic.toasts.listFailTitle'),
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage'),
      )
    }
  }

  const download = async (file_id?: number | null) => {
    try {
      const url = getShareDownloadUrl(token, { file_id }, accessToken.value ?? undefined)
      const link = document.createElement('a')
      link.href = url
      link.rel = 'noopener'
      link.click()
      message.success(t('sharePublic.toasts.downloadStarted'))
    } catch (error) {
      message.error(
        t('sharePublic.toasts.downloadFailTitle'),
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage'),
      )
    }
  }

  const preview = async (file_id?: number | null) => {
    try {
      const result = await previewShare(token, { file_id }, accessToken.value ?? undefined)
      openBlob(result.blob)
    } catch (error) {
      message.error(
        t('sharePublic.toasts.previewFailTitle'),
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage'),
      )
    }
  }

  const saveToDrive = async (targetParentId: number | null) => {
    try {
      await saveShare(token, { targetParentId })
      message.success(t('sharePublic.toasts.saveSuccessTitle'))
    } catch (error) {
      message.error(
        t('sharePublic.toasts.saveFailTitle'),
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage'),
      )
    }
  }

  return {
    loading,
    locked,
    share,
    fileMeta,
    items,
    currentParentId,
    isFile,
    accessToken,
    unlockError,
    loadShare,
    unlock,
    clearUnlockError: () => {
      unlockError.value = ''
    },
    errorMessage,
    loadEntries,
    download,
    preview,
    saveToDrive,
  }
}
