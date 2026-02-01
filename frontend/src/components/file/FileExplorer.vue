<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FileToolbar from './FileToolbar.vue'
import FileBreadcrumb from './FileBreadcrumb.vue'
import FileTable from './FileTable.vue'
import FileMoveDialog from './FileMoveDialog.vue'
import UploadQueueDrawer from './UploadQueueDrawer.vue'
import Modal from '@/components/common/Modal.vue'
import FileEditorDialog from '@/components/file/FileEditorDialog.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ShareForm, { type ShareFormValue } from '@/components/share/ShareForm.vue'
import ImagePreview from '@/components/common/ImagePreview.vue'
import PdfPreview from '@/components/common/PdfPreview.vue'
import VideoPreview from '@/components/common/VideoPreview.vue'
import {
  createDownloadToken,
  getPreviewFileUrl,
  previewFileByToken,
  readEditFile,
  saveEditFile,
} from '@/api/modules/userDisk'
import { useDiskExplorer } from '@/composables/useDiskExplorer'
import { useSelection } from '@/composables/useSelection'
import { useUploader } from '@/composables/useUploader'
import { useShareActions } from '@/composables/useShareActions'
import { useMessage } from '@/stores/message'
import { useUploadsStore } from '@/stores/uploads'
import type { DiskEntry } from '@/types/disk'
import type { Share } from '@/types/share'
import { copyToClipboard } from '@/utils/clipboard'
import { normalizeDiskError } from '@/utils/diskError'
import { formatBytes, formatTime } from '@/utils/format'
import { getFileKind } from '@/utils/fileType'
import { joinPath, toRelativePath } from '@/utils/path'

const { t, locale } = useI18n({ useScope: 'global' })
const rootName = computed(() => t('files.rootName'))

const explorer = useDiskExplorer()
const selection = useSelection(() => explorer.items.value)
const uploader = useUploader()
const shareActions = useShareActions()
const message = useMessage()
const uploadsStore = useUploadsStore()

const queueOpen = ref(false)
const shareModal = ref(false)
const deleteConfirm = ref(false)
const shareEntry = ref<DiskEntry | null>(null)
const shareLink = ref('')
const shareLinkWithCode = ref('')
const shareCode = ref('')
const shareIncludeCode = ref(true)
const shareResult = ref<Share | null>(null)
const shareSubmitting = ref(false)
const lastShareSignature = ref<string | null>(null)
const detailModal = ref(false)
const detailEntry = ref<DiskEntry | null>(null)
const moveModal = ref(false)
const moveEntries = ref<DiskEntry[]>([])
const creatingText = ref(false)
const previewOpen = ref(false)
const previewItems = ref<Array<{ src: string; name?: string }>>([])
const previewIndex = ref(0)
const previewUrls = ref<string[]>([])
const previewEntries = ref<DiskEntry[]>([])
const previewLoading = ref(new Set<number>())
const pdfOpen = ref(false)
const pdfSrc = ref<string | null>(null)
const pdfName = ref<string>('')
const pdfUrls = ref<string[]>([])
const videoOpen = ref(false)
const videoSrc = ref<string | null>(null)
const videoName = ref<string>('')
const videoType = ref<string | null>(null)
const editorOpen = ref(false)
const editorRootPath = ref('/')
const editorRootName = ref(rootName.value)
const editorFilePath = ref<string | null>(null)
const editorFileName = ref('')
const editorContent = ref('')
const editorLanguage = ref('plaintext')
const editorLoading = ref(false)
const editorSaving = ref(false)
const shareForm = ref<ShareFormValue>({
  expiresInDays: 7,
  expiresAt: null,
  requiresCode: true,
  code: '',
})
const deleteBatch = ref<DiskEntry[]>([])
const creatingFolder = ref(false)
const renamingEntry = ref<DiskEntry | null>(null)
const renamingName = ref('')
const refreshTimer = ref<number | null>(null)
const LAST_PATH_KEY = 'cowdisk:last_path'

const openFolderModal = () => {
  creatingFolder.value = true
  creatingText.value = false
  renamingEntry.value = null
  renamingName.value = ''
}

