import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  batchDeleteShares,
  batchUpdateShareStatus,
  createShare,
  listShares,
  updateShare,
} from '@/api/modules/shares'
import { useMessage } from '@/stores/message'
import type { Share, ShareCreateIn, ShareUpdateIn } from '@/types/share'

export const useShareActions = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
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
      message.error(
        t('shares.toasts.loadFailTitle'),
        error instanceof Error ? error.message : t('shares.toasts.loadFailMessage'),
      )
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
      message.success(t('shares.toasts.createSuccessTitle'))
      return share
    } catch (error) {
      message.error(
        t('shares.toasts.createFailTitle'),
        error instanceof Error ? error.message : t('shares.toasts.createFailMessage'),
      )
      return null
    }
  }

  const update = async (shareId: string, payload: ShareUpdateIn) => {
    try {
      const share = await updateShare(shareId, payload)
      message.success(t('shares.toasts.updateSuccessTitle'))
      await fetchShares(currentPage.value)
      return share
    } catch (error) {
      message.error(
        t('shares.toasts.updateFailTitle'),
        error instanceof Error ? error.message : t('shares.toasts.updateFailMessage'),
      )
      return null
    }
  }

  const remove = async (shareId: string) => {
    try {
      await batchDeleteShares({ ids: [shareId] })
      message.success(t('shares.toasts.deleteSuccessTitle'))
      await fetchShares(currentPage.value)
      return true
    } catch (error) {
      message.error(
        t('shares.toasts.deleteFailTitle'),
        error instanceof Error ? error.message : t('shares.toasts.deleteFailMessage'),
      )
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
    update,
    remove,
    revokeBatch: async (ids: string[]) => {
      const result = await batchUpdateShareStatus({ ids, status: 0 })
      await fetchShares(currentPage.value)
      return result
    },
    enableBatch: async (ids: string[]) => {
      const result = await batchUpdateShareStatus({ ids, status: 1 })
      await fetchShares(currentPage.value)
      return result
    },
    removeBatch: async (ids: string[]) => {
      const result = await batchDeleteShares({ ids })
      await fetchShares(currentPage.value)
      return result
    },
  }
}
