<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    label?: string
    placeholder?: string
    type?: string
    disabled?: boolean
    readonly?: boolean
    error?: string
  }>(),
  {
    modelValue: '',
    label: '',
    placeholder: '',
    type: 'text',
    disabled: false,
    readonly: false,
    error: '',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
}>()

const classes = computed(() => ['input', props.error ? 'input--error' : ''])
</script>

<template>
  <label class="field">
    <span v-if="label" class="field__label">{{ label }}</span>
    <input
      :class="classes"
      :value="modelValue"
      :placeholder="placeholder"
      :type="type"
      :disabled="disabled"
      :readonly="readonly"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
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

.input {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  transition:
    border var(--transition-fast),
    box-shadow var(--transition-fast);
}

.input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.input:disabled {
  background: var(--color-surface-2);
  color: var(--color-muted);
}

.input:read-only {
  background: var(--color-surface-2);
  color: var(--color-muted);
}

.input--error {
  border-color: var(--color-danger);
}

.field__error {
  font-size: 12px;
  color: var(--color-danger);
}
</style>
