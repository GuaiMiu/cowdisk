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
      const items = []
      let cursor: string | null | undefined = null
      for (let i = 0; i < 20; i += 1) {
        const data = await getRoleList({ cursor, size: 100 })
        items.push(...(data.items || []))
        cursor = data.next_page
        if (!cursor) {
          break
        }
      }
      options.value = items.map((role) => ({
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
