<script setup lang="ts">
type TagTone = 'default' | 'success' | 'warning' | 'danger' | 'info'

const props = withDefaults(
  defineProps<{
    tone?: TagTone
  }>(),
  {
    tone: 'default',
  },
)
</script>

<template>
  <span class="tag" :class="`tag--${tone}`">
    <slot />
  </span>
</template>

<style scoped>
.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  font-size: 12px;
  font-weight: 600;
  background: var(--color-surface-2);
  color: var(--color-text);
}

.tag--success {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.tag--warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.tag--danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.tag--info {
  background: var(--color-info-soft);
  color: var(--color-info);
}
</style>
