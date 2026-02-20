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
import TreeCheckList from '@/components/common/TreeCheckList.vue'
import Switch from '@/components/common/Switch.vue'
import { useAdminRoles } from '@/composables/useAdminRoles'
import { useMenuOptions } from '@/composables/useMenuOptions'
import { useSelection } from '@/composables/useSelection'
import { formatTime } from '@/utils/format'
import type { RoleOut } from '@/types/role'
import { getRoleDetail } from '@/api/modules/adminSystem'
import { getRouteSearchKeyword } from '@/composables/useHeaderSearch'

const roleStore = useAdminRoles()
const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const columns = computed(() => [
  { key: 'select', label: '', width: '44px', align: 'center' as const },
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
const deleteMode = ref<'single' | 'batch'>('single')
const currentRole = ref<RoleOut | null>(null)
const menuOptions = useMenuOptions()
const toggling = ref(new Set<number>())
const selectAllRef = ref<HTMLInputElement | null>(null)
const searchKeyword = computed(() => getRouteSearchKeyword(route).toLowerCase())
const filteredRoles = computed(() => {
  const keyword = searchKeyword.value
  if (!keyword) {
    return roleStore.items.value
  }
  return roleStore.items.value.filter((role) => {
    const name = (role.name || '').toLowerCase()
    const permission = (role.permission_char || '').toLowerCase()
    const description = (role.description || '').toLowerCase()
    return name.includes(keyword) || permission.includes(keyword) || description.includes(keyword)
  })
})
const selection = useSelection(() => filteredRoles.value, (item) => String(item.id || ''))
const selectedIds = computed(() =>
  selection.selectedItems.value
    .map((item) => item.id || 0)
    .filter((id) => id > 0),
)

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
  deleteMode.value = 'single'
  currentRole.value = role
  deleteConfirm.value = true
}

const requestBatchDelete = () => {
  if (!selectedIds.value.length) {
    return
  }
  deleteMode.value = 'batch'
  currentRole.value = null
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  if (deleteMode.value === 'batch') {
    const success = await roleStore.removeRoles(selectedIds.value)
    if (success) {
      selection.clear()
    }
  } else if (currentRole.value?.id) {
    await roleStore.removeRole(currentRole.value.id)
  }
  deleteConfirm.value = false
  currentRole.value = null
}

const deleteMessage = computed(() =>
  deleteMode.value === 'batch'
    ? t('admin.role.bulk.confirmDeleteMessage', { count: selectedIds.value.length })
    : t('admin.role.confirmDeleteMessage'),
)

const isToggling = (id?: number) => (id ? toggling.value.has(id) : false)

const toggleStatus = async (row: RoleOut, next: boolean) => {
  if (!row.id || toggling.value.has(row.id)) {
    return
  }
  toggling.value = new Set(toggling.value).add(row.id)
  try {
    const detail = await getRoleDetail(row.id)
    const menus = (detail.menus || row.menus || [])
      .map((menu) => menu.id || 0)
      .filter((id) => id > 0)
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

onMounted(() => {
  void roleStore.fetchRoles()
  void menuOptions.load()
})

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
  () => filteredRoles.value,
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
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.role.title')" :subtitle="t('admin.role.subtitle')">
      <template #actions>
        <Button variant="secondary" @click="roleStore.fetchRoles()">
          {{ t('admin.role.refresh') }}
        </Button>
        <Button
          v-permission="'system:role:delete'"
          variant="ghost"
          :disabled="!selectedIds.length"
          @click="requestBatchDelete"
        >
          {{ t('admin.role.bulk.deleteSelected', { count: selectedIds.length }) }}
        </Button>
        <Button v-permission="'system:role:create'" @click="openCreate">{{
          t('admin.role.add')
        }}</Button>
      </template>
    </PageHeader>

    <div class="table-wrap">
      <Table
        :columns="columns"
        :rows="filteredRoles"
        :min-rows="roleStore.size.value"
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
            :disabled="isToggling(row.id)"
            @update:modelValue="(value: boolean) => toggleStatus(row, value)"
          />
        </template>
        <template #cell-update_time="{ row }">
          {{ formatTime(row.update_time as string) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <Button
              size="sm"
              variant="secondary"
              v-permission="'system:role:update'"
              @click="openEdit(row)"
            >
              {{ t('common.edit') }}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              v-permission="'system:role:delete'"
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
      :total="roleStore.total.value"
      :has-prev="!!roleStore.hasPrev.value"
      :has-next="!!roleStore.hasNext.value"
      :page-size="roleStore.size.value"
      :current-page="roleStore.page.value"
      @prev="roleStore.fetchPrev"
      @next="roleStore.fetchNext"
      @update:pageSize="
        (size) => {
          roleStore.size.value = size
          roleStore.fetchRoles()
        }
      "
    />
  </section>

  <Modal
    :open="formOpen"
    :width="760"
    :title="form.id ? t('admin.role.modal.editTitle') : t('admin.role.modal.createTitle')"
    @close="formOpen = false"
  >
    <div class="form">
      <Input
        class="form__field"
        v-model="form.name"
        size="sm"
        :label="t('admin.role.form.name')"
        :placeholder="t('admin.role.placeholders.name')"
        :error="errors.name"
      />
      <Input
        class="form__field"
        v-model="form.permission_char"
        size="sm"
        :label="t('admin.role.form.permission')"
        :placeholder="t('admin.role.placeholders.permission')"
      />
      <Input
        class="form__field form__field--full"
        v-model="form.description"
        size="sm"
        :label="t('admin.role.form.description')"
        :placeholder="t('admin.common.optional')"
      />
      <Select
        class="form__field"
        v-model="form.status"
        size="sm"
        :label="t('admin.role.form.status')"
        :options="statusOptions"
      />
      <div class="form__menus form__field--full">
        <div class="form__label">{{ t('admin.role.form.menus') }}</div>
        <TreeCheckList
          v-model="form.menus"
          :items="menuOptions.options.value"
          :empty-text="t('admin.role.menusEmpty')"
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
    :title="t('admin.role.confirmDeleteTitle')"
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

.form__menus {
  display: grid;
  gap: var(--space-1);
}

.form__label {
  font-size: 12px;
  color: var(--color-muted);
}

</style>

