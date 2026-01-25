<script setup lang="ts">
import { RouterLink } from 'vue-router'

type Crumb = {
  label: string
  to?: string
}

const props = withDefaults(
  defineProps<{
    items: Crumb[]
  }>(),
  {
    items: () => [],
  },
)
</script>

<template>
  <nav class="breadcrumb">
    <template v-for="(item, index) in items" :key="item.label + index">
      <RouterLink v-if="item.to" :to="item.to" class="breadcrumb__link">
        {{ item.label }}
      </RouterLink>
      <span v-else class="breadcrumb__text">{{ item.label }}</span>
      <span v-if="index < items.length - 1" class="breadcrumb__sep">/</span>
    </template>
  </nav>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  color: var(--color-muted);
}

.breadcrumb__link {
  color: var(--color-text);
  font-weight: 600;
}

.breadcrumb__sep {
  color: var(--color-border);
}
</style>
