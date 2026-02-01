<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, Pencil, Power, Trash2, RotateCcw } from 'lucide-vue-next'
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
import { useSelection } from '@/composables/useSelection'
import { formatTime } from '@/utils/format'
import type { Share } from '@/types/share'
import { copyToClipboard } from '@/utils/clipboard'
import { useMessage } from '@/stores/message'

const shareActions = useShareActions()
const message = useMessage()
const selection = useSelection(
  () => shareActions.items.value,
  (item) => String(item.id),
)

const { t } = useI18n({ useScope: 'global' })

const columns = computed(() => [
  { key: 'select', label: '', width: '32px', align: 'center' as const },
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
const editShareLinkWithCode = ref('')
const editShareCode = ref('')
const editIncludeCode = ref(true)
const editForm = ref<ShareFormValue>({
  expiresInDays: 7,
  expiresAt: null,
  requiresCode: true,
  code: '',
})
const toggling = ref(new Set<string>())
const deleteConfirm = ref(false)
const deletingShare = ref<Share | null>(null)
const batchConfirm = ref(false)
const batchAction = ref<'revoke' | 'enable' | 'delete' | null>(null)
const selectAllRef = ref<HTMLInputElement | null>(null)

const isToggling = (id: string) => toggling.value.has(id)
const asShare = (row: unknown) => row as Share
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
  () => shareActions.items.value,
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
  editShareCode.value = share.code ?? ''
  editShareLink.value = buildShareUrl(share.token)
  editShareLinkWithCode.value = buildShareUrl(share.token, share.code)
  editIncludeCode.value = true
  editModal.value = true
}

const copyShareLink = async (share: Share) => {
  const link = buildShareUrl(share.token)
  const linkWithCode = buildShareUrl(share.token, share.code)
  const text = share.code
    ? `${t('shares.edit.copyLinkPrefix')}: ${linkWithCode} ${t('shares.edit.copyCodePrefix')}: ${share.code}`
    : link
  const ok = await copyToClipboard(text)
  if (ok) {
    message.success(t('shares.toasts.copySuccess'))
  } else {
    message.error(t('shares.toasts.copyFailTitle'), t('shares.toasts.copyFailMessage'))
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
  const link =
    editIncludeCode.value && editShareCode.value ? editShareLinkWithCode.value : editShareLink.value
  const text = editShareCode.value
    ? `${t('shares.edit.copyLinkPrefix')}: ${link} ${t('shares.edit.copyCodePrefix')}: ${editShareCode.value}`
    : link
  const ok = await copyToClipboard(text)
  if (ok) {
    message.success(t('shares.toasts.copySuccess'))
  } else {
    message.error(t('shares.toasts.copyFailTitle'), t('shares.toasts.copyFailMessage'))
  }
}

const buildShareUrl = (token: string, code?: string | null) => {
  const url = new URL(`/s/${token}`, window.location.origin)
  if (code) {
    url.searchParams.set('code', code)
  }
  return url.toString()
}

const requestDelete = (share: Share) => {
  deletingShare.value = share
  deleteConfirm.value = true
}

const requestBatch = (action: 'revoke' | 'enable' | 'delete') => {
  if (selectedCount.value === 0) {
    return
  }
  batchAction.value = action
  batchConfirm.value = true
}

const confirmDelete = async () => {
  if (deletingShare.value) {
    await shareActions.remove(deletingShare.value.id)
  }
  deleteConfirm.value = false
  deletingShare.value = null
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
  if (batchAction.value === 'revoke') {
    const result = await shareActions.revokeBatch(ids)
    if (result.failed.length === 0) {
      message.success(
        t('shares.toasts.batchRevokeTitle'),
        t('shares.toasts.batchSuccessMessage', { count: result.success }),
      )
    } else {
      message.warning(
        t('shares.toasts.batchRevokePartialTitle'),
        t('shares.toasts.batchPartialMessage', {
          success: result.success,
          failed: result.failed.length,
        }),
      )
    }
  } else if (batchAction.value === 'enable') {
    const result = await shareActions.enableBatch(ids)
    if (result.failed.length === 0) {
      message.success(
        t('shares.toasts.batchEnableTitle'),
        t('shares.toasts.batchSuccessMessage', { count: result.success }),
      )
    } else {
      message.warning(
        t('shares.toasts.batchEnablePartialTitle'),
        t('shares.toasts.batchPartialMessage', {
          success: result.success,
          failed: result.failed.length,
        }),
      )
    }
  } else {
    const result = await shareActions.removeBatch(ids)
    if (result.failed.length === 0) {
      message.success(
        t('shares.toasts.batchDeleteTitle'),
        t('shares.toasts.batchSuccessMessage', { count: result.success }),
      )
    } else {
      message.warning(
        t('shares.toasts.batchDeletePartialTitle'),
        t('shares.toasts.batchPartialMessage', {
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

onMounted(() => {
  void shareActions.fetchShares()
})
</script>

<template>
  <section class="page">
    <div class="page__bar">
      <div v-show="selectedCount > 0" class="page__actions">
        <div class="bulk-actions">
          <div class="bulk-actions__buttons">
            <Button variant="secondary" @click="requestBatch('revoke')">
              <Trash2 :size="16" />
              {{ t('shares.bulk.revokeSelected', { count: selectedCount }) }}
            </Button>
            <Button variant="secondary" @click="requestBatch('enable')">
              <RotateCcw :size="16" />
              {{ t('shares.bulk.enableSelected', { count: selectedCount }) }}
            </Button>
            <Button variant="danger" @click="requestBatch('delete')">
              <Trash2 :size="16" />
              {{ t('shares.bulk.deleteSelected', { count: selectedCount }) }}
            </Button>
          </div>
        </div>
      </div>
      <div class="page__info">
        {{ t('shares.itemsCount', { count: shareActions.total.value }) }}
      </div>
    </div>

    <div class="table-wrap shares-table">
      <Table
        :columns="columns"
        :rows="shareActions.items.value"
        :min-rows="shareActions.limit.value"
        scrollable
        fill
      >
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
              :checked="selection.isSelected(asShare(row))"
              @click.stop
              @change="selection.toggle(asShare(row))"
            />
          </div>
        </template>
        <template #cell-name="{ row }">
          <button type="button" class="name name--link" @click="copyShareLink(asShare(row))">
            <FileTypeIcon :name="asShare(row).name" :resource-type="asShare(row).resourceType" />
            <span class="name__text">{{ asShare(row).name }}</span>
          </button>
        </template>
        <template #cell-status="{ row }">
          <Tag v-if="asShare(row).status === -1" tone="danger">{{
            t('shares.status.missing')
          }}</Tag>
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
          {{
            asShare(row).expiresAt
              ? formatTime(asShare(row).expiresAt as number)
              : t('shares.permanent')
          }}
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
      <Input
        :model-value="
          editShareCode
            ? `${t('shares.edit.copyLinkPrefix')}: ${editIncludeCode ? editShareLinkWithCode : editShareLink} ${t('shares.edit.copyCodePrefix')}: ${editShareCode}`
            : editShareLink
        "
        :label="t('shares.edit.linkLabel')"
        :readonly="true"
      />
      <label class="share-link__toggle">
        <input type="checkbox" v-model="editIncludeCode" />
        <span>{{ t('shares.edit.includeCodeInLink') }}</span>
      </label>
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

  <ConfirmDialog
    :open="batchConfirm"
    :title="
      batchAction === 'revoke'
        ? t('shares.bulk.confirmRevokeTitle')
        : batchAction === 'enable'
          ? t('shares.bulk.confirmEnableTitle')
          : t('shares.bulk.confirmDeleteTitle')
    "
    :message="
      batchAction === 'revoke'
        ? t('shares.bulk.confirmRevokeMessage', { count: selectedCount })
        : batchAction === 'enable'
          ? t('shares.bulk.confirmEnableMessage', { count: selectedCount })
          : t('shares.bulk.confirmDeleteMessage', { count: selectedCount })
    "
    @close="batchConfirm = false"
    @confirm="confirmBatch"
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

.page__bar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  gap: var(--space-3);
  min-height: 65.6px;
}

.page__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  min-height: 28px;
}

.bulk-actions__buttons {
  flex-wrap: wrap;
  row-gap: var(--space-2);
}

.page__info {
  font-size: 12px;
  color: var(--color-muted);
  margin-left: auto;
}

.table-wrap {
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.bulk-actions__count {
  font-size: 12px;
  color: var(--color-muted);
}

.bulk-actions__buttons {
  margin-left: auto;
  display: inline-flex;
  gap: var(--space-2);
}

.bulk-actions__buttons :deep(button) {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
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

.select-cell {
  display: inline-flex;
  align-items: center;
  height: 100%;
}

.shares-table :deep(.table__cell:first-child) {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.shares-table :deep(.table),
.shares-table :deep(.table__row),
.shares-table :deep(.table__header) {
  min-width: 0;
  width: 100%;
}

.shares-table :deep(.table__cell) {
  min-width: 0;
}

.share-link {
  display: grid;
  gap: var(--space-3);
}

.share-link__toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 12px;
  color: var(--color-muted);
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
  .page__bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .shares-table :deep(.table) {
    --table-columns: 32px minmax(0, 1fr) 88px;
  }

  .shares-table :deep(.table__cell:nth-child(3)),
  .shares-table :deep(.table__cell:nth-child(4)),
  .shares-table :deep(.table__cell:nth-child(5)),
  .shares-table :deep(.table__cell:nth-child(6)) {
    display: none;
  }
}
</style>
