import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMenuList } from '@/api/modules/adminSystem'
import { useMessage } from '@/stores/message'

type MenuOption = {
  id: number
  label: string
  description?: string
  pid?: number | null
  sort?: number | null
  children?: MenuOption[]
}

export const useMenuOptions = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const options = ref<MenuOption[]>([])

  const load = async () => {
    try {
      const data = await getMenuList({ page: 1, size: 1000 })
      const nodes = (data.items || []).map((menu) => ({
        id: menu.id || 0,
        label: menu.name || '未命名菜单',
        description: menu.permission_char || '',
        pid: menu.pid ?? null,
        sort: menu.sort ?? 0,
        children: [] as MenuOption[],
      }))

      const map = new Map<number, MenuOption>()
      nodes.forEach((node) => map.set(node.id, node))

      const roots: MenuOption[] = []
      nodes.forEach((node) => {
        const parentId = node.pid
        if (parentId && map.has(parentId)) {
          map.get(parentId)!.children!.push(node)
        } else {
          roots.push(node)
        }
      })

      const sortTree = (items: MenuOption[]) => {
        items.sort((a, b) => (a.sort ?? 0) - (b.sort ?? 0))
        items.forEach((item) => {
          if (item.children?.length) {
            sortTree(item.children)
          }
        })
      }

      sortTree(roots)
      options.value = roots
    } catch (error) {
      message.error(
        t('admin.menu.toasts.loadFailTitle'),
        error instanceof Error ? error.message : t('admin.menu.toasts.loadFailMessage'),
      )
    }
  }

  return {
    options,
    load,
  }
}
