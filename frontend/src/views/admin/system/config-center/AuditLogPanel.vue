<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'
import Table from '@/components/common/Table.vue'
import Pagination from '@/components/common/Pagination.vue'
import type { AuditLogItem } from '@/types/config-center'
import { formatTime } from '@/utils/format'

const props = defineProps<{
  filters: {
    start: string
    end: string
    action: string
    status: string
    user_id: string
    q: string
    page: number
    page_size: number
  }
  loading: boolean
  rows: AuditLogItem[]
  total: number
  columns: Array<{ key: string; label: string; width?: string }>
  page: number
  pageSize: number
  actionOptions: Array<{ label: string; value: string }>
  statusOptions: Array<{ label: string; value: string }>
}>()

const emit = defineEmits<{
  (event: 'update-filter', payload: { key: keyof typeof props.filters; value: string | number }): void
  (event: 'search'): void
  (event: 'reset'): void
  (event: 'export'): void
  (event: 'cleanup'): void
  (event: 'open-detail', item: AuditLogItem): void
  (event: 'page-change', value: number): void
  (event: 'size-change', value: number): void
}>()

const { t } = useI18n({ useScope: 'global' })

const updateFilter = (key: keyof typeof props.filters, value: string | number) => {
  emit('update-filter', { key, value })
}

const hasPrev = computed(() => props.page > 1)
const hasNext = computed(() => props.page * props.pageSize < props.total)
</script>

<template>
  <div class="audit-panel">
    <div class="audit-toolbar">
      <div class="audit-filters">
        <Input
          :model-value="filters.start"
          type="date"
          :label="t('admin.audit.filters.start')"
          @update:model-value="(value) => updateFilter('start', value)"
        />
        <Input
          :model-value="filters.end"
          type="date"
          :label="t('admin.audit.filters.end')"
          @update:model-value="(value) => updateFilter('end', value)"
        />
        <Select
          :model-value="filters.action"
          :label="t('admin.audit.filters.action')"
          :options="actionOptions"
          @update:model-value="(value) => updateFilter('action', value)"
        />
        <Select
          :model-value="filters.status"
          :label="t('admin.audit.filters.status')"
          :options="statusOptions"
          @update:model-value="(value) => updateFilter('status', value)"
        />
        <Input
          :model-value="filters.user_id"
          :label="t('admin.audit.filters.userId')"
          :placeholder="t('admin.audit.filters.userIdPlaceholder')"
          @update:model-value="(value) => updateFilter('user_id', value)"
        />
        <Input
          :model-value="filters.q"
          :label="t('admin.audit.filters.keyword')"
          :placeholder="t('admin.audit.filters.keywordPlaceholder')"
          @update:model-value="(value) => updateFilter('q', value)"
        />
      </div>
      <div class="toolbar-actions">
        <Button variant="primary" :loading="loading" @click="emit('search')">{{
          t('admin.audit.actions.search')
        }}</Button>
        <Button variant="secondary" :disabled="loading" @click="emit('reset')">{{
          t('admin.audit.actions.reset')
        }}</Button>
        <Button variant="secondary" :disabled="loading" @click="emit('export')">{{
          t('admin.audit.actions.export')
        }}</Button>
        <Button variant="danger" :disabled="loading" @click="emit('cleanup')">{{
          t('admin.audit.actions.cleanup')
        }}</Button>
      </div>
    </div>

    <div class="audit-table-wrap">
      <Table
        :columns="columns"
        :rows="rows"
        row-key="id"
        :min-rows="6"
        :scrollable="true"
        :fill="true"
        class="audit-table"
      >
        <template #cell-created_at="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
        <template #cell-detail="{ row }">
          <Button variant="secondary" size="sm" @click="emit('open-detail', row)">{{
            t('admin.audit.actions.view')
          }}</Button>
        </template>
      </Table>
    </div>
    <Pagination
      cursor-mode
      :total="total"
      :has-prev="hasPrev"
      :has-next="hasNext"
      :current-page="page"
      :page-size="pageSize"
      @prev="emit('page-change', Math.max(1, page - 1))"
      @next="emit('page-change', page + 1)"
      @update:pageSize="(value) => emit('size-change', value)"
    />
  </div>
</template>

<style scoped>
.audit-panel {
  display: grid;
  gap: var(--space-4);
}

.audit-toolbar {
  display: grid;
  gap: var(--space-3);
}

.audit-filters {
  display: grid;
  grid-template-columns: repeat(6, minmax(140px, 1fr));
  gap: var(--space-3);
  align-items: end;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--color-border) 85%, transparent);
  background: color-mix(in srgb, var(--color-surface-2) 55%, var(--color-surface));
}

.audit-filters :deep(.input),
.audit-filters :deep(.select) {
  min-width: 0;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  justify-content: flex-end;
  align-items: center;
}

.audit-table {
  height: 100%;
}

.audit-table-wrap {
  height: clamp(280px, 48vh, 560px);
  min-height: 280px;
}

@media (max-width: 1200px) {
  .audit-filters {
    grid-template-columns: repeat(3, minmax(140px, 1fr));
  }
}

@media (max-width: 720px) {
  .audit-filters {
    grid-template-columns: 1fr;
  }

  .toolbar-actions {
    justify-content: stretch;
  }

  .toolbar-actions :deep(button) {
    flex: 1;
  }
}
</style>
