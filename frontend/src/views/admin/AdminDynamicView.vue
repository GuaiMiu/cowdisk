<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { findAdminMenuByPath, resolveAdminViewLoader } from '@/router/adminDynamic'
import Empty from '@/components/common/Empty.vue'

const route = useRoute()
const authStore = useAuthStore()
const { t } = useI18n({ useScope: 'global' })

const resolvedMenu = computed(() => findAdminMenuByPath(route.path, authStore.routers))

const resolvedComponent = computed(() => {
  const menu = resolvedMenu.value
  if (!menu) {
    return null
  }
  const loader = resolveAdminViewLoader(menu.componentPath)
  if (!loader) {
    return null
  }
  return defineAsyncComponent(loader)
})
</script>

<template>
  <component :is="resolvedComponent" v-if="resolvedComponent" />
  <Empty
    v-else
    :title="t('admin.dynamic.notConfiguredTitle')"
    :description="t('admin.dynamic.notConfiguredDesc')"
  />
</template>

