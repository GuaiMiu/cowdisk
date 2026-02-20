<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { LayoutGrid, PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'
import MenuTree from '@/components/common/MenuTree.vue'
import IconButton from '@/components/common/IconButton.vue'
import Dropdown from '@/components/common/Dropdown.vue'
import HeaderSearch from '@/components/common/HeaderSearch.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { getAvatar } from '@/api/modules/auth'
import { getLocale, setLocale } from '@/i18n'
import type { MenuRoutersOut } from '@/types/menu'
import { useHeaderSearchQuery } from '@/composables/useHeaderSearch'
import { useResponsiveSidebar } from '@/composables/useResponsiveSidebar'
import { useUserAvatar } from '@/composables/useUserAvatar'
import { useTheme } from '@/composables/useTheme'

const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const route = useRoute()
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
const { sidebarOpen, handleNavItemClick } = useResponsiveSidebar()
const { themeMode, setThemeMode } = useTheme()

const userLabel = computed(() => authStore.me?.nickname || authStore.me?.username || '')
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

const { avatarFailed, avatarSrc, initials, onAvatarError } = useUserAvatar({
  label: userLabel,
  avatarPath: computed(() => authStore.me?.avatar_path),
  token: computed(() => authStore.token),
  loadAvatar: getAvatar,
})

const normalizedPath = computed(() => route.path.trim().toLowerCase())
const searchPlaceholder = computed(() => {
  if (normalizedPath.value.startsWith('/admin/access/user')) {
    return t('admin.user.searchPlaceholder')
  }
  if (normalizedPath.value.startsWith('/admin/access/role')) {
    return t('admin.role.searchPlaceholder')
  }
  if (normalizedPath.value.startsWith('/admin/access/menu')) {
    return t('admin.menu.searchPlaceholder')
  }
  return ''
})
const searchEnabled = computed(() => !!searchPlaceholder.value)
const { modelValue: searchValue, submit: submitSearch } = useHeaderSearchQuery({
  route,
  router,
  enabled: searchEnabled,
})

const closeMobileSidebar = () => {
  sidebarOpen.value = false
}
</script>

<template>
  <div
    class="layout"
    :class="{ 'layout--collapsed': !sidebarOpen, 'layout--mobile-open': sidebarOpen }"
  >
    <button
      v-if="sidebarOpen"
      type="button"
      class="layout__backdrop"
      :aria-label="t('layout.sidebar.close')"
      @click="closeMobileSidebar"
    ></button>
    <aside class="layout__sidebar">
      <div class="brand">
        <img v-if="siteLogoUrl" :src="siteLogoUrl" alt="logo" class="brand__logo" />
        <LayoutGrid v-else class="brand__icon" :size="20" />
        <span class="brand__text" :title="siteName">{{ siteName }}</span>
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
      <div class="toolbar__center">
        <HeaderSearch
          v-if="searchEnabled"
          v-model="searchValue"
          :placeholder="searchPlaceholder"
          @submit="submitSearch"
        />
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
              <div class="user-menu__group">
                <div class="user-menu__label">{{ t('layout.userMenu.theme') }}</div>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': themeMode === 'system' }"
                  @click="setThemeMode('system'); close()"
                >
                  {{ t('layout.userMenu.themeSystem') }}
                </button>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': themeMode === 'light' }"
                  @click="setThemeMode('light'); close()"
                >
                  {{ t('layout.userMenu.themeLight') }}
                </button>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': themeMode === 'dark' }"
                  @click="setThemeMode('dark'); close()"
                >
                  {{ t('layout.userMenu.themeDark') }}
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

@media (max-width: 768px) {
  .layout--mobile-open .layout__sidebar {
    grid-template-rows: auto 1fr;
  }
}
</style>
