<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { HardDrive, MenuSquare, Settings, Shield, Users } from 'lucide-vue-next'
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
const { t } = useI18n({ useScope: 'global' })

const iconMap: Record<string, typeof Users> = {
  system: Settings,
  users: Users,
  roles: Shield,
  menus: MenuSquare,
  disk: HardDrive,
}

const resolveKey = (item: MenuRoutersOut) => {
  const path = item.router_path?.trim().toLowerCase() || ''
  if (path === '/system') {
    return 'system'
  }
  if (path === '/user') {
    return 'users'
  }
  if (path === '/role') {
    return 'roles'
  }
  if (path === '/menu') {
    return 'menus'
  }
  if (path === '/disk') {
    return 'disk'
  }
  return ''
}

const getLabel = (item: MenuRoutersOut) => {
  const key = resolveKey(item)
  if (key) {
    return t(`admin.nav.${key}`)
  }
  return item.name || ''
}

const getIcon = (item: MenuRoutersOut) => {
  const key = resolveKey(item)
  return key ? iconMap[key] : null
}
</script>

<template>
  <ul class="menu">
    <li v-for="item in normalizedItems" :key="item.id ?? item.name">
      <div v-if="item.type === 1" class="menu__group">
        <div class="menu__group-title">
          <component :is="getIcon(item)" v-if="getIcon(item)" class="menu__icon" :size="14" />
          <span>{{ getLabel(item) }}</span>
        </div>
        <MenuTree
          v-if="item.children?.length"
          :items="item.children"
          :parent-path="buildFullPath(item, parentPath, basePath)"
          :base-path="basePath"
        />
      </div>
      <RouterLink v-else class="menu__item" :to="buildFullPath(item, parentPath, basePath)">
        <component :is="getIcon(item)" v-if="getIcon(item)" class="menu__icon" :size="16" />
        <span>{{ getLabel(item) }}</span>
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
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-muted);
  margin-top: var(--space-2);
}

.menu__icon {
  color: var(--color-muted);
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
