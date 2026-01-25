import { ref } from 'vue'
import { useToastStore } from '@/stores/toast'

type PageResult<T> = {
  items?: T[]
  total?: number
  page?: number
  size?: number
  pages?: number
}

type Messages = {
  listFail: string
  createSuccess?: string
  createFail?: string
  updateSuccess?: string
  updateFail?: string
  deleteSuccess?: string
  deleteFail?: string
}

export const usePagedCrud = <TItem, TCreate = unknown, TUpdate = unknown, TDelete = unknown>(config: {
  list: (params: { page: number; size: number }) => Promise<PageResult<TItem>>
  create?: (payload: TCreate) => Promise<TItem>
  update?: (payload: TUpdate) => Promise<TItem>
  remove?: (payload: TDelete) => Promise<unknown>
  messages: Messages
  initialSize?: number
}) => {
  const toast = useToastStore()
  const loading = ref(false)
  const items = ref<TItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(config.initialSize ?? 20)
  const pages = ref(0)

  const fetchPage = async (nextPage = page.value) => {
    loading.value = true
    try {
      const data = await config.list({ page: nextPage, size: size.value })
      items.value = data.items || []
      total.value = data.total ?? 0
      page.value = data.page ?? nextPage
      size.value = data.size ?? size.value
      pages.value = data.pages ?? pages.value
    } catch (error) {
      toast.error(config.messages.listFail, error instanceof Error ? error.message : '请稍后重试')
    } finally {
      loading.value = false
    }
  }

  const createItem = async (payload: TCreate) => {
    if (!config.create) {
      return null
    }
    try {
      const data = await config.create(payload)
      if (config.messages.createSuccess) {
        toast.success(config.messages.createSuccess)
      }
      await fetchPage()
      return data
    } catch (error) {
      if (config.messages.createFail) {
        toast.error(config.messages.createFail, error instanceof Error ? error.message : '请稍后重试')
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
        toast.success(config.messages.updateSuccess)
      }
      await fetchPage()
      return data
    } catch (error) {
      if (config.messages.updateFail) {
        toast.error(config.messages.updateFail, error instanceof Error ? error.message : '请稍后重试')
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
        toast.success(config.messages.deleteSuccess)
      }
      await fetchPage()
      return true
    } catch (error) {
      if (config.messages.deleteFail) {
        toast.error(config.messages.deleteFail, error instanceof Error ? error.message : '请稍后重试')
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
    pages,
    fetchPage,
    createItem,
    updateItem,
    removeItem,
  }
}
