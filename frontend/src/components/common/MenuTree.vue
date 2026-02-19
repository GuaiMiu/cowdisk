<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  Circle,
  ChevronDown,
  FolderTree,
  HardDrive,
  MenuSquare,
  Settings,
  Shield,
  ShieldCheck,
  Users,
} from 'lucide-vue-next'
import type { MenuRoutersOut } from '@/types/menu'
import { buildFullPath } from '@/router/menu'
import {
  ADMIN_ACCESS_MENU,
  ADMIN_ACCESS_ROLE,
  ADMIN_ACCESS_USER,
  ADMIN_CONFIG_AUDIT,
  ADMIN_CONFIG_SYSTEM,
  ADMIN_CONFIG_BASE,
} from '@/router/adminPaths'

const props = withDefaults(
  defineProps<{
    items: MenuRoutersOut[]
    parentPath?: string
    basePath?: string
    level?: number
  }>(),
  {
    items: () => [],
    parentPath: '',
    basePath: '',
    level: 0,
  },
)

const normalizedItems = computed(() => props.items || [])
const { t, te } = useI18n({ useScope: 'global' })

const iconMap: Record<string, typeof Users> = {
  system: Settings,
  access: Shield,
  config: Settings,
  systemConfig: Settings,
  audit: ShieldCheck,
  users: Users,
  roles: Shield,
  menus: MenuSquare,
  disk: HardDrive,
  folder: FolderTree,
  default: Circle,
}

const iconNameMap: Record<string, typeof Users> = {
  settings: Settings,
  shield: Shield,
  'shield-check': ShieldCheck,
  users: Users,
  'menu-square': MenuSquare,
  'hard-drive': HardDrive,
  folder: FolderTree,
}

const normalizeSegment = (path: string) => path.trim().replace(/^\/+/, '').toLowerCase()

const routeKeyMap: Record<string, string> = {
  'admin-system': 'system',
  'admin-access': 'access',
  'admin-access-user': 'users',
  'admin-access-role': 'roles',
  'admin-access-menu': 'menus',
  'admin-config': 'config',
  'admin-config-system': 'configSystem',
  'admin-config-audit': 'audit',
}

const pathKeyMap: Record<string, string> = {
  [ADMIN_ACCESS_USER]: 'users',
  [ADMIN_ACCESS_ROLE]: 'roles',
  [ADMIN_ACCESS_MENU]: 'menus',
  [ADMIN_CONFIG_BASE]: 'config',
  [ADMIN_CONFIG_SYSTEM]: 'configSystem',
  [ADMIN_CONFIG_AUDIT]: 'audit',
  system: 'system',
  access: 'access',
  user: 'users',
  role: 'roles',
  menu: 'menus',
  disk: 'disk',
  audit: 'audit',
}

const resolveKey = (item: MenuRoutersOut) => {
  const routeName = normalizeSegment(item.route_name || '')
  if (routeName && routeKeyMap[routeName]) {
    return routeKeyMap[routeName]
  }
  const path = normalizeSegment(item.router_path || '')
  return pathKeyMap[path] || ''
}

const resolveIconKey = (item: MenuRoutersOut) => {
  const path = normalizeSegment(item.router_path || '')
  if (path === ADMIN_CONFIG_BASE) {
    return 'config'
  }
  if (path === ADMIN_CONFIG_SYSTEM || path === 'system') {
    return 'systemConfig'
  }
  if (path === ADMIN_CONFIG_AUDIT || path === 'audit') {
    return 'audit'
  }
  return resolveKey(item)
}

const getLabel = (item: MenuRoutersOut) => {
  const key = resolveKey(item)
  if (key && te(`admin.nav.${key}`)) {
    return t(`admin.nav.${key}`)
  }
  return item.name || ''
}

const getIcon = (item: MenuRoutersOut) => {
  const rawIcon = (item.icon || '').trim().toLowerCase()
  if (rawIcon && iconNameMap[rawIcon]) {
    return iconNameMap[rawIcon]
  }
  const key = resolveIconKey(item)
  if (key && iconMap[key]) {
    return iconMap[key]
  }
  if (item.type === 1) {
    return iconMap.folder
  }
  if (item.type === 2) {
    return iconMap.menus
  }
  return iconMap.default
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

const depthStyle = () => ({ '--depth': String(props.level) })
const isNested = computed(() => (props.level || 0) > 0)
</script>

<template>
  <ul class="menu" :class="{ 'menu--nested': isNested }" :style="depthStyle()">
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
          <ChevronDown
            class="menu__chevron"
            :class="{ 'menu__chevron--open': isGroupOpen(item) }"
            :size="14"
          />
        </button>
        <div v-show="isGroupOpen(item)" class="menu__children">
          <MenuTree
            v-if="item.children?.length"
            :items="item.children"
            :parent-path="buildFullPath(item, parentPath, basePath)"
            :base-path="basePath"
            :level="(level || 0) + 1"
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
  --menu-indent-base: 12px;
  --menu-indent-step: 16px;
  display: grid;
  gap: 2px;
  min-width: 0;
}

.menu--nested {
  margin-top: 0;
}

.menu__group {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.menu__group-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 6px;
  padding: 0 var(--menu-indent-base);
  height: 40px;
  line-height: 40px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-muted);
  padding-left: calc(var(--menu-indent-base) + (var(--depth, 0) * var(--menu-indent-step)));
}

.menu__group-title:hover {
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  color: var(--color-text);
}

.menu__icon {
  color: currentColor;
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
  height: 40px;
  line-height: 40px;
  padding: 0 var(--menu-indent-base);
  padding-left: calc(var(--menu-indent-base) + (var(--depth, 0) * var(--menu-indent-step)));
  border-radius: 6px;
  color: var(--color-muted);
  border-left: 3px solid transparent;
  font-size: 14px;
  font-weight: 500;
  transition:
    background var(--transition-base),
    color var(--transition-base),
    border-color var(--transition-base);
}

.menu__item.router-link-active {
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  color: var(--color-primary);
  border-left-color: var(--color-primary);
}

.menu__item:hover {
  background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  color: var(--color-text);
}

.menu__children {
  min-width: 0;
}
</style>
