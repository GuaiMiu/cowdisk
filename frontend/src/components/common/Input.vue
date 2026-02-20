<script setup lang="ts">
import { computed } from 'vue'

let inputSeed = 1

const props = withDefaults(
  defineProps<{
    modelValue?: string
    label?: string
    placeholder?: string
    type?: string
    disabled?: boolean
    readonly?: boolean
    error?: string
    help?: string
    id?: string
    name?: string
    required?: boolean
    size?: 'sm' | 'md'
  }>(),
  {
    modelValue: '',
    label: '',
    placeholder: '',
    type: 'text',
    disabled: false,
    readonly: false,
    error: '',
    help: '',
    id: '',
    name: '',
    required: false,
    size: 'md',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'blur', payload: FocusEvent): void
  (event: 'focus', payload: FocusEvent): void
  (event: 'enter', payload: KeyboardEvent): void
}>()

const classes = computed(() => ['input', `input--${props.size}`, props.error ? 'input--error' : ''])
const inputId = computed(() => props.id || `input-${inputSeed++}`)
const helpId = computed(() => `${inputId.value}-help`)
const errorId = computed(() => `${inputId.value}-error`)
const describedBy = computed(() => {
  const ids: string[] = []
  if (props.help) {
    ids.push(helpId.value)
  }
  if (props.error) {
    ids.push(errorId.value)
  }
  return ids.join(' ') || undefined
})
</script>

<template>
  <label class="field" :for="inputId">
    <span v-if="label" class="field__label">
      {{ label }}<span v-if="required" class="field__required">*</span>
    </span>
    <input
      :id="inputId"
      :name="name || undefined"
      :class="classes"
      :value="modelValue"
      :placeholder="placeholder"
      :type="type"
      :disabled="disabled"
      :readonly="readonly"
      :required="required"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @blur="emit('blur', $event)"
      @focus="emit('focus', $event)"
      @keydown.enter="emit('enter', $event)"
    />
    <span v-if="help" :id="helpId" class="field__help">{{ help }}</span>
    <span :id="errorId" class="field__error" :class="{ 'field__error--hidden': !error }">
      <slot name="error">{{ error || ' ' }}</slot>
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

.field__label {
  font-size: 12px;
  color: var(--color-muted);
}

.field__required {
  margin-left: 2px;
  color: var(--color-danger);
}

.input {
  width: 100%;
  min-height: 36px;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  line-height: 1.2;
  transition:
    background var(--transition-base),
    border var(--transition-fast),
    box-shadow var(--transition-fast),
    color var(--transition-base);
}

.input--sm {
  min-height: 32px;
  padding: 7px 10px;
  font-size: 13px;
}

.input::placeholder {
  color: var(--color-muted);
}

.input:focus-visible {
  outline: none;
  color: var(--color-text);
  background: var(--color-surface);
  border-color: var(--color-primary);
  box-shadow: inset 0 0 0 2px var(--color-primary-soft);
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
  line-height: 1.2;
  margin-top: 2px;
}

.field__help {
  font-size: 12px;
  color: var(--color-muted);
  line-height: 1.2;
  margin-top: 2px;
}

.field__error--hidden {
  display: none;
}
</style>
