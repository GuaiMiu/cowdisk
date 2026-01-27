<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Table from '@/components/common/Table.vue'
import Tag from '@/components/common/Tag.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import TreeCheckList from '@/components/common/TreeCheckList.vue'
import Switch from '@/components/common/Switch.vue'
import { useAdminRoles } from '@/composables/useAdminRoles'
import { useMenuOptions } from '@/composables/useMenuOptions'
import { formatTime } from '@/utils/format'
import type { RoleOut } from '@/types/role'
import { getRoleDetail } from '@/api/modules/adminSystem'

const roleStore = useAdminRoles()
const { t } = useI18n({ useScope: 'global' })
const columns = computed(() => [
  { key: 'name', label: t('admin.role.columns.name') },
  { key: 'permission_char', label: t('admin.role.columns.permission') },
  { key: 'status', label: t('admin.role.columns.status') },
  { key: 'update_time', label: t('admin.role.columns.updateTime') },
  { key: 'actions', label: t('admin.role.columns.actions'), width: '120px' },
])

const statusOptions = computed(() => [
  { label: t('admin.role.statusOptions.enabled'), value: 'true' },
  { label: t('admin.role.statusOptions.disabled'), value: 'false' },
])

const formOpen = ref(false)
const deleteConfirm = ref(false)
const currentRole = ref<RoleOut | null>(null)
const menuOptions = useMenuOptions()
const keyword = ref('')
const statusFilter = ref('all')
const toggling = ref(new Set<number>())

const form = reactive({
  id: 0,
  name: '',
  permission_char: '',
  description: '',
  status: 'true',
  menus: [] as Array<number>,
})

const errors = reactive({
  name: '',
})

const resetForm = () => {
  form.id = 0
  form.name = ''
  form.permission_char = ''
  form.description = ''
  form.status = 'true'
  form.menus = []
  errors.name = ''
}

const openCreate = () => {
  resetForm()
  formOpen.value = true
}

const openEdit = (role: RoleOut) => {
  form.id = role.id || 0
  form.name = role.name || ''
  form.permission_char = role.permission_char || ''
  form.description = role.description || ''
  form.status = role.status ? 'true' : 'false'
  form.menus = (role.menus || []).map((menu) => menu.id || 0).filter((id) => id > 0)
  errors.name = ''
  formOpen.value = true
}

const submitForm = async () => {
  errors.name = ''
  if (!form.name) {
    errors.name = t('admin.role.errors.nameRequired')
    return
  }
  const payload = {
    name: form.name,
    permission_char: form.permission_char || null,
    description: form.description || null,
    status: form.status === 'true',
    menus: form.menus.length ? form.menus : null,
  }
  if (form.id) {
    await roleStore.updateRole({ id: form.id, ...payload })
  } else {
    await roleStore.createRole(payload)
  }
  formOpen.value = false
}

const requestDelete = (role: RoleOut) => {
  currentRole.value = role
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  if (currentRole.value?.id) {
    await roleStore.removeRole(currentRole.value.id)
  }
  deleteConfirm.value = false
  currentRole.value = null
}

const isToggling = (id?: number) => (id ? toggling.value.has(id) : false)

const toggleStatus = async (row: RoleOut, next: boolean) => {
  if (!row.id || toggling.value.has(row.id)) {
    return
  }
  toggling.value = new Set(toggling.value).add(row.id)
  try {
    const detail = await getRoleDetail(row.id)
    const menus = (detail.menus || row.menus || []).map((menu) => menu.id || 0).filter((id) => id > 0)
    await roleStore.updateRole({
      id: row.id,
      name: row.name || '',
      permission_char: row.permission_char || null,
      description: row.description || null,
      status: next,
      menus,
    })
  } finally {
    const nextSet = new Set(toggling.value)
    nextSet.delete(row.id)
    toggling.value = nextSet
  }
}

const filteredRoles = computed(() => {
  const keywordValue = keyword.value.trim().toLowerCase()
  return roleStore.items.value.filter((role) => {
    const statusMatch =
      statusFilter.value === 'all' ||
      (statusFilter.value === 'true' ? !!role.status : !role.status)
    if (!statusMatch) {
      return false
    }
    if (!keywordValue) {
      return true
    }
    return [role.name, role.permission_char, role.description]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(keywordValue))
  })
})

