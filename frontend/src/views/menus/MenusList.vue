<template>
  <section class="module">
    <div class="module-head">
      <div>
        <h2>菜单管理</h2>
        <p>配置路由、权限字符与菜单结构。</p>
      </div>
      <button v-if="canAdd" class="btn accent" @click="openCreate">
        新增菜单
      </button>
    </div>

    <div class="tree-controls">
      <button class="btn ghost" @click="expandAll">展开全部</button>
      <button class="btn ghost" @click="collapseAll">收起全部</button>
    </div>

    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>权限字符</th>
            <th>路由</th>
            <th>排序</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in menuRows" :key="item.node.id">
            <td>
              <span
                class="tree-name"
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
                {{ item.node.name }}
              </span>
            </td>
            <td>{{ menuTypeLabel(item.node.type) }}</td>
            <td>{{ item.node.permission_char || "-" }}</td>
            <td>{{ item.node.router_path || "-" }}</td>
            <td>{{ item.node.sort || 0 }}</td>
            <td>
              <span class="pill" :class="{ off: !item.node.status }">
                {{ item.node.status ? "启用" : "禁用" }}
              </span>
            </td>
            <td class="actions">
              <button v-if="canEdit" class="btn ghost" @click="openEdit(item.node)">
                编辑
              </button>
              <button
                v-if="canDelete"
                class="btn secondary"
                @click="handleDelete(item.node.id)"
              >
                删除
              </button>
            </td>
          </tr>
          <tr v-if="!menus.length">
            <td colspan="7" class="empty">暂无菜单</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="drawer" v-if="showForm">
      <div class="drawer-panel card">
        <div class="drawer-head">
          <div>
            <div class="drawer-title">{{ editing ? "编辑菜单" : "新增菜单" }}</div>
            <div class="drawer-subtitle">对应后台权限配置</div>
          </div>
          <button class="btn ghost" @click="closeForm">关闭</button>
        </div>
        <form class="drawer-body" @submit.prevent="submit">
          <div class="field">
            <label>名称</label>
            <input v-model="form.name" class="input" required />
          </div>
          <div class="field">
            <label>路由名</label>
            <input v-model="form.route_name" class="input" />
          </div>
          <div class="field">
            <label>上级菜单</label>
            <select v-model="form.pid" class="select">
              <option :value="0">根目录</option>
              <option
                v-for="item in menuRows"
                :key="item.node.id"
                :value="item.node.id"
              >
                {{ item.depth ? "—".repeat(item.depth) + " " : "" }}
                {{ item.node.name }}
              </option>
            </select>
          </div>
          <div class="field">
            <label>类型</label>
            <select v-model="form.type" class="select">
              <option :value="1">目录</option>
              <option :value="2">菜单</option>
              <option :value="3">按钮</option>
            </select>
          </div>
          <div class="field">
            <label>路由路径</label>
            <input v-model="form.router_path" class="input" />
          </div>
          <div class="field">
            <label>权限字符</label>
            <input v-model="form.permission_char" class="input" />
          </div>
          <div class="field">
            <label>排序</label>
            <input v-model.number="form.sort" class="input" type="number" />
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
import { computed, onMounted, reactive, ref, watch } from "vue";
import { createMenu, deleteMenu, fetchMenusList, updateMenu } from "../../api/admin";
import { useAdminAuthStore } from "../../stores/adminAuth";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { useNotifyStore } from "../../stores/notify";
import { getAppStorage, setAppStorage } from "../../utils/storage";

const menus = ref<any[]>([]);
const menuTree = computed(() => buildTree(menus.value));
const menuRows = computed(() => flattenTree(menuTree.value));
const expandedIds = ref<Set<number>>(new Set());
const auth = useAdminAuthStore();
const notify = useNotifyStore();
const canAdd = computed(() => auth.hasPerm("system:menu:add"));
const canEdit = computed(() => auth.hasPerm("system:menu:edit"));
const canDelete = computed(() => auth.hasPerm("system:menu:delete"));
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
  route_name: "",
  pid: 0,
  type: 2,
  router_path: "",
  permission_char: "",
  sort: 0,
  status: true,
  description: ""
});

const menuTypeLabel = (type: number) => {
  if (type === 1) return "目录";
  if (type === 2) return "菜单";
  if (type === 3) return "按钮";
  return "-";
};

const load = async () => {
  const { data } = await fetchMenusList();
  menus.value = data?.data?.items || [];
};

const resetForm = () => {
  form.id = null;
  form.name = "";
  form.route_name = "";
  form.pid = 0;
  form.type = 2;
  form.router_path = "";
  form.permission_char = "";
  form.sort = 0;
  form.status = true;
  form.description = "";
};

const openCreate = () => {
  editing.value = false;
  resetForm();
  showForm.value = true;
};

const openEdit = (item: any) => {
  editing.value = true;
  form.id = item.id;
  form.name = item.name;
  form.route_name = item.route_name;
  form.pid = item.pid ?? 0;
  form.type = item.type;
  form.router_path = item.router_path;
  form.permission_char = item.permission_char;
  form.sort = item.sort;
  form.status = item.status;
  form.description = item.description;
  showForm.value = true;
};

const closeForm = () => {
  showForm.value = false;
  error.value = "";
};

const submit = async () => {
  error.value = "";
  try {
    const payload = {
      id: form.id,
      name: form.name,
      route_name: form.route_name,
      pid: form.pid,
      type: form.type,
      router_path: form.router_path,
      permission_char: form.permission_char,
      sort: form.sort,
      status: form.status,
      description: form.description
    };
    if (editing.value) {
      await updateMenu(payload);
    } else {
      await createMenu(payload);
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
  confirmAction("确认删除", "确定删除该菜单吗？", async () => {
    await deleteMenu(id);
    await load();
  }, "删除成功");
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

const collectIds = (node: any, acc: number[]) => {
  acc.push(node.id);
  if (node.children?.length) {
    node.children.forEach((child: any) => collectIds(child, acc));
  }
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

onMounted(() => {
  const raw = getAppStorage().menuExpanded;
  if (!raw) return;
  if (Array.isArray(raw)) {
    expandedIds.value = new Set(raw.filter((id) => typeof id === "number"));
  }
});

watch(
  () => Array.from(expandedIds.value),
  (ids) => {
    setAppStorage({ menuExpanded: ids });
  }
);

watch(
  () => menus.value,
  (items) => {
    const valid = new Set<number>(items.map((item) => item.id));
    const next = new Set<number>();
    expandedIds.value.forEach((id) => {
      if (valid.has(id)) {
        next.add(id);
      }
    });
    expandedIds.value = next;
  },
  { deep: true }
);

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
  display: flex;
  gap: 8px;
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

.tree-name {
  display: inline-flex;
  align-items: center;
}

.tree-controls {
  display: flex;
  gap: 8px;
}

.tree-toggle {
  width: 22px;
  height: 22px;
  border: 1px solid var(--stroke);
  border-radius: 6px;
  background: var(--surface-alt);
  cursor: pointer;
  margin-right: 6px;
}

.tree-spacer {
  width: 22px;
  height: 22px;
  display: inline-block;
  margin-right: 6px;
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

  .tree-controls {
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
