<script setup lang="ts">
import { computed } from 'vue'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    variant?: ButtonVariant
    size?: ButtonSize
    ariaLabel?: string
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
  }>(),
  {
    variant: 'ghost',
    size: 'md',
    ariaLabel: 'icon button',
    type: 'button',
    disabled: false,
  },
)

const classes = computed(() => ['icon-btn', `icon-btn--${props.variant}`, `icon-btn--${props.size}`])
</script>

<template>
  <button :type="type" :class="classes" :aria-label="ariaLabel" :disabled="disabled">
    <slot />
  </button>
</template>

<style scoped>
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  transition: background var(--transition-base), transform var(--transition-fast),
    box-shadow var(--transition-base);
}

.icon-btn--primary {
  background: var(--color-primary);
  color: var(--color-primary-contrast);
}

.icon-btn--secondary {
  background: var(--color-surface);
  border-color: var(--color-border);
  box-shadow: var(--shadow-xs);
}

.icon-btn--danger {
  background: var(--color-danger);
  color: var(--color-on-danger);
}

.icon-btn--sm {
  width: 30px;
  height: 30px;
}

.icon-btn--md {
  width: 36px;
  height: 36px;
}

.icon-btn--lg {
  width: 42px;
  height: 42px;
}

.icon-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.icon-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
</style>
