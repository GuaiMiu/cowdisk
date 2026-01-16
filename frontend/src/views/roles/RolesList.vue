<template>
  <section class="module">
    <div class="module-head">
      <div>
        <h2>角色管理</h2>
        <p>为不同岗位定义权限集合。</p>
      </div>
      <button v-if="canAdd" class="btn accent" @click="openCreate">
        新增角色
      </button>
    </div>

    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>角色名称</th>
            <th>权限标识</th>
            <th>状态</th>
            <th>描述</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in roles" :key="item.id">
            <td>{{ item.name }}</td>
            <td>{{ item.permission_char }}</td>
            <td>
              <span class="pill" :class="{ off: !item.status }">
                {{ item.status ? "启用" : "禁用" }}
              </span>
            </td>
            <td>{{ item.description || "-" }}</td>
            <td class="actions">
              <button v-if="canEdit" class="btn ghost" @click="openEdit(item)">
                编辑
              </button>
              <button
                v-if="canDelete"
                class="btn secondary"
                @click="handleDelete(item.id)"
              >
                删除
              </button>
            </td>
          </tr>
          <tr v-if="!roles.length">
            <td colspan="5" class="empty">暂无角色</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="drawer" v-if="showForm">
      <div class="drawer-panel card">
        <div class="drawer-head">
          <div>
            <div class="drawer-title">{{ editing ? "编辑角色" : "新增角色" }}</div>
            <div class="drawer-subtitle">选择菜单权限</div>
          </div>
          <button class="btn ghost" @click="closeForm">关闭</button>
        </div>
        <form class="drawer-body" @submit.prevent="submit">
          <div class="field">
            <label>角色名称</label>
            <input v-model="form.name" class="input" required />
          </div>
          <div class="field">
            <label>权限标识</label>
            <input v-model="form.permission_char" class="input" />
          </div>
          <div class="field">
            <label>状态</label>
            <select v-model="form.status" class="select">
              <option :value="true">启用</option>
              <option :value="false">禁用</option>
            </select>
          </div>
          <div class="field">
            <label>描述</label>
            <textarea v-model="form.description" class="textarea" rows="3"></textarea>
          </div>
          <div class="field">
            <label>菜单权限</label>
            <div class="tree-controls">
              <button class="btn ghost" type="button" @click="expandAll">
                展开全部
              </button>
              <button class="btn ghost" type="button" @click="collapseAll">
                收起全部
              </button>
            </div>
            <div class="menu-tree">
              <label
                v-for="item in menuRows"
                :key="item.node.id"
                class="menu-node"
                :style="{ paddingLeft: `${item.depth * 16}px` }"
              >
                <button
                  v-if="item.node.children?.length"
                  class="tree-toggle"
                  type="button"
                  @click="toggleExpand(item.node.id)"
                >
                  {{ isExpanded(item.node.id) ? "-" : "+" }}
                </button>
                <span v-else class="tree-spacer"></span>
                <input
                  type="checkbox"
                  :checked="isChecked(item.node.id)"
                  @change="onToggle(item.node, $event)"
                  :ref="(el) => setIndeterminate(el, item.node.id)"
                />
                {{ item.node.name }}
              </label>
            </div>
          </div>
          <div class="drawer-actions">
            <button class="btn secondary" type="button" @click="closeForm">
              取消
            </button>
            <button class="btn accent" type="submit">
              {{ editing ? "保存" : "创建" }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      v-if="confirmState.visible"
      :title="confirmState.title"
      :message="confirmState.message"
      @confirm="confirmState.onConfirm"
      @cancel="closeConfirm"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  createRole,
  deleteRole,
  fetchMenusList,
  fetchRoles,
  updateRole
} from "../../api/admin";
import { useAdminAuthStore } from "../../stores/adminAuth";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { useNotifyStore } from "../../stores/notify";

