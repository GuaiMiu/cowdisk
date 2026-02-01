import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getRoleList } from '@/api/modules/adminSystem'
import { useMessage } from '@/stores/message'

export const useRoleOptions = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
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
      message.error(
        t('admin.role.toasts.loadFailTitle'),
        error instanceof Error ? error.message : t('admin.role.toasts.loadFailMessage'),
      )
    }
  }

  return {
    options,
    load,
  }
}