onMounted(() => {
  void roleStore.fetchRoles()
  void menuOptions.load()
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.role.title')" :subtitle="t('admin.role.subtitle')">
      <template #actions>
        <Button variant="secondary" @click="roleStore.fetchRoles(roleStore.page.value)">
          {{ t('admin.role.refresh') }}
        </Button>
        <Button v-permission="'system:role:add'" @click="openCreate">{{ t('admin.role.add') }}</Button>
      </template>
    </PageHeader>

    <div class="filters">
      <Input v-model="keyword" :label="t('admin.role.searchLabel')" :placeholder="t('admin.role.searchPlaceholder')" />
      <Select
        v-model="statusFilter"
        :label="t('admin.role.statusLabel')"
        :options="[
          { label: t('admin.role.statusOptions.all'), value: 'all' },
          { label: t('admin.role.statusOptions.enabled'), value: 'true' },
          { label: t('admin.role.statusOptions.disabled'), value: 'false' },
        ]"
      />
    </div>

    <div class="table-wrap">
      <Table :columns="columns" :rows="filteredRoles" :min-rows="roleStore.size.value" scrollable fill>
        <template #cell-status="{ row }">
          <Switch :model-value="!!row.status" :disabled="isToggling(row.id)" @update:modelValue="toggleStatus(row, $event)" />
        </template>
        <template #cell-update_time="{ row }">
          {{ formatTime(row.update_time as string) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <Button size="sm" variant="secondary" v-permission="'system:role:edit'" @click="openEdit(row)">
              {{ t('common.edit') }}
            </Button>
            <Button size="sm" variant="ghost" v-permission="'system:role:delete'" @click="requestDelete(row)">
              {{ t('common.delete') }}
            </Button>
          </div>
        </template>
      </Table>
    </div>

    <Pagination
      :total="roleStore.total.value"
      :page-size="roleStore.size.value"
      :current-page="roleStore.page.value"
      @update:currentPage="roleStore.fetchRoles"
      @update:pageSize="(size) => { roleStore.size.value = size; roleStore.fetchRoles(1) }"
    />
  </section>

  <Modal
    :open="formOpen"
    :title="form.id ? t('admin.role.modal.editTitle') : t('admin.role.modal.createTitle')"
    @close="formOpen = false"
  >
    <div class="form">
      <Input
        v-model="form.name"
        :label="t('admin.role.form.name')"
        :placeholder="t('admin.role.placeholders.name')"
        :error="errors.name"
      />
      <Input
        v-model="form.permission_char"
        :label="t('admin.role.form.permission')"
        :placeholder="t('admin.role.placeholders.permission')"
      />
      <Input
        v-model="form.description"
        :label="t('admin.role.form.description')"
        :placeholder="t('admin.common.optional')"
      />
      <Select v-model="form.status" :label="t('admin.role.form.status')" :options="statusOptions" />
      <div class="form__menus">
        <div class="form__label">{{ t('admin.role.form.menus') }}</div>
        <TreeCheckList v-model="form.menus" :items="menuOptions.options.value" :empty-text="t('admin.role.menusEmpty')" />
      </div>
    </div>
    <template #footer>
      <Button variant="secondary" @click="formOpen = false">{{ t('common.cancel') }}</Button>
      <Button @click="submitForm">{{ t('common.save') }}</Button>
    </template>
  </Modal>

  <ConfirmDialog
    :open="deleteConfirm"
    :title="t('admin.role.confirmDeleteTitle')"
    :message="t('admin.role.confirmDeleteMessage')"
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
  grid-template-rows: auto auto 1fr auto;
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
  gap: var(--space-3);
}

.form__menus {
  display: grid;
  gap: var(--space-2);
}

.form__label {
  font-size: 13px;
  color: var(--color-muted);
}

.filters {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(180px, 240px);
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

@media (max-width: 768px) {
  .filters {
    grid-template-columns: 1fr;
  }
}
</style>
