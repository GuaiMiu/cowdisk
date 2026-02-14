<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterView, useRouter } from 'vue-router'
import { LayoutGrid, PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'
import MenuTree from '@/components/common/MenuTree.vue'
import IconButton from '@/components/common/IconButton.vue'
import Dropdown from '@/components/common/Dropdown.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { getAvatar } from '@/api/modules/auth'
import { getLocale, setLocale } from '@/i18n'
import type { MenuRoutersOut } from '@/types/menu'

const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const filterAdminMenus = (items: MenuRoutersOut[]): MenuRoutersOut[] => {
  return items
    .filter((item) => {
      const perm = item.permission_char || ''
      const path = (item.router_path || '').trim().toLowerCase()
      if (perm.startsWith('disk:')) {
        return false
      }
      if (path === 'disk-permissions') {
        return false
      }
      return true
    })
    .map((item) => ({
      ...item,
      children: item.children ? filterAdminMenus(item.children) : [],
    }))
}

const menus = computed(() => filterAdminMenus(authStore.routers))
const siteName = computed(() => appStore.siteName || 'CowDisk')
const siteLogoUrl = computed(() => appStore.siteLogoUrl || '')
const { t } = useI18n({ useScope: 'global' })
const sidebarOpen = ref(true)
let mobileQuery: MediaQueryList | null = null
let compactQuery: MediaQueryList | null = null

const syncSidebarWithViewport = () => {
  if (mobileQuery?.matches) {
    sidebarOpen.value = false
    return
  }
  if (compactQuery?.matches) {
    sidebarOpen.value = false
    return
  }
  sidebarOpen.value = true
}

const userLabel = computed(() => authStore.me?.nickname || authStore.me?.username || '')
const initials = computed(() => {
  const label = userLabel.value || ''
  if (!label) {
    return '?'
  }
  return label.trim().slice(0, 1).toUpperCase()
})

const avatarFailed = ref(false)
const avatarSrc = ref<string | null>(null)
const hasAvatar = computed(() => !!authStore.me?.avatar_path)
const currentLocale = computed(() => getLocale())

const switchLocale = async (locale: string) => {
  await setLocale(locale)
}

const goDrive = () => {
  router.push('/app')
}

const goSettings = () => {
  router.push('/app/settings')
}

const logout = () => {
  void authStore.logout()
}

const onAvatarError = () => {
  avatarFailed.value = true
}

const clearAvatar = () => {
  if (avatarSrc.value) {
    URL.revokeObjectURL(avatarSrc.value)
  }
  avatarSrc.value = null
  avatarFailed.value = false
}

const loadAvatar = async () => {
  if (!hasAvatar.value) {
    clearAvatar()
    return
  }
  try {
    const result = await getAvatar()
    if (avatarSrc.value) {
      URL.revokeObjectURL(avatarSrc.value)
    }
    avatarSrc.value = URL.createObjectURL(result.blob)
    avatarFailed.value = false
  } catch {
    clearAvatar()
  }
}

watch([() => authStore.me?.avatar_path, () => authStore.token], () => {
  void loadAvatar()
})

onBeforeUnmount(() => {
  clearAvatar()
  if (mobileQuery) {
    mobileQuery.removeEventListener('change', handleViewportChange)
  }
  if (compactQuery) {
    compactQuery.removeEventListener('change', handleViewportChange)
  }
})

const handleViewportChange = () => {
  syncSidebarWithViewport()
}

const handleNavItemClick = () => {
  if (mobileQuery?.matches) {
    sidebarOpen.value = false
  }
}

onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 768px)')
  compactQuery = window.matchMedia('(max-width: 1440px)')
  syncSidebarWithViewport()
  mobileQuery.addEventListener('change', handleViewportChange)
  compactQuery.addEventListener('change', handleViewportChange)
})
</script>

<template>
  <div
    class="layout"
    :class="{ 'layout--collapsed': !sidebarOpen, 'layout--mobile-open': sidebarOpen }"
  >
    <aside class="layout__sidebar">
      <div class="brand">
        <img v-if="siteLogoUrl" :src="siteLogoUrl" alt="logo" class="brand__logo" />
        <LayoutGrid v-else class="brand__icon" :size="20" />
        <span class="brand__text" :title="siteName">{{ siteName }}</span>
        <IconButton
          size="sm"
          variant="ghost"
          :aria-label="t('layout.sidebar.close')"
          class="brand__close"
          @click="sidebarOpen = false"
        >
          <PanelLeftClose :size="16" />
        </IconButton>
      </div>
      <nav class="nav" @click="handleNavItemClick">
        <MenuTree :items="menus" base-path="/admin" />
      </nav>
    </aside>

    <header class="layout__toolbar">
      <div class="toolbar__left">
        <IconButton
          size="sm"
          variant="ghost"
          :aria-label="t('layout.sidebar.toggle')"
          class="toolbar__toggle"
          @click="sidebarOpen = !sidebarOpen"
        >
          <PanelLeftClose v-if="sidebarOpen" :size="16" />
          <PanelLeftOpen v-else :size="16" />
        </IconButton>
      </div>
      <div class="toolbar__actions">
        <Dropdown v-if="userLabel" align="right" :width="220">
          <template #trigger>
            <button type="button" class="user-menu__trigger">
              <span class="user-menu__avatar">
                <img
                  v-if="avatarSrc && !avatarFailed"
                  :src="avatarSrc"
                  :alt="userLabel"
                  @error="onAvatarError"
                />
                <span v-else class="user-menu__initials">{{ initials }}</span>
              </span>
              <span class="user-menu__name">{{ userLabel }}</span>
            </button>
          </template>
          <template #content="{ close }">
            <div class="user-menu">
              <div class="user-menu__group">
                <div class="user-menu__label">{{ t('layout.userMenu.language') }}</div>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': currentLocale === 'zh-CN' }"
                  @click="switchLocale('zh-CN'); close()"
                >
                  {{ t('layout.userMenu.langZh') }}
                </button>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': currentLocale === 'en-US' }"
                  @click="switchLocale('en-US'); close()"
                >
                  {{ t('layout.userMenu.langEn') }}
                </button>
              </div>
              <div class="user-menu__divider"></div>
              <button
                type="button"
                class="user-menu__item"
                @click="
                  goSettings();
                  close();
                "
              >
                {{ t('layout.userMenu.profile') }}
              </button>
              <button
                type="button"
                class="user-menu__item"
                @click="
                  goDrive();
                  close();
                "
              >
                {{ t('layout.userMenu.backToDrive') }}
              </button>
              <button
                type="button"
                class="user-menu__item user-menu__item--danger"
                @click="
                  logout();
                  close();
                "
              >
                {{ t('layout.userMenu.logout') }}
              </button>
            </div>
          </template>
        </Dropdown>
        <slot name="toolbar" />
      </div>
    </header>

    <main class="layout__content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  height: 100%;
  display: grid;
  grid-template-columns: 240px 1fr;
  grid-template-rows: auto 1fr;
  grid-template-areas:
    'sidebar toolbar'
    'sidebar content';
  gap: var(--space-4);
  padding: var(--space-5);
  overflow: hidden;
  transition:
    grid-template-columns 260ms cubic-bezier(0.22, 1, 0.36, 1),
    gap 220ms ease;
}

