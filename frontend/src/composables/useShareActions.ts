import { ref } from 'vue'
import { createShare, deleteShare, listShares, revokeShare, updateShare } from '@/api/modules/shares'
import { useToastStore } from '@/stores/toast'
import type { Share, ShareCreateIn, ShareUpdateIn } from '@/types/share'

export const useShareActions = () => {
  const toast = useToastStore()
  const loading = ref(false)
  const items = ref<Share[]>([])
  const limit = ref(20)
  const currentPage = ref(1)
  const total = ref(0)
  const pages = ref(0)

  const fetchShares = async (page = 1) => {
    loading.value = true
    try {
      const data = await listShares({ page, size: limit.value })
      items.value = data.items || []
      total.value = data.total ?? 0
      pages.value = data.pages ?? 0
      currentPage.value = data.page ?? page
      limit.value = data.size ?? limit.value
    } catch (error) {
      toast.error('加载分享失败', error instanceof Error ? error.message : '请稍后重试')
    } finally {
      loading.value = false
    }
  }

  const setPageSize = async (nextSize: number) => {
    limit.value = nextSize
    await fetchShares(1)
  }

  const create = async (payload: ShareCreateIn) => {
    try {
      const share = await createShare(payload)
      toast.success('分享已创建')
      return share
    } catch (error) {
      toast.error('创建分享失败', error instanceof Error ? error.message : '请稍后重试')
      return null
    }
  }

  const revoke = async (shareId: string) => {
    try {
      await revokeShare(shareId)
      toast.success('已取消分享')
      await fetchShares(currentPage.value)
      return true
    } catch (error) {
      toast.error('取消分享失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  const update = async (shareId: string, payload: ShareUpdateIn) => {
    try {
      const share = await updateShare(shareId, payload)
      toast.success('分享已更新')
      await fetchShares(currentPage.value)
      return share
    } catch (error) {
      toast.error('更新分享失败', error instanceof Error ? error.message : '请稍后重试')
      return null
    }
  }

  const remove = async (shareId: string) => {
    try {
      await deleteShare(shareId)
      toast.success('分享已删除')
      await fetchShares(currentPage.value)
      return true
    } catch (error) {
      toast.error('删除分享失败', error instanceof Error ? error.message : '请稍后重试')
      return false
    }
  }

  return {
    loading,
    items,
    limit,
    currentPage,
    total,
    pages,
    fetchShares,
    setPageSize,
    create,
    revoke,
    update,
    remove,
  }
}
