<script setup lang="ts">
import { Search, X } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    modelValue: '',
    placeholder: '',
    disabled: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'submit'): void
}>()

const clear = () => {
  emit('update:modelValue', '')
  emit('submit')
}
</script>

<template>
  <div class="header-search" role="search">
    <input
      class="header-search__input"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @keydown.enter.prevent="emit('submit')"
      @keydown.esc.prevent="clear"
    />
    <button
      type="button"
      class="header-search__clear"
      :class="{ 'is-hidden': !modelValue }"
      :aria-label="'clear search'"
      :disabled="!modelValue"
      @click="clear"
    >
      <X :size="14" />
    </button>
    <button
      type="button"
      class="header-search__submit"
      :aria-label="'search'"
      @click="emit('submit')"
    >
      <Search class="header-search__icon" :size="16" />
    </button>
  </div>
</template>

<style scoped>
.header-search {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-width: 0;
  height: 36px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    background var(--transition-base);
}

.header-search:focus-within {
  border-color: var(--color-primary);
  box-shadow: inset 0 0 0 2px var(--color-primary-soft);
}

.header-search__submit {
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--color-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    color var(--transition-fast),
    background var(--transition-fast),
    transform var(--transition-fast);
}

.header-search__submit:hover {
  color: var(--color-text);
  background: var(--color-surface-2);
}

.header-search__submit:active {
  transform: var(--interaction-press-scale);
}

.header-search__icon {
  color: currentColor;
  flex: 0 0 auto;
}

.header-search__input {
  width: 100%;
  min-width: 0;
  border: none;
  background: transparent;
  color: var(--color-text);
  font-size: 13px;
}

.header-search__input:focus-visible {
  outline: none;
}

.header-search__input::placeholder {
  color: var(--color-muted);
}

.header-search__clear {
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--color-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    color var(--transition-fast),
    background var(--transition-fast),
    transform var(--transition-fast);
}

.header-search__clear:hover {
  color: var(--color-text);
  background: var(--color-surface-2);
}

.header-search__clear:active {
  transform: var(--interaction-press-scale);
}

.header-search__clear.is-hidden {
  visibility: hidden;
  pointer-events: none;
}
</style>
