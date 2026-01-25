<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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

const columns = [
  { key: 'name', label: '名称', width: 'minmax(240px, 1fr)' },
  { key: 'size', label: '大小', width: '110px' },
  { key: 'deleted_at', label: '删除时间', width: '140px' },
  { key: 'actions', label: '操作', width: 'minmax(96px, 0.35fr)' },
]

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
    <PageHeader title="回收站" subtitle="可恢复被删除的文件">
      <template #actions>
        <Button variant="secondary" v-permission="'disk:file:delete'" @click="clearConfirm = true">
          清空回收站
        </Button>
      </template>
    </PageHeader>

    <div class="table-wrap">
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
              恢复
            </Button>
            <Button
              size="sm"
              variant="ghost"
              class="action-btn action-btn--danger"
              v-permission="'disk:file:delete'"
              @click="requestDelete(asTrash(row))"
            >
              彻底删除
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
    title="确认清空回收站"
    message="清空后不可恢复，是否继续？"
    @close="clearConfirm = false"
    @confirm="confirmClear"
  />

  <ConfirmDialog
    :open="deleteConfirm"
    title="确认删除"
    message="删除后无法恢复，是否继续？"
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
  justify-content: flex-end;
  white-space: nowrap;
  justify-self: end;
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
</style>
