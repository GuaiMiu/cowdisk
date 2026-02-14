<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Table from '@/components/common/Table.vue'
import Tag from '@/components/common/Tag.vue'
import Modal from '@/components/common/Modal.vue'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import Switch from '@/components/common/Switch.vue'
import { useAdminMenus } from '@/composables/useAdminMenus'
import type { MenuOut } from '@/types/menu'

const menuStore = useAdminMenus()
const { t } = useI18n({ useScope: 'global' })
const columns = computed(() => [
  { key: 'name', label: t('admin.menu.columns.name') },
  { key: 'type', label: t('admin.menu.columns.type') },
  { key: 'router_path', label: t('admin.menu.columns.path') },
  { key: 'permission_char', label: t('admin.menu.columns.permission') },
  { key: 'status', label: t('admin.menu.columns.status') },
  { key: 'actions', label: t('admin.menu.columns.actions'), width: '120px' },
])

const typeOptions = computed(() => [
  { label: t('admin.menu.typeOptions.directory'), value: '1' },
  { label: t('admin.menu.typeOptions.menu'), value: '2' },
  { label: t('admin.menu.typeOptions.button'), value: '3' },
])

const statusOptions = computed(() => [
  { label: t('admin.menu.statusOptions.enabled'), value: 'true' },
  { label: t('admin.menu.statusOptions.disabled'), value: 'false' },
])

const boolOptions = computed(() => [
  { label: t('admin.menu.boolOptions.no'), value: 'false' },
  { label: t('admin.menu.boolOptions.yes'), value: 'true' },
])

const formOpen = ref(false)
const deleteConfirm = ref(false)
const currentMenu = ref<MenuOut | null>(null)
const toggling = ref(new Set<number>())

const form = reactive({
  id: 0,
  name: '',
  type: '2',
  pid: '0',
  route_name: '',
  router_path: '',
  permission_char: '',
  sort: '0',
  status: 'true',
  keep_alive: 'true',
  is_frame: 'false',
  redirect: '',
  component_path: '',
  icon: '',
  description: '',
})

const errors = reactive({
  name: '',
  type: '',
})

const parentOptions = computed(() => [
  { label: t('admin.menu.parentNone'), value: '0' },
  ...menuStore.items.value.map((item) => ({
    label: item.name || t('admin.menu.unnamedMenu'),
    value: String(item.id || 0),
  })),
])

type TreeNode = MenuOut & { children?: TreeNode[]; _level?: number }

const buildTree = (items: MenuOut[]) => {
  const map = new Map<number, TreeNode>()
  items.forEach((item) => {
    if (item.id) {
      map.set(item.id, { ...item, children: [] })
    }
  })
  const roots: TreeNode[] = []
  map.forEach((node) => {
    if (node.pid && map.has(node.pid)) {
      map.get(node.pid)?.children?.push(node)
    } else {
      roots.push(node)
    }
  })
  const sortTree = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => (a.sort ?? 0) - (b.sort ?? 0))
    nodes.forEach((node) => {
      if (node.children?.length) {
        sortTree(node.children)
      }
    })
  }
  sortTree(roots)
  return roots
}

const collapsed = ref(new Set<number>())

const toggleCollapse = (id: number) => {
  if (collapsed.value.has(id)) {
    collapsed.value.delete(id)
  } else {
    collapsed.value.add(id)
  }
  collapsed.value = new Set(collapsed.value)
}

const treeRows = computed(() => {
  const source = menuStore.items.value
  if (!source.length) {
    return [] as Array<MenuOut & { _level: number }>
  }
  const map = new Map<number, MenuOut>()
  source.forEach((item) => {
    if (item.id) {
      map.set(item.id, item)
    }
  })
  const included = new Set<number>()
  const matches = new Set(source.map((item) => item.id).filter((id): id is number => !!id))
  matches.forEach((id) => {
    let current = map.get(id)
    while (current?.id) {
      included.add(current.id)
      if (!current.pid) {
        break
      }
      current = map.get(current.pid)
    }
  })
  const items = source.filter((item) => (item.id ? included.has(item.id) : false))
  const tree = buildTree(items)
  const rows: Array<MenuOut & { _level: number }> = []
  const walk = (nodes: TreeNode[], level: number) => {
    nodes.forEach((node) => {
      rows.push({ ...node, _level: level })
      if (node.children?.length && !collapsed.value.has(node.id || 0)) {
        walk(node.children, level + 1)
      }
    })
  }
  walk(tree, 0)
  return rows
})

