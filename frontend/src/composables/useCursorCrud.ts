import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from '@/stores/message'
import type { CursorPageResult } from '@/types/pagination'

type Messages = {
  listFail: string
  createSuccess?: string
  createFail?: string
  updateSuccess?: string
  updateFail?: string
  deleteSuccess?: string
  deleteFail?: string
}

export const useCursorCrud = <
  TItem,
  TCreate = unknown,
  TUpdate = unknown,
  TDelete = unknown,
>(config: {
  list: (params: { cursor?: string | null; size: number }) => Promise<CursorPageResult<TItem>>
  create?: (payload: TCreate) => Promise<TItem>
  update?: (payload: TUpdate) => Promise<TItem>
  remove?: (payload: TDelete) => Promise<unknown>
  messages: Messages
  initialSize?: number
}) => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const loading = ref(false)
  const items = ref<TItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(config.initialSize ?? 20)
  const currentCursor = ref<string | null>(null)
  const nextCursor = ref<string | null>(null)
  const prevCursor = ref<string | null>(null)

  const applyPage = (data: CursorPageResult<TItem>, direction: 'reset' | 'next' | 'prev') => {
    items.value = data.items || []
    total.value = data.total ?? total.value
    currentCursor.value = data.current_page ?? null
    nextCursor.value = data.next_page ?? null
    prevCursor.value = data.previous_page ?? null
    if (direction === 'reset') {
      page.value = 1
      return
    }
    if (direction === 'next') {
      page.value += 1
      return
    }
    if (direction === 'prev') {
      page.value = Math.max(1, page.value - 1)
    }
  }

  const fetchPage = async (cursor: string | null = null, direction: 'reset' | 'next' | 'prev' = 'reset') => {
    loading.value = true
    try {
      const data = await config.list({ cursor, size: size.value })
      applyPage(data, direction)
    } catch (error) {
      message.error(
        config.messages.listFail,
        error instanceof Error ? error.message : t('common.retryLater'),
      )
    } finally {
      loading.value = false
    }
  }

  const fetchFirst = async () => fetchPage(null, 'reset')
  const fetchNext = async () => {
    if (!nextCursor.value) {
      return
    }
    await fetchPage(nextCursor.value, 'next')
  }
  const fetchPrev = async () => {
    if (!prevCursor.value) {
      return
    }
    await fetchPage(prevCursor.value, 'prev')
  }

  const createItem = async (payload: TCreate) => {
    if (!config.create) {
      return null
    }
    try {
      const data = await config.create(payload)
      if (config.messages.createSuccess) {
        message.success(config.messages.createSuccess)
      }
      await fetchFirst()
      return data
    } catch (error) {
      if (config.messages.createFail) {
        message.error(
          config.messages.createFail,
          error instanceof Error ? error.message : t('common.retryLater'),
        )
      }
      return null
    }
  }

  const updateItem = async (payload: TUpdate) => {
    if (!config.update) {
      return null
    }
    try {
      const data = await config.update(payload)
      if (config.messages.updateSuccess) {
        message.success(config.messages.updateSuccess)
      }
      await fetchFirst()
      return data
    } catch (error) {
      if (config.messages.updateFail) {
        message.error(
          config.messages.updateFail,
          error instanceof Error ? error.message : t('common.retryLater'),
        )
      }
      return null
    }
  }

  const removeItem = async (payload: TDelete) => {
    if (!config.remove) {
      return false
    }
    try {
      await config.remove(payload)
      if (config.messages.deleteSuccess) {
        message.success(config.messages.deleteSuccess)
      }
      await fetchFirst()
      return true
    } catch (error) {
      if (config.messages.deleteFail) {
        message.error(
          config.messages.deleteFail,
          error instanceof Error ? error.message : t('common.retryLater'),
        )
      }
      return false
    }
  }

  return {
    loading,
    items,
    total,
    page,
    size,
    currentCursor,
    nextCursor,
    prevCursor,
    hasNext: nextCursor,
    hasPrev: prevCursor,
    fetchFirst,
    fetchNext,
    fetchPrev,
    createItem,
    updateItem,
    removeItem,
  }
}