.layout--collapsed {
  grid-template-columns: 72px 1fr;
}

.layout--collapsed .layout__sidebar {
  opacity: 1;
  transform: translateX(-4px);
  padding: var(--space-5) var(--space-3);
}

.layout--collapsed .brand__text {
  opacity: 0;
  max-width: 0;
  transform: translateX(-6px);
}

.layout--collapsed .brand {
  justify-content: center;
  gap: 0;
}

.layout--collapsed :deep(.menu__item span) {
  opacity: 0;
  transform: translateX(-4px);
  width: 0;
  max-width: 0;
  overflow: hidden;
}

.layout--collapsed :deep(.menu__group-title span) {
  opacity: 0;
  transform: translateX(-4px);
  width: 0;
  max-width: 0;
  overflow: hidden;
}

.layout--collapsed :deep(.menu__chevron) {
  opacity: 0;
  transform: scale(0.9);
  width: 0;
  margin-left: 0;
  overflow: hidden;
}

.layout--collapsed :deep(.menu__item) {
  justify-content: center;
  padding: var(--space-2) 0;
  gap: 0;
}

.layout--collapsed :deep(.menu__group-title) {
  justify-content: center;
  padding: var(--space-2) 0;
  gap: 0;
}

.layout__sidebar {
  grid-area: sidebar;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: grid;
  gap: var(--space-3);
  align-content: start;
  grid-auto-rows: max-content;
  box-shadow: var(--shadow-xs);
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  transition:
    opacity 220ms ease,
    transform 260ms cubic-bezier(0.22, 1, 0.36, 1),
    padding 260ms cubic-bezier(0.22, 1, 0.36, 1);
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

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 700;
  font-family: var(--font-display);
  min-height: 32px;
}

.brand__close {
  margin-left: auto;
  display: none;
}

.brand__icon {
  color: var(--color-primary);
}

.brand__logo {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  object-fit: cover;
}

.brand__text {
  line-height: 1;
  flex: 1;
  min-width: 0;
  max-width: 180px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  transition:
    opacity 180ms ease,
    transform 220ms ease,
    max-width 220ms ease;
}

.nav {
  display: grid;
  gap: var(--space-2);
}

:deep(.menu__item),
:deep(.menu__group-title) {
  height: 48px;
}

:deep(.menu__icon) {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
}

:deep(.menu__item span),
:deep(.menu__group-title span),
:deep(.menu__chevron) {
  transition:
    opacity 160ms ease,
    transform 220ms ease;
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

.toolbar__toggle {
  margin-right: var(--space-3);
}

.user-menu__trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base);
}

.user-menu__trigger:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-xs);
}

.user-menu__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--color-surface-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text);
}

.user-menu__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-menu__initials {
  letter-spacing: 0.02em;
}

.user-menu__name {
  font-size: 12px;
  color: var(--color-muted);
}

.user-menu {
  display: grid;
  gap: var(--space-2);
}

.user-menu__group {
  display: grid;
  gap: var(--space-1);
}

.user-menu__label {
  font-size: 11px;
  color: var(--color-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.user-menu__item {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text);
}

.user-menu__item:hover {
  background: var(--color-surface-2);
}

.user-menu__item.is-active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.user-menu__item--danger {
  color: var(--color-danger);
}

.user-menu__divider {
  height: 1px;
  background: var(--color-border);
  margin: 2px 0;
}

@media (max-width: 1280px) {
  .layout {
    grid-template-columns: 240px 1fr;
    grid-template-rows: auto 1fr;
    grid-template-areas:
      'sidebar toolbar'
      'sidebar content';
  }

  .layout--collapsed {
    grid-template-columns: 72px 1fr;
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

  .layout--mobile-open .layout__sidebar {
    display: grid;
    position: fixed;
    inset: 0;
    z-index: var(--z-overlay);
    grid-template-rows: auto 1fr;
    border-radius: 0;
    padding: var(--space-6);
  }

  .layout--mobile-open .brand__close {
    display: inline-flex;
  }
}
</style>
