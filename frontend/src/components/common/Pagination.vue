<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from './Button.vue'
import Select from './Select.vue'

const props = withDefaults(
  defineProps<{
    total: number
    pageSize: number
    currentPage: number
    cursorMode?: boolean
    hasNext?: boolean
    hasPrev?: boolean
    pageSizeOptions?: number[]
    showPageSize?: boolean
  }>(),
  {
    total: 0,
    pageSize: 20,
    currentPage: 1,
    cursorMode: false,
    hasNext: false,
    hasPrev: false,
    pageSizeOptions: () => [10, 20, 50, 100],
    showPageSize: true,
  },
)

const emit = defineEmits<{
  (event: 'update:currentPage', value: number): void
  (event: 'update:pageSize', value: number): void
  (event: 'next'): void
  (event: 'prev'): void
}>()

const { t } = useI18n({ useScope: 'global' })

const totalPages = () => Math.max(1, Math.ceil(props.total / props.pageSize))

const go = (page: number) => {
  const target = Math.min(Math.max(page, 1), totalPages())
  emit('update:currentPage', target)
}

const sizeOptions = () =>
  props.pageSizeOptions.map((size) => ({
    label: t('pagination.sizeOption', { size }),
    value: String(size),
  }))
</script>

<template>
  <div class="pagination">
    <div class="pagination__left">
      <span v-if="!cursorMode" class="pagination__info">{{
        t('pagination.info', { total, pages: totalPages() })
      }}</span>
      <span v-else class="pagination__info">
        {{ t('pagination.page', { page: currentPage }) }}
      </span>
      <div v-if="showPageSize" class="pagination__size">
        <span class="pagination__size-label">{{ t('pagination.perPage') }}</span>
        <Select
          size="sm"
          :model-value="String(pageSize)"
          :options="sizeOptions()"
          @update:modelValue="(value) => emit('update:pageSize', Number(value))"
        />
      </div>
    </div>
    <div class="pagination__actions">
      <template v-if="cursorMode">
        <Button variant="secondary" size="sm" :disabled="!hasPrev" @click="emit('prev')">
          {{ t('pagination.prev') }}
        </Button>
        <span class="pagination__page">{{ currentPage }}</span>
        <Button variant="secondary" size="sm" :disabled="!hasNext" @click="emit('next')">
          {{ t('pagination.next') }}
        </Button>
      </template>
      <template v-else>
        <Button variant="secondary" size="sm" :disabled="currentPage <= 1" @click="go(1)">
          {{ t('pagination.first') }}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          :disabled="currentPage <= 1"
          @click="go(currentPage - 1)"
        >
          {{ t('pagination.prev') }}
        </Button>
        <span class="pagination__page">{{ currentPage }}</span>
        <Button
          variant="secondary"
          size="sm"
          :disabled="currentPage >= totalPages()"
          @click="go(currentPage + 1)"
        >
          {{ t('pagination.next') }}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          :disabled="currentPage >= totalPages()"
          @click="go(totalPages())"
        >
          {{ t('pagination.last') }}
        </Button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.pagination__left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.pagination__info {
  font-size: 13px;
  color: var(--color-muted);
}

.pagination__size {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
}

.pagination__size-label {
  font-size: 13px;
  color: var(--color-muted);
}

.pagination__size :deep(.field) {
  display: flex;
  align-items: center;
  gap: 0;
}

.pagination__size :deep(.field__error) {
  display: none;
}

.pagination__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.pagination__page {
  font-weight: 600;
}

@media (max-width: 768px) {
  .pagination {
    flex-direction: column;
    align-items: flex-start;
  }

  .pagination__left {
    width: 100%;
  }
}
</style>
