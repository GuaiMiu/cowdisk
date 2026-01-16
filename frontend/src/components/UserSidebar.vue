<template>
  <aside class="user-sidebar">
    <div class="brand">
      <div class="brand-mark">Cow</div>
      <div>
        <div class="brand-title">个人网盘</div>
        <div class="brand-subtitle">Personal Drive</div>
      </div>
    </div>
    <nav class="nav">
      <router-link class="nav-item" to="/" exact-active-class="router-link-active"
        >我的文件</router-link>
      <router-link class="nav-item" to="/share">分享</router-link>
      <router-link class="nav-item" to="/recycle">回收站</router-link>
    </nav>
    <div class="user-panel">
      <div class="user-card">
        <div class="avatar">{{ initials }}</div>
        <div class="meta">
          <div class="name">{{ userAuth.user?.username || "用户" }}</div>
          <div class="role">{{ roleLabel }}</div>
        </div>
        <div class="user-menu" @click.stop>
          <button class="btn ghost more-trigger" type="button" @click.stop="toggleUserMenu">
            <span class="more-icon" aria-hidden="true"></span>
            <span class="sr-only">更多</span>
          </button>
          <div v-show="showUserMenu" class="dropdown-menu user-menu-dropdown">
            <button class="dropdown-item" type="button" @click="handleLogout">
              退出登录
            </button>
          </div>
        </div>
      </div>
      <div class="storage" v-if="totalSpace">
        <div class="storage-row">
          <span>已用 {{ formatBytes(usedSpace) }}</span>
          <span>余量 {{ formatBytes(freeSpace) }}</span>
        </div>
        <div class="storage-bar">
          <div class="storage-fill" :style="{ width: `${usedPercent}%` }"></div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useUserAuthStore } from "../stores/userAuth";

const userAuth = useUserAuthStore();
const router = useRouter();
const showUserMenu = ref(false);

const initials = computed(() => {
  const name = userAuth.user?.username || "User";
  return name.slice(0, 2).toUpperCase();
});
const roleLabel = computed(() => {
  if (userAuth.user?.is_superuser) return "超级管理员";
  const roles = userAuth.user?.roles || [];
  const names = roles
    .map((role: any) => role?.name)
    .filter((name: string) => Boolean(name));
  if (names.length) return names.join(" / ");
  return "普通用户";
});

const totalSpace = computed(() => userAuth.user?.total_space || 0);
const usedSpace = computed(() => userAuth.user?.used_space || 0);
const freeSpace = computed(() =>
  Math.max(totalSpace.value - usedSpace.value, 0)
);
const usedPercent = computed(() => {
  if (!totalSpace.value) return 0;
  return Math.min(100, Math.round((usedSpace.value / totalSpace.value) * 100));
});

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

const handleLogout = async () => {
  showUserMenu.value = false;
  await userAuth.logout();
  router.push("/login");
};

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value;
};

const closeUserMenu = () => {
  showUserMenu.value = false;
};

onMounted(() => {
  window.addEventListener("click", closeUserMenu);
});

onBeforeUnmount(() => {
  window.removeEventListener("click", closeUserMenu);
});
</script>

<style scoped>
.user-sidebar {
  padding: 24px 18px;
  background: linear-gradient(160deg, #fff 0%, #fff7ef 50%, #f7efe4 100%);
  border-right: 1px solid var(--stroke);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  gap: 24px;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f0cfa7, #c55d35);
  color: #1b1b1b;
  font-weight: 700;
  display: grid;
  place-items: center;
  font-family: "Space Grotesk", sans-serif;
}

.brand-title {
  font-size: 16px;
  font-weight: 700;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--muted);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nav-item {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  transition: background 0.2s ease, transform 0.2s ease;
}

.nav-item.router-link-active {
  background: var(--accent-soft);
  color: var(--accent-strong);
}

.nav-item:hover {
  background: rgba(197, 93, 53, 0.08);
  transform: translateX(4px);
}

.user-panel {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.8);
  padding: 8px 12px;
  border-radius: 16px;
  border: 1px solid var(--stroke);
}

.avatar {
  width: 34px;
  height: 34px;
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
  min-width: 0;
}

.role {
  color: var(--muted);
}

.storage {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 11px;
  color: var(--muted);
}

.storage-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.storage-bar {
  height: 6px;
  background: rgba(197, 93, 53, 0.15);
  border-radius: 999px;
  overflow: hidden;
}

.storage-fill {
  height: 100%;
  background: linear-gradient(135deg, #c55d35, #f0cfa7);
}

.user-menu {
  position: relative;
  margin-left: auto;
}

.more-trigger {
  padding: 6px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.user-menu-dropdown {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  background: var(--surface);
  border: 1px solid var(--stroke);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 6px;
  min-width: 120px;
  z-index: 10;
}

.user-menu-dropdown .dropdown-item {
  width: 100%;
  border: none;
  background: transparent;
  padding: 8px 10px;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  border-radius: 8px;
}

.user-menu-dropdown .dropdown-item:hover {
  background: var(--surface-alt);
}

.more-icon {
  position: relative;
  width: 16px;
  height: 16px;
}

.more-icon::before,
.more-icon::after {
  content: "";
  position: absolute;
  top: 7px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
}

.more-icon::before {
  left: 0;
}

.more-icon::after {
  right: 0;
}

.more-icon {
  display: inline-block;
}

.more-icon::after,
.more-icon::before {
  opacity: 0.9;
}

.more-icon::after,
.more-icon::before,
.more-icon::selection {
  user-select: none;
}

.more-icon::before {
  box-shadow: 6px 0 0 0 currentColor;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 768px) {
  .user-sidebar {
    min-height: auto;
    border-right: none;
    border-bottom: 1px solid var(--stroke);
    padding: 16px;
  }

  .nav {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .nav-item {
    padding: 8px 12px;
  }

  .user-panel {
    width: 100%;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .user-card {
    flex: 1;
  }
}
</style>
