import { computed, ref } from 'vue'
import { getPublicShare, getShareDownloadUrl, listShareEntries, previewShare, saveShare, unlockShare } from '@/api/modules/shares'
import { useToastStore } from '@/stores/toast'
import type { SharePublicResult } from '@/types/share'
import { openBlob } from '@/utils/download'

export const usePublicShare = (token: string) => {
  const toast = useToastStore()
  const loading = ref(false)
  const accessToken = ref<string | null>(null)
  const share = ref<SharePublicResult['share'] | null>(null)
  const locked = ref(true)
  const unlockError = ref('')
  const errorMessage = ref('')
  const fileMeta = ref<SharePublicResult['fileMeta'] | null>(null)
  const items = ref<Record<string, unknown>[]>([])
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
        await loadEntries()
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '请稍后重试'
      errorMessage.value = message
      toast.error('加载分享失败', message)
    } finally {
      loading.value = false
    }
  }

  const unlock = async (code: string) => {
    loading.value = true
    try {
      const data = await unlockShare(token, { code })
      if (!data.accessToken && !data.ok) {
        const message = '提取码错误'
        unlockError.value = message
        toast.error('解锁失败', message)
        return false
      }
      accessToken.value = data.accessToken ?? null
      await loadShare()
      unlockError.value = ''
      toast.success('分享已解锁')
      return true
    } catch (error) {
      const message = error instanceof Error ? error.message : '请稍后重试'
      unlockError.value = message
      toast.error('解锁失败', message)
      return false
    } finally {
      loading.value = false
    }
  }

  const loadEntries = async (path?: string) => {
    try {
      const data = await listShareEntries(
        token,
        { path },
        accessToken.value ?? undefined,
      )
      items.value = data.items || []
      currentPath.value = path ?? '/'
    } catch (error) {
      toast.error('加载分享目录失败', error instanceof Error ? error.message : '请稍后重试')
    }
  }

  const download = async (path?: string) => {
    try {
      const url = getShareDownloadUrl(token, { path }, accessToken.value ?? undefined)
      const link = document.createElement('a')
      link.href = url
      link.rel = 'noopener'
      link.click()
      toast.success('下载已开始')
    } catch (error) {
      toast.error('下载失败', error instanceof Error ? error.message : '请稍后重试')
    }
  }

  const preview = async (path?: string) => {
    try {
      const result = await previewShare(token, { path }, accessToken.value ?? undefined)
      openBlob(result.blob)
    } catch (error) {
      toast.error('预览失败', error instanceof Error ? error.message : '请稍后重试')
    }
  }

  const saveToDrive = async (targetPath: string) => {
    try {
      await saveShare(token, { targetPath })
      toast.success('已保存到网盘')
    } catch (error) {
      toast.error('保存失败', error instanceof Error ? error.message : '请稍后重试')
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
