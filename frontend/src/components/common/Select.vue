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
    autoWidth?: boolean
  }>(),
  {
    modelValue: '',
    label: '',
    options: () => [],
    placeholder: '',
    disabled: false,
    error: '',
    size: 'md',
    autoWidth: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void
}>()

const classes = computed(() => [
  'select',
  `select--${props.size}`,
  props.autoWidth ? 'select--auto' : '',
  props.error ? 'select--error' : '',
])

const fieldClasses = computed(() => ['field', props.autoWidth ? 'field--auto' : ''])
</script>

<template>
  <label :class="fieldClasses">
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
    <span class="field__error" :class="{ 'field__error--hidden': !error }">
      {{ error || ' ' }}
    </span>
  </label>
</template>

<style scoped>
.field {
  display: grid;
  gap: var(--space-1);
  width: 100%;
  min-width: 0;
}

.field--auto {
  width: fit-content;
}

.field__label {
  font-size: 12px;
  color: var(--color-muted);
}

.select {
  width: 100%;
  min-height: 36px;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  transition:
    background var(--transition-base),
    border var(--transition-fast),
    box-shadow var(--transition-fast),
    color var(--transition-base);
  appearance: none;
  font-size: inherit;
  line-height: 1.2;
}

.select:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: inset 0 0 0 2px var(--color-primary-soft);
}

.select:disabled {
  background: var(--color-surface-2);
  color: var(--color-muted);
}

.select--error {
  border-color: var(--color-danger);
}

.select--sm {
  min-height: 32px;
  padding: 7px 10px;
  font-size: 13px;
}

.select--auto {
  width: fit-content;
  min-width: 0;
}

.field__error {
  font-size: 12px;
  color: var(--color-danger);
  line-height: 1.2;
  margin-top: 2px;
}

.field__error--hidden {
  display: none;
}
</style>
