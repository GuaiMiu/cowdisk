<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Table from '@/components/common/Table.vue'
import Tag from '@/components/common/Tag.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import CheckList from '@/components/common/CheckList.vue'
import { useAdminRoles } from '@/composables/useAdminRoles'
import { useMenuOptions } from '@/composables/useMenuOptions'
import { formatTime } from '@/utils/format'
import type { RoleOut } from '@/types/role'

const roleStore = useAdminRoles()
const columns = [
  { key: 'name', label: '角色名称' },
  { key: 'permission_char', label: '权限标识' },
  { key: 'status', label: '状态' },
  { key: 'update_time', label: '更新时间' },
  { key: 'actions', label: '操作' },
]

const statusOptions = [
  { label: '启用', value: 'true' },
  { label: '禁用', value: 'false' },
]

const formOpen = ref(false)
const deleteConfirm = ref(false)
const currentRole = ref<RoleOut | null>(null)
const menuOptions = useMenuOptions()
const keyword = ref('')
const statusFilter = ref('all')

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
    errors.name = '请输入角色名称'
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
    <PageHeader title="角色管理" subtitle="定义角色与授权范围">
      <template #actions>
        <Button variant="secondary" @click="roleStore.fetchRoles(roleStore.page.value)">刷新</Button>
        <Button v-permission="'system:role:add'" @click="openCreate">新增角色</Button>
      </template>
    </PageHeader>

    <div class="filters">
      <Input v-model="keyword" label="搜索" placeholder="角色名称 / 权限标识" />
      <Select
        v-model="statusFilter"
        label="状态"
        :options="[
          { label: '全部', value: 'all' },
          { label: '启用', value: 'true' },
          { label: '禁用', value: 'false' },
        ]"
      />
    </div>

    <div class="table-wrap">
      <Table :columns="columns" :rows="filteredRoles" :min-rows="roleStore.size.value">
        <template #cell-status="{ row }">
          <Tag :tone="row.status ? 'success' : 'warning'">{{ row.status ? '启用' : '禁用' }}</Tag>
        </template>
        <template #cell-update_time="{ row }">
          {{ formatTime(row.update_time as string) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <Button size="sm" variant="secondary" v-permission="'system:role:edit'" @click="openEdit(row)">
              编辑
            </Button>
            <Button size="sm" variant="ghost" v-permission="'system:role:delete'" @click="requestDelete(row)">
              删除
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

  <Modal :open="formOpen" :title="form.id ? '编辑角色' : '新增角色'" @close="formOpen = false">
    <div class="form">
      <Input v-model="form.name" label="角色名称" placeholder="请输入角色名称" :error="errors.name" />
      <Input v-model="form.permission_char" label="权限标识" placeholder="例如 system:role" />
      <Input v-model="form.description" label="描述" placeholder="可选" />
      <Select v-model="form.status" label="状态" :options="statusOptions" />
      <div class="form__menus">
        <div class="form__label">菜单权限</div>
        <CheckList v-model="form.menus" :items="menuOptions.options.value" empty-text="暂无菜单可选" />
      </div>
    </div>
    <template #footer>
      <Button variant="secondary" @click="formOpen = false">取消</Button>
      <Button @click="submitForm">保存</Button>
    </template>
  </Modal>

  <ConfirmDialog
    :open="deleteConfirm"
    title="确认删除角色"
    message="删除后角色权限将失效，是否继续？"
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
}

.actions {
  display: flex;
  justify-content: flex-end;
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
