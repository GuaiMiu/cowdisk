<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    align?: 'left' | 'right'
    width?: number
  }>(),
  {
    align: 'left',
    width: 200,
  },
)

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const close = () => {
  open.value = false
}

const toggle = () => {
  open.value = !open.value
}

const onDocumentClick = (event: MouseEvent) => {
  const target = event.target as Node
  if (rootRef.value && !rootRef.value.contains(target)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
})
</script>

<template>
  <div ref="rootRef" class="dropdown">
    <div class="dropdown__trigger" @click="toggle">
      <slot name="trigger" />
    </div>
    <transition name="fade-slide">
      <div v-if="open" class="dropdown__content" :style="{ width: `${width}px`, [align]: '0px' }">
        <slot name="content" :close="close" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.dropdown {
  position: relative;
  display: inline-flex;
}

.dropdown__content {
  position: absolute;
  top: calc(100% + var(--space-2));
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  z-index: var(--z-dropdown);
  padding: var(--space-2);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity var(--transition-fast),
    transform var(--transition-fast);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