const openNewTextInline = () => {
  creatingFolder.value = false
  renamingEntry.value = null
  creatingText.value = true
}

const openRenameModal = (entry: DiskEntry) => {
  renamingEntry.value = entry
  renamingName.value = entry.name
  creatingFolder.value = false
  creatingText.value = false
}

const openMoveModal = (entries: DiskEntry[]) => {
  moveEntries.value = entries
  moveModal.value = true
}

const openShareModal = (entry: DiskEntry) => {
  shareEntry.value = entry
  shareForm.value = {
    expiresInDays: 7,
    expiresAt: null,
    requiresCode: true,
    code: '',
  }
  shareLink.value = ''
  shareLinkWithCode.value = ''
  shareCode.value = ''
  shareIncludeCode.value = true
  shareResult.value = null
  lastShareSignature.value = null
  shareModal.value = true
}

const buildShareSignature = () => {
  const expiresAt =
    shareForm.value.expiresAt && Number.isFinite(Date.parse(shareForm.value.expiresAt))
      ? Date.parse(shareForm.value.expiresAt)
      : null
  return JSON.stringify({
    path: shareEntry.value?.path ?? '',
    resourceType: shareEntry.value?.is_dir ? 'FOLDER' : 'FILE',
    expiresInDays: shareForm.value.expiresInDays ?? null,
    expiresAt,
    code:
      shareForm.value.requiresCode && shareForm.value.code.trim()
        ? shareForm.value.code.trim()
        : null,
  })
}

const canRegenerateShare = computed(() => {
  if (!shareResult.value) {
    return true
  }
  return buildShareSignature() !== lastShareSignature.value
})

const submitShare = async () => {
  if (!shareEntry.value || shareSubmitting.value || !canRegenerateShare.value) {
    return
  }
  shareSubmitting.value = true
  const expiresAt =
    shareForm.value.expiresAt && Number.isFinite(Date.parse(shareForm.value.expiresAt))
      ? Date.parse(shareForm.value.expiresAt)
      : null
  const payload = {
    resourceType: shareEntry.value.is_dir ? 'FOLDER' : 'FILE',
    path: shareEntry.value.path,
    expiresInDays: shareForm.value.expiresInDays ?? null,
    expiresAt,
    code:
      shareForm.value.requiresCode && shareForm.value.code.trim()
        ? shareForm.value.code.trim()
        : null,
  }
  const share = await shareActions.create(payload)
  shareSubmitting.value = false
  if (share) {
    shareResult.value = share
    shareCode.value = share.code ?? ''
    shareLink.value = buildShareUrl(share.token)
    shareLinkWithCode.value = buildShareUrl(share.token, share.code)
    lastShareSignature.value = buildShareSignature()
  }
}

const handleCopyLink = async () => {
  const link = shareIncludeCode.value && shareCode.value ? shareLinkWithCode.value : shareLink.value
  const text = shareCode.value
    ? `${t('fileExplorer.modals.copyLinkPrefix')}: ${link} ${t('fileExplorer.modals.copyCodePrefix')}: ${shareCode.value}`
    : link
  const ok = await copyToClipboard(text)
  if (ok) {
    message.success(t('fileExplorer.toasts.linkCopied'))
  } else {
    message.error(t('fileExplorer.toasts.copyFailTitle'), t('fileExplorer.toasts.copyFailMessage'))
  }
}

const handleDelete = (entries: DiskEntry[]) => {
  deleteBatch.value = entries
  deleteConfirm.value = true
}

const confirmDelete = async () => {
  const targets = deleteBatch.value
  deleteConfirm.value = false
  if (targets.length === 1) {
    const [first] = targets
    if (first) {
      await explorer.removeEntry(first)
    }
  } else {
    await explorer.removeEntries(targets)
  }
  selection.clear()
  deleteBatch.value = []
}

const openUpload = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.onchange = () => {
    const files = input.files ? Array.from(input.files) : []
    if (files.length) {
      uploader.enqueue(files, explorer.path.value)
      queueOpen.value = true
    }
  }
  input.click()
}

