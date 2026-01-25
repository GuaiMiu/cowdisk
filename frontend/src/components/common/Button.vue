<script setup lang="ts">
import { computed } from 'vue'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    variant?: ButtonVariant
    size?: ButtonSize
    loading?: boolean
    block?: boolean
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    loading: false,
    block: false,
    type: 'button',
    disabled: false,
  },
)

const classes = computed(() => [
  'btn',
  `btn--${props.variant}`,
  `btn--${props.size}`,
  props.block ? 'btn--block' : '',
  props.loading ? 'btn--loading' : '',
])
</script>

<template>
  <button :type="type" :class="classes" :disabled="disabled || loading">
    <span v-if="loading" class="btn__spinner" aria-hidden="true"></span>
    <span class="btn__content"><slot /></span>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-4);
  font-weight: 600;
  transition: transform var(--transition-fast), box-shadow var(--transition-base),
    background var(--transition-base), color var(--transition-base);
  cursor: pointer;
  border: 1px solid transparent;
  background: var(--color-primary);
  color: var(--color-on-primary);
  box-shadow: var(--shadow-xs);
}

.btn--secondary {
  background: var(--color-surface);
  color: var(--color-text);
  border-color: var(--color-border);
}

.btn--ghost {
  background: transparent;
  color: var(--color-text);
  border-color: transparent;
  box-shadow: none;
}

.btn--danger {
  background: var(--color-danger);
  color: var(--color-on-danger);
}

.btn--sm {
  padding: var(--space-1) var(--space-3);
  font-size: 13px;
}

.btn--md {
  font-size: 14px;
}

.btn--lg {
  padding: var(--space-3) var(--space-5);
  font-size: 15px;
}

.btn--block {
  width: 100%;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
}

.btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn__spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--color-on-primary-weak);
  border-top-color: var(--color-on-primary);
  animation: spin 0.8s linear infinite;
}

.btn--secondary .btn__spinner,
.btn--ghost .btn__spinner {
  border-color: var(--color-text-weak);
  border-top-color: var(--color-text);
}

.btn__content {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
