<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { Cloud, Folder, PanelLeftClose, PanelLeftOpen, Share2, Trash2 } from 'lucide-vue-next'
import IconButton from '@/components/common/IconButton.vue'
import Dropdown from '@/components/common/Dropdown.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { getAvatar } from '@/api/modules/auth'
import { getLocale, setLocale } from '@/i18n'
import { useResponsiveSidebar } from '@/composables/useResponsiveSidebar'
import { useUserAvatar } from '@/composables/useUserAvatar'

const authStore = useAuthStore()
const appStore = useAppStore()
const { sidebarOpen, handleNavItemClick } = useResponsiveSidebar()
const userLabel = computed(() => authStore.me?.nickname || authStore.me?.username || '')
const siteName = computed(() => appStore.siteName || 'CowDisk')
const siteLogoUrl = computed(() => appStore.siteLogoUrl || '')
const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
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

@media (max-width: 768px) {
  .layout--mobile-open .nav {
    align-content: start;
    justify-items: stretch;
  }
}
</style>
