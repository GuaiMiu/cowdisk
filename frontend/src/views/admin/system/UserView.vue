<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import CheckList from '@/components/common/CheckList.vue'
import Switch from '@/components/common/Switch.vue'
import { useAdminUsers } from '@/composables/useAdminUsers'
import { formatTime } from '@/utils/format'
import { useRoleOptions } from '@/composables/useRoleOptions'
import type { UserOut } from '@/types/auth'
import { useAuthStore } from '@/stores/auth'
import { useMessage } from '@/stores/message'
import { getRouteSearchKeyword } from '@/composables/useHeaderSearch'

const userStore = useAdminUsers()
const authStore = useAuthStore()
const message = useMessage()
const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const columns = computed(() => [
  { key: 'username', label: t('admin.user.columns.username') },
  { key: 'nickname', label: t('admin.user.columns.nickname') },
  { key: 'mail', label: t('admin.user.columns.mail') },
  { key: 'status', label: t('admin.user.columns.status') },
  { key: 'create_time', label: t('admin.user.columns.createTime') },
  { key: 'actions', label: t('admin.user.columns.actions'), width: '120px' },
])

const statusOptions = computed(() => [
  { label: t('admin.user.statusOptions.enabled'), value: 'true' },
  { label: t('admin.user.statusOptions.disabled'), value: 'false' },
])

const superOptions = computed(() => [
  { label: t('admin.user.superOptions.no'), value: 'false' },
  { label: t('admin.user.superOptions.yes'), value: 'true' },
])

const formOpen = ref(false)
const deleteConfirm = ref(false)
const currentUser = ref<UserOut | null>(null)
const roleOptions = useRoleOptions()
const toggling = ref(new Set<number>())
const currentUserId = computed(() => authStore.me?.id)
const searchKeyword = computed(() => getRouteSearchKeyword(route).toLowerCase())
const filteredUsers = computed(() => {
  const keyword = searchKeyword.value
  if (!keyword) {
    return userStore.items.value
  }
  return userStore.items.value.filter((user) => {
    const username = (user.username || '').toLowerCase()
    const nickname = (user.nickname || '').toLowerCase()
    const mail = (user.mail || '').toLowerCase()
    return username.includes(keyword) || nickname.includes(keyword) || mail.includes(keyword)
  })
})

const form = reactive({
  id: 0,
  username: '',
  nickname: '',
  mail: '',
  password: '',
  status: 'true',
  is_superuser: 'false',
  total_space: '',
  used_space: '',
  roles: [] as Array<number>,
})

const errors = reactive({
  username: '',
  password: '',
  total_space: '',
  used_space: '',
})

const resetForm = () => {
  form.id = 0
  form.username = ''
  form.nickname = ''
  form.mail = ''
  form.password = ''
  form.status = 'true'
  form.is_superuser = 'false'
  form.total_space = ''
  form.used_space = ''
  form.roles = []
  errors.username = ''
  errors.password = ''
  errors.total_space = ''
  errors.used_space = ''
}

const openCreate = () => {
  resetForm()
  formOpen.value = true
}

const openEdit = (user: UserOut) => {
  form.id = user.id || 0
  form.username = user.username || ''
  form.nickname = user.nickname || ''
  form.mail = user.mail || ''
  form.password = ''
  form.status = user.status ? 'true' : 'false'
  form.is_superuser = user.is_superuser ? 'true' : 'false'
  form.total_space = user.total_space !== undefined ? String(user.total_space) : ''
  form.used_space = user.used_space !== undefined ? String(user.used_space) : ''
  form.roles = (user.roles || []).map((role) => role.id || 0).filter((id) => id > 0)
  errors.username = ''
  errors.password = ''
  errors.total_space = ''
  errors.used_space = ''
  formOpen.value = true
}

const submitForm = async () => {
  errors.username = ''
  errors.password = ''
  errors.total_space = ''
  errors.used_space = ''
  const totalSpaceValue = form.total_space ? Number(form.total_space) : undefined
  const usedSpaceValue = form.used_space ? Number(form.used_space) : undefined
  const payload = {
    username: form.username,
    nickname: form.nickname || null,
    mail: form.mail || null,
    status: form.status === 'true',
    is_superuser: form.is_superuser === 'true',
    total_space: totalSpaceValue,
    used_space: usedSpaceValue,
    roles: form.roles.length ? form.roles : null,
  }
  if (!form.username) {
    errors.username = t('admin.user.errors.usernameRequired')
    return
  }
  if (form.total_space && Number.isNaN(totalSpaceValue)) {
    errors.total_space = t('admin.user.errors.totalSpaceInvalid')
    return
  }
  if (form.used_space && Number.isNaN(usedSpaceValue)) {
    errors.used_space = t('admin.user.errors.usedSpaceInvalid')
    return
  }
  if (form.id) {
    await userStore.updateUser({
      id: form.id,
      ...payload,
      password: form.password || null,
    })
  } else {
    if (!form.password) {
      errors.password = t('admin.user.errors.passwordRequired')
      return
    }
    await userStore.createUser({
      ...payload,
      password: form.password,
    })
  }
  formOpen.value = false
}

const isToggling = (id?: number) => (id ? toggling.value.has(id) : false)
const isSelf = (id?: number) => !!id && id === currentUserId.value

