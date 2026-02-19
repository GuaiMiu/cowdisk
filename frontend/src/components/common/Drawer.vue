<script setup lang="ts">
import { computed, ref } from 'vue'
import { X } from 'lucide-vue-next'
import { useDismissibleLayer } from '@/composables/useDismissibleLayer'
import { useFocusTrap } from '@/composables/useFocusTrap'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    width?: number
  }>(),
  {
    title: '',
    width: 360,
  },
)

const emit = defineEmits<{
  (event: 'close'): void
}>()

const panelRef = ref<HTMLElement | null>(null)
const enabled = computed(() => props.open)

useDismissibleLayer({
  enabled,
  rootRef: panelRef,
  onEscape: () => emit('close'),
  onPointerDownOutside: () => emit('close'),
})

useFocusTrap({
  enabled,
  panelRef,
})
</script>

<template>
  <teleport to="body">
    <div class="drawer" :class="{ 'drawer--open': open }">
      <transition name="fade">
        <div v-show="open" class="drawer__backdrop"></div>
      </transition>
      <transition name="slide">
        <div
          v-show="open"
          ref="panelRef"
          class="drawer__panel"
          :style="{ width: `${width}px` }"
          tabindex="-1"
        >
          <header class="drawer__header">
            <h3>{{ title }}</h3>
            <button class="drawer__close" type="button" aria-label="Close" @click="emit('close')">
              <X :size="16" />
            </button>
          </header>
          <section class="drawer__body">
            <slot />
          </section>
          <footer v-if="$slots.footer" class="drawer__footer">
            <slot name="footer" />
          </footer>
        </div>
      </transition>
    </div>
  </teleport>
</template>

<style scoped>
.drawer {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay);
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}

.drawer--open {
  pointer-events: auto;
}

.drawer__backdrop {
  position: absolute;
  inset: 0;
  background: var(--color-overlay);
}

.drawer__panel {
  position: relative;
  height: 100%;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  padding: var(--space-6);
  z-index: 1;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: var(--space-4);
}

.drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer__close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid transparent;
  background: transparent;
  font-size: 18px;
  line-height: 1;
  color: var(--color-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition:
    border-color var(--transition-base),
    color var(--transition-base),
    background var(--transition-base),
    transform var(--transition-fast);
}

.drawer__close:hover {
  border-color: var(--color-border);
  color: var(--color-text);
  background: var(--color-surface-2);
}

.drawer__body {
  overflow: auto;
  overflow-x: hidden;
  display: grid;
  gap: var(--space-4);
  align-content: start;
}

.drawer__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.slide-enter-active,
.slide-leave-active {
  transition:
    transform var(--transition-slow),
    opacity var(--transition-base);
}

.drawer__close:active {
  transform: var(--interaction-press-scale);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
  opacity: 0.98;
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
