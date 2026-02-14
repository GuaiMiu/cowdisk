<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSegments, joinPath } from '@/utils/path'

type BreadcrumbItem =
  | { id: string | number | null; label: string }
  | { label: string; path: string }

const props = defineProps<{
  path?: string
  items?: Array<{ id: string | number | null; label: string }>
}>()

const emit = defineEmits<{
  (event: 'navigate', value: string | number | null): void
}>()

const { t } = useI18n({ useScope: 'global' })

const crumbs = computed<BreadcrumbItem[]>(() => {
  if (props.items && props.items.length) {
    return props.items.map((item) => ({ ...item }))
  }
  const inputPath = props.path ?? '/'
  const segments = getSegments(inputPath)
  const items = [{ label: t('fileBreadcrumb.root'), path: '/' as string }]
  let current = ''
  segments.forEach((segment) => {
    current = joinPath(current || '/', segment)
    items.push({ label: segment, path: current })
  })
  return items
})

const getCrumbKey = (item: BreadcrumbItem) => {
  if ('id' in item) {
    return item.id ?? item.label
  }
  return item.path || item.label
}
</script>

<template>
  <div class="breadcrumb">
    <button
      v-for="(item, index) in crumbs"
      :key="getCrumbKey(item)"
      type="button"
      class="breadcrumb__item"
      :class="{
        'breadcrumb__item--ancestor': index < crumbs.length - 1,
        'breadcrumb__item--current': index === crumbs.length - 1,
      }"
      @click="emit('navigate', 'id' in item ? item.id : item.path ?? '/')"
    >
      <span class="breadcrumb__label">{{ item.label }}</span>
      <span v-if="index < crumbs.length - 1" class="breadcrumb__sep">/</span>
    </button>
  </div>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  font-size: 13px;
  color: var(--color-muted);
}

.breadcrumb__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  color: inherit;
}

.breadcrumb__label {
  color: var(--color-text);
  font-weight: 600;
}

.breadcrumb__item--ancestor .breadcrumb__label {
  color: var(--color-primary);
}

.breadcrumb__item--ancestor:hover .breadcrumb__label {
  text-decoration: underline;
}

.breadcrumb__item--current .breadcrumb__label {
  color: var(--color-text);
}

.breadcrumb__sep {
  color: var(--color-border);
}
</style>