const openFolderUpload = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  ;(input as HTMLInputElement & { webkitdirectory?: boolean }).webkitdirectory = true
  input.onchange = () => {
    const files = input.files ? Array.from(input.files) : []
    if (files.length) {
      uploader.enqueue(files, explorer.path.value)
      queueOpen.value = true
    }
  }
  input.click()
}

const handleOpen = async (entry: DiskEntry) => {
  if (!entry.is_dir) {
    return
  }
  await explorer.load(entry.path)
  selection.clear()
  creatingFolder.value = false
  renamingEntry.value = null
}

const handleAction = async (payload: {
  entry: DiskEntry
  action: 'download' | 'rename' | 'delete' | 'share' | 'detail' | 'preview' | 'move' | 'edit'
}) => {
  if (payload.action === 'download') {
    await explorer.downloadEntry(payload.entry)
  }
  if (payload.action === 'rename') {
    openRenameModal(payload.entry)
  }
  if (payload.action === 'move') {
    openMoveModal([payload.entry])
  }
  if (payload.action === 'delete') {
    handleDelete([payload.entry])
  }
  if (payload.action === 'share') {
    openShareModal(payload.entry)
  }
  if (payload.action === 'detail') {
    detailEntry.value = payload.entry
    detailModal.value = true
  }
  if (payload.action === 'preview') {
    await openPreview(payload.entry)
  }
  if (payload.action === 'edit') {
    if (payload.entry.is_dir) {
      await openEditorForFolder(payload.entry)
      return
    }
    if (isTextEntry(payload.entry)) {
      await openEditorForFile(payload.entry)
      return
    }
    message.warning(t('fileExplorer.toasts.notEditable'))
  }
}

const isImageEntry = (entry: DiskEntry) => getFileKind(entry.name, entry.is_dir) === 'image'
const isPdfEntry = (entry: DiskEntry) => getFileKind(entry.name, entry.is_dir) === 'pdf'
const isVideoEntry = (entry: DiskEntry) => getFileKind(entry.name, entry.is_dir) === 'video'
const isTextEntry = (entry: DiskEntry) => {
  const kind = getFileKind(entry.name, entry.is_dir)
  return kind === 'text' || kind === 'code'
}

const clearPreview = () => {
  previewUrls.value.forEach((url) => URL.revokeObjectURL(url))
  previewUrls.value = []
  previewItems.value = []
  previewOpen.value = false
  previewIndex.value = 0
  previewEntries.value = []
  previewLoading.value = new Set()
}

const clearPdfPreview = () => {
  pdfUrls.value.forEach((url) => URL.revokeObjectURL(url))
  pdfUrls.value = []
  pdfSrc.value = null
  pdfName.value = ''
  pdfOpen.value = false
}

const clearVideoPreview = () => {
  videoSrc.value = null
  videoName.value = ''
  videoType.value = null
  videoOpen.value = false
}

const clearEditor = () => {
  editorOpen.value = false
  editorRootPath.value = '/'
  editorRootName.value = rootName.value
  editorFilePath.value = null
  editorFileName.value = ''
  editorContent.value = ''
  editorLanguage.value = 'plaintext'
  editorLoading.value = false
  editorSaving.value = false
}

const getVideoMime = (name: string) => {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    mp4: 'video/mp4',
    webm: 'video/webm',
    mov: 'video/quicktime',
    mkv: 'video/x-matroska',
    avi: 'video/x-msvideo',
    flv: 'video/x-flv',
    wmv: 'video/x-ms-wmv',
    m4v: 'video/x-m4v',
  }
  return map[ext] || 'video/mp4'
}

const buildShareUrl = (token: string, code?: string | null) => {
  const url = new URL(`/s/${token}`, window.location.origin)
  if (code) {
    url.searchParams.set('code', code)
  }
  return url.toString()
}

const openPreview = async (entry: DiskEntry) => {
  if (entry.is_dir) {
    message.warning(t('fileExplorer.toasts.folderNoPreview'))
    return
  }
  if (isImageEntry(entry)) {
    await openImagePreview(entry)
    return
  }
  if (isPdfEntry(entry)) {
    await openPdfPreview(entry)
    return
  }
  if (isVideoEntry(entry)) {
    await openVideoPreview(entry)
    return
  }
  if (isTextEntry(entry)) {
    await openEditorForFile(entry)
    return
  }
  message.warning(t('fileExplorer.toasts.fileNoPreview'))
}

