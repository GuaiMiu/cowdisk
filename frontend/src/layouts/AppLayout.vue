<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { Cloud, Folder, PanelLeftClose, PanelLeftOpen, Share2, Trash2 } from 'lucide-vue-next'
import IconButton from '@/components/common/IconButton.vue'
import Dropdown from '@/components/common/Dropdown.vue'
import HeaderSearch from '@/components/common/HeaderSearch.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { getAvatar } from '@/api/modules/auth'
import { getLocale, setLocale } from '@/i18n'
import { useResponsiveSidebar } from '@/composables/useResponsiveSidebar'
import { useHeaderSearchQuery } from '@/composables/useHeaderSearch'
import { useUserAvatar } from '@/composables/useUserAvatar'
import { useTheme } from '@/composables/useTheme'
import { formatBytes } from '@/utils/format'

const authStore = useAuthStore()
const appStore = useAppStore()
const { sidebarOpen, handleNavItemClick } = useResponsiveSidebar()
const { themeMode, setThemeMode } = useTheme()
const userLabel = computed(() => authStore.me?.nickname || authStore.me?.username || '')
const siteName = computed(() => appStore.siteName || 'CowDisk')
const siteLogoUrl = computed(() => appStore.siteLogoUrl || '')
const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const route = useRoute()
const currentLocale = computed(() => getLocale())
const canAdmin = computed(() => {
  if (authStore.me?.is_superuser) {
    return true
  }
  return Array.from(authStore.permissions).some((perm) => perm.startsWith('system:'))
})

const switchLocale = async (locale: string) => {
  await setLocale(locale)
}

const goAdmin = () => {
  router.push('/admin')
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

const searchPlaceholder = computed(() => {
  if (route.name === 'app-files') {
    return t('fileToolbar.searchPlaceholder')
  }
  if (route.name === 'app-shares') {
    return t('shares.searchPlaceholder')
  }
  if (route.name === 'app-trash') {
    return t('trash.searchPlaceholder')
  }
  return ''
})

const searchEnabled = computed(() => !!searchPlaceholder.value)
const { modelValue: searchValue, submit: submitSearch } = useHeaderSearchQuery({
  route,
  router,
  enabled: searchEnabled,
})
const totalSpace = computed(() => Math.max(Number(authStore.me?.total_space ?? 0), 0))
const usedSpace = computed(() => Math.max(Number(authStore.me?.used_space ?? 0), 0))
const hasQuota = computed(() => totalSpace.value > 0)
const usageRatio = computed(() => {
  if (!hasQuota.value) {
    return 0
  }
  return Math.max(0, Math.min(usedSpace.value / totalSpace.value, 1))
})
const usagePercent = computed(() => Math.round(usageRatio.value * 100))
const usageLabel = computed(() =>
  hasQuota.value
    ? `${formatBytes(usedSpace.value)} / ${formatBytes(totalSpace.value)}`
    : formatBytes(usedSpace.value),
)
const usageRingStyle = computed(() => ({
  '--usage': `${usagePercent.value}`,
}))
</script>

<template>
  <div
    class="layout"
    :class="{ 'layout--collapsed': !sidebarOpen, 'layout--mobile-open': sidebarOpen }"
  >
    <aside class="layout__sidebar">
      <div class="brand">
        <img v-if="siteLogoUrl" :src="siteLogoUrl" alt="logo" class="brand__logo" />
        <Cloud v-else class="brand__icon" :size="20" />
        <span class="brand__text" :title="siteName">{{ siteName }}</span>
      </div>
      <nav class="nav">
        <RouterLink class="nav__item" to="/app/files" @click="handleNavItemClick">
          <Folder class="nav__icon" />
          <span>{{ t('layout.nav.files') }}</span>
        </RouterLink>
        <RouterLink class="nav__item" to="/app/shares" @click="handleNavItemClick">
          <Share2 class="nav__icon" />
          <span>{{ t('layout.nav.shares') }}</span>
        </RouterLink>
        <RouterLink class="nav__item" to="/app/trash" @click="handleNavItemClick">
          <Trash2 class="nav__icon" />
          <span>{{ t('layout.nav.trash') }}</span>
        </RouterLink>
      </nav>
      <div class="sidebar-storage" :title="usageLabel">
        <template v-if="sidebarOpen">
          <div class="sidebar-storage__value">{{ usageLabel }}</div>
          <div class="sidebar-storage__track">
            <div class="sidebar-storage__fill" :style="{ width: `${usagePercent}%` }"></div>
          </div>
        </template>
        <template v-else>
          <div class="sidebar-storage__ring" :style="usageRingStyle">
            <span>{{ usagePercent }}%</span>
          </div>
        </template>
      </div>
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
                  @click="switchLocale('zh-CN'); close();"
                >
                  {{ t('layout.userMenu.langZh') }}
                </button>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': currentLocale === 'en-US' }"
                  @click="switchLocale('en-US'); close();"
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
                  @click="setThemeMode('system'); close();"
                >
                  {{ t('layout.userMenu.themeSystem') }}
                </button>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': themeMode === 'light' }"
                  @click="setThemeMode('light'); close();"
                >
                  {{ t('layout.userMenu.themeLight') }}
                </button>
                <button
                  type="button"
                  class="user-menu__item"
                  :class="{ 'is-active': themeMode === 'dark' }"
                  @click="setThemeMode('dark'); close();"
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
                v-if="canAdmin"
                type="button"
                class="user-menu__item"
                @click="
                  goAdmin();
                  close();
                "
              >
                {{ t('layout.userMenu.admin') }}
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
.layout__sidebar {
  grid-template-rows: auto 1fr auto;
  align-content: stretch;
}

.layout--collapsed .nav__item span {
  opacity: 0;
  transform: translateX(-4px);
  width: 0;
  max-width: 0;
  overflow: hidden;
}

.layout--collapsed .nav__item {
  justify-content: center;
  padding: var(--space-2) 0;
  gap: 0;
}

.nav__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  height: 48px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  transition:
    background var(--transition-base),
    color var(--transition-base),
    padding 220ms ease,
    justify-content 220ms ease;
}

