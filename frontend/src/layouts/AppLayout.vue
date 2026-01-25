<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { Cloud, Folder, Share2, Trash2 } from 'lucide-vue-next'
</script>

<template>
  <div class="layout">
    <aside class="layout__sidebar">
      <div class="brand">
        <Cloud class="brand__icon" :size="20" />
        <span class="brand__text">CowDisk</span>
      </div>
      <nav class="nav">
        <RouterLink class="nav__item" to="/app/files">
          <Folder :size="18" />
          <span>我的文件</span>
        </RouterLink>
        <RouterLink class="nav__item" to="/app/shares">
          <Share2 :size="18" />
          <span>分享</span>
        </RouterLink>
        <RouterLink class="nav__item" to="/app/trash">
          <Trash2 :size="18" />
          <span>回收站</span>
        </RouterLink>
      </nav>
    </aside>

    <header class="layout__toolbar">
      <div class="toolbar__left">
        <div class="toolbar__title">个人网盘</div>
        <div class="toolbar__subtitle">保持文件井然有序</div>
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
          <div class="panel-card__title">存储概览</div>
          <div class="panel-card__value">0 GB / 0 GB</div>
          <div class="panel-card__hint">上传后将展示使用情况</div>
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

.nav__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  transition: background var(--transition-base), color var(--transition-base);
}

.nav__item.router-link-active {
  background: var(--color-primary);
  color: var(--color-primary-contrast);
}

.nav__item:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
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
  font-size: 20px;
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
