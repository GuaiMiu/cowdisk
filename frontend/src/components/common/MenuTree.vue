<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ChevronDown, HardDrive, MenuSquare, Settings, Shield, Users } from 'lucide-vue-next'
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

const openGroups = ref(new Set<number | string>())

const getGroupKey = (item: MenuRoutersOut) => item.id ?? item.router_path ?? item.name ?? ''

const collectGroupKeys = (items: MenuRoutersOut[], set: Set<number | string>) => {
  items.forEach((item) => {
    if (item.type === 1) {
      const key = getGroupKey(item)
      if (key) {
        set.add(key)
      }
    }
    if (item.children?.length) {
      collectGroupKeys(item.children, set)
    }
  })
}

watch(
  normalizedItems,
  (items) => {
    if (openGroups.value.size > 0) {
      return
    }
    const next = new Set<number | string>()
    collectGroupKeys(items, next)
    openGroups.value = next
  },
  { immediate: true },
)

const isGroupOpen = (item: MenuRoutersOut) => {
  const key = getGroupKey(item)
  return !key || openGroups.value.has(key)
}

const toggleGroup = (item: MenuRoutersOut) => {
  const key = getGroupKey(item)
  if (!key) {
    return
  }
  const next = new Set(openGroups.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  openGroups.value = next
}
</script>

<template>
  <ul class="menu">
    <li v-for="item in normalizedItems" :key="item.id ?? item.name">
      <div v-if="item.type === 1" class="menu__group">
        <button
          type="button"
          class="menu__group-title"
          :aria-expanded="isGroupOpen(item)"
          @click="toggleGroup(item)"
        >
          <component :is="getIcon(item)" v-if="getIcon(item)" class="menu__icon" :size="16" />
          <span>{{ getLabel(item) }}</span>
          <ChevronDown class="menu__chevron" :class="{ 'menu__chevron--open': isGroupOpen(item) }" :size="14" />
        </button>
        <div v-show="isGroupOpen(item)">
          <MenuTree
            v-if="item.children?.length"
            :items="item.children"
            :parent-path="buildFullPath(item, parentPath, basePath)"
            :base-path="basePath"
          />
        </div>
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
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  font-size: 13px;
  color: var(--color-muted);
}

.menu__group-title:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.menu__icon {
  color: var(--color-muted);
}

.menu__chevron {
  margin-left: auto;
  transition: transform 160ms ease;
}

.menu__chevron--open {
  transform: rotate(180deg);
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
