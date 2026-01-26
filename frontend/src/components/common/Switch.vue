<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue: boolean
    disabled?: boolean
  }>(),
  {
    disabled: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()
</script>

<template>
  <label class="switch" :class="{ 'is-disabled': disabled }">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      @change="emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="switch__track"></span>
  </label>
</template>

<style scoped>
.switch {
  display: inline-flex;
  align-items: center;
}

.switch input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.switch__track {
  width: 36px;
  height: 20px;
  border-radius: 999px;
  background: var(--color-border);
  position: relative;
  transition: background var(--transition-base);
}

.switch__track::after {
  content: '';
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--color-surface);
  top: 3px;
  left: 4px;
  transition: transform var(--transition-base);
  box-shadow: var(--shadow-xs);
}

.switch input:checked + .switch__track {
  background: var(--color-primary);
}

.switch input:checked + .switch__track::after {
  transform: translateX(16px);
}

.switch.is-disabled {
  opacity: 0.6;
  pointer-events: none;
}
</style>