const treeMap = computed(() => {
  const map = new Map<number, TreeNode>()
  const source = menuStore.items.value
  source.forEach((item) => {
    if (item.id) {
      map.set(item.id, { ...item })
    }
  })
  return map
})

const hasChildren = (row: MenuOut) => {
  if (!row.id) {
    return false
  }
  return menuStore.items.value.some((item) => item.pid === row.id)
}

const resetForm = () => {
  form.id = 0
  form.name = ''
  form.type = '2'
  form.pid = '0'
  form.route_name = ''
  form.router_path = ''
  form.permission_char = ''
  form.sort = '0'
  form.status = 'true'
  form.keep_alive = 'true'
  form.is_frame = 'false'
  form.redirect = ''
  form.component_path = ''
  form.icon = ''
  form.description = ''
  errors.name = ''
  errors.type = ''
}

const openCreate = () => {
  resetForm()
  formOpen.value = true
}

const openEdit = (menu: MenuOut) => {
  form.id = menu.id || 0
  form.name = menu.name || ''
  form.type = String(menu.type ?? 2)
  form.pid = String(menu.pid ?? 0)
  form.route_name = menu.route_name || ''
  form.router_path = menu.router_path || ''
  form.permission_char = menu.permission_char || ''
  form.sort = String(menu.sort ?? 0)
  form.status = menu.status ? 'true' : 'false'
  form.keep_alive = menu.keep_alive ? 'true' : 'false'
  form.is_frame = menu.is_frame ? 'true' : 'false'
  form.redirect = menu.redirect || ''
  form.component_path = menu.component_path || ''
  form.icon = menu.icon || ''
  form.description = menu.description || ''
  errors.name = ''
  errors.type = ''
  formOpen.value = true
}

const submitForm = async () => {
  errors.name = ''
  errors.type = ''
  if (!form.name) {
    errors.name = t('admin.menu.errors.nameRequired')
    return
  }
  const payload = {
    name: form.name,
    type: Number(form.type),
    pid: Number(form.pid) || null,
    route_name: form.route_name || null,
    router_path: form.router_path || null,
    permission_char: form.permission_char || null,
    sort: Number(form.sort) || 0,
    status: form.status === 'true',
    keep_alive: form.keep_alive === 'true',
    is_frame: form.is_frame === 'true',
    redirect: form.redirect || null,
    component_path: form.component_path || null,
    icon: form.icon || null,
    description: form.description || null,
  }
  if (Number.isNaN(payload.type)) {
    errors.type = t('admin.menu.errors.typeRequired')
    return
  }
  if (form.id) {
    await menuStore.updateMenu({ id: form.id, ...payload })
  } else {
    await menuStore.createMenu(payload)
  }
  formOpen.value = false
}

const requestDelete = (menu: MenuOut) => {
  currentMenu.value = menu
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  if (currentMenu.value?.id) {
    await menuStore.removeMenu(currentMenu.value.id)
  }
  deleteConfirm.value = false
  currentMenu.value = null
}

const isToggling = (id?: number) => (id ? toggling.value.has(id) : false)

const toggleStatus = async (row: MenuOut, next: boolean) => {
  if (!row.id || toggling.value.has(row.id)) {
    return
  }
  toggling.value = new Set(toggling.value).add(row.id)
  try {
    await menuStore.updateMenu({
      id: row.id,
      name: row.name || '',
      type: Number(row.type ?? 2),
      pid: row.pid ?? null,
      route_name: row.route_name ?? null,
      router_path: row.router_path ?? null,
      permission_char: row.permission_char ?? null,
      sort: row.sort ?? 0,
      status: next,
      keep_alive: row.keep_alive ?? true,
      is_frame: row.is_frame ?? false,
      redirect: row.redirect ?? null,
      component_path: row.component_path ?? null,
      icon: row.icon ?? null,
      description: row.description ?? null,
    })
  } finally {
    const nextSet = new Set(toggling.value)
    nextSet.delete(row.id)
    toggling.value = nextSet
  }
}

