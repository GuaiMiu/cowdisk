<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
import { useSelection } from '@/composables/useSelection'
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
  { key: 'select', label: '', width: '44px', align: 'center' as const },
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

type SpaceUnit = 'B' | 'KB' | 'MB' | 'GB' | 'TB'
const SPACE_UNIT_FACTORS: Record<SpaceUnit, number> = {
  B: 1,
  KB: 1024,
  MB: 1024 * 1024,
  GB: 1024 * 1024 * 1024,
  TB: 1024 * 1024 * 1024 * 1024,
}
const SPACE_UNITS: readonly SpaceUnit[] = ['KB', 'MB', 'GB', 'TB'] as const

const formOpen = ref(false)
const deleteConfirm = ref(false)
const deleteMode = ref<'single' | 'batch'>('single')
const currentUser = ref<UserOut | null>(null)
const roleOptions = useRoleOptions()
const toggling = ref(new Set<number>())
const selectAllRef = ref<HTMLInputElement | null>(null)
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
const selection = useSelection(() => filteredUsers.value, (item) => String(item.id || ''))
const selectedIds = computed(() =>
  selection.selectedItems.value
    .map((item) => item.id || 0)
    .filter((id) => id > 0),
)

const form = reactive({
  id: 0,
  username: '',
  nickname: '',
  mail: '',
  password: '',
  status: 'true',
  is_superuser: 'false',
  total_space: '',
  total_space_unit: 'GB' as SpaceUnit,
  used_space: '',
  used_space_unit: 'GB' as SpaceUnit,
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
  form.total_space_unit = 'GB'
  form.used_space = ''
  form.used_space_unit = 'GB'
  form.roles = []
  errors.username = ''
  errors.password = ''
  errors.total_space = ''
  errors.used_space = ''
}

const normalizeDisplayNumber = (value: number) => {
  if (!Number.isFinite(value)) {
    return ''
  }
  return Number(value.toFixed(2)).toString()
}

const bytesToSpaceInput = (bytes?: number | null): { value: string; unit: SpaceUnit } => {
  const value = Number(bytes ?? NaN)
  if (!Number.isFinite(value) || value < 0) {
    return { value: '', unit: 'GB' }
  }
  const unitsDesc = [...SPACE_UNITS].reverse()
  for (const unit of unitsDesc) {
    const factor = SPACE_UNIT_FACTORS[unit]
    if (value >= factor) {
      return { value: normalizeDisplayNumber(value / factor), unit }
    }
  }
  return { value: normalizeDisplayNumber(value / SPACE_UNIT_FACTORS.KB), unit: 'KB' }
}

const parseSpaceToBytes = (value: string, unit: SpaceUnit) => {
  if (!value.trim()) {
    return { bytes: undefined, invalid: false as const }
  }
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric < 0) {
    return { bytes: undefined, invalid: true as const }
  }
  return { bytes: Math.round(numeric * SPACE_UNIT_FACTORS[unit]), invalid: false as const }
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
  const totalSpaceInput = bytesToSpaceInput(user.total_space)
  form.total_space = totalSpaceInput.value
  form.total_space_unit = totalSpaceInput.unit
  const usedSpaceInput = bytesToSpaceInput(user.used_space)
  form.used_space = usedSpaceInput.value
  form.used_space_unit = usedSpaceInput.unit
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
  const totalSpaceParsed = parseSpaceToBytes(form.total_space, form.total_space_unit)
  const usedSpaceParsed = parseSpaceToBytes(form.used_space, form.used_space_unit)
  const payload = {
    username: form.username,
    nickname: form.nickname || null,
    mail: form.mail || null,
    status: form.status === 'true',
    is_superuser: form.is_superuser === 'true',
    total_space: totalSpaceParsed.bytes,
    used_space: usedSpaceParsed.bytes,
    roles: form.roles.length ? form.roles : null,
  }
  if (!form.username) {
    errors.username = t('admin.user.errors.usernameRequired')
    return
  }
  if (totalSpaceParsed.invalid) {
    errors.total_space = t('admin.user.errors.totalSpaceInvalid')
    return
  }
  if (usedSpaceParsed.invalid) {
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
  deleteMode.value = 'single'
  currentUser.value = user
  deleteConfirm.value = true
}

const requestBatchDelete = () => {
  if (!selectedIds.value.length) {
    return
  }
  deleteMode.value = 'batch'
  currentUser.value = null
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  if (deleteMode.value === 'batch') {
    const success = await userStore.removeUsers(selectedIds.value)
    if (success) {
      selection.clear()
    }
  } else if (currentUser.value?.id) {
    await userStore.removeUser(currentUser.value.id)
  }
  deleteConfirm.value = false
  currentUser.value = null
}

const deleteMessage = computed(() =>
  deleteMode.value === 'batch'
    ? t('admin.user.bulk.confirmDeleteMessage', { count: selectedIds.value.length })
    : t('admin.user.confirmDeleteMessage'),
)

watch(
  () => selection.indeterminate.value,
  (value) => {
    if (selectAllRef.value) {
      selectAllRef.value.indeterminate = value
    }
  },
  { immediate: true },
)

watch(
  () => filteredUsers.value,
  (items) => {
    const valid = new Set(items.map((item) => String(item.id || '')))
    const next = new Set<string>()
    selection.selected.value.forEach((key) => {
      if (valid.has(key)) {
        next.add(key)
      }
    })
    if (next.size !== selection.selected.value.size) {
      selection.selected.value = next
    }
  },
  { deep: true },
)

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
        <Button
          v-permission="'system:user:delete'"
          variant="ghost"
          :disabled="!selectedIds.length"
          @click="requestBatchDelete"
        >
          {{ t('admin.user.bulk.deleteSelected', { count: selectedIds.length }) }}
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
        <template #head-select>
          <div class="select-cell">
            <input
              ref="selectAllRef"
              type="checkbox"
              :checked="selection.allSelected.value"
              @change="selection.toggleAll()"
            />
          </div>
        </template>
        <template #cell-select="{ row }">
          <div class="select-cell">
            <input
              type="checkbox"
              :checked="selection.isSelected(row)"
              @change="selection.toggle(row)"
            />
          </div>
        </template>
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
      >
        <template #append>
          <select v-model="form.total_space_unit" class="space-unit-select">
            <option v-for="unit in SPACE_UNITS" :key="unit" :value="unit">
              {{ t(`admin.user.spaceUnits.${unit}`) }}
            </option>
          </select>
        </template>
      </Input>
      <Input
        class="form__field"
        v-model="form.used_space"
        size="sm"
        :label="t('admin.user.form.usedSpace')"
        type="number"
        :placeholder="t('admin.common.optional')"
        :error="errors.used_space"
      >
        <template #append>
          <select v-model="form.used_space_unit" class="space-unit-select">
            <option v-for="unit in SPACE_UNITS" :key="unit" :value="unit">
              {{ t(`admin.user.spaceUnits.${unit}`) }}
            </option>
          </select>
        </template>
      </Input>
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
    :message="deleteMessage"
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

.select-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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

.space-unit-select {
  width: auto;
  min-width: 0;
  max-width: 100%;
  height: 100%;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--color-text);
  font-size: 13px;
  cursor: pointer;
}

</style>
