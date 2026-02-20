<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useDismissibleLayer } from '@/composables/useDismissibleLayer'

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
const triggerRef = ref<HTMLElement | null>(null)
const contentRef = ref<HTMLElement | null>(null)
const enabled = computed(() => open.value)
const contentId = `dropdown-${Math.random().toString(36).slice(2, 10)}`

const close = () => {
  open.value = false
  triggerRef.value?.focus()
}

const toggle = () => {
  open.value = !open.value
  if (open.value) {
    void nextTick(() => {
      const target = contentRef.value?.querySelector<HTMLElement>(
        'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])',
      )
      target?.focus()
    })
  }
}

const focusMenuItem = (index: number) => {
  const nodes = Array.from(
    contentRef.value?.querySelectorAll<HTMLElement>(
      'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])',
    ) ?? [],
  )
  if (!nodes.length) {
    return
  }
  const next = (index + nodes.length) % nodes.length
  nodes[next]?.focus()
}

const onContentKeyDown = (event: KeyboardEvent) => {
  if (!open.value) {
    return
  }
  const nodes = Array.from(
    contentRef.value?.querySelectorAll<HTMLElement>(
      'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])',
    ) ?? [],
  )
  if (!nodes.length) {
    return
  }
  const active = document.activeElement as HTMLElement | null
  const index = nodes.findIndex((node) => node === active)
  const safeIndex = index < 0 ? 0 : index
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    focusMenuItem(safeIndex + 1)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    focusMenuItem(safeIndex - 1)
    return
  }
  if (event.key === 'Home') {
    event.preventDefault()
    focusMenuItem(0)
    return
  }
  if (event.key === 'End') {
    event.preventDefault()
    focusMenuItem(nodes.length - 1)
  }
}

const onTriggerKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggle()
    return
  }
  if (event.key === 'ArrowDown' && !open.value) {
    event.preventDefault()
    toggle()
  }
}

useDismissibleLayer({
  enabled,
  rootRef,
  onEscape: close,
  onPointerDownOutside: () => {
    open.value = false
  },
})
</script>

<template>
  <div ref="rootRef" class="dropdown">
    <div
      ref="triggerRef"
      class="dropdown__trigger"
      role="button"
      tabindex="0"
      :aria-expanded="open"
      aria-haspopup="menu"
      :aria-controls="open ? contentId : undefined"
      @click="toggle"
      @keydown="onTriggerKeyDown"
    >
      <slot name="trigger" />
    </div>
    <transition name="fade-slide">
      <div
        v-if="open"
        :id="contentId"
        ref="contentRef"
        class="dropdown__content"
        role="menu"
        :style="{ width: `${width}px`, [align]: '0px' }"
        @keydown="onContentKeyDown"
      >
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
  transform-origin: top;
}

.dropdown__trigger:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity var(--motion-fast),
    transform var(--motion-normal);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}
</style>
