<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pencil, Trash2 } from 'lucide-vue-next'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import IconButton from '@/components/common/IconButton.vue'
import Table from '@/components/common/Table.vue'
import Tag from '@/components/common/Tag.vue'
import Pagination from '@/components/common/Pagination.vue'
import Modal from '@/components/common/Modal.vue'
import Input from '@/components/common/Input.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ShareForm, { type ShareFormValue } from '@/components/share/ShareForm.vue'
import { useShareActions } from '@/composables/useShareActions'
import { formatTime } from '@/utils/format'
import type { Share } from '@/types/share'
import { copyToClipboard } from '@/utils/clipboard'
import { useToastStore } from '@/stores/toast'

const shareActions = useShareActions()
const toast = useToastStore()

const { t } = useI18n({ useScope: 'global' })

const columns = computed(() => [
  { key: 'name', label: t('shares.columns.name'), width: 'minmax(240px, 1fr)' },
  { key: 'status', label: t('shares.columns.status'), width: '90px' },
  { key: 'resourceType', label: t('shares.columns.resourceType'), width: '80px' },
  { key: 'createdAt', label: t('shares.columns.createdAt'), width: '130px' },
  { key: 'expiresAt', label: t('shares.columns.expiresAt'), width: '130px' },
  { key: 'actions', label: t('shares.columns.actions'), width: '88px' },
])

const formatResourceType = (value: string) => {
  const normalized = value?.toLowerCase()
  if (normalized === 'folder' || normalized === 'dir') {
    return t('shares.resourceType.folder')
  }
  if (normalized === 'file') {
    return t('shares.resourceType.file')
  }
  return value
}

const editModal = ref(false)
const editingShare = ref<Share | null>(null)
const editSubmitting = ref(false)
const editShareLink = ref('')
const editForm = ref<ShareFormValue>({
  expiresInDays: 7,
  expiresAt: null,
  requiresCode: true,
  code: '',
})
const toggling = ref(new Set<string>())
const deleteConfirm = ref(false)
const deletingShare = ref<Share | null>(null)

const isToggling = (id: string) => toggling.value.has(id)
const asShare = (row: unknown) => row as Share

