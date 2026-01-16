<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">Cow</div>
      <div>
        <div class="brand-title">笨牛系统</div>
        <div class="brand-subtitle">Admin Console</div>
      </div>
    </div>
    <nav class="nav">
      <router-link class="nav-item" to="/admin" exact-active-class="router-link-active">
        <span>概览</span>
      </router-link>
      <div class="nav-section">系统管理</div>
      <router-link v-if="canUser" class="nav-item" to="/admin/user">
        <span>用户管理</span>
      </router-link>
      <router-link v-if="canRole" class="nav-item" to="/admin/role">
        <span>角色管理</span>
      </router-link>
      <router-link v-if="canMenu" class="nav-item" to="/admin/menu">
        <span>菜单管理</span>
      </router-link>
      <router-link v-if="canDisk" class="nav-item" to="/admin/disk">
        <span>网盘管理</span>
      </router-link>
      <div v-if="extraMenus.length" class="nav-section">更多</div>
      <router-link
        v-for="item in extraMenus"
        :key="item.id"
        class="nav-item"
        :to="item.path"
      >
        <span>{{ item.name }}</span>
      </router-link>
    </nav>
    <div class="sidebar-footer">
      <div class="pill">API: /api/v1/admin</div>
      <div class="footer-note">Vite + Vue 3</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAdminAuthStore } from "../stores/adminAuth";

const auth = useAdminAuthStore();
const canUser = computed(() => auth.hasPerm("system:user:list"));
const canRole = computed(() => auth.hasPerm("system:role:list"));
const canMenu = computed(() => auth.hasPerm("system:menu:list"));
const canDisk = computed(() => auth.hasPerm("disk:file:list"));

const extraMenus = computed(() => {
  const flat = (items: any[] = [], acc: any[] = []) => {
    items.forEach((item) => {
      if (item?.type === 2 && item.router_path) {
        const suffix = item.router_path.startsWith("/")
          ? item.router_path
          : `/${item.router_path}`;
        const path = `/admin${suffix}`;
        const known = ["/admin/user", "/admin/role", "/admin/menu", "/admin/disk"];
        if (!known.includes(path)) {
          acc.push({ id: item.id, name: item.name, path });
        }
      }
      if (item?.children?.length) {
        flat(item.children, acc);
      }
    });
    return acc;
  };
  return flat(auth.menus || []);
});
</script>

<style scoped>
.sidebar {
  padding: 28px 22px;
  background: linear-gradient(160deg, #0f1720 0%, #1b2a34 50%, #2c4352 100%);
  color: #e5ecf1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: sticky;
  top: 0;
}

.brand {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 32px;
}

.brand-mark {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f0cfa7, #c55d35);
  color: #1b1b1b;
  font-weight: 700;
  display: grid;
  place-items: center;
  font-family: "Space Grotesk", sans-serif;
}

.brand-title {
  font-size: 18px;
  font-weight: 600;
}

.brand-subtitle {
  font-size: 12px;
  opacity: 0.7;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.nav-section {
  margin-top: 16px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1.4px;
  opacity: 0.5;
}

.nav-item {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s ease, transform 0.2s ease;
}

.nav-item.router-link-active {
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(4px);
}

.sidebar-footer {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  opacity: 0.7;
}

.footer-note {
  opacity: 0.7;
}

@media (max-width: 768px) {
  .sidebar {
    position: relative;
    min-height: auto;
    padding: 18px 16px;
  }

  .brand {
    margin-bottom: 20px;
  }

  .sidebar-footer {
    margin-top: 16px;
  }
}
</style>
