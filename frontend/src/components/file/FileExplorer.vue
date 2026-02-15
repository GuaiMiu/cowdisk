<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FileToolbar from './FileToolbar.vue'
import FileBreadcrumb from './FileBreadcrumb.vue'
import FileTable from './FileTable.vue'
import FileMoveDialog from './FileMoveDialog.vue'
import UploadQueueDrawer from './UploadQueueDrawer.vue'
import Modal from '@/components/common/Modal.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ShareForm from '@/components/share/ShareForm.vue'
import { previewFile, readEditFile, saveEditFile } from '@/api/modules/userDisk'
import { useFileEditor } from '@/components/file/composables/useFileEditor'
import { useFileActions } from '@/components/file/composables/useFileActions'
import { useDiskExplorer } from '@/composables/useDiskExplorer'
import { useSelection } from '@/composables/useSelection'
import { useUploader } from '@/composables/useUploader'
import { useShareActions } from '@/composables/useShareActions'
import { useFilePreview } from '@/components/file/composables/useFilePreview'
import { useShareDialog } from '@/components/file/composables/useShareDialog'
import { useMessage } from '@/stores/message'
import { useUploadsStore } from '@/stores/uploads'
import { formatBytes, formatTime } from '@/utils/format'
import { toRelativePath } from '@/utils/path'

const FileEditorDialog = defineAsyncComponent(() => import('@/components/file/FileEditorDialog.vue'))
const ImagePreview = defineAsyncComponent(() => import('@/components/common/ImagePreview.vue'))
const PdfPreview = defineAsyncComponent(() => import('@/components/common/PdfPreview.vue'))
const VideoPreview = defineAsyncComponent(() => import('@/components/common/VideoPreview.vue'))

const { t } = useI18n({ useScope: 'global' })
const rootName = computed(() => t('files.rootName'))

const explorer = useDiskExplorer()
const selection = useSelection(() => explorer.items.value)
const uploader = useUploader()
const shareActions = useShareActions()
const message = useMessage()
const uploadsStore = useUploadsStore()
const queuePendingCount = computed(
  () =>
    uploadsStore.items.filter((item) =>
      ['queued', 'uploading', 'paused'].includes(item.status),
    ).length,
)
const queueErrorCount = computed(
  () => uploadsStore.items.filter((item) => item.status === 'error').length,
)

const queueOpen = ref(false)
const refreshTimer = ref<number | null>(null)
const successInViewIds = ref(new Set<string>())
const observedUploadsPath = ref<string>('')
const LAST_PATH_KEY = 'cowdisk:last_path'
const LAST_STACK_KEY = 'cowdisk:last_stack'

const {
  shareModal,
  shareForm,
  shareResult,
  shareSubmitting,
  shareIncludeCode,
  shareCode,
  shareLink,
  shareLinkWithCode,
  canRegenerateShare,
  openShareModal,
  closeShareModal,
  submitShare,
  handleCopyLink,
} = useShareDialog({
  t,
  createShare: shareActions.create,
  message,
})

const breadcrumbItems = computed(() => {
  const rootLabel = t('fileBreadcrumb.root')
  return [
    { id: null as number | null, label: rootLabel },
    ...explorer.folderStack.value.map((item) => ({
      id: item.id,
      label: item.name,
    })),
  ]
})

const {
  editorOpen,
  editorRootId,
  editorRootName,
  editorFileId,
  editorContent,
  editorLanguage,
  editorLoading,
  editorSaving,
  openEditorForFolder,
  openEditorForFile,
  selectEditorFile,
  saveEditor,
  clearEditor,
} = useFileEditor({
  t,
  message,
  rootLabel: rootName,
  folderStack: explorer.folderStack,
  readFile: readEditFile,
  saveFile: saveEditFile,
  refresh: explorer.refresh,
})

const {
  previewOpen,
  previewItems,
  previewIndex,
  pdfOpen,
  pdfSrc,
  pdfName,
  videoOpen,
  videoSrc,
  videoName,
  videoType,
  openPreview,
  handlePreviewChange,
  clearPreview,
  clearPdfPreview,
  clearVideoPreview,
  clearAllPreviews,
} = useFilePreview({
  items: explorer.items,
  t,
  message,
  previewFile,
  openTextPreview: openEditorForFile,
})

const {
  deleteConfirm,
  detailModal,
  detailEntry,
  moveModal,
  moveEntries,
  creatingFolder,
  creatingText,
  renamingEntry,
  renamingName,
  openFolderModal,
  openNewTextInline,
  closeMoveModal,
  closeDetailModal,
  handleDelete,
  closeDeleteConfirm,
  confirmDelete,
  openUpload,
  openFolderUpload,
  handleOpen,
  handleAction,
  handleCreateInline,
  cancelCreateInline,
  handleCreateTextInline,
  handleRenameInline,
  cancelRenameInline,
  openMoveSelected,
  confirmMove,
} = useFileActions({
  t,
  message,
  explorer,
  selection,
  uploader,
  openShareModal,
  openPreview,
  openEditorForFolder,
  openEditorForFile,
})

