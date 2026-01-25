<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    width?: number
  }>(),
  {
    title: '',
    width: 520,
  },
)

const emit = defineEmits<{
  (event: 'close'): void
}>()
</script>

<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="open" class="modal">
        <div class="modal__backdrop" @click="emit('close')"></div>
        <div class="modal__panel" :style="{ width: `${width}px` }">
          <header class="modal__header">
            <h3>{{ title }}</h3>
            <button class="modal__close" type="button" @click="emit('close')">关闭</button>
          </header>
          <section class="modal__body">
            <slot />
          </section>
          <footer v-if="$slots.footer" class="modal__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<style scoped>
.modal {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay);
  display: grid;
  place-items: center;
}

.modal__backdrop {
  position: absolute;
  inset: 0;
  background: var(--color-overlay);
}

.modal__panel {
  position: relative;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  padding: var(--space-6);
  z-index: 1;
  max-width: calc(100vw - 32px);
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.modal__close {
  font-size: 13px;
  color: var(--color-muted);
  cursor: pointer;
}

.modal__body {
  display: grid;
  gap: var(--space-4);
}

.modal__footer {
  margin-top: var(--space-6);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
