<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type TreeCheckItem = {
  id: number | string
  label: string
  description?: string
  children?: TreeCheckItem[]
}

const props = withDefaults(
  defineProps<{
    modelValue: Array<number | string>
    items: TreeCheckItem[]
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

const expanded = ref(new Set<number | string>())

const rows = computed(() => {
  const result: Array<{ item: TreeCheckItem; level: number }> = []
  const walk = (items: TreeCheckItem[], level: number) => {
    items.forEach((item) => {
      result.push({ item, level })
      if (item.children?.length && expanded.value.has(item.id)) {
        walk(item.children, level + 1)
      }
    })
  }
  walk(props.items, 0)
  return result
})

const isChecked = (id: number | string) => props.modelValue.includes(id)

const collectIds = (item: TreeCheckItem) => {
  const ids: Array<number | string> = [item.id]
  if (item.children?.length) {
    item.children.forEach((child) => {
      ids.push(...collectIds(child))
    })
  }
  return ids
}

const toggleExpand = (item: TreeCheckItem) => {
  if (!item.children?.length) {
    return
  }
  const next = new Set(expanded.value)
  if (next.has(item.id)) {
    next.delete(item.id)
  } else {
    next.add(item.id)
  }
  expanded.value = next
}

watch(
  () => props.items,
  (items) => {
    const next = new Set<number | string>()
    const walk = (nodes: TreeCheckItem[]) => {
      nodes.forEach((node) => {
        if (node.children?.length) {
          next.add(node.id)
          walk(node.children)
        }
      })
    }
    walk(items || [])
    expanded.value = next
  },
  { immediate: true },
)

const stateMap = computed(() => {
  const map = new Map<number | string, { checked: boolean; indeterminate: boolean }>()
  const walk = (item: TreeCheckItem): { checked: boolean; indeterminate: boolean } => {
    if (!item.children?.length) {
      const checked = isChecked(item.id)
      const state = { checked, indeterminate: false }
      map.set(item.id, state)
      return state
    }

    let allChecked = true
    let anyChecked = false
    item.children.forEach((child) => {
      const childState = walk(child)
      if (!childState.checked || childState.indeterminate) {
        allChecked = false
      }
      if (childState.checked || childState.indeterminate) {
        anyChecked = true
      }
    })

    const selfChecked = isChecked(item.id)
    const checked = allChecked || (selfChecked && !anyChecked)
    const indeterminate = !checked && anyChecked
    const state = { checked, indeterminate }
    map.set(item.id, state)
    return state
  }

  props.items.forEach((item) => {
    walk(item)
  })
  return map
})

const toggle = (item: TreeCheckItem) => {
  const next = new Set(props.modelValue)
  const state = stateMap.value.get(item.id)
  const selfChecked = next.has(item.id)

  if (item.children?.length) {
    const ids = collectIds(item)
    const shouldCheck = state?.indeterminate ? true : !(state?.checked || selfChecked)
    ids.forEach((id) => {
      if (shouldCheck) {
        next.add(id)
      } else {
        next.delete(id)
      }
    })
  } else if (selfChecked) {
    next.delete(item.id)
  } else {
    next.add(item.id)
  }
  emit('update:modelValue', Array.from(next))
}
</script>

<template>
  <div class="tree-checklist">
    <div v-if="rows.length === 0" class="tree-checklist__empty">{{ emptyText }}</div>
    <label
      v-for="row in rows"
      :key="row.item.id"
      class="tree-checklist__item"
      :style="{ paddingLeft: `${row.level * 12}px` }"
    >
      <button
        v-if="row.item.children?.length"
        class="tree-checklist__toggle"
        type="button"
        @click.stop="toggleExpand(row.item)"
      >
        {{ expanded.has(row.item.id) ? '▾' : '▸' }}
      </button>
      <span v-else class="tree-checklist__toggle tree-checklist__toggle--empty"></span>
      <input
        type="checkbox"
        :checked="stateMap.get(row.item.id)?.checked || false"
        :indeterminate="stateMap.get(row.item.id)?.indeterminate || false"
        @change="toggle(row.item)"
      />
      <span class="tree-checklist__label">{{ row.item.label }}</span>
      <span v-if="row.item.description" class="tree-checklist__desc">{{
        row.item.description
      }}</span>
    </label>
  </div>
</template>

<style scoped>
.tree-checklist {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  max-height: 260px;
  overflow: auto;
}

.tree-checklist__item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 13px;
  color: var(--color-text);
}

.tree-checklist__label {
  font-weight: 600;
}

.tree-checklist__toggle {
  width: 14px;
  height: 14px;
  border: none;
  background: transparent;
  color: var(--color-muted);
  font-size: 12px;
  line-height: 14px;
  text-align: center;
  cursor: pointer;
  padding: 0;
}

.tree-checklist__toggle--empty {
  cursor: default;
  opacity: 0;
}

.tree-checklist__desc {
  color: var(--color-muted);
  font-size: 12px;
}

.tree-checklist__empty {
  font-size: 13px;
  color: var(--color-muted);
  text-align: center;
}
</style>
