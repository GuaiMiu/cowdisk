<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { MenuRoutersOut } from '@/types/menu'
import { buildFullPath } from '@/router/menu'

const props = withDefaults(
  defineProps<{
    items: MenuRoutersOut[]
    parentPath?: string
    basePath?: string
  }>(),
  {
    items: () => [],
    parentPath: '',
    basePath: '',
  },
)

const normalizedItems = computed(() => props.items || [])
</script>

<template>
  <ul class="menu">
    <li v-for="item in normalizedItems" :key="item.id ?? item.name">
      <div v-if="item.type === 1" class="menu__group">
        <div class="menu__group-title">{{ item.name }}</div>
        <MenuTree
          v-if="item.children?.length"
          :items="item.children"
          :parent-path="buildFullPath(item, parentPath, basePath)"
          :base-path="basePath"
        />
      </div>
      <RouterLink v-else class="menu__item" :to="buildFullPath(item, parentPath, basePath)">
        {{ item.name }}
      </RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.menu {
  display: grid;
  gap: var(--space-2);
}

.menu__group {
  display: grid;
  gap: var(--space-2);
}

.menu__group-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-muted);
  margin-top: var(--space-2);
}

.menu__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  transition: background var(--transition-base), color var(--transition-base);
}

.menu__item.router-link-active {
  background: var(--color-primary);
  color: var(--color-primary-contrast);
}

.menu__item:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}
</style>
