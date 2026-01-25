<script setup lang="ts">
import { onMounted, ref } from 'vue'
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

const columns = [
  { key: 'name', label: '分享名称', width: 'minmax(240px, 1fr)' },
  { key: 'status', label: '状态', width: '90px' },
  { key: 'resourceType', label: '类型', width: '80px' },
  { key: 'createdAt', label: '创建时间', width: '130px' },
  { key: 'expiresAt', label: '有效期', width: '130px' },
  { key: 'actions', label: '操作', width: '88px' },
]

const formatResourceType = (value: string) => {
  const normalized = value?.toLowerCase()
  if (normalized === 'folder' || normalized === 'dir') {
    return '文件夹'
  }
  if (normalized === 'file') {
    return '文件'
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
    toast.success('链接已复制')
  } else {
    toast.error('复制失败', '请手动复制链接')
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
    toast.success('链接已复制')
  } else {
    toast.error('复制失败', '请手动复制链接')
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
    <PageHeader title="分享管理" subtitle="统一管理对外分享链接">
      <template #actions>
        <Button variant="secondary" @click="shareActions.fetchShares(shareActions.currentPage.value)">
          刷新
        </Button>
      </template>
    </PageHeader>

    <div class="table-wrap">
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
          <label
            class="status-switch"
            :class="{ 'is-disabled': isToggling(asShare(row).id) || asShare(row).status === -1 }"
          >
            <input
              type="checkbox"
              :checked="asShare(row).status === 1"
              :disabled="isToggling(asShare(row).id) || asShare(row).status === -1"
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
          {{ asShare(row).expiresAt ? formatTime(asShare(row).expiresAt as number) : '永久' }}
        </template>
        <template #cell-actions="{ row }">
          <div class="actions">
            <IconButton
              size="sm"
              variant="ghost"
              aria-label="编辑分享"
              @click="openEdit(asShare(row))"
            >
              <Pencil :size="16" />
            </IconButton>
            <IconButton
              size="sm"
              variant="ghost"
              aria-label="删除分享"
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

  <Modal :open="editModal" title="编辑分享" @close="editModal = false">
    <ShareForm v-model="editForm" />
    <div class="share-link">
      <Input :model-value="editShareLink" label="分享地址" :readonly="true" />
      <Button variant="secondary" @click="copyLink">
        复制链接
      </Button>
    </div>
    <template #footer>
      <Button variant="ghost" @click="editModal = false">取消</Button>
      <Button :loading="editSubmitting" @click="submitEdit">保存</Button>
    </template>
  </Modal>

  <ConfirmDialog
    :open="deleteConfirm"
    title="确认删除分享"
    message="删除后分享链接将失效，是否继续？"
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
  justify-content: center;
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
</style>
