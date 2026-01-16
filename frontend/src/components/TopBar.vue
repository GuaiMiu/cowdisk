<template>
  <header class="topbar">
    <div>
      <div class="title">控制台</div>
      <div class="subtitle">今天也要稳稳地运行</div>
    </div>
    <div class="actions">
      <div class="user">
        <div class="avatar">{{ initials }}</div>
        <div class="meta">
          <div class="name">{{ auth.user?.username || "管理员" }}</div>
          <div class="role">
            {{ auth.user?.is_superuser ? "超级管理员" : "普通用户" }}
          </div>
        </div>
      </div>
      <button class="btn secondary" @click="handleLogout">退出</button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAdminAuthStore } from "../stores/adminAuth";

const auth = useAdminAuthStore();
const router = useRouter();

const initials = computed(() => {
  const name = auth.user?.username || "Admin";
  return name.slice(0, 2).toUpperCase();
});

const handleLogout = async () => {
  await auth.logout();
  router.push("/admin/login");
};
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 32px 8px;
}

.title {
  font-size: 26px;
  font-weight: 700;
  font-family: "Space Grotesk", sans-serif;
}

.subtitle {
  font-size: 13px;
  color: var(--muted);
}

.actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.8);
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e4c6a0, #c55d35);
  color: #3b1f14;
  display: grid;
  place-items: center;
  font-weight: 700;
}

.meta {
  display: flex;
  flex-direction: column;
  font-size: 12px;
}

.role {
  color: var(--muted);
}

@media (max-width: 768px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 18px 16px 8px;
  }

  .actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
