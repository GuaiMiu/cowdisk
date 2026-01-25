<script setup lang="ts">
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { LayoutGrid } from 'lucide-vue-next'
import MenuTree from '@/components/common/MenuTree.vue'
import { useAuthStore } from '@/stores/auth'
import { filterMenus } from '@/router/menu'

const authStore = useAuthStore()
const menus = computed(() => filterMenus(authStore.routers, authStore.permissions, !!authStore.me?.is_superuser))
</script>

<template>
  <div class="layout">
    <aside class="layout__sidebar">
      <div class="brand">
        <LayoutGrid class="brand__icon" :size="20" />
        <span class="brand__text">系统后台</span>
      </div>
      <nav class="nav">
        <MenuTree :items="menus" base-path="/admin" />
      </nav>
    </aside>

    <header class="layout__toolbar">
      <div class="toolbar__left">
        <div class="toolbar__title">系统管理</div>
        <div class="toolbar__subtitle">权限、角色、菜单统一配置</div>
      </div>
      <div class="toolbar__actions">
        <slot name="toolbar" />
      </div>
    </header>

    <main class="layout__content">
      <RouterView />
    </main>

    <aside class="layout__panel">
      <slot name="panel">
        <div class="panel-card">
          <div class="panel-card__title">提示</div>
          <div class="panel-card__value">后台仅用于系统管理</div>
          <div class="panel-card__hint">不管理任何用户文件</div>
        </div>
      </slot>
    </aside>
  </div>
</template>

<style scoped>
.layout {
  height: 100%;
  display: grid;
  grid-template-columns: 240px 1fr 280px;
  grid-template-rows: auto 1fr;
  grid-template-areas:
    'sidebar toolbar panel'
    'sidebar content panel';
  gap: var(--space-4);
  padding: var(--space-5);
  overflow: hidden;
}

.layout__sidebar {
  grid-area: sidebar;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: grid;
  gap: var(--space-5);
  align-content: start;
  grid-auto-rows: max-content;
  box-shadow: var(--shadow-xs);
  overflow: auto;
  min-height: 0;
}

.layout__toolbar {
  grid-area: toolbar;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-xs);
}

.layout__content {
  grid-area: content;
  display: grid;
  gap: var(--space-4);
  align-content: stretch;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.layout__panel {
  grid-area: panel;
  display: grid;
  align-content: start;
  gap: var(--space-4);
  overflow: auto;
  min-height: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 700;
  font-family: var(--font-display);
}

.brand__icon {
  color: var(--color-primary);
}

.nav {
  display: grid;
  gap: var(--space-2);
}

.toolbar__title {
  font-size: 18px;
  font-weight: 600;
}

.toolbar__subtitle {
  font-size: 12px;
  color: var(--color-muted);
}

.toolbar__actions {
  display: flex;
  gap: var(--space-2);
}

.panel-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-xs);
  display: grid;
  gap: var(--space-2);
}

.panel-card__title {
  font-size: 13px;
  color: var(--color-muted);
}

.panel-card__value {
  font-size: 18px;
  font-weight: 600;
}

.panel-card__hint {
  font-size: 12px;
  color: var(--color-muted);
}

@media (max-width: 1280px) {
  .layout {
    grid-template-columns: 220px 1fr;
    grid-template-rows: auto 1fr;
    grid-template-areas:
      'sidebar toolbar'
      'sidebar content';
  }

  .layout__panel {
    display: none;
  }
}

@media (max-width: 1024px) {
  .layout {
    grid-template-columns: 200px 1fr;
  }
}

@media (max-width: 768px) {
  .layout {
    grid-template-columns: 1fr;
    grid-template-areas:
      'toolbar'
      'content';
    padding: var(--space-3);
  }

  .layout__sidebar {
    display: none;
  }
}
</style>
