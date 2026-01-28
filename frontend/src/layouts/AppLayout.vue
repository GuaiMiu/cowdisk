<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { Cloud, Folder, PanelLeftClose, PanelLeftOpen, Share2, Trash2 } from 'lucide-vue-next'
import IconButton from '@/components/common/IconButton.vue'
import Dropdown from '@/components/common/Dropdown.vue'
import { useAuthStore } from '@/stores/auth'
import { getAvatar } from '@/api/modules/auth'
import { getLocale, setLocale } from '@/i18n'

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
const authStore = useAuthStore()
const userLabel = computed(() => authStore.me?.nickname || authStore.me?.username || '')
const { t } = useI18n({ useScope: 'global' })
const router = useRouter()

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

onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 768px)')
  compactQuery = window.matchMedia('(max-width: 1440px)')
  syncSidebarWithViewport()
  mobileQuery.addEventListener('change', handleViewportChange)
  compactQuery.addEventListener('change', handleViewportChange)
})
</script>

<template>
  <div class="layout" :class="{ 'layout--collapsed': !sidebarOpen, 'layout--mobile-open': sidebarOpen }">
    <aside class="layout__sidebar">
      <div class="brand">
        <Cloud class="brand__icon" :size="20" />
        <span class="brand__text">CowDisk</span>
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
      <nav class="nav">
        <RouterLink class="nav__item" to="/app/files">
          <Folder class="nav__icon" />
          <span>{{ t('layout.nav.files') }}</span>
        </RouterLink>
        <RouterLink class="nav__item" to="/app/shares">
          <Share2 class="nav__icon" />
          <span>{{ t('layout.nav.shares') }}</span>
        </RouterLink>
        <RouterLink class="nav__item" to="/app/trash">
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
                <img v-if="avatarSrc && !avatarFailed" :src="avatarSrc" :alt="userLabel" @error="onAvatarError" />
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
              <button type="button" class="user-menu__item" @click="goSettings(); close()">
                {{ t('layout.userMenu.profile') }}
              </button>
              <button v-if="canAdmin" type="button" class="user-menu__item" @click="goAdmin(); close()">
                {{ t('layout.userMenu.admin') }}
              </button>
              <button type="button" class="user-menu__item user-menu__item--danger" @click="logout(); close()">
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
  display: none;
}

.layout--collapsed .nav__item span {
  display: none;
}

.layout--collapsed .nav__item {
  justify-content: center;
  padding: var(--space-2) 0;
}

.layout--collapsed .brand {
  justify-content: center;
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
  transition: opacity 160ms ease, transform 160ms ease;
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

.brand__text {
  line-height: 1;
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
  height: 48px;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  transition: background var(--transition-base), color var(--transition-base);
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

.toolbar__title {
  font-size: 18px;
  font-weight: 600;
}

.toolbar__toggle {
  margin-right: var(--space-3);
}

.toolbar__user {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  font-size: 12px;
  color: var(--color-muted);
  background: var(--color-surface);
}

.toolbar__subtitle {
  font-size: 12px;
  color: var(--color-muted);
}

.toolbar__actions {
  display: flex;
  gap: var(--space-2);
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
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
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
    grid-template-rows: auto auto 1fr;
    border-radius: 0;
    padding: var(--space-6);
  }

  .layout--mobile-open .brand__close {
    display: inline-flex;
  }

  .layout--mobile-open .nav {
    align-content: start;
    justify-items: stretch;
  }
}
</style>
