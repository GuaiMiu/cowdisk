<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { findAdminMenuByPath, resolveAdminViewLoader } from '@/router/adminDynamic'
import Empty from '@/components/common/Empty.vue'

const route = useRoute()
const authStore = useAuthStore()

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
    title="页面未配置"
    description="当前菜单未配置 component_path 或组件路径无效，请在菜单管理中修正。"
  />
</template>

