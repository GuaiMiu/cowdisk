<script setup lang="ts">
type CheckItem = {
  id: number | string
  label: string
  description?: string
}

const props = withDefaults(
  defineProps<{
    modelValue: Array<number | string>
    items: CheckItem[]
    emptyText?: string
  }>(),
  {
    items: () => [],
    emptyText: '暂无可选项',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: Array<number | string>): void
}>()

const isChecked = (id: number | string) => props.modelValue.includes(id)

const toggle = (id: number | string) => {
  const next = new Set(props.modelValue)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  emit('update:modelValue', Array.from(next))
}
</script>

<template>
  <div class="checklist">
    <div v-if="items.length === 0" class="checklist__empty">{{ emptyText }}</div>
    <label v-for="item in items" :key="item.id" class="checklist__item">
      <input type="checkbox" :checked="isChecked(item.id)" @change="toggle(item.id)" />
      <span class="checklist__label">{{ item.label }}</span>
      <span v-if="item.description" class="checklist__desc">{{ item.description }}</span>
    </label>
  </div>
</template>

<style scoped>
.checklist {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  max-height: 220px;
  overflow: auto;
}

.checklist__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  color: var(--color-text);
}

.checklist__label {
  font-weight: 600;
}

.checklist__desc {
  color: var(--color-muted);
  font-size: 12px;
}

.checklist__empty {
  font-size: 13px;
  color: var(--color-muted);
  text-align: center;
}
</style>
