import { addUser, deleteUser, deleteUsers, editUser, getUserList } from '@/api/modules/adminSystem'
import type { UserAddIn, UserEditIn } from '@/types/user'
import type { UserOut } from '@/types/auth'
import { useCursorCrud } from './useCursorCrud'
import { useMessage } from '@/stores/message'
import { useI18n } from 'vue-i18n'

export const useAdminUsers = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const crud = useCursorCrud<UserOut, UserAddIn, UserEditIn, number>({
    list: getUserList,
    create: addUser,
    update: editUser,
    remove: deleteUser,
    messages: {
      listFail: t('admin.user.crud.listFail'),
      createSuccess: t('admin.user.crud.createSuccess'),
      createFail: t('admin.user.crud.createFail'),
      updateSuccess: t('admin.user.crud.updateSuccess'),
      updateFail: t('admin.user.crud.updateFail'),
      deleteSuccess: t('admin.user.crud.deleteSuccess'),
      deleteFail: t('admin.user.crud.deleteFail'),
    },
  })

  const removeUsers = async (ids: number[]) => {
    if (!ids.length) {
      return false
    }
    try {
      await deleteUsers({ ids })
      message.success(t('admin.user.crud.deleteSuccess'))
      await crud.fetchFirst()
      return true
    } catch (error) {
      message.error(
        t('admin.user.crud.deleteFail'),
        error instanceof Error ? error.message : t('common.retryLater'),
      )
      return false
    }
  }

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
    removeUsers,
  }
}
