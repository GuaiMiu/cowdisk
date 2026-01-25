import { addMenu, deleteMenu, editMenu, getMenuList } from '@/api/modules/adminSystem'
import type { MenuAddIn, MenuEditIn, MenuOut } from '@/types/menu'
import { usePagedCrud } from './usePagedCrud'

export const useAdminMenus = () => {
  const crud = usePagedCrud<MenuOut, MenuAddIn, MenuEditIn, number>({
    list: getMenuList,
    create: addMenu,
    update: editMenu,
    remove: deleteMenu,
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
    fetchMenus: crud.fetchPage,
    createMenu: crud.createItem,
    updateMenu: crud.updateItem,
    removeMenu: crud.removeItem,
  }
}
