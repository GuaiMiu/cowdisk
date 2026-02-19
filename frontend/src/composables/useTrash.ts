import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { batchDeleteTrash, batchRestoreTrash, clearTrash, listTrash } from '@/api/modules/userDisk'
import { useMessage } from '@/stores/message'
import type { DiskTrashEntry } from '@/types/disk'

export const useTrash = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const loading = ref(false)
  const items = ref<DiskTrashEntry[]>([])

  const fetchTrash = async () => {
    loading.value = true
    try {
      const data = await listTrash()
      items.value = data.items || []
    } catch (error) {
      message.error(
        t('trash.toasts.loadFailTitle'),
        error instanceof Error ? error.message : t('trash.toasts.loadFailMessage'),
      )
    } finally {
      loading.value = false
    }
  }

  const restore = async (entry: DiskTrashEntry) => {
    try {
      await batchRestoreTrash({ ids: [entry.id] })
      message.success(t('trash.toasts.restoreSuccessTitle'), entry.name)
      await fetchTrash()
      return true
    } catch (error) {
      message.error(
        t('trash.toasts.restoreFailTitle'),
        error instanceof Error ? error.message : t('trash.toasts.restoreFailMessage'),
      )
      return false
    }
  }

  const remove = async (entry: DiskTrashEntry) => {
    try {
      await batchDeleteTrash({ ids: [entry.id] })
      message.success(t('trash.toasts.deleteSuccessTitle'), entry.name)
      await fetchTrash()
      return true
    } catch (error) {
      message.error(
        t('trash.toasts.deleteFailTitle'),
        error instanceof Error ? error.message : t('trash.toasts.deleteFailMessage'),
      )
      return false
    }
  }

  const clear = async () => {
    try {
      await clearTrash()
      message.success(t('trash.toasts.clearSuccessTitle'))
      await fetchTrash()
      return true
    } catch (error) {
      message.error(
        t('trash.toasts.clearFailTitle'),
        error instanceof Error ? error.message : t('trash.toasts.clearFailMessage'),
      )
      return false
    }
  }

  return {
    loading,
    items,
    fetchTrash,
    restore,
    remove,
    clear,
    restoreBatch: async (ids: string[]) => {
      const result = await batchRestoreTrash({ ids })
      await fetchTrash()
      return result
    },
    removeBatch: async (ids: string[]) => {
      const result = await batchDeleteTrash({ ids })
      await fetchTrash()
      return result
    },
  }
}