const toLocalInputValue = (date: Date) => {
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes(),
  )}`
}

const openEdit = (share: Share) => {
  editingShare.value = share
  editForm.value = {
    expiresInDays: null,
    expiresAt: share.expiresAt ? toLocalInputValue(new Date(share.expiresAt)) : null,
    requiresCode: share.hasCode ?? false,
    code: share.code ?? '',
  }
  editShareLink.value = `${window.location.origin}/public/shares/${share.token}`
  editModal.value = true
}

const copyShareLink = async (share: Share) => {
  const link = `${window.location.origin}/public/shares/${share.token}`
  const ok = await copyToClipboard(link)
  if (ok) {
    toast.success(t('shares.toasts.copySuccess'))
  } else {
    toast.error(t('shares.toasts.copyFailTitle'), t('shares.toasts.copyFailMessage'))
  }
}

const submitEdit = async () => {
  if (!editingShare.value || editSubmitting.value) {
    return
  }
  editSubmitting.value = true
  const expiresAt =
    editForm.value.expiresAt && Number.isFinite(Date.parse(editForm.value.expiresAt))
      ? Date.parse(editForm.value.expiresAt)
      : null
  const payload = {
    expiresInDays: editForm.value.expiresInDays ?? null,
    expiresAt,
    code: editForm.value.requiresCode ? editForm.value.code.trim() : '',
  }
  const updated = await shareActions.update(editingShare.value.id, payload)
  editSubmitting.value = false
  if (updated) {
    editModal.value = false
  }
}

const toggleStatus = async (row: Share, next: boolean) => {
  if (toggling.value.has(row.id)) {
    return
  }
  toggling.value = new Set(toggling.value).add(row.id)
  await shareActions.update(row.id, { status: next ? 1 : 0 })
  const nextSet = new Set(toggling.value)
  nextSet.delete(row.id)
  toggling.value = nextSet
}

const copyLink = async () => {
  const ok = await copyToClipboard(editShareLink.value)
  if (ok) {
    toast.success(t('shares.toasts.copySuccess'))
  } else {
    toast.error(t('shares.toasts.copyFailTitle'), t('shares.toasts.copyFailMessage'))
  }
}

const requestDelete = (share: Share) => {
  deletingShare.value = share
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  if (deletingShare.value) {
    await shareActions.remove(deletingShare.value.id)
  }
  deleteConfirm.value = false
  deletingShare.value = null
}

onMounted(() => {
  void shareActions.fetchShares()
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('shares.title')" :subtitle="t('shares.subtitle')">
      <template #actions>
        <Button variant="secondary" @click="shareActions.fetchShares(shareActions.currentPage.value)">
          {{ t('shares.refresh') }}
        </Button>
      </template>
    </PageHeader>

    <div class="table-wrap shares-table">
      <Table
        :columns="columns"
        :rows="shareActions.items.value"
        :min-rows="shareActions.limit.value"
        scrollable
        fill
      >
        <template #cell-name="{ row }">
          <button type="button" class="name name--link" @click="copyShareLink(asShare(row))">
            <FileTypeIcon :name="asShare(row).name" :resource-type="asShare(row).resourceType" />
            <span class="name__text">{{ asShare(row).name }}</span>
          </button>
        </template>
        <template #cell-status="{ row }">
          <Tag v-if="asShare(row).status === -1" tone="danger">{{ t('shares.status.missing') }}</Tag>
          <label
            v-else
            class="status-switch"
            :class="{ 'is-disabled': isToggling(asShare(row).id) }"
          >
            <input
              type="checkbox"
              :checked="asShare(row).status === 1"
              :disabled="isToggling(asShare(row).id)"
              @change="toggleStatus(asShare(row), ($event.target as HTMLInputElement).checked)"
            />
            <span class="status-switch__track"></span>
          </label>
        </template>
        <template #cell-resourceType="{ row }">
          <Tag tone="info">{{ formatResourceType(asShare(row).resourceType) }}</Tag>
        </template>
        <template #cell-createdAt="{ row }">
          {{ formatTime(asShare(row).createdAt as number) }}
        </template>
        <template #cell-expiresAt="{ row }">
          {{ asShare(row).expiresAt ? formatTime(asShare(row).expiresAt as number) : t('shares.permanent') }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <IconButton
              size="sm"
              variant="ghost"
              :aria-label="t('shares.aria.edit')"
              @click="openEdit(asShare(row))"
            >
              <Pencil :size="16" />
            </IconButton>
            <IconButton
              size="sm"
              variant="ghost"
              :aria-label="t('shares.aria.delete')"
              @click="requestDelete(asShare(row))"
            >
              <Trash2 :size="16" />
            </IconButton>
          </div>
        </template>
      </Table>
    </div>

    <Pagination
      :total="shareActions.total.value"
      :page-size="shareActions.limit.value"
      :current-page="shareActions.currentPage.value"
      @update:currentPage="shareActions.fetchShares"
      @update:pageSize="shareActions.setPageSize"
    />
  </section>

  <Modal :open="editModal" :title="t('shares.edit.title')" @close="editModal = false">
    <ShareForm v-model="editForm" />
    <div class="share-link">
      <Input :model-value="editShareLink" :label="t('shares.edit.linkLabel')" :readonly="true" />
      <Button variant="secondary" @click="copyLink">
        {{ t('shares.edit.copyLink') }}
      </Button>
    </div>
    <template #footer>
      <Button variant="ghost" @click="editModal = false">{{ t('shares.edit.cancel') }}</Button>
      <Button :loading="editSubmitting" @click="submitEdit">{{ t('shares.edit.save') }}</Button>
    </template>
  </Modal>

  <ConfirmDialog
    :open="deleteConfirm"
    :title="t('shares.confirmDeleteTitle')"
    :message="t('shares.confirmDeleteMessage')"
    @close="deleteConfirm = false"
    @confirm="confirmDelete"
  />
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-4);
  grid-template-rows: auto 1fr auto;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.table-wrap {
  height: 100%;
  min-height: 0;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-2);
  white-space: nowrap;
  height: 100%;
}

.name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  max-width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  text-align: left;
}

.name__text {
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.name--link {
  cursor: pointer;
}

.name--link:hover .name__text {
  color: var(--color-primary);
}

.share-link {
  display: grid;
  gap: var(--space-3);
}

.status-switch {
  display: inline-flex;
  align-items: center;
}

.status-switch input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.status-switch__track {
  width: 36px;
  height: 20px;
  border-radius: 999px;
  background: var(--color-border);
  position: relative;
  transition: background var(--transition-base);
}

.status-switch__track::after {
  content: '';
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--color-surface);
  top: 3px;
  left: 4px;
  transition: transform var(--transition-base);
  box-shadow: var(--shadow-xs);
}

.status-switch input:checked + .status-switch__track {
  background: var(--color-primary);
}

.status-switch input:checked + .status-switch__track::after {
  transform: translateX(16px);
}


.status-switch.is-disabled {
  opacity: 0.6;
  pointer-events: none;
}

@media (max-width: 768px) {
  .shares-table :deep(.table) {
    --table-columns: minmax(180px, 1fr) 88px;
  }

  .shares-table :deep(.table__cell:nth-child(2)),
  .shares-table :deep(.table__cell:nth-child(3)),
  .shares-table :deep(.table__cell:nth-child(4)),
  .shares-table :deep(.table__cell:nth-child(5)) {
    display: none;
  }
}
</style>
