<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    value?: number
  }>(),
  {
    value: 0,
  },
)
</script>

<template>
  <div class="progress">
    <div class="progress__bar" :style="{ width: `${Math.min(value, 100)}%` }"></div>
  </div>
</template>

<style scoped>
.progress {
  height: 8px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-2);
  overflow: hidden;
}

.progress__bar {
  height: 100%;
  background: var(--color-primary);
  transition: width var(--transition-base);
}
</style>
