<script setup lang="ts">
import { computed, ref } from 'vue'
import { X } from 'lucide-vue-next'
import { useDismissibleLayer } from '@/composables/useDismissibleLayer'
import { useFocusTrap } from '@/composables/useFocusTrap'
import { useBodyScrollLock } from '@/composables/useBodyScrollLock'

let modalSeed = 1

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    width?: number
    closeOnBackdrop?: boolean
    closeOnEsc?: boolean
  }>(),
  {
    title: '',
    width: 520,
    closeOnBackdrop: true,
    closeOnEsc: true,
  },
)

const emit = defineEmits<{
  (event: 'close'): void
}>()

const panelRef = ref<HTMLElement | null>(null)
const enabled = computed(() => props.open)
const titleId = `modal-title-${modalSeed++}`

useDismissibleLayer({
  enabled,
  rootRef: panelRef,
  onEscape: () => {
    if (props.closeOnEsc) {
      emit('close')
    }
  },
  onPointerDownOutside: () => {
    if (props.closeOnBackdrop) {
      emit('close')
    }
  },
})

useFocusTrap({
  enabled,
  panelRef,
})

useBodyScrollLock(enabled)
</script>

<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="open" class="modal">
        <div class="modal__backdrop"></div>
        <div
          ref="panelRef"
          class="modal__panel"
          :style="{ '--modal-width': `${width}px` }"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="title ? titleId : undefined"
          tabindex="-1"
        >
          <header class="modal__header">
            <h3 :id="title ? titleId : undefined">{{ title }}</h3>
            <button class="modal__close" type="button" aria-label="Close" @click="emit('close')">
              <X :size="16" />
            </button>
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
  padding: 16px;
}

.modal__backdrop {
  position: absolute;
  inset: 0;
  background: var(--color-overlay);
}

.modal__panel {
  position: relative;
  box-sizing: border-box;
  width: min(var(--modal-width), 100%);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  padding: var(--space-6);
  z-index: 1;
  max-width: 100%;
  max-height: calc(100dvh - 32px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transform-origin: center;
  transition:
    transform var(--motion-normal),
    box-shadow var(--motion-normal),
    opacity var(--motion-normal);
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.modal__close {
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

.modal__close:hover {
  border-color: var(--color-border);
  color: var(--color-text);
  background: var(--color-surface-2);
}

.modal__body {
  display: grid;
  gap: var(--space-4);
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.modal__footer {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

@media (max-width: 640px) {
  .modal {
    padding: 8px;
  }

  .modal__panel {
    padding: var(--space-4);
    border-radius: var(--radius-md);
    max-height: calc(100dvh - 16px);
  }

  .modal__header {
    margin-bottom: var(--space-3);
  }

  .modal__body {
    gap: var(--space-3);
  }

  .modal__close {
    width: 28px;
    height: 28px;
  }

  .modal__footer {
    margin-top: var(--space-3);
    padding-top: var(--space-3);
    flex-wrap: wrap;
    justify-content: stretch;
  }

  .modal__footer :deep(.btn) {
    flex: 1 1 calc(50% - var(--space-1));
    min-width: 0;
  }
}

@media (max-height: 720px) {
  .modal {
    place-items: start center;
    padding-top: 8px;
    padding-bottom: 8px;
  }

  .modal__panel {
    max-height: calc(100dvh - 16px);
  }
}

@media (max-width: 420px) {
  .modal__footer :deep(.btn) {
    flex-basis: 100%;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--motion-normal);
}

.modal__close:active {
  transform: var(--interaction-press-scale);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-enter-from .modal__panel,
.fade-leave-to .modal__panel {
  transform: scale(0.975);
  box-shadow: var(--shadow-xs);
}
</style>
