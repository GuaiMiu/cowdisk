import { addMenu, deleteMenu, editMenu, getMenuList } from '@/api/modules/adminSystem'
import type { MenuAddIn, MenuEditIn, MenuOut } from '@/types/menu'
import { useCursorCrud } from './useCursorCrud'

export const useAdminMenus = () => {
  const crud = useCursorCrud<MenuOut, MenuAddIn, MenuEditIn, number>({
    list: getMenuList,
    create: addMenu,
    update: editMenu,
    remove: deleteMenu,
    initialSize: 100,
    messages: {
      listFail: '加载菜单失败',
      createSuccess: '菜单已创建',
      createFail: '创建菜单失败',
      updateSuccess: '菜单已更新',
      updateFail: '更新菜单失败',
      deleteSuccess: '菜单已删除',
      deleteFail: '删除菜单失败',
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
