<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    rows?: number
  }>(),
  {
    rows: 3,
  },
)
</script>

<template>
  <div class="skeleton">
    <div v-for="row in rows" :key="row" class="skeleton__line"></div>
  </div>
</template>

<style scoped>
.skeleton {
  display: grid;
  gap: var(--space-2);
}

.skeleton__line {
  height: 14px;
  border-radius: var(--radius-xs);
  background: linear-gradient(
    90deg,
    var(--color-skeleton),
    var(--color-skeleton-strong),
    var(--color-skeleton)
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s ease infinite;
}

@keyframes shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
