<script setup lang="ts">
import { computed, useSlots } from 'vue'

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

const slots = useSlots()
const hasPrepend = computed(() => !!slots.prepend)
const hasAppend = computed(() => !!slots.append)
const shellClasses = computed(() => [
  'input-shell',
  `input-shell--${props.size}`,
  props.error ? 'input-shell--error' : '',
  props.disabled ? 'input-shell--disabled' : '',
  props.readonly ? 'input-shell--readonly' : '',
  hasPrepend.value ? 'input-shell--with-prepend' : '',
  hasAppend.value ? 'input-shell--with-append' : '',
])
const controlClasses = computed(() => ['input-control', `input-control--${props.size}`])
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
    <span :class="shellClasses">
      <span v-if="hasPrepend" class="input-addon input-addon--prepend">
        <slot name="prepend" />
      </span>
      <input
        :id="inputId"
        :name="name || undefined"
        :class="controlClasses"
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
      <span v-if="hasAppend" class="input-addon input-addon--append">
        <slot name="append" />
      </span>
    </span>
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

.input-shell {
  display: inline-flex;
  align-items: stretch;
  width: 100%;
  overflow: hidden;
  min-height: 36px;
  box-sizing: border-box;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  transition:
    background var(--transition-base),
    border var(--transition-fast),
    box-shadow var(--transition-fast),
    color var(--transition-base);
}

.input-shell--sm {
  min-height: 32px;
}

.input-control {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: none;
  box-sizing: border-box;
  background: transparent;
  color: inherit;
  line-height: 1.2;
  padding: 10px 12px;
}

.input-control--sm {
  padding: 7px 10px;
  font-size: 13px;
}

.input-control::placeholder {
  color: var(--color-muted);
}

.input-shell:focus-within {
  border-color: var(--color-primary);
  box-shadow: inset 0 0 0 2px var(--color-primary-soft);
}

.input-shell--disabled {
  background: var(--color-surface-2);
  color: var(--color-muted);
}

.input-shell--readonly {
  background: var(--color-surface-2);
  color: var(--color-muted);
}

.input-shell--error {
  border-color: var(--color-danger);
}

.input-addon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-2);
  background: var(--color-surface-2);
  color: var(--color-muted);
  white-space: nowrap;
}

.input-addon--prepend {
  border-right: 1px solid var(--color-border);
}

.input-addon--append {
  border-left: 1px solid var(--color-border);
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
