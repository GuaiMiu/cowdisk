<template>
  <section class="module">
    <div class="module-head">
      <div>
        <h2>用户管理</h2>
        <p>维护系统用户、状态与角色绑定。</p>
      </div>
      <button v-if="canAdd" class="btn accent" @click="openCreate">
        新增用户
      </button>
    </div>

    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>邮箱</th>
            <th>角色</th>
            <th>空间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in users" :key="item.id">
            <td>{{ item.username }}</td>
            <td>{{ item.mail }}</td>
            <td>
              <span class="pill" v-for="role in item.roles || []" :key="role.id">
                {{ role.name }}
              </span>
            </td>
            <td>
              <div class="space-info">
                <span>{{ formatBytes(item.used_space || 0) }}</span>
                <span class="muted">/ {{ formatBytes(item.total_space || 0) }}</span>
              </div>
              <div class="space-bar">
                <div
                  class="space-fill"
                  :style="{ width: `${getUsedPercent(item)}%` }"
                ></div>
              </div>
            </td>
            <td>
              <span class="pill" :class="{ off: !item.status }">
                {{ item.status ? "启用" : "禁用" }}
              </span>
            </td>
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
          <tr v-if="!users.length">
            <td colspan="6" class="empty">暂无用户</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="drawer" v-if="showForm">
      <div class="drawer-panel card">
        <div class="drawer-head">
          <div>
            <div class="drawer-title">{{ editing ? "编辑用户" : "新增用户" }}</div>
            <div class="drawer-subtitle">配置基础信息和角色</div>
          </div>
          <button class="btn ghost" @click="closeForm">关闭</button>
        </div>
        <form class="drawer-body" @submit.prevent="submit">
          <div class="field">
            <label>用户名</label>
            <input v-model="form.username" class="input" required />
          </div>
          <div class="field">
            <label>昵称</label>
            <input v-model="form.nickname" class="input" />
          </div>
          <div class="field">
            <label>邮箱</label>
            <input v-model="form.mail" class="input" type="email" required />
          </div>
          <div class="field">
            <label>可用空间 (GB)</label>
            <input
              v-model="form.totalSpaceGb"
              class="input"
              type="number"
              min="0"
              step="0.1"
              placeholder="留空则使用默认配额"
            />
          </div>
          <div class="field" v-if="!editing">
            <label>密码</label>
            <input
              v-model="form.password"
              class="input"
              type="password"
              required
            />
          </div>
          <div class="field">
            <label>状态</label>
            <select v-model="form.status" class="select">
              <option :value="true">启用</option>
              <option :value="false">禁用</option>
            </select>
          </div>
          <div class="field">
            <label>超级管理员</label>
            <select v-model="form.is_superuser" class="select">
              <option :value="true">是</option>
              <option :value="false">否</option>
            </select>
          </div>
          <div class="field">
            <label>角色</label>
            <div class="role-list">
              <label v-for="role in roles" :key="role.id" class="role-chip">
                <input
                  type="checkbox"
                  :value="role.id"
                  v-model="form.roles"
                />
                {{ role.name }}
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
  createUser,
  deleteUser,
  fetchRoles,
  fetchUsers,
  updateUser
} from "../../api/admin";
import { useAdminAuthStore } from "../../stores/adminAuth";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { useNotifyStore } from "../../stores/notify";

const users = ref<any[]>([]);
const roles = ref<any[]>([]);
const auth = useAdminAuthStore();
const notify = useNotifyStore();
const canAdd = computed(() => auth.hasPerm("system:user:add"));
const canEdit = computed(() => auth.hasPerm("system:user:edit"));
const canDelete = computed(() => auth.hasPerm("system:user:delete"));
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
  username: "",
  nickname: "",
  mail: "",
  totalSpaceGb: "",
  password: "",
  status: true,
  is_superuser: false,
  roles: []
});

const BYTES_PER_GB = 1024 ** 3;
const formatBytes = (value: number) => {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let idx = 0;
  let size = value;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(1)} ${units[idx]}`;
};

const getUsedPercent = (item: any) => {
  const total = Number(item?.total_space || 0);
  const used = Number(item?.used_space || 0);
  if (!total) return 0;
  return Math.min(100, Math.round((used / total) * 100));
};

const load = async () => {
  const [{ data: usersResp }, { data: rolesResp }] = await Promise.all([
    fetchUsers(),
    fetchRoles()
  ]);
  users.value = usersResp?.data?.items || [];
  roles.value = rolesResp?.data?.items || [];
};

const resetForm = () => {
  form.id = null;
  form.username = "";
  form.nickname = "";
  form.mail = "";
  form.totalSpaceGb = "";
  form.password = "";
  form.status = true;
  form.is_superuser = false;
  form.roles = [];
};

const openCreate = () => {
  editing.value = false;
  resetForm();
  showForm.value = true;
};

const openEdit = (item: any) => {
  editing.value = true;
  form.id = item.id;
  form.username = item.username;
  form.nickname = item.nickname;
  form.mail = item.mail;
  form.totalSpaceGb =
    typeof item.total_space === "number"
      ? (item.total_space / BYTES_PER_GB).toFixed(1)
      : "";
  form.password = "";
  form.status = item.status;
  form.is_superuser = Boolean(item.is_superuser);
  form.roles = (item.roles || []).map((role: any) => role.id);
  showForm.value = true;
};

const closeForm = () => {
  showForm.value = false;
  error.value = "";
};

const submit = async () => {
  error.value = "";
  try {
    const totalSpaceGb = Number(form.totalSpaceGb);
    const hasSpaceInput =
      form.totalSpaceGb !== "" && !Number.isNaN(totalSpaceGb);
    if (editing.value) {
      const payload: Record<string, unknown> = {
        id: form.id,
        username: form.username,
        nickname: form.nickname,
        mail: form.mail,
        status: form.status,
        is_superuser: form.is_superuser,
        roles: form.roles
      };
      if (hasSpaceInput) {
        payload.total_space = Math.max(
          0,
          Math.round(totalSpaceGb * BYTES_PER_GB)
        );
      }
      await updateUser(payload);
      notify.success("更新成功");
    } else {
      const payload: Record<string, unknown> = {
        username: form.username,
        nickname: form.nickname,
        mail: form.mail,
        password: form.password,
        status: form.status,
        is_superuser: form.is_superuser,
        roles: form.roles
      };
      if (hasSpaceInput) {
        payload.total_space = Math.max(
          0,
          Math.round(totalSpaceGb * BYTES_PER_GB)
        );
      }
      await createUser(payload);
      notify.success("创建成功");
    }
    await load();
    closeForm();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "操作失败";
    notify.error(error.value);
  }
};

const handleDelete = async (id: number) => {
  confirmAction("确认删除", "确定删除该用户吗？", async () => {
    await deleteUser(id);
    await load();
  }, "删除成功");
};

const closeConfirm = () => {
  confirmState.value.visible = false;
};

const confirmAction = (
  title: string,
  message: string,
  action: () => Promise<void>,
  successMessage?: string
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

onMounted(load);
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

.space-info {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.space-info .muted {
  color: var(--muted);
}

.space-bar {
  margin-top: 6px;
  height: 6px;
  background: rgba(197, 93, 53, 0.12);
  border-radius: 999px;
  overflow: hidden;
}

.space-fill {
  height: 100%;
  background: linear-gradient(135deg, #c55d35, #f0cfa7);
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
  width: min(440px, 100%);
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

.role-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.role-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
  font-size: 12px;
  background: var(--surface-alt);
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
