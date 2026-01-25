import { ref } from 'vue'
import { clearTrash, deleteTrash, listTrash, restoreTrash } from '@/api/modules/userDisk'
import { useToastStore } from '@/stores/toast'
import type { DiskTrashEntry } from '@/types/disk'

export const useTrash = () => {
  const toast = useToastStore()
  const loading = ref(false)
  const items = ref<DiskTrashEntry[]>([])

  const fetchTrash = async () => {
    loading.value = true
    try {
      const data = await listTrash()
      items.value = data.items || []
    } catch (error) {
      toast.error('加载回收站失败', error instanceof Error ? error.message : '请稍后重试')
    } finally {
      loading.value = false
    }
  }

  const restore = async (entry: DiskTrashEntry) => {
    try {
      await restoreTrash({ id: entry.id })
      toast.success('已恢复')
      await fetchTrash()
      return true
    } catch (error) {
      toast.error('恢复失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const remove = async (entry: DiskTrashEntry) => {
    try {
      await deleteTrash({ id: entry.id })
      toast.success('已删除')
      await fetchTrash()
      return true
    } catch (error) {
      toast.error('删除失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const clear = async () => {
    try {
      await clearTrash()
      toast.success('回收站已清空')
      await fetchTrash()
      return true
    } catch (error) {
      toast.error('清空失败', error instanceof Error ? error.message : '请稍后重试')
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
  }
}
