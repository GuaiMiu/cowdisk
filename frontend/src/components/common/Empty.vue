<script setup lang="ts">
import { i18n } from '@/i18n'

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
  }>(),
  {
    title: i18n.global.t('common.emptyTitle'),
    description: i18n.global.t('common.emptyDescription'),
  },
)
</script>

<template>
  <div class="empty">
    <div class="empty__icon">◎</div>
    <div class="empty__title">{{ title }}</div>
    <div class="empty__desc">{{ description }}</div>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  padding: var(--space-7);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  display: grid;
  gap: var(--space-2);
  place-items: center;
  background: var(--color-surface);
  text-align: center;
}

.empty__icon {
  font-size: 28px;
  color: var(--color-muted);
}

.empty__title {
  font-weight: 600;
}

.empty__desc {
  font-size: 13px;
  color: var(--color-muted);
}
</style>