onMounted(() => {
  const savedStack = sessionStorage.getItem(LAST_STACK_KEY)
  if (savedStack) {
    try {
      const parsed = JSON.parse(savedStack)
      if (Array.isArray(parsed)) {
        explorer.folderStack.value = parsed.filter(
          (item) => item && typeof item.id === 'number' && typeof item.name === 'string',
        )
      }
    } catch {
      explorer.folderStack.value = []
    }
  }
  const savedPath = sessionStorage.getItem(LAST_PATH_KEY) || '/'
  const savedParent =
    savedPath && savedPath !== '/' && explorer.folderStack.value.length
      ? explorer.folderStack.value[explorer.folderStack.value.length - 1]?.id ?? null
      : null
  void explorer.load(savedParent)
})

watch(
  () => explorer.path.value,
  (value) => {
    if (value) {
      sessionStorage.setItem(LAST_PATH_KEY, value)
    }
    sessionStorage.setItem(LAST_STACK_KEY, JSON.stringify(explorer.folderStack.value))
  },
)

watch(
  () => [uploadsStore.items, explorer.path.value] as const,
  ([items, explorerPath]) => {
    const currentPath = toRelativePath(explorerPath)
    const nextSuccessIds = new Set<string>()
    let needsRefresh = false
    for (const item of items) {
      if (item.status !== 'success') {
        continue
      }
      if (toRelativePath(item.path) !== currentPath) {
        continue
      }
      nextSuccessIds.add(item.id)
      if (!successInViewIds.value.has(item.id)) {
        needsRefresh = true
      }
    }
    if (observedUploadsPath.value !== currentPath) {
      observedUploadsPath.value = currentPath
      successInViewIds.value = nextSuccessIds
      return
    }
    successInViewIds.value = nextSuccessIds
    if (needsRefresh && refreshTimer.value === null) {
      refreshTimer.value = window.setTimeout(() => {
        refreshTimer.value = null
        void explorer.refresh()
      }, 300)
    }
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (refreshTimer.value !== null) {
    window.clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
  clearAllPreviews()
  clearEditor()
})
</script>

<template>
  <section class="explorer">
    <FileToolbar
      :selected-count="selection.selectedItems.value.length"
      :queue-pending-count="queuePendingCount"
      :queue-error-count="queueErrorCount"
      @new-folder="openFolderModal"
      @new-text="openNewTextInline"
      @upload="openUpload"
      @upload-folder="openFolderUpload"
      @refresh="explorer.refresh"
      @toggle-queue="queueOpen = !queueOpen"
      @delete-selected="handleDelete(selection.selectedItems.value)"
      @move-selected="openMoveSelected"
    />
    <div class="explorer__bar">
      <FileBreadcrumb :items="breadcrumbItems" @navigate="explorer.goToBreadcrumb" />
      <div class="explorer__count">
        {{ t('files.itemsCount', { count: explorer.items.value.length }) }}
      </div>
    </div>
    <div class="explorer__table">
      <FileTable
        :items="explorer.sortedItems.value"
        :selected="selection.selected.value"
        :all-selected="selection.allSelected.value"
        :indeterminate="selection.indeterminate.value"
        :is-selected="selection.isSelected"
        :toggle="selection.toggle"
        :toggle-all="selection.toggleAll"
        :sort-key="explorer.sortKey.value"
        :sort-order="explorer.sortOrder.value"
        :creating-folder="creatingFolder"
        :creating-text="creatingText"
        :editing-entry="renamingEntry"
        :editing-name="renamingName"
        @sort-change="explorer.setSort"
        @open="handleOpen"
        @action="handleAction"
        @create-confirm="handleCreateInline"
        @create-text-confirm="handleCreateTextInline"
        @create-cancel="cancelCreateInline"
        @rename-confirm="handleRenameInline"
        @rename-cancel="cancelRenameInline"
      />
    </div>
  </section>

  <UploadQueueDrawer :open="queueOpen" @close="queueOpen = false" />

  <Modal
    :open="shareModal"
    :title="t('fileExplorer.modals.shareTitle')"
    @close="closeShareModal"
  >
    <ShareForm v-model="shareForm" />
    <div v-if="shareResult" class="share__result">
      <Input
        :model-value="
          shareCode
            ? `${t('fileExplorer.modals.copyLinkPrefix')}: ${shareIncludeCode ? shareLinkWithCode : shareLink} ${t('fileExplorer.modals.copyCodePrefix')}: ${shareCode}`
            : shareLink
        "
        :label="t('fileExplorer.modals.shareLinkLabel')"
        :readonly="true"
      />
      <label class="share__toggle">
        <input type="checkbox" v-model="shareIncludeCode" />
        <span>{{ t('fileExplorer.modals.includeCodeInLink') }}</span>
      </label>
      <Button variant="secondary" @click="handleCopyLink">
        {{ t('common.copyLink') }}
      </Button>
    </div>
    <template #footer>
      <Button variant="ghost" @click="closeShareModal">{{ t('common.cancel') }}</Button>
      <Button :loading="shareSubmitting" :disabled="!canRegenerateShare" @click="submitShare">
        {{ t('fileExplorer.modals.shareGenerate') }}
      </Button>
    </template>
  </Modal>

  <Modal
    :open="detailModal"
    :title="t('fileExplorer.modals.detailTitle')"
    @close="closeDetailModal"
  >
    <div v-if="detailEntry" class="detail">
      <div class="detail__row">
        <span class="detail__label">{{ t('fileExplorer.modals.detailName') }}</span>
        <span class="detail__value">{{ detailEntry.name }}</span>
      </div>
      <div class="detail__row">
        <span class="detail__label">{{ t('fileExplorer.modals.detailType') }}</span>
        <span class="detail__value">{{
          detailEntry.is_dir ? t('common.folder') : t('common.file')
        }}</span>
      </div>
      <div class="detail__row">
        <span class="detail__label">{{ t('fileExplorer.modals.detailPath') }}</span>
        <span class="detail__value">{{ detailEntry.path }}</span>
      </div>
      <div class="detail__row">
        <span class="detail__label">{{ t('fileExplorer.modals.detailSize') }}</span>
        <span class="detail__value">
          {{ detailEntry.is_dir ? '-' : formatBytes(detailEntry.size) }}
        </span>
      </div>
      <div class="detail__row">
        <span class="detail__label">{{ t('fileExplorer.modals.detailUpdatedAt') }}</span>
        <span class="detail__value">{{ formatTime(detailEntry.updated_at) }}</span>
      </div>
    </div>
    <template #footer>
      <Button variant="ghost" @click="closeDetailModal">{{ t('common.close') }}</Button>
    </template>
  </Modal>

  <FileMoveDialog
    :open="moveModal"
    :entries="moveEntries"
    :current-path="explorer.path.value"
    :current-parent-id="explorer.parentId.value"
    @close="closeMoveModal"
    @confirm="confirmMove"
  />

  <ImagePreview
    :open="previewOpen"
    :images="previewItems"
    :start-index="previewIndex"
    @change="handlePreviewChange"
    @update:open="
      (value) => {
        if (!value) clearPreview()
      }
    "
    @close="clearPreview"
  />

  <PdfPreview
    :open="pdfOpen"
    :src="pdfSrc"
    :name="pdfName"
    @update:open="
      (value) => {
        if (!value) clearPdfPreview()
      }
    "
    @close="clearPdfPreview"
  />

  <VideoPreview
    :open="videoOpen"
    :src="videoSrc"
    :name="videoName"
    :type="videoType"
    @update:open="
      (value) => {
        if (!value) clearVideoPreview()
      }
    "
    @close="clearVideoPreview"
  />

  <FileEditorDialog
    :open="editorOpen"
    :root-id="editorRootId"
    :root-name="editorRootName"
    :active-id="editorFileId"
    :language="editorLanguage"
    :loading="editorLoading"
    :saving="editorSaving"
    v-model="editorContent"
    @select="selectEditorFile"
    @save="saveEditor"
    @close="clearEditor"
  />

  <ConfirmDialog
    :open="deleteConfirm"
    :title="t('fileExplorer.modals.confirmDeleteTitle')"
    :message="t('fileExplorer.modals.confirmDeleteMessage')"
    @close="closeDeleteConfirm"
    @confirm="confirmDelete"
  />
</template>

<style scoped>
.explorer {
  display: grid;
  gap: var(--space-4);
  grid-template-rows: auto auto 1fr;
  min-height: 0;
  height: 100%;
}

.explorer__bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.explorer__count {
  font-size: 12px;
  color: var(--color-muted);
}

.explorer__table {
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.share__result {
  display: grid;
  gap: var(--space-3);
}

.share__toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 12px;
  color: var(--color-muted);
}

.detail {
  display: grid;
  gap: var(--space-3);
}

.detail__row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: var(--space-3);
  align-items: center;
}

.detail__label {
  font-size: 12px;
  color: var(--color-muted);
}

.detail__value {
  font-size: 13px;
  color: var(--color-text);
  word-break: break-all;
}

@media (max-width: 768px) {
  .explorer__bar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }
}
</style>