onMounted(() => {
  void menuStore.fetchMenus()
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.menu.title')" :subtitle="t('admin.menu.subtitle')">
      <template #actions>
        <Button variant="secondary" @click="menuStore.fetchMenus()">
          {{ t('admin.menu.refresh') }}
        </Button>
        <Button v-permission="'system:menu:create'" @click="openCreate">{{
          t('admin.menu.add')
        }}</Button>
      </template>
    </PageHeader>

    <div class="table-wrap">
      <Table :columns="columns" :rows="treeRows" :min-rows="menuStore.size.value" scrollable fill>
        <template #cell-name="{ row }">
          <span class="tree-name" :style="{ paddingLeft: `${Number(row._level ?? 0) * 16}px` }">
            <button
              v-if="hasChildren(row)"
              type="button"
              class="tree-toggle"
              @click="toggleCollapse(Number(row.id ?? 0))"
            >
              {{ collapsed.has(Number(row.id ?? 0)) ? '▸' : '▾' }}
            </button>
            <span v-else class="tree-toggle tree-toggle--placeholder"></span>
            <span class="tree-label" :class="`tree-label--type-${row.type ?? 2}`">{{ row.name }}</span>
          </span>
        </template>
        <template #cell-type="{ row }">
          <Tag tone="warning">
            {{
              row.type === 1
                ? t('admin.menu.tags.directory')
                : row.type === 2
                  ? t('admin.menu.tags.menu')
                  : t('admin.menu.tags.button')
            }}
          </Tag>
        </template>
        <template #cell-status="{ row }">
          <Switch
            :model-value="!!row.status"
            :disabled="isToggling(row.id)"
            @update:modelValue="(value: boolean) => toggleStatus(row, value)"
          />
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <Button
              size="sm"
              variant="secondary"
              v-permission="'system:menu:update'"
              @click="openEdit(row)"
            >
              {{ t('common.edit') }}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              v-permission="'system:menu:delete'"
              @click="requestDelete(row)"
            >
              {{ t('common.delete') }}
            </Button>
          </div>
        </template>
      </Table>
    </div>

  </section>

  <Modal
    :open="formOpen"
    :title="form.id ? t('admin.menu.modal.editTitle') : t('admin.menu.modal.createTitle')"
    @close="formOpen = false"
  >
    <div class="form">
      <Input
        v-model="form.name"
        :label="t('admin.menu.form.name')"
        :placeholder="t('admin.menu.placeholders.name')"
        :error="errors.name"
      />
      <Select
        v-model="form.type"
        :label="t('admin.menu.form.type')"
        :options="typeOptions"
        :error="errors.type"
      />
      <Select v-model="form.pid" :label="t('admin.menu.form.parent')" :options="parentOptions" />
      <Input
        v-model="form.route_name"
        :label="t('admin.menu.form.routeName')"
        :placeholder="t('admin.common.optional')"
      />
      <Input
        v-model="form.router_path"
        :label="t('admin.menu.form.routerPath')"
        :placeholder="t('admin.menu.placeholders.routerPath')"
      />
      <Input
        v-model="form.permission_char"
        :label="t('admin.menu.form.permission')"
        :placeholder="t('admin.menu.placeholders.permission')"
      />
      <Input
        v-model="form.sort"
        :label="t('admin.menu.form.sort')"
        :placeholder="t('admin.menu.placeholders.sort')"
      />
      <Select v-model="form.status" :label="t('admin.menu.form.status')" :options="statusOptions" />
      <Select
        v-model="form.keep_alive"
        :label="t('admin.menu.form.keepAlive')"
        :options="boolOptions"
      />
      <Select
        v-model="form.is_frame"
        :label="t('admin.menu.form.isFrame')"
        :options="boolOptions"
      />
      <Input
        v-model="form.redirect"
        :label="t('admin.menu.form.redirect')"
        :placeholder="t('admin.common.optional')"
      />
      <Input
        v-model="form.component_path"
        :label="t('admin.menu.form.componentPath')"
        :placeholder="t('admin.common.optional')"
      />
      <Input
        v-model="form.icon"
        :label="t('admin.menu.form.icon')"
        :placeholder="t('admin.common.optional')"
      />
      <Input
        v-model="form.description"
        :label="t('admin.menu.form.description')"
        :placeholder="t('admin.common.optional')"
      />
    </div>
    <template #footer>
      <Button variant="secondary" @click="formOpen = false">{{ t('common.cancel') }}</Button>
      <Button @click="submitForm">{{ t('common.save') }}</Button>
    </template>
  </Modal>

  <ConfirmDialog
    :open="deleteConfirm"
    :title="t('admin.menu.confirmDeleteTitle')"
    :message="t('admin.menu.confirmDeleteMessage')"
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
  grid-template-rows: auto 1fr;
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

.tree-name {
  display: inline-flex;
  align-items: center;
}

.tree-toggle {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  margin-right: var(--space-2);
}

.tree-toggle:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.tree-label {
  font-weight: 600;
}

.tree-label--type-1 {
  font-weight: 700;
}

.tree-label--type-2 {
  font-weight: 600;
}

.tree-label--type-3 {
  font-weight: 500;
  color: var(--color-muted);
}

.tree-toggle--placeholder {
  opacity: 0;
  cursor: default;
  pointer-events: none;
}

</style>

