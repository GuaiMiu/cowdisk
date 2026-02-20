import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  listDir,
  mkdir,
  renameFile,
  moveFile,
  deleteFiles,
  batchDeleteTrash,
  getDownloadUrl,
  searchFiles,
} from '@/api/modules/userDisk'
import { useMessage } from '@/stores/message'
import { useAuthStore } from '@/stores/auth'
import type { DiskEntry } from '@/types/disk'
import { triggerDownload } from '@/utils/download'
import { normalizeDiskError } from '@/utils/diskError'

type SortKey = 'name' | 'size' | 'type' | 'updatedAt'

export const useDiskExplorer = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const authStore = useAuthStore()
  const loading = ref(false)
  const path = ref('/')
  const parentId = ref<number | null>(null)
  const folderStack = ref<Array<{ id: number; name: string }>>([])
  const items = ref<DiskEntry[]>([])
  const total = ref(0)
  const searchKeyword = ref('')
  const sortKey = ref<SortKey | null>(null)
  const sortOrder = ref<'asc' | 'desc'>('asc')
  const listController = ref<AbortController | null>(null)
  const pendingLoadCount = ref(0)

  const syncPathFromStack = () => {
    const segments = folderStack.value.map((item) => item.name).filter(Boolean)
    path.value = segments.length ? `/${segments.join('/')}` : '/'
  }

  const load = async (nextParentId?: number | null, nextKeyword?: string) => {
    pendingLoadCount.value += 1
    loading.value = true
    if (listController.value) {
      listController.value.abort()
    }
    const controller = new AbortController()
    listController.value = controller
    try {
      const keyword = (nextKeyword ?? searchKeyword.value).trim()
      searchKeyword.value = keyword
      const targetParentId =
        nextParentId !== undefined ? nextParentId : parentId.value ?? null
      if (keyword) {
        const data = await searchFiles(keyword, { signal: controller.signal })
        items.value = data.items || []
        total.value = data.total || 0
      } else {
        const data = await listDir(targetParentId, { signal: controller.signal })
        parentId.value = data.parent_id ?? targetParentId ?? null
        items.value = data.items || []
        total.value = data.total || 0
      }
      syncPathFromStack()
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
      pendingLoadCount.value = Math.max(0, pendingLoadCount.value - 1)
      loading.value = pendingLoadCount.value > 0
    }
  }

  const refresh = () => load(parentId.value ?? null)
  const setSearchKeyword = async (keyword: string) => {
    await load(parentId.value ?? null, keyword)
  }

  const getTypeKey = (entry: DiskEntry) => {
    if (entry.is_dir) {
      return ''
    }
    const parts = (entry.name || '').split('.')
    return parts.length > 1 ? parts[parts.length - 1]?.toLowerCase() || '' : ''
  }

  const getUpdatedKey = (entry: DiskEntry) => {
    if (!entry.updated_at) {
      return 0
    }
    const time = new Date(entry.updated_at).getTime()
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
      await mkdir({ parent_id: parentId.value ?? null, name: name.trim() })
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
      await renameFile(entry.id, { new_name: nextName.trim() })
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

  const moveEntry = async (entry: DiskEntry, targetParentId: number | null) => {
    if (targetParentId === entry.parent_id) {
      message.info(t('fileExplorer.toasts.alreadyHere'))
      return false
    }
    try {
      await moveFile(entry.id, { target_parent_id: targetParentId, new_name: entry.name })
      message.success(t('fileExplorer.toasts.moveSuccessTitle'))
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

  const moveEntries = async (entries: DiskEntry[], targetParentId: number | null) => {
    if (!entries.length) {
      message.warning(t('fileExplorer.toasts.noSelection'))
      return false
    }
    const toMove = entries.filter((entry) => entry.parent_id !== targetParentId)
    if (!toMove.length) {
      message.info(t('fileExplorer.toasts.alreadyHere'))
      return false
    }
    try {
      let success = 0
      let failed = 0
      for (const entry of toMove) {
        try {
          await moveFile(entry.id, { target_parent_id: targetParentId, new_name: entry.name })
          success += 1
        } catch {
          failed += 1
        }
      }
      if (failed === 0) {
        message.success(
          t('fileExplorer.toasts.moveBatchSuccessTitle'),
          t('fileExplorer.toasts.moveBatchSuccessMessage', { count: success }),
        )
      } else if (success > 0) {
        message.warning(
          t('fileExplorer.toasts.moveBatchPartialTitle'),
          t('fileExplorer.toasts.moveBatchPartialMessage', { success, failed }),
        )
      } else {
        message.error(t('fileExplorer.toasts.moveFailedTitle'), t('fileExplorer.toasts.moveFailedMessage'))
      }
      if (success > 0) {
        await refresh()
      }
      return success > 0 && failed === 0
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
      const ids = entries.map((entry) => entry.id)
      const result = await deleteFiles(ids)
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
        void authStore.refreshMe().catch(() => null)
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
      const data = await getDownloadUrl(entry.id)
      const base = import.meta.env.VITE_API_BASE_URL || ''
      const href = base ? new URL(data.url, base).toString() : data.url
      triggerDownload(href)
      message.success(t('fileExplorer.toasts.downloadStarted'))
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

  const openEntry = async (entry: DiskEntry) => {
    if (!entry.is_dir) {
      return
    }
    if (searchKeyword.value) {
      searchKeyword.value = ''
      folderStack.value = [{ id: entry.id, name: entry.name }]
      await load(entry.id, '')
      return
    }
    folderStack.value = [...folderStack.value, { id: entry.id, name: entry.name }]
    await load(entry.id)
  }

  const suggestAvailableName = (name: string) => {
    const normalized = (name || '').trim()
    if (!normalized) {
      return ''
    }
    const exists = (candidate: string) =>
      items.value.some((item) => item.name.toLowerCase() === candidate.toLowerCase())
    if (!exists(normalized)) {
      return normalized
    }
    const dot = normalized.lastIndexOf('.')
    const hasExt = dot > 0 && dot < normalized.length - 1
    const stem = hasExt ? normalized.slice(0, dot) : normalized
    const ext = hasExt ? normalized.slice(dot) : ''
    for (let index = 1; index < 1000; index += 1) {
      const candidate = `${stem} (${index})${ext}`
      if (!exists(candidate)) {
        return candidate
      }
    }
    return normalized
  }

  const hardRemoveEntries = async (entries: DiskEntry[]) => {
    if (!entries.length) {
      return false
    }
    try {
      const ids = entries.map((entry) => entry.id)
      const softDeleteResult = await deleteFiles(ids)
      if (softDeleteResult.success.length === 0) {
        message.error(
          t('fileExplorer.toasts.hardDeleteFailedTitle'),
          softDeleteResult.failed[0]?.error || t('fileExplorer.toasts.hardDeleteFailedMessage'),
        )
        return false
      }

      const hardDeleteResult = await batchDeleteTrash({
        ids: softDeleteResult.success.map((id) => String(id)),
      })

      const failedCount = softDeleteResult.failed.length + hardDeleteResult.failed.length
      if (failedCount === 0) {
        message.success(
          t('fileExplorer.toasts.hardDeleteSuccessTitle'),
          t('fileExplorer.toasts.hardDeleteSuccessMessage', { count: hardDeleteResult.success }),
        )
      } else if (hardDeleteResult.success > 0) {
        message.warning(
          t('fileExplorer.toasts.hardDeletePartialTitle'),
          t('fileExplorer.toasts.hardDeletePartialMessage', {
            success: hardDeleteResult.success,
            failed: failedCount,
          }),
        )
      } else {
        message.error(t('fileExplorer.toasts.hardDeleteFailedTitle'), t('fileExplorer.toasts.hardDeleteFailedMessage'))
      }

      if (hardDeleteResult.success > 0) {
        await refresh()
        void authStore.refreshMe().catch(() => null)
      }
      return failedCount === 0
    } catch (error) {
      message.error(
        t('fileExplorer.toasts.hardDeleteFailedTitle'),
        normalizeDiskError(error, t('fileExplorer.toasts.hardDeleteFailedMessage')),
      )
      return false
    }
  }

  const goToBreadcrumb = async (targetId: number | string | null) => {
    if (targetId === null) {
      folderStack.value = []
      await load(null)
      return
    }
    if (typeof targetId === 'string') {
      return
    }
    const index = folderStack.value.findIndex((item) => item.id === targetId)
    if (index >= 0) {
      folderStack.value = folderStack.value.slice(0, index + 1)
    } else {
      folderStack.value = []
    }
    await load(targetId)
  }

  return {
    loading,
    path,
    parentId,
    folderStack,
    items,
    total,
    searchKeyword,
    sortedItems,
    sortKey,
    sortOrder,
    setSort,
    load,
    refresh,
    setSearchKeyword,
    suggestAvailableName,
    createFolder,
    renameEntry,
    moveEntry,
    moveEntries,
    removeEntry,
    removeEntries,
    hardRemoveEntries,
    downloadEntry,
    canGoUp,
    openEntry,
    goToBreadcrumb,
  }
}