.nav__item span {
  transition:
    opacity 160ms ease,
    transform 220ms ease;
}

.nav__icon {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
}

.nav__item.router-link-active {
  background: var(--color-primary);
  color: var(--color-primary-contrast);
}

.nav__item:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.nav {
  align-content: start;
}

.sidebar-storage {
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-2);
  display: grid;
  gap: var(--space-2);
}

.sidebar-storage__value {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text);
}

.sidebar-storage__track {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: var(--color-border);
  overflow: hidden;
}

.sidebar-storage__fill {
  height: 100%;
  border-radius: 999px;
  background: var(--color-primary);
  min-width: 2px;
}

.layout--collapsed .sidebar-storage {
  margin-top: var(--space-2);
  padding: 0;
  border: 0;
  background: transparent;
  justify-items: center;
  justify-self: center;
}

.sidebar-storage__ring {
  --ring-size: 40px;
  width: var(--ring-size);
  height: var(--ring-size);
  border-radius: 50%;
  display: grid;
  place-items: center;
  position: relative;
  background: conic-gradient(
    var(--color-primary) calc(var(--usage, 0) * 1%),
    var(--color-border) 0
  );
}

.sidebar-storage__ring::before {
  content: '';
  width: calc(var(--ring-size) - 10px);
  height: calc(var(--ring-size) - 10px);
  border-radius: 50%;
  background: var(--color-surface-2);
}

.sidebar-storage__ring span {
  position: absolute;
  font-size: 10px;
  font-weight: 700;
  color: var(--color-text);
}

@media (max-width: 768px) {
  .layout--mobile-open .nav {
    align-content: start;
    justify-items: stretch;
  }
}
</style>