const openImagePreview = async (entry: DiskEntry) => {
  try {
    clearPreview()
    const images = explorer.items.value.filter((item) => !item.is_dir && isImageEntry(item))
    previewEntries.value = images
    previewItems.value = images.map((item) => ({ src: '', name: item.name }))
    const currentIndex = Math.max(
      0,
      images.findIndex((item) => item.path === entry.path),
    )
    previewIndex.value = currentIndex
    previewOpen.value = true
    await ensurePreview(currentIndex)
    await Promise.all([ensurePreview(currentIndex - 1), ensurePreview(currentIndex + 1)])
  } catch (error) {
    message.error(
      t('fileExplorer.toasts.previewFailedTitle'),
      error instanceof Error ? error.message : t('fileExplorer.toasts.previewFailedMessage'),
    )
    clearPreview()
  }
}

const openPdfPreview = async (entry: DiskEntry) => {
  try {
    clearPdfPreview()
    const token = await createDownloadToken({ path: entry.path })
    const result = await previewFileByToken(token.token)
    const url = URL.createObjectURL(result.blob)
    pdfUrls.value = [url]
    pdfSrc.value = url
    pdfName.value = entry.name || t('fileExplorer.pdfPreviewDefault')
    pdfOpen.value = true
  } catch (error) {
    message.error(
      t('fileExplorer.toasts.previewFailedTitle'),
      error instanceof Error ? error.message : t('fileExplorer.toasts.previewFailedMessage'),
    )
    clearPdfPreview()
  }
}

const openVideoPreview = async (entry: DiskEntry) => {
  try {
    clearVideoPreview()
    const token = await createDownloadToken({ path: entry.path })
    videoSrc.value = getPreviewFileUrl(token.token)
    videoName.value = entry.name || t('fileExplorer.videoPreviewDefault')
    videoType.value = getVideoMime(entry.name || '')
    videoOpen.value = true
  } catch (error) {
    message.error(
      t('fileExplorer.toasts.previewFailedTitle'),
      error instanceof Error ? error.message : t('fileExplorer.toasts.previewFailedMessage'),
    )
    clearVideoPreview()
  }
}

const getTextLanguage = (name: string) => {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    txt: 'plaintext',
    log: 'plaintext',
    md: 'markdown',
    markdown: 'markdown',
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    xml: 'xml',
    html: 'html',
    htm: 'html',
    css: 'css',
    scss: 'scss',
    less: 'less',
    js: 'javascript',
    ts: 'typescript',
    jsx: 'javascript',
    tsx: 'typescript',
    vue: 'html',
    py: 'python',
    rb: 'ruby',
    go: 'go',
    java: 'java',
    kt: 'kotlin',
    swift: 'swift',
    cs: 'csharp',
    dart: 'dart',
    rs: 'rust',
    c: 'c',
    h: 'c',
    cpp: 'cpp',
    hpp: 'cpp',
    cc: 'cpp',
    cxx: 'cpp',
    m: 'objective-c',
    mm: 'objective-cpp',
    php: 'php',
    sh: 'shell',
    bash: 'shell',
    zsh: 'shell',
    sql: 'sql',
    ini: 'ini',
    conf: 'ini',
    cfg: 'ini',
    toml: 'toml',
    gradle: 'groovy',
    properties: 'properties',
    make: 'makefile',
    mk: 'makefile',
  }
  return map[ext] || 'plaintext'
}

const getParentPath = (path: string) => {
  if (!path) {
    return '/'
  }
  const segments = path.split('/').filter(Boolean)
  if (segments.length <= 1) {
    return '/'
  }
  return `/${segments.slice(0, -1).join('/')}`
}

const openEditorForFolder = async (entry: DiskEntry) => {
  clearEditor()
  editorRootPath.value = entry.path ? `/${entry.path}` : '/'
  editorRootName.value = entry.name || rootName.value
  editorOpen.value = true
}

