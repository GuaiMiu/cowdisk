<template>
  <section class="module">
    <div class="module-head">
      <div>
        <h2>分享管理</h2>
        <p>管理已创建的分享链接。</p>
      </div>
      <button class="btn secondary" @click="load">刷新</button>
    </div>

    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>创建时间</th>
            <th>到期时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in shares" :key="item.id">
            <td>{{ item.name }}</td>
            <td>{{ item.is_dir ? "目录" : "文件" }}</td>
            <td>{{ formatTime(item.created_at) }}</td>
            <td>{{ item.expires_at ? formatTime(item.expires_at) : "永久" }}</td>
            <td class="actions">
              <button class="btn ghost" @click="copyLink(item)">复制链接</button>
              <button class="btn secondary" @click="revoke(item)">撤销</button>
            </td>
          </tr>
          <tr v-if="!shares.length">
            <td colspan="5" class="empty">暂无分享</td>
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
import { listDiskShare, revokeDiskShare } from "../../api/user";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { useNotifyStore } from "../../stores/notify";

const shares = ref<any[]>([]);
const confirmState = ref({
  visible: false,
  title: "",
  message: "",
  onConfirm: () => {}
});
const notify = useNotifyStore();

const load = async () => {
  try {
    const { data } = await listDiskShare();
    shares.value = data?.data?.items || [];
  } catch (err: any) {
    notify.error(err?.response?.data?.msg || err?.message || "加载失败");
  }
};

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    notify.success("分享链接已复制");
  } catch (err) {
    notify.error("复制失败，请手动复制");
  }
};

const shareUrl = (id: string) => {
  const base = import.meta.env.VITE_API_BASE || "/api/v1";
  return `${base}/share?token=${encodeURIComponent(id)}`;
};

const copyLink = (item: any) => {
  copyText(shareUrl(item.id));
};

const revoke = (item: any) => {
  confirmAction("撤销分享", `确定撤销 ${item.name} 的分享吗？`, async () => {
    await revokeDiskShare(item.id);
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
        notify.success("已撤销");
      } catch (err: any) {
        notify.error(err?.response?.data?.msg || err?.message || "操作失败");
      } finally {
        closeConfirm();
      }
    }
  };
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
    gap: 12px;
  }
}
</style>
