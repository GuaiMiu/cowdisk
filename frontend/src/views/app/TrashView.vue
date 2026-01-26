<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Table from '@/components/common/Table.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import Pagination from '@/components/common/Pagination.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { useTrash } from '@/composables/useTrash'
import { formatBytes, formatTime } from '@/utils/format'
import type { DiskTrashEntry } from '@/types/disk'

const trash = useTrash()
const clearConfirm = ref(false)
const deleteConfirm = ref(false)
const currentEntry = ref<DiskTrashEntry | null>(null)
const page = ref(1)
const pageSize = ref(20)

const { t } = useI18n({ useScope: 'global' })

const columns = computed(() => [
  { key: 'name', label: t('trash.columns.name'), width: 'minmax(240px, 1fr)' },
  { key: 'size', label: t('trash.columns.size'), width: '110px' },
  { key: 'deleted_at', label: t('trash.columns.deletedAt'), width: '140px' },
  { key: 'actions', label: t('trash.columns.actions'), width: '126px' },
])

const requestDelete = (entry: DiskTrashEntry) => {
  currentEntry.value = entry
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  if (currentEntry.value) {
    await trash.remove(currentEntry.value)
  }
  deleteConfirm.value = false
  currentEntry.value = null
}

const confirmClear = async () => {
  await trash.clear()
  clearConfirm.value = false
}

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  const end = start + pageSize.value
  return trash.items.value.slice(start, end)
})

const updatePage = (next: number) => {
  page.value = next
}

const updatePageSize = (size: number) => {
  pageSize.value = size
  page.value = 1
}
const asTrash = (row: unknown) => row as DiskTrashEntry

onMounted(() => {
  void trash.fetchTrash()
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('trash.title')" :subtitle="t('trash.subtitle')">
      <template #actions>
        <Button variant="secondary" v-permission="'disk:file:delete'" @click="clearConfirm = true">
          {{ t('trash.clear') }}
        </Button>
      </template>
    </PageHeader>

    <div class="table-wrap trash-table">
      <Table :columns="columns" :rows="pagedItems" :min-rows="pageSize" scrollable fill>
        <template #cell-name="{ row }">
          <div class="name">
            <FileTypeIcon :name="asTrash(row).name" :is-dir="asTrash(row).is_dir" />
            <span class="name__text">{{ asTrash(row).name }}</span>
          </div>
        </template>
        <template #cell-size="{ row }">
          {{ formatBytes(asTrash(row).size as number) }}
        </template>
        <template #cell-deleted_at="{ row }">
          {{ formatTime(asTrash(row).deleted_at as string) }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions actions--group">
            <Button
              size="sm"
              variant="ghost"
              class="action-btn"
              v-permission="'disk:file:delete'"
              @click="trash.restore(asTrash(row))"
            >
              {{ t('trash.restore') }}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              class="action-btn action-btn--danger"
              v-permission="'disk:file:delete'"
              @click="requestDelete(asTrash(row))"
            >
              {{ t('trash.deleteForever') }}
            </Button>
          </div>
        </template>
      </Table>
    </div>

    <Pagination
      :total="trash.items.value.length"
      :page-size="pageSize"
      :current-page="page"
      @update:currentPage="updatePage"
      @update:pageSize="updatePageSize"
    />
  </section>

  <ConfirmDialog
    :open="clearConfirm"
    :title="t('trash.confirmClearTitle')"
    :message="t('trash.confirmClearMessage')"
    @close="clearConfirm = false"
    @confirm="confirmClear"
  />

  <ConfirmDialog
    :open="deleteConfirm"
    :title="t('trash.confirmDeleteTitle')"
    :message="t('trash.confirmDeleteMessage')"
    @close="deleteConfirm = false"
    @confirm="confirmDelete"
  />
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-4);
  height: 100%;
  min-height: 0;
  grid-template-rows: auto 1fr auto;
  overflow: hidden;
}

.table-wrap {
  height: 100%;
  min-height: 0;
}

.actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  justify-content: flex-start;
  white-space: nowrap;
  justify-self: start;
}

.actions--group {
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface);
}

.actions--group :deep(.action-btn) {
  border: 0;
  box-shadow: none;
  padding: var(--space-1) var(--space-3);
  border-radius: 0;
}

.actions--group :deep(.action-btn + .action-btn) {
  border-left: 1px solid var(--color-border);
}

.actions--group :deep(.action-btn:hover) {
  background: var(--color-surface-2);
  transform: none;
  box-shadow: none;
}

.actions--group :deep(.action-btn--danger) {
  color: var(--color-danger);
}

.actions--group :deep(.action-btn--danger:hover) {
  background: var(--color-danger-soft);
}

.name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  max-width: 100%;
}

.name__text {
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .trash-table :deep(.table) {
    --table-columns: minmax(180px, 1fr) 96px;
  }

  .trash-table :deep(.table__cell:nth-child(2)),
  .trash-table :deep(.table__cell:nth-child(3)) {
    display: none;
  }
}
</style>
