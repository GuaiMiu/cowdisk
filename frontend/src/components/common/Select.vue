<script setup lang="ts">
import { computed } from 'vue'

type Option = {
  label: string
  value: string | number
}

type SelectSize = 'sm' | 'md'

const props = withDefaults(
  defineProps<{
    modelValue?: string | number
    label?: string
    options?: Option[]
    placeholder?: string
    disabled?: boolean
    error?: string
    size?: SelectSize
  }>(),
  {
    modelValue: '',
    label: '',
    options: () => [],
    placeholder: '',
    disabled: false,
    error: '',
    size: 'md',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void
}>()

const classes = computed(() => [
  'select',
  `select--${props.size}`,
  props.error ? 'select--error' : '',
])
</script>

<template>
  <label class="field">
    <span v-if="label" class="field__label">{{ label }}</span>
    <select
      :class="classes"
      :value="modelValue"
      :disabled="disabled"
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option v-if="placeholder" disabled value="">{{ placeholder }}</option>
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <span v-if="error" class="field__error">{{ error }}</span>
  </label>
</template>

<style scoped>
.field {
  display: grid;
  gap: var(--space-2);
}

.field__label {
  font-size: 13px;
  color: var(--color-muted);
}

.select {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  transition: border var(--transition-fast), box-shadow var(--transition-fast);
  appearance: none;
  font-size: 14px;
}

.select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.select:disabled {
  background: var(--color-surface-2);
  color: var(--color-muted);
}

.select--error {
  border-color: var(--color-danger);
}

.select--sm {
  padding: var(--space-1) var(--space-3);
  font-size: 13px;
}

.field__error {
  font-size: 12px;
  color: var(--color-danger);
}
</style>
