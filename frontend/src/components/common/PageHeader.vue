<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    title: string
    subtitle?: string
  }>(),
  {
    subtitle: '',
  },
)
</script>

<template>
  <div class="page-header">
    <div>
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4) var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
}

.page-header__title {
  font-size: 24px;
}

.page-header__subtitle {
  color: var(--color-muted);
  font-size: 14px;
  margin-top: var(--space-1);
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-2);
}

@media (max-width: 768px) {
  .page-header {
    grid-template-columns: 1fr;
  }

  .page-header__actions {
    justify-content: flex-start;
  }
}
</style>
