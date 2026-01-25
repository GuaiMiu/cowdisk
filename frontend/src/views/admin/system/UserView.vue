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
import { useAdminUsers } from '@/composables/useAdminUsers'
import { formatTime } from '@/utils/format'
import { useRoleOptions } from '@/composables/useRoleOptions'
import type { UserOut } from '@/types/auth'

const userStore = useAdminUsers()
const columns = [
  { key: 'username', label: '用户名' },
  { key: 'nickname', label: '昵称' },
  { key: 'mail', label: '邮箱' },
  { key: 'status', label: '状态' },
  { key: 'create_time', label: '创建时间' },
  { key: 'actions', label: '操作' },
]

const statusOptions = [
  { label: '启用', value: 'true' },
  { label: '禁用', value: 'false' },
]

const superOptions = [
  { label: '否', value: 'false' },
  { label: '是', value: 'true' },
]

const formOpen = ref(false)
const deleteConfirm = ref(false)
const currentUser = ref<UserOut | null>(null)
const roleOptions = useRoleOptions()
const keyword = ref('')
const statusFilter = ref('all')

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
    errors.username = '请输入用户名'
    return
  }
  if (form.total_space && Number.isNaN(totalSpaceValue)) {
    errors.total_space = '请输入有效数字'
    return
  }
  if (form.used_space && Number.isNaN(usedSpaceValue)) {
    errors.used_space = '请输入有效数字'
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
      errors.password = '请输入密码'
      return
    }
    await userStore.createUser({
      ...payload,
      password: form.password,
    })
  }
  formOpen.value = false
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

const filteredUsers = computed(() => {
  const keywordValue = keyword.value.trim().toLowerCase()
  return userStore.items.value.filter((user) => {
    const statusMatch =
      statusFilter.value === 'all' ||
      (statusFilter.value === 'true' ? !!user.status : !user.status)
    if (!statusMatch) {
      return false
    }
    if (!keywordValue) {
      return true
    }
    return [user.username, user.nickname, user.mail]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(keywordValue))
  })
})

onMounted(() => {
  void userStore.fetchUsers()
  void roleOptions.load()
})
</script>

<template>
  <section class="page">
    <PageHeader title="用户管理" subtitle="管理系统用户与状态">
      <template #actions>
        <Button variant="secondary" @click="userStore.fetchUsers(userStore.page.value)">刷新</Button>
        <Button v-permission="'system:user:add'" @click="openCreate">新增用户</Button>
      </template>
    </PageHeader>

    <div class="filters">
      <Input v-model="keyword" label="搜索" placeholder="用户名 / 昵称 / 邮箱" />
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
      <Table :columns="columns" :rows="filteredUsers" :min-rows="userStore.size.value">
        <template #cell-status="{ row }">
          <Tag :tone="row.status ? 'success' : 'warning'">{{ row.status ? '启用' : '禁用' }}</Tag>
        </template>
        <template #cell-create_time="{ row }">
          {{ formatTime(row.create_time as string) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <Button size="sm" variant="secondary" v-permission="'system:user:edit'" @click="openEdit(row)">
              编辑
            </Button>
            <Button size="sm" variant="ghost" v-permission="'system:user:delete'" @click="requestDelete(row)">
              删除
            </Button>
          </div>
        </template>
      </Table>
    </div>

    <Pagination
      :total="userStore.total.value"
      :page-size="userStore.size.value"
      :current-page="userStore.page.value"
      @update:currentPage="userStore.fetchUsers"
      @update:pageSize="(size) => { userStore.size.value = size; userStore.fetchUsers(1) }"
    />
  </section>

  <Modal :open="formOpen" :title="form.id ? '编辑用户' : '新增用户'" @close="formOpen = false">
    <div class="form">
      <Input v-model="form.username" label="用户名" placeholder="请输入用户名" :error="errors.username" />
      <Input v-model="form.nickname" label="昵称" placeholder="可选" />
      <Input v-model="form.mail" label="邮箱" placeholder="可选" />
      <Input
        v-model="form.total_space"
        label="总空间(字节)"
        type="number"
        placeholder="可选"
        :error="errors.total_space"
      />
      <Input
        v-model="form.used_space"
        label="已用空间(字节)"
        type="number"
        placeholder="可选"
        :error="errors.used_space"
      />
      <Input
        v-model="form.password"
        label="密码"
        type="password"
        placeholder="新增用户必填"
        :error="errors.password"
      />
      <Select v-model="form.status" label="状态" :options="statusOptions" />
      <Select v-model="form.is_superuser" label="超级管理员" :options="superOptions" />
      <div class="form__roles">
        <div class="form__label">角色分配</div>
        <CheckList v-model="form.roles" :items="roleOptions.options.value" empty-text="暂无角色可选" />
      </div>
    </div>
    <template #footer>
      <Button variant="secondary" @click="formOpen = false">取消</Button>
      <Button @click="submitForm">保存</Button>
    </template>
  </Modal>

  <ConfirmDialog
    :open="deleteConfirm"
    title="确认删除用户"
    message="删除后该用户将无法登录，是否继续？"
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

.form__roles {
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