const openEditorForFile = async (entry: DiskEntry) => {
  try {
    clearEditor()
    editorRootPath.value = getParentPath(entry.path)
    editorRootName.value =
      editorRootPath.value === '/'
        ? rootName.value
        : editorRootPath.value.split('/').pop() || rootName.value
    editorFilePath.value = entry.path
    editorFileName.value = entry.name || ''
    editorLanguage.value = getTextLanguage(entry.name || '')
    editorLoading.value = true
    editorOpen.value = true
    const data = await readEditFile(entry.path)
    editorContent.value = data.content || ''
  } catch (error) {
    message.error(
      t('fileExplorer.toasts.readFailedTitle'),
      error instanceof Error ? error.message : t('fileExplorer.toasts.readFailedMessage'),
    )
    clearEditor()
  } finally {
    editorLoading.value = false
  }
}

const selectEditorFile = async (payload: { path: string; name: string }) => {
  try {
    editorFilePath.value = payload.path
    editorFileName.value = payload.name
    editorLanguage.value = getTextLanguage(payload.name)
    editorLoading.value = true
    const data = await readEditFile(payload.path)
    editorContent.value = data.content || ''
  } catch (error) {
    message.error(
      t('fileExplorer.toasts.readFailedTitle'),
      error instanceof Error ? error.message : t('fileExplorer.toasts.readFailedMessage'),
    )
  } finally {
    editorLoading.value = false
  }
}

const saveEditor = async () => {
  if (!editorFilePath.value || editorSaving.value) {
    return
  }
  editorSaving.value = true
  try {
    await saveEditFile({
      path: editorFilePath.value,
      content: editorContent.value,
      overwrite: true,
    })
    message.success(t('fileExplorer.toasts.saveSuccess'))
    await explorer.refresh()
  } catch (error) {
    message.error(
      t('fileExplorer.toasts.saveFailedTitle'),
      error instanceof Error ? error.message : t('fileExplorer.toasts.saveFailedMessage'),
    )
  } finally {
    editorSaving.value = false
  }
}

const ensurePreview = async (index: number) => {
  if (index < 0 || index >= previewEntries.value.length) {
    return
  }
  if (previewItems.value[index]?.src) {
    return
  }
  if (previewLoading.value.has(index)) {
    return
  }
  const entry = previewEntries.value[index]
  if (!entry) {
    return
  }
  previewLoading.value = new Set(previewLoading.value).add(index)
  try {
    const token = await createDownloadToken({ path: entry.path })
    const result = await previewFileByToken(token.token)
    const url = URL.createObjectURL(result.blob)
    previewUrls.value = [...previewUrls.value, url]
    const next = [...previewItems.value]
    next[index] = { src: url, name: entry.name }
    previewItems.value = next
  } finally {
    const next = new Set(previewLoading.value)
    next.delete(index)
    previewLoading.value = next
  }
}

const handlePreviewChange = async (index: number) => {
  await ensurePreview(index)
  await Promise.all([ensurePreview(index - 1), ensurePreview(index + 1)])
}

const handleCreateInline = async (name: string) => {
  const ok = await explorer.createFolder(name)
  if (ok) {
    creatingFolder.value = false
  }
}

const cancelCreateInline = () => {
  creatingFolder.value = false
  creatingText.value = false
}

const handleCreateTextInline = async (name: string) => {
  const filename = name.trim()
  if (!filename) {
    message.warning(t('fileExplorer.toasts.docNameRequired'))
    return
  }
  const path = toRelativePath(joinPath(explorer.path.value, filename))
  try {
    await saveEditFile({ path, content: '', overwrite: false })
    message.success(t('fileExplorer.toasts.docCreated'))
    creatingText.value = false
    await explorer.refresh()
  } catch (error) {
    message.error(
      t('fileExplorer.toasts.createFailedTitle'),
      normalizeDiskError(error, t('fileExplorer.toasts.createFailedMessage')),
    )
  }
}
const handleRenameInline = async (payload: { entry: DiskEntry; name: string }) => {
  const ok = await explorer.renameEntry(payload.entry, payload.name)
  if (ok) {
    renamingEntry.value = null
  }
}