const roles = ref<any[]>([]);
const menus = ref<any[]>([]);
const menuTree = computed(() => buildTree(menus.value));
const menuRows = computed(() => flattenTree(menuTree.value));
const stateMap = computed(() => {
  const base = new Set(form.menus);
  const expanded = expandSelection(menuTree.value, base);
  return buildStateMap(menuTree.value, expanded);
});
const expandedIds = ref<Set<number>>(new Set());
const auth = useAdminAuthStore();
const notify = useNotifyStore();
const canAdd = computed(() => auth.hasPerm("system:role:add"));
const canEdit = computed(() => auth.hasPerm("system:role:edit"));
const canDelete = computed(() => auth.hasPerm("system:role:delete"));
const showForm = ref(false);
const editing = ref(false);
const error = ref("");
const confirmState = ref({
  visible: false,
  title: "",
  message: "",
  onConfirm: () => {}
});
const form = reactive<any>({
  id: null,
  name: "",
  permission_char: "",
  status: true,
  description: "",
  menus: []
});

const load = async () => {
  const [{ data: rolesResp }, { data: menusResp }] = await Promise.all([
    fetchRoles(),
    fetchMenusList()
  ]);
  roles.value = rolesResp?.data?.items || [];
  menus.value = menusResp?.data?.items || [];
};

const resetForm = () => {
  form.id = null;
  form.name = "";
  form.permission_char = "";
  form.status = true;
  form.description = "";
  form.menus = [];
  expandedIds.value = new Set();
};

const openCreate = () => {
  editing.value = false;
  resetForm();
  showForm.value = true;
  expandAll();
};

const openEdit = (item: any) => {
  editing.value = true;
  form.id = item.id;
  form.name = item.name;
  form.permission_char = item.permission_char;
  form.status = item.status;
  form.description = item.description;
  form.menus = (item.menus || []).map((menu: any) => menu.id);
  showForm.value = true;
  expandAll();
};

const closeForm = () => {
  showForm.value = false;
  error.value = "";
};

const submit = async () => {
  error.value = "";
  try {
    if (editing.value) {
      await updateRole({
        id: form.id,
        name: form.name,
        permission_char: form.permission_char,
        status: form.status,
        description: form.description,
        menus: form.menus
      });
    } else {
      await createRole({
        name: form.name,
        permission_char: form.permission_char,
        status: form.status,
        description: form.description,
        menus: form.menus
      });
    }
    await load();
    notify.success(editing.value ? "保存成功" : "创建成功");
    closeForm();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "操作失败";
    notify.error(error.value);
  }
};

const handleDelete = async (id: number) => {
  confirmAction("确认删除", "确定删除该角色吗？", async () => {
    await deleteRole(id);
    await load();
  }, "删除成功");
};

const onToggle = (node: any, event: Event) => {
  const target = event.target as HTMLInputElement;
  updateSelection(node, target.checked);
};

const isChecked = (id: number) => stateMap.value.get(id)?.checked ?? false;

const setIndeterminate = (el: HTMLInputElement | null, id: number) => {
  if (!el) return;
  const state = stateMap.value.get(id);
  el.indeterminate = state?.indeterminate ?? false;
};

const updateSelection = (node: any, checked: boolean) => {
  const selected = new Set(form.menus);
  const ids: number[] = [];
  collectIds(node, ids);
  if (checked) {
    ids.forEach((id) => selected.add(id));
  } else {
    ids.forEach((id) => selected.delete(id));
  }
  const normalized = normalizeSelection(menuTree.value, selected);
  form.menus = Array.from(normalized);
};

const collectIds = (node: any, acc: number[]) => {
  acc.push(node.id);
  if (node.children?.length) {
    node.children.forEach((child: any) => collectIds(child, acc));
  }
};

const expandSelection = (nodes: any[], selected: Set<number>) => {
  const expanded = new Set<number>(selected);
  const walk = (node: any, parentSelected: boolean) => {
    const isSelected = parentSelected || expanded.has(node.id);
    if (isSelected) {
      expanded.add(node.id);
    }
    if (node.children?.length) {
      node.children.forEach((child: any) => walk(child, isSelected));
    }
  };
  nodes.forEach((node) => walk(node, false));
  return expanded;
};

const normalizeSelection = (nodes: any[], selected: Set<number>) => {
  const normalized = new Set(selected);
  const walk = (node: any): boolean => {
    if (!node.children?.length) {
      return normalized.has(node.id);
    }
    const childStates = node.children.map(walk);
    const allSelected = childStates.every(Boolean);
    if (allSelected) {
      normalized.add(node.id);
    } else {
      normalized.delete(node.id);
    }
    return allSelected;
  };
  nodes.forEach(walk);
  return normalized;
};

