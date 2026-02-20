import { addRole, deleteRole, deleteRoles, editRole, getRoleList } from '@/api/modules/adminSystem'
import type { RoleAddIn, RoleEditIn, RoleOut } from '@/types/role'
import { useCursorCrud } from './useCursorCrud'
import { useMessage } from '@/stores/message'
import { useI18n } from 'vue-i18n'

export const useAdminRoles = () => {
  const { t } = useI18n({ useScope: 'global' })
  const message = useMessage()
  const crud = useCursorCrud<RoleOut, RoleAddIn, RoleEditIn, number>({
    list: getRoleList,
    create: addRole,
    update: editRole,
    remove: deleteRole,
    messages: {
      listFail: t('admin.role.crud.listFail'),
      createSuccess: t('admin.role.crud.createSuccess'),
      createFail: t('admin.role.crud.createFail'),
      updateSuccess: t('admin.role.crud.updateSuccess'),
      updateFail: t('admin.role.crud.updateFail'),
      deleteSuccess: t('admin.role.crud.deleteSuccess'),
      deleteFail: t('admin.role.crud.deleteFail'),
    },
  })

  const removeRoles = async (ids: number[]) => {
    if (!ids.length) {
      return false
    }
    try {
      await deleteRoles({ ids })
      message.success(t('admin.role.crud.deleteSuccess'))
      await crud.fetchFirst()
      return true
    } catch (error) {
      message.error(
        t('admin.role.crud.deleteFail'),
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
    fetchRoles: crud.fetchFirst,
    fetchNext: crud.fetchNext,
    fetchPrev: crud.fetchPrev,
    createRole: crud.createItem,
    updateRole: crud.updateItem,
    removeRole: crud.removeItem,
    removeRoles,
  }
}
