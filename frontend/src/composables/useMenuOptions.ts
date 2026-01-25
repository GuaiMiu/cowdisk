import { ref } from 'vue'
import { getMenuList } from '@/api/modules/adminSystem'
import { useToastStore } from '@/stores/toast'

export const useMenuOptions = () => {
  const toast = useToastStore()
  const options = ref<Array<{ id: number; label: string; description?: string }>>([])

  const load = async () => {
    try {
      const data = await getMenuList({ page: 1, size: 1000 })
      options.value = (data.items || []).map((menu) => ({
        id: menu.id || 0,
        label: menu.name || '未命名菜单',
        description: menu.permission_char || '',
      }))
    } catch (error) {
      toast.error('加载菜单失败', error instanceof Error ? error.message : '请稍后重试')
    }
  }

  return {
    options,
    load,
  }
}
