import { addRole, deleteRole, editRole, getRoleList } from '@/api/modules/adminSystem'
import type { RoleAddIn, RoleEditIn, RoleOut } from '@/types/role'
import { useCursorCrud } from './useCursorCrud'

export const useAdminRoles = () => {
  const crud = useCursorCrud<RoleOut, RoleAddIn, RoleEditIn, number>({
    list: getRoleList,
    create: addRole,
    update: editRole,
    remove: deleteRole,
    messages: {
      listFail: '加载角色失败',
      createSuccess: '角色已创建',
      createFail: '创建角色失败',
      updateSuccess: '角色已更新',
      updateFail: '更新角色失败',
      deleteSuccess: '角色已删除',
      deleteFail: '删除角色失败',
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
    fetchRoles: crud.fetchFirst,
    fetchNext: crud.fetchNext,
    fetchPrev: crud.fetchPrev,
    createRole: crud.createItem,
    updateRole: crud.updateItem,
    removeRole: crud.removeItem,
  }
}
