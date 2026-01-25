<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  perm: string | string[]
}>()

const authStore = useAuthStore()
const allowed = computed(() => authStore.hasAnyPerm(props.perm))
</script>

<template>
  <slot v-if="allowed" />
</template>
