import { computed, ref } from 'vue'

export const useSelection = <T extends { path?: string; id?: string }>(items: () => T[]) => {
  const selected = ref(new Set<string>())

  const getKey = (item: T) => item.path || String(item.id)

  const isSelected = (item: T) => selected.value.has(getKey(item))

  const toggle = (item: T) => {
    const key = getKey(item)
    if (selected.value.has(key)) {
      selected.value.delete(key)
    } else {
      selected.value.add(key)
    }
    selected.value = new Set(selected.value)
  }

  const clear = () => {
    selected.value = new Set()
  }

  const toggleAll = () => {
    const list = items()
    if (list.length === 0) {
      clear()
      return
    }
    const allSelected = list.every((item) => selected.value.has(getKey(item)))
    if (allSelected) {
      clear()
      return
    }
    selected.value = new Set(list.map((item) => getKey(item)))
  }

  const selectedItems = computed(() => items().filter((item) => selected.value.has(getKey(item))))
  const allSelected = computed(() => items().length > 0 && selectedItems.value.length === items().length)
  const indeterminate = computed(
    () => selectedItems.value.length > 0 && selectedItems.value.length < items().length,
  )

  return {
    selected,
    selectedItems,
    isSelected,
    toggle,
    toggleAll,
    clear,
    allSelected,
    indeterminate,
  }
}
