<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RotateCcw, Trash2 } from 'lucide-vue-next'
import Button from '@/components/common/Button.vue'
import IconButton from '@/components/common/IconButton.vue'
import Table from '@/components/common/Table.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import Pagination from '@/components/common/Pagination.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { useTrash } from '@/composables/useTrash'
import { useSelection } from '@/composables/useSelection'
import { useMessage } from '@/stores/message'
import { formatBytes, formatTime } from '@/utils/format'
import type { DiskTrashEntry } from '@/types/disk'

const trash = useTrash()
const selection = useSelection(
  () => trash.items.value,
  (item) => String(item.id),
)
const message = useMessage()
const clearConfirm = ref(false)
const deleteConfirm = ref(false)
const batchConfirm = ref(false)
const batchAction = ref<'restore' | 'delete' | null>(null)
const selectAllRef = ref<HTMLInputElement | null>(null)
const currentEntry = ref<DiskTrashEntry | null>(null)
const page = ref(1)
const pageSize = ref(20)

const { t } = useI18n({ useScope: 'global' })

const columns = computed(() => [
  { key: 'select', label: '', width: '32px', align: 'center' as const },
  { key: 'name', label: t('trash.columns.name'), width: 'minmax(240px, 1fr)' },
  { key: 'size', label: t('trash.columns.size'), width: '110px' },
  { key: 'deleted_at', label: t('trash.columns.deletedAt'), width: '140px' },
  { key: 'actions', label: t('trash.columns.actions'), width: '88px' },
])

const selectedCount = computed(() => selection.selectedItems.value.length)

watch(
  () => selection.indeterminate.value,
  (value) => {
    if (selectAllRef.value) {
      selectAllRef.value.indeterminate = value
    }
  },
  { immediate: true },
)

watch(
  () => trash.items.value,
  (items) => {
    const valid = new Set(items.map((item) => item.id))
    const next = new Set<string>()
    selection.selected.value.forEach((id) => {
      if (valid.has(id)) {
        next.add(id)
      }
    })
    if (next.size !== selection.selected.value.size) {
      selection.selected.value = next
    }
  },
  { deep: true },
)

const requestDelete = (entry: DiskTrashEntry) => {
  currentEntry.value = entry
  deleteConfirm.value = true
}

