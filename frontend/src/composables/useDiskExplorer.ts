import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  listDir,
  mkdir,
  renamePaths,
  deletePaths,
  createDownloadToken,
  getDownloadFileUrl,
  getDownloadJobUrl,
  prepareDownload,
  downloadStatus,
} from '@/api/modules/userDisk'
import { useMessage } from '@/stores/message'
import type { DiskEntry } from '@/types/disk'
import { joinPath, toRelativePath } from '@/utils/path'
import { triggerDownload } from '@/utils/download'
import { normalizeDiskError } from '@/utils/diskError'
import { usePolling } from './usePolling'

type SortKey = 'name' | 'size' | 'type' | 'updatedAt'

export const useDiskExplorer = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const loading = ref(false)
  const path = ref('/')
  const items = ref<DiskEntry[]>([])
  const sortKey = ref<SortKey | null>(null)
  const sortOrder = ref<'asc' | 'desc'>('asc')
  const { poll } = usePolling()
  const listController = ref<AbortController | null>(null)

  const normalizeRoot = (value: string) => {
    if (!value || value === '/') {
      return ''
    }
    return toRelativePath(value)
  }

  const load = async (nextPath?: string) => {
    loading.value = true
    if (listController.value) {
      listController.value.abort()
    }
    const controller = new AbortController()
    listController.value = controller
    try {
      const target = nextPath ?? path.value
      const data = await listDir(normalizeRoot(target), { signal: controller.signal })
      path.value = data.path || '/'
      items.value = data.items || []
    } catch (error) {
      if (controller.signal.aborted) {
        return
      }
      message.error(
        t('fileExplorer.toasts.loadFailTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.loadFailMessage')),
      )
    } finally {
      if (listController.value === controller) {
        listController.value = null
      }
      loading.value = false
    }
  }

  const refresh = () => load(path.value)

  const getTypeKey = (entry: DiskEntry) => {
    if (entry.is_dir) {
      return ''
    }
    const parts = (entry.name || '').split('.')
    return parts.length > 1 ? parts[parts.length - 1]?.toLowerCase() || '' : ''
  }

  const getUpdatedKey = (entry: DiskEntry) => {
    if (!entry.modified_time) {
      return 0
    }
    const time = new Date(entry.modified_time).getTime()
    return Number.isNaN(time) ? 0 : time
  }

  const sortedItems = computed(() => {
    if (!sortKey.value) {
      return items.value
    }
    const next = [...items.value]
    const order = sortOrder.value === 'asc' ? 1 : -1
    next.sort((a, b) => {
      if (a.is_dir !== b.is_dir) {
        return a.is_dir ? -1 : 1
      }
      if (sortKey.value === 'name') {
        return order * a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
      }
      if (sortKey.value === 'size') {
        return order * ((a.size || 0) - (b.size || 0))
      }
      if (sortKey.value === 'type') {
        return order * getTypeKey(a).localeCompare(getTypeKey(b), undefined, { numeric: true, sensitivity: 'base' })
      }
      return order * (getUpdatedKey(a) - getUpdatedKey(b))
    })
    return next
  })

  const setSort = (key: SortKey) => {
    if (sortKey.value === key) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
      return
    }
    sortKey.value = key
    sortOrder.value = 'asc'
  }

  const createFolder = async (name: string) => {
    if (!name.trim()) {
      message.warning(t('fileExplorer.toasts.folderNameRequired'))
      return false
    }
    try {
      await mkdir({ path: toRelativePath(joinPath(path.value, name.trim())) })
      message.success(t('fileExplorer.toasts.folderCreatedTitle'), name.trim())
      await refresh()
      return true
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.createFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.createFailedMessage')),
      )
      return false
    }
  }

  const renameEntry = async (entry: DiskEntry, nextName: string) => {
    if (!nextName.trim()) {
      message.warning(t('fileExplorer.toasts.renameRequired'))
      return false
    }
    try {
      const target = toRelativePath(joinPath(path.value, nextName.trim()))
      const result = await renamePaths([{ src: entry.path, dst: target, overwrite: false }])
      if (result.failed.length > 0) {
        throw new Error(result.failed[0]?.error || '重命名失败')
      }
      message.success(
        t('fileExplorer.toasts.renameSuccessTitle'),
        `${entry.name} → ${nextName.trim()}`,
      )
      await refresh()
      return true
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.renameFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.renameFailedMessage')),
      )
      return false
    }
  }

  const moveEntry = async (entry: DiskEntry, targetPath: string) => {
    const base = targetPath ? `/${targetPath}` : '/'
    const target = toRelativePath(joinPath(base, entry.name))
    if (target === entry.path) {
      message.info(t('fileExplorer.toasts.alreadyHere'))
      return false
    }
    try {
      const result = await renamePaths([{ src: entry.path, dst: target, overwrite: false }])
      if (result.failed.length > 0) {
        throw new Error(result.failed[0]?.error || '移动失败')
      }
      message.success(
        t('fileExplorer.toasts.moveSuccessTitle'),
        `${entry.name} → ${targetPath || '/'}`,
      )
      await refresh()
      return true
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.moveFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.moveFailedMessage')),
      )
      return false
    }
  }

  const moveEntries = async (entries: DiskEntry[], targetPath: string) => {
    if (!entries.length) {
      message.warning(t('fileExplorer.toasts.noSelection'))
      return false
    }
    const base = targetPath ? `/${targetPath}` : '/'
    const items = entries
      .map((entry) => ({
        src: entry.path,
        dst: toRelativePath(joinPath(base, entry.name)),
        overwrite: false,
      }))
      .filter((item) => item.src !== item.dst)
    if (!items.length) {
      message.info(t('fileExplorer.toasts.alreadyHere'))
      return false
    }
    try {
      const result = await renamePaths(items)
      if (result.failed.length === 0) {
        message.success(
          t('fileExplorer.toasts.moveBatchSuccessTitle'),
          t('fileExplorer.toasts.moveBatchSuccessMessage', { count: result.success.length }),
        )
      } else if (result.success.length > 0) {
        message.warning(
          t('fileExplorer.toasts.moveBatchPartialTitle'),
          t('fileExplorer.toasts.moveBatchPartialMessage', {
            success: result.success.length,
            failed: result.failed.length,
          }),
        )
      } else {
        message.error(
          t('fileExplorer.toasts.moveFailedTitle'),
          result.failed[0]?.error || t('fileExplorer.toasts.moveFailedMessage'),
        )
      }
      if (result.success.length > 0) {
        await refresh()
      }
      return result.success.length > 0 && result.failed.length === 0
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.moveFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.moveFailedMessage')),
      )
      return false
    }
  }

  const removeEntry = async (entry: DiskEntry) => {
    try {
      return await removeEntries([entry])
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.deleteFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.deleteFailedMessage')),
      )
      return false
    }
  }

  const removeEntries = async (entries: DiskEntry[]) => {
    if (!entries.length) {
      return false
    }
    try {
      const paths = entries.map((entry) => entry.path)
      const recursive = entries.some((entry) => entry.is_dir)
      const result = await deletePaths(paths, recursive)
      if (result.failed.length === 0) {
        message.success(
          t('fileExplorer.toasts.deleteSuccessTitle'),
          t('fileExplorer.toasts.deleteSuccessMessage', { count: result.success.length }),
        )
      } else if (result.success.length > 0) {
        message.warning(
          t('fileExplorer.toasts.deletePartialTitle'),
          t('fileExplorer.toasts.deletePartialMessage', {
            success: result.success.length,
            failed: result.failed.length,
          }),
        )
      } else {
        message.error(
          t('fileExplorer.toasts.deleteFailedTitle'),
          result.failed[0]?.error || t('fileExplorer.toasts.deleteFailedMessage'),
        )
      }
      if (result.success.length > 0) {
        await refresh()
      }
      return result.success.length > 0 && result.failed.length === 0
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.deleteFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.deleteFailedMessage')),
      )
      return false
    }
  }

  const downloadEntry = async (entry: DiskEntry) => {
    try {
      if (entry.is_dir) {
        const loadingId = message.loading(
          t('fileExplorer.toasts.packagingTitle'),
          t('fileExplorer.toasts.packagingMessage'),
        )
        const job = await prepareDownload({ path: entry.path })
        const status = await poll(() => downloadStatus(job.job_id), {
          stopCondition: (data) => data.status === 'ready' || data.status === 'error',
          interval: 1500,
        })
        if (status.status !== 'ready') {
          message.remove(loadingId)
          throw new Error(status.message || '打包失败')
        }
        const token = await createDownloadToken({ job_id: job.job_id })
        triggerDownload(getDownloadJobUrl(token.token))
        message.remove(loadingId)
        message.success(
          t('fileExplorer.toasts.packageDoneTitle'),
          t('fileExplorer.toasts.downloadStarted'),
        )
      } else {
        const token = await createDownloadToken({ path: entry.path })
        triggerDownload(getDownloadFileUrl(token.token))
        message.success(t('fileExplorer.toasts.downloadStarted'))
      }
      return true
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.downloadFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.downloadFailedMessage')),
      )
      return false
    }
  }

  const canGoUp = computed(() => path.value && path.value !== '/')

  return {
    loading,
    path,
    items,
    sortedItems,
    sortKey,
    sortOrder,
    setSort,
    load,
    refresh,
    createFolder,
    renameEntry,
    moveEntry,
    moveEntries,
    removeEntry,
    removeEntries,
    downloadEntry,
    canGoUp,
  }
}
