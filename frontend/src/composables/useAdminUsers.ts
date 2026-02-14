import { addUser, deleteUser, editUser, getUserList } from '@/api/modules/adminSystem'
import type { UserAddIn, UserEditIn } from '@/types/user'
import type { UserOut } from '@/types/auth'
import { useCursorCrud } from './useCursorCrud'

export const useAdminUsers = () => {
  const crud = useCursorCrud<UserOut, UserAddIn, UserEditIn, number>({
    list: getUserList,
    create: addUser,
    update: editUser,
    remove: deleteUser,
    messages: {
      listFail: '加载用户失败',
      createSuccess: '用户已创建',
      createFail: '创建用户失败',
      updateSuccess: '用户已更新',
      updateFail: '更新用户失败',
      deleteSuccess: '用户已删除',
      deleteFail: '删除用户失败',
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
    fetchUsers: crud.fetchFirst,
    fetchNext: crud.fetchNext,
    fetchPrev: crud.fetchPrev,
    createUser: crud.createItem,
    updateUser: crud.updateItem,
    removeUser: crud.removeItem,
  }
}
