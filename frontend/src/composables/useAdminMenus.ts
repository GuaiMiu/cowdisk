import { addMenu, deleteMenu, editMenu, getMenuList } from '@/api/modules/adminSystem'
import type { MenuAddIn, MenuEditIn, MenuOut } from '@/types/menu'
import { useCursorCrud } from './useCursorCrud'
import { useI18n } from 'vue-i18n'

export const useAdminMenus = () => {
  const { t } = useI18n({ useScope: 'global' })
  const crud = useCursorCrud<MenuOut, MenuAddIn, MenuEditIn, number>({
    list: getMenuList,
    create: addMenu,
    update: editMenu,
    remove: deleteMenu,
    initialSize: 100,
    messages: {
      listFail: t('admin.menu.crud.listFail'),
      createSuccess: t('admin.menu.crud.createSuccess'),
      createFail: t('admin.menu.crud.createFail'),
      updateSuccess: t('admin.menu.crud.updateSuccess'),
      updateFail: t('admin.menu.crud.updateFail'),
      deleteSuccess: t('admin.menu.crud.deleteSuccess'),
      deleteFail: t('admin.menu.crud.deleteFail'),
    },
  })

  return {
    loading: crud.loading,
    items: crud.items,
    total: crud.total,
    page: crud.page,
    size: crud.size,
    hasNext: crud.hasNext,
    hasPrev: crud.hasPrev,
    fetchMenus: crud.fetchFirst,
    fetchNext: crud.fetchNext,
    fetchPrev: crud.fetchPrev,
    createMenu: crud.createItem,
    updateMenu: crud.updateItem,
    removeMenu: crud.removeItem,
  }
}
