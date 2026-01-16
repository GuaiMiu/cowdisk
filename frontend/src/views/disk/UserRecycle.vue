<template>
  <section class="module">
    <div class="module-head">
      <div>
        <h2>回收站</h2>
        <p>删除的文件会先进入回收站。</p>
      </div>
      <div class="actions">
        <button class="btn secondary" @click="load">刷新</button>
        <button class="btn accent" @click="clearAll" :disabled="!items.length">
          清空回收站
        </button>
      </div>
    </div>

    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>路径</th>
            <th>类型</th>
            <th>大小</th>
            <th>删除时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.name }}</td>
            <td>/{{ item.path }}</td>
            <td>{{ item.is_dir ? "目录" : "文件" }}</td>
            <td>{{ item.is_dir ? "-" : formatSize(item.size) }}</td>
            <td>{{ formatTime(item.deleted_at) }}</td>
            <td class="row-actions">
              <button class="btn ghost" @click="restore(item)">恢复</button>
              <button class="btn secondary" @click="remove(item)">彻底删除</button>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="6" class="empty">回收站为空</td>
          </tr>
        </tbody>
      </table>
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
import { onMounted, ref } from "vue";
import {
  clearDiskTrash,
  deleteDiskTrash,
  listDiskTrash,
  restoreDiskTrash
} from "../../api/user";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { useNotifyStore } from "../../stores/notify";

const items = ref<any[]>([]);
const confirmState = ref({
  visible: false,
  title: "",
  message: "",
  onConfirm: () => {}
});
const notify = useNotifyStore();

const load = async () => {
  try {
    const { data } = await listDiskTrash();
    items.value = data?.data?.items || [];
  } catch (err: any) {
    notify.error(err?.response?.data?.msg || err?.message || "加载失败");
  }
};

const restore = (item: any) => {
  confirmAction("恢复文件", `确定恢复 ${item.name} 吗？`, async () => {
    await restoreDiskTrash(item.id);
    await load();
  });
};

const remove = (item: any) => {
  confirmAction("彻底删除", `确定彻底删除 ${item.name} 吗？`, async () => {
    await deleteDiskTrash(item.id);
    await load();
  });
};

const clearAll = () => {
  confirmAction("清空回收站", "确定清空全部回收站内容吗？", async () => {
    await clearDiskTrash();
    await load();
  });
};

const closeConfirm = () => {
  confirmState.value.visible = false;
};

const confirmAction = (title: string, message: string, action: () => Promise<void>) => {
  confirmState.value = {
    visible: true,
    title,
    message,
    onConfirm: async () => {
      try {
        await action();
        notify.success("操作成功");
      } catch (err: any) {
        notify.error(err?.response?.data?.msg || err?.message || "操作失败");
      } finally {
        closeConfirm();
      }
    }
  };
};

const formatSize = (size: number) => {
  if (!size) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let idx = 0;
  let value = size;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(1)} ${units[idx]}`;
};

const formatTime = (value: string) => {
  if (!value) return "-";
  const date = new Date(value);
  return date.toLocaleString();
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
  gap: 12px;
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

.actions,
.row-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty {
  text-align: center;
  padding: 24px;
  color: var(--muted);
}

@media (max-width: 768px) {
  .module-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
