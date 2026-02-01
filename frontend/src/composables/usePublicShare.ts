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
  const currentPath = ref<string | undefined>(undefined)

  const isFile = computed(() => {
    const resourceType = (share.value as { resourceType?: string } | null)?.resourceType
    return resourceType === 'FILE'
  })

  const loadShare = async () => {
    loading.value = true
    try {
      const data = await getPublicShare(token, accessToken.value ?? undefined)
      locked.value = data.locked
      share.value = data.share
      fileMeta.value = data.fileMeta ?? null
      errorMessage.value = ''
      if (!data.locked && !isFile.value) {
        currentPath.value = '/'
      }
    } catch (error) {
      const detail =
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage')
      errorMessage.value = detail
      message.error(t('sharePublic.toasts.loadFailTitle'), detail)
    } finally {
      loading.value = false
    }
  }

  const unlock = async (code: string) => {
    loading.value = true
    try {
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
    } catch (error) {
      const detail =
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage')
      unlockError.value = detail
      message.error(t('sharePublic.toasts.unlockFailTitle'), detail)
      return false
    } finally {
      loading.value = false
    }
  }

  const loadEntries = async (path?: string) => {
    try {
      const normalizedPath = path && path !== '/' ? path : undefined
      const data = await listShareEntries(token, { path: normalizedPath }, accessToken.value ?? undefined)
      items.value = data.items || []
      currentPath.value = normalizedPath ?? '/'
    } catch (error) {
      message.error(
        t('sharePublic.toasts.listFailTitle'),
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage'),
      )
    }
  }

  const download = async (path?: string) => {
    try {
      const url = getShareDownloadUrl(token, { path }, accessToken.value ?? undefined)
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

  const preview = async (path?: string) => {
    try {
      const result = await previewShare(token, { path }, accessToken.value ?? undefined)
      openBlob(result.blob)
    } catch (error) {
      message.error(
        t('sharePublic.toasts.previewFailTitle'),
        error instanceof Error ? error.message : t('sharePublic.toasts.commonFailMessage'),
      )
    }
  }

  const saveToDrive = async (targetPath: string) => {
    try {
      await saveShare(token, { targetPath })
      message.success(t('sharePublic.toasts.saveSuccessTitle'), targetPath)
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
    currentPath,
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