const toggleStatus = async (row: UserOut, next: boolean) => {
  if (isSelf(row.id)) {
    message.warning(
      t('admin.user.toasts.selfDisableTitle'),
      t('admin.user.toasts.selfDisableMessage'),
    )
    return
  }
  if (!row.id || toggling.value.has(row.id)) {
    return
  }
  toggling.value = new Set(toggling.value).add(row.id)
  try {
    const roles = (row.roles || []).map((role) => role.id || 0).filter((id) => id > 0)
    await userStore.updateUser({
      id: row.id,
      username: row.username || '',
      nickname: row.nickname ?? null,
      mail: row.mail ?? null,
      status: next,
      is_superuser: !!row.is_superuser,
      total_space: row.total_space ?? undefined,
      used_space: row.used_space ?? undefined,
      roles,
      password: null,
    })
  } finally {
    const nextSet = new Set(toggling.value)
    nextSet.delete(row.id)
    toggling.value = nextSet
  }
}

const requestDelete = (user: UserOut) => {
  currentUser.value = user
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  if (currentUser.value?.id) {
    await userStore.removeUser(currentUser.value.id)
  }
  deleteConfirm.value = false
  currentUser.value = null
}

onMounted(() => {
  void userStore.fetchUsers()
  void roleOptions.load()
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.user.title')" :subtitle="t('admin.user.subtitle')">
      <template #actions>
        <Button variant="secondary" @click="userStore.fetchUsers()">
          {{ t('admin.user.refresh') }}
        </Button>
        <Button v-permission="'system:user:create'" @click="openCreate">{{
          t('admin.user.add')
        }}</Button>
      </template>
    </PageHeader>

    <div class="table-wrap">
      <Table
        :columns="columns"
        :rows="filteredUsers"
        :min-rows="userStore.size.value"
        scrollable
        fill
      >
        <template #cell-status="{ row }">
          <Switch
            :model-value="!!row.status"
            :disabled="isToggling(row.id) || isSelf(row.id)"
            @update:modelValue="(value: boolean) => toggleStatus(row, value)"
          />
        </template>
        <template #cell-create_time="{ row }">
          {{ formatTime(row.create_time as string) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <Button
              size="sm"
              variant="secondary"
              v-permission="'system:user:update'"
              @click="openEdit(row)"
            >
              {{ t('common.edit') }}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              v-permission="'system:user:delete'"
              @click="requestDelete(row)"
            >
              {{ t('common.delete') }}
            </Button>
          </div>
        </template>
      </Table>
    </div>

    <Pagination
      cursor-mode
      :total="userStore.total.value"
      :has-prev="!!userStore.hasPrev.value"
      :has-next="!!userStore.hasNext.value"
      :page-size="userStore.size.value"
      :current-page="userStore.page.value"
      @prev="userStore.fetchPrev"
      @next="userStore.fetchNext"
      @update:pageSize="
        (size) => {
          userStore.size.value = size
          userStore.fetchUsers()
        }
      "
    />
  </section>

  <Modal
    :open="formOpen"
    :width="800"
    :title="form.id ? t('admin.user.modal.editTitle') : t('admin.user.modal.createTitle')"
    @close="formOpen = false"
  >
    <div class="form">
      <Input
        class="form__field"
        v-model="form.username"
        size="sm"
        :label="t('admin.user.form.username')"
        :placeholder="t('admin.user.placeholders.username')"
        :error="errors.username"
      />
      <Input
        class="form__field"
        v-model="form.nickname"
        size="sm"
        :label="t('admin.user.form.nickname')"
        :placeholder="t('admin.common.optional')"
      />
      <Input
        class="form__field"
        v-model="form.mail"
        size="sm"
        :label="t('admin.user.form.mail')"
        :placeholder="t('admin.common.optional')"
      />
      <Input
        class="form__field"
        v-model="form.total_space"
        size="sm"
        :label="t('admin.user.form.totalSpace')"
        type="number"
        :placeholder="t('admin.common.optional')"
        :error="errors.total_space"
      />
      <Input
        class="form__field"
        v-model="form.used_space"
        size="sm"
        :label="t('admin.user.form.usedSpace')"
        type="number"
        :placeholder="t('admin.common.optional')"
        :error="errors.used_space"
      />
      <Input
        class="form__field"
        v-model="form.password"
        size="sm"
        :label="t('admin.user.form.password')"
        type="password"
        :placeholder="t('admin.user.placeholders.password')"
        :error="errors.password"
      />
      <Select
        class="form__field"
        v-model="form.status"
        size="sm"
        :label="t('admin.user.form.status')"
        :options="statusOptions"
      />
      <Select
        class="form__field"
        v-model="form.is_superuser"
        size="sm"
        :label="t('admin.user.form.superuser')"
        :options="superOptions"
      />
      <div class="form__roles form__field--full">
        <div class="form__label">{{ t('admin.user.form.roles') }}</div>
        <CheckList
          v-model="form.roles"
          :items="roleOptions.options.value"
          :empty-text="t('admin.user.rolesEmpty')"
        />
      </div>
    </div>
    <template #footer>
      <Button variant="secondary" @click="formOpen = false">{{ t('common.cancel') }}</Button>
      <Button @click="submitForm">{{ t('common.save') }}</Button>
    </template>
  </Modal>

  <ConfirmDialog
    :open="deleteConfirm"
    :title="t('admin.user.confirmDeleteTitle')"
    :message="t('admin.user.confirmDeleteMessage')"
    @close="deleteConfirm = false"
    @confirm="confirmDelete"
  />
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-4);
  height: 100%;
  min-height: 0;
  grid-template-rows: auto 1fr auto;
  overflow: hidden;
}

.table-wrap {
  overflow: auto;
  min-height: 0;
  height: 100%;
}

.actions {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-2) var(--space-3);
}

.form__field {
  min-width: 0;
}

.form__field--full {
  grid-column: 1 / -1;
}

.form__roles {
  display: grid;
  gap: var(--space-1);
}

.form__label {
  font-size: 12px;
  color: var(--color-muted);
}

</style>