const toggleExpand = (id: number) => {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id);
  } else {
    expandedIds.value.add(id);
  }
};

const isExpanded = (id: number) => expandedIds.value.has(id);

const expandAll = () => {
  const ids: number[] = [];
  menuTree.value.forEach((node) => collectIds(node, ids));
  expandedIds.value = new Set(ids);
};

const collapseAll = () => {
  expandedIds.value = new Set();
};

const buildTree = (items: any[]) => {
  const map = new Map<number, any[]>();
  items.forEach((item) => {
    const parentId = item.pid ?? 0;
    if (!map.has(parentId)) map.set(parentId, []);
    map.get(parentId)?.push(item);
  });
  const walk = (parentId: number) => {
    const children = map.get(parentId) || [];
    return children.map((child) => ({
      ...child,
      children: walk(child.id)
    }));
  };
  return walk(0);
};

const buildStateMap = (nodes: any[], selected: Set<number>) => {
  const map = new Map<number, { checked: boolean; indeterminate: boolean }>();
  const walk = (node: any) => {
    if (!node.children?.length) {
      const checked = selected.has(node.id);
      map.set(node.id, { checked, indeterminate: false });
      return map.get(node.id);
    }
    const childStates = node.children.map(walk);
    const allChecked = childStates.every((state) => state?.checked);
    const someChecked = childStates.some(
      (state) => state?.checked || state?.indeterminate
    );
    map.set(node.id, {
      checked: allChecked,
      indeterminate: !allChecked && someChecked
    });
    return map.get(node.id);
  };
  nodes.forEach(walk);
  return map;
};

const flattenTree = (nodes: any[], depth = 0, acc: any[] = []) => {
  nodes.forEach((node) => {
    acc.push({ node, depth });
    if (node.children?.length && expandedIds.value.has(node.id)) {
      flattenTree(node.children, depth + 1, acc);
    }
  });
  return acc;
};

onMounted(load);

const closeConfirm = () => {
  confirmState.value.visible = false;
};

const confirmAction = (
  title: string,
  message: string,
  action: () => Promise<void>,
  successMessage = ""
) => {
  confirmState.value = {
    visible: true,
    title,
    message,
    onConfirm: async () => {
      try {
        await action();
        if (successMessage) {
          notify.success(successMessage);
        }
      } catch (err: any) {
        error.value = err?.response?.data?.msg || err?.message || "操作失败";
        notify.error(error.value);
      } finally {
        closeConfirm();
      }
    }
  };
};
</script>

<style scoped>
.module {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.module-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h2 {
  margin: 0;
  font-size: 24px;
}

p {
  margin: 4px 0 0;
  color: var(--muted);
}

.table-card {
  padding: 8px 12px;
}

.actions {
  white-space: nowrap;
}

.actions .btn + .btn {
  margin-left: 8px;
}

.pill.off {
  background: rgba(178, 59, 43, 0.12);
  color: #b23b2b;
}

.empty {
  text-align: center;
  padding: 24px;
  color: var(--muted);
}

.drawer {
  position: fixed;
  inset: 0;
  background: rgba(20, 22, 27, 0.35);
  display: flex;
  justify-content: flex-end;
  z-index: 20;
}

.drawer-panel {
  width: min(480px, 100%);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-title {
  font-size: 20px;
  font-weight: 700;
}

.drawer-subtitle {
  font-size: 12px;
  color: var(--muted);
}

.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.menu-tree {
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--stroke);
  border-radius: var(--radius-sm);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tree-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.menu-node {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.tree-toggle {
  width: 22px;
  height: 22px;
  border: 1px solid var(--stroke);
  border-radius: 6px;
  background: var(--surface-alt);
  cursor: pointer;
}

.tree-spacer {
  width: 22px;
  height: 22px;
  display: inline-block;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 768px) {
  .module-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .actions {
    flex-wrap: wrap;
  }

  .table-card {
    overflow-x: auto;
  }

  .drawer-panel {
    padding: 18px;
  }
}

</style>