const cancelRenameInline = () => {
  renamingEntry.value = null
}

const openMoveSelected = () => {
  const targets = selection.selectedItems.value
  if (targets.length === 0) {
    return
  }
  openMoveModal(targets)
}

const confirmMove = async (targetPath: string) => {
  const targets = moveEntries.value
  if (!targets.length) {
    return
  }
  await explorer.moveEntries(targets, targetPath)
  selection.clear()
  moveModal.value = false
  moveEntries.value = []
}

onMounted(() => {
  const savedPath = sessionStorage.getItem(LAST_PATH_KEY) || '/'
  void explorer.load(savedPath)
})

watch(
  () => explorer.path.value,
  (value) => {
    if (value) {
      sessionStorage.setItem(LAST_PATH_KEY, value)
    }
  },
)

watch(locale, () => {
  if (editorRootPath.value === '/') {
    editorRootName.value = rootName.value
  }
})

watch(
  () =>
    uploadsStore.items.map((item) => ({
      id: item.id,
      status: item.status,
      path: item.path,
    })),
  (next, prev) => {
    if (!prev) {
      return
    }
    const prevMap = new Map(prev.map((item) => [item.id, item]))
    const currentPath = toRelativePath(explorer.path.value)
    let needsRefresh = false
    for (const item of next) {
      const before = prevMap.get(item.id)
      if (!before) {
        continue
      }
      if (before.status !== 'success' && item.status === 'success') {
        if (toRelativePath(item.path) === currentPath) {
          needsRefresh = true
          break
        }
      }
    }
    if (needsRefresh && refreshTimer.value === null) {
      refreshTimer.value = window.setTimeout(() => {
        refreshTimer.value = null
        void explorer.refresh()
      }, 300)
    }
  },
)
</script>

<template>
  <section class="explorer">
    <FileToolbar
      :selected-count="selection.selectedItems.value.length"
      @new-folder="openFolderModal"
      @new-text="openNewTextInline"
      @upload="openUpload"
      @upload-folder="openFolderUpload"
      @refresh="explorer.refresh"
      @toggle-queue="queueOpen = true"
      @delete-selected="handleDelete(selection.selectedItems.value)"
      @move-selected="openMoveSelected"
    />
    <div class="explorer__bar">
      <FileBreadcrumb :path="explorer.path.value" @navigate="explorer.load" />
      <div class="explorer__count">
        {{ t('files.itemsCount', { count: explorer.items.value.length }) }}
      </div>
    </div>
    <div class="explorer__table">
      <FileTable
        :items="explorer.items.value"
        :selected="selection.selected.value"
        :all-selected="selection.allSelected.value"
        :indeterminate="selection.indeterminate.value"
        :is-selected="selection.isSelected"
        :toggle="selection.toggle"
        :toggle-all="selection.toggleAll"
        :creating-folder="creatingFolder"
        :creating-text="creatingText"
        :editing-entry="renamingEntry"
        :editing-name="renamingName"
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
    @close="shareModal = false"
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
      <Button variant="ghost" @click="shareModal = false">{{ t('common.cancel') }}</Button>
      <Button :loading="shareSubmitting" :disabled="!canRegenerateShare" @click="submitShare">
        {{ t('fileExplorer.modals.shareGenerate') }}
      </Button>
    </template>
  </Modal>

  <Modal
    :open="detailModal"
    :title="t('fileExplorer.modals.detailTitle')"
    @close="detailModal = false"
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
        <span class="detail__value">{{ formatTime(detailEntry.modified_time) }}</span>
      </div>
    </div>
    <template #footer>
      <Button variant="ghost" @click="detailModal = false">{{ t('common.close') }}</Button>
    </template>
  </Modal>

  <FileMoveDialog
    :open="moveModal"
    :entries="moveEntries"
    :current-path="explorer.path.value"
    @close="
      () => {
        moveModal = false
        moveEntries = []
      }
    "
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
    :root-path="editorRootPath"
    :root-name="editorRootName"
    :active-path="editorFilePath"
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
    @close="deleteConfirm = false"
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
