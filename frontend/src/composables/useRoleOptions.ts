import { ref } from 'vue'
import { getRoleList } from '@/api/modules/adminSystem'
import { useToastStore } from '@/stores/toast'

export const useRoleOptions = () => {
  const toast = useToastStore()
  const options = ref<Array<{ id: number; label: string; description?: string }>>([])

  const load = async () => {
    try {
      const data = await getRoleList({ page: 1, size: 1000 })
      options.value = (data.items || []).map((role) => ({
        id: role.id || 0,
        label: role.name || '未命名角色',
        description: role.permission_char || '',
      }))
    } catch (error) {
      toast.error('加载角色失败', error instanceof Error ? error.message : '请稍后重试')
    }
  }

  return {
    options,
    load,
  }
}