const requestBatch = (action: 'restore' | 'delete') => {
  if (selectedCount.value === 0) {
    return
  }
  batchAction.value = action
  batchConfirm.value = true
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

const confirmBatch = async () => {
  if (!batchAction.value) {
    return
  }
  const ids = selection.selectedItems.value.map((item) => item.id).filter(Boolean)
  if (ids.length === 0) {
    batchConfirm.value = false
    return
  }
  if (batchAction.value === 'restore') {
    const result = await trash.restoreBatch(ids)
    if (result.failed.length === 0) {
      message.success(
        t('trash.toasts.batchRestoreTitle'),
        t('trash.toasts.batchSuccessMessage', { count: result.success }),
      )
    } else {
      message.warning(
        t('trash.toasts.batchRestorePartialTitle'),
        t('trash.toasts.batchPartialMessage', {
          success: result.success,
          failed: result.failed.length,
        }),
      )
    }
  } else {
    const result = await trash.removeBatch(ids)
    if (result.failed.length === 0) {
      message.success(
        t('trash.toasts.batchDeleteTitle'),
        t('trash.toasts.batchSuccessMessage', { count: result.success }),
      )
    } else {
      message.warning(
        t('trash.toasts.batchDeletePartialTitle'),
        t('trash.toasts.batchPartialMessage', {
          success: result.success,
          failed: result.failed.length,
        }),
      )
    }
  }
  selection.clear()
  batchConfirm.value = false
  batchAction.value = null
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
    <div class="page__bar">
      <div class="page__actions">
        <Button variant="secondary" v-permission="'disk:trash:clear'" @click="clearConfirm = true">
          <Trash2 :size="16" />
          {{ t('trash.clear') }}
        </Button>
        <div v-show="selectedCount > 0" class="bulk-actions">
          <div class="bulk-actions__buttons">
            <Button variant="secondary" @click="requestBatch('restore')">
              <RotateCcw :size="16" />
              {{ t('trash.bulk.restoreSelected', { count: selectedCount }) }}
            </Button>
            <Button variant="danger" @click="requestBatch('delete')">
              <Trash2 :size="16" />
              {{ t('trash.bulk.deleteSelected', { count: selectedCount }) }}
            </Button>
          </div>
        </div>
      </div>
      <div class="page__info">
        {{ t('trash.itemsCount', { count: trash.items.value.length }) }}
      </div>
    </div>

    <div class="table-wrap trash-table">
      <Table :columns="columns" :rows="pagedItems" :min-rows="pageSize" scrollable fill>
        <template #head-select>
          <div class="select-cell">
            <input
              ref="selectAllRef"
              type="checkbox"
              :checked="selection.allSelected.value"
              @change="selection.toggleAll()"
            />
          </div>
        </template>
        <template #cell-select="{ row }">
          <div class="select-cell">
            <input
              type="checkbox"
              :checked="selection.isSelected(asTrash(row))"
              @click.stop
              @change="selection.toggle(asTrash(row))"
            />
          </div>
        </template>
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
          <div class="actions actions--icons">
            <IconButton
              size="sm"
              variant="ghost"
              :aria-label="t('trash.restore')"
              v-permission="'disk:trash:restore'"
              @click="trash.restore(asTrash(row))"
            >
              <RotateCcw :size="16" />
            </IconButton>
            <IconButton
              size="sm"
              variant="ghost"
              class="action-btn--danger"
              :aria-label="t('trash.deleteForever')"
              v-permission="'disk:trash:delete'"
              @click="requestDelete(asTrash(row))"
            >
              <Trash2 :size="16" />
            </IconButton>
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

  <ConfirmDialog
    :open="batchConfirm"
    :title="
      batchAction === 'restore'
        ? t('trash.bulk.confirmRestoreTitle')
        : t('trash.bulk.confirmDeleteTitle')
    "
    :message="
      batchAction === 'restore'
        ? t('trash.bulk.confirmRestoreMessage', { count: selectedCount })
        : t('trash.bulk.confirmDeleteMessage', { count: selectedCount })
    "
    @close="batchConfirm = false"
    @confirm="confirmBatch"
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

.page__bar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  gap: var(--space-3);
}

.page__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.page__info {
  font-size: 12px;
  color: var(--color-muted);
  margin-left: auto;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.bulk-actions__buttons {
  margin-left: auto;
  display: inline-flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  row-gap: var(--space-2);
}

.trash-table :deep(.table__cell:first-child) {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.trash-table :deep(.table__cell:nth-child(2)) {
  display: flex;
  align-items: center;
}

.trash-table :deep(.table),
.trash-table :deep(.table__row),
.trash-table :deep(.table__header) {
  min-width: 0;
  width: 100%;
}

.trash-table :deep(.table__cell) {
  min-width: 0;
}

.select-cell {
  display: inline-flex;
  align-items: center;
  height: 100%;
}

.table-wrap {
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  justify-content: flex-start;
  white-space: nowrap;
  justify-self: start;
}

.actions--icons {
  gap: var(--space-2);
}

.actions--icons :deep(.action-btn--danger) {
  color: var(--color-danger);
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
  transition: color var(--transition-fast);
}

.trash-table :deep(.table__row) {
  transition: background var(--transition-fast);
}

.trash-table :deep(.table__row:hover) .name__text {
  color: var(--color-primary);
}

@media (max-width: 768px) {
  .page__bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .trash-table :deep(.table) {
    --table-columns: 32px minmax(0, 1fr) 96px;
  }

  .trash-table :deep(.table__cell:nth-child(3)),
  .trash-table :deep(.table__cell:nth-child(4)) {
    display: none;
  }
}
</style>
