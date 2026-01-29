<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSegments, joinPath } from '@/utils/path'

const props = defineProps<{
  path: string
}>()

const emit = defineEmits<{
  (event: 'navigate', path: string): void
}>()

const { t } = useI18n({ useScope: 'global' })

const crumbs = computed(() => {
  const segments = getSegments(props.path)
  const items = [{ label: t('fileBreadcrumb.root'), path: '/' }]
  let current = ''
  segments.forEach((segment) => {
    current = joinPath(current || '/', segment)
    items.push({ label: segment, path: current })
  })
  return items
})
</script>

<template>
  <div class="breadcrumb">
    <button
      v-for="(item, index) in crumbs"
      :key="item.path"
      type="button"
      class="breadcrumb__item"
      :class="{
        'breadcrumb__item--ancestor': index < crumbs.length - 1,
        'breadcrumb__item--current': index === crumbs.length - 1,
      }"
      @click="emit('navigate', item.path)"
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
