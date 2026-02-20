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
      const items = []
      let cursor: string | null | undefined = null
      for (let i = 0; i < 20; i += 1) {
        const data = await getMenuList({ cursor, size: 100 })
        items.push(...(data.items || []))
        cursor = data.next_page
        if (!cursor) {
          break
        }
      }
      const nodes = items.map((menu) => ({
        id: menu.id || 0,
        label: menu.name || t('admin.menu.unnamedMenu'),
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
