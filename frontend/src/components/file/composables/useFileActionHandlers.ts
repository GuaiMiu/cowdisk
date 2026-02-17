import type { Ref } from 'vue'
import { uploadFiles } from '@/api/modules/userDisk'
import {
  compressStatus,
  extractStatus,
  prepareCompress,
  prepareCompressBatch,
  prepareExtract,
} from '@/api/modules/userDisk'
import type { DiskEntry } from '@/types/disk'
import { normalizeDiskError } from '@/utils/diskError'
import { getFileKind } from '@/utils/fileType'
import type { FileActionState } from './useFileActionState'

type Translate = (key: string, params?: Record<string, unknown>) => string

type MessageApi = {
  warning: (title: string, message?: string) => number
  success: (title: string, message?: string) => number
  error: (title: string, message?: string) => number
}

type ExplorerApi = {
  path: Ref<string>
  parentId: Ref<number | null>
  suggestAvailableName: (name: string) => string
  createFolder: (name: string) => Promise<boolean>
  renameEntry: (entry: DiskEntry, name: string) => Promise<boolean>
  removeEntry: (entry: DiskEntry) => Promise<unknown>
  removeEntries: (entries: DiskEntry[]) => Promise<unknown>
  hardRemoveEntries: (entries: DiskEntry[]) => Promise<unknown>
  moveEntries: (entries: DiskEntry[], parentId: number | null) => Promise<unknown>
  openEntry: (entry: DiskEntry) => Promise<unknown>
  downloadEntry: (entry: DiskEntry) => Promise<unknown>
  refresh: () => Promise<unknown>
}

type SelectionApi = {
  selectedItems: Ref<DiskEntry[]>
  clear: () => void
}

type UploaderApi = {
  enqueue: (files: File[], path: string, parentId: number | null) => void
  notifyQueue: () => void
}

type EntryAction =
  | 'download'
  | 'rename'
  | 'delete'
  | 'share'
  | 'detail'
  | 'preview'
  | 'move'
  | 'edit'
  | 'compress'
  | 'extract'
type DeleteMode = 'trash' | 'hard'
type ArchiveStatusResult = { status?: string; message?: string }

type UseFileActionHandlersOptions = {
  t: Translate
  message: MessageApi
  explorer: ExplorerApi
  selection: SelectionApi
  uploader: UploaderApi
  requestArchiveName: (suggested: string) => Promise<string | null>
  openShareModal: (entry: DiskEntry) => void
  openPreview: (entry: DiskEntry) => Promise<void>
  openOfficeEdit: (entry: DiskEntry) => Promise<void>
  openEditorForFolder: (entry: DiskEntry) => Promise<void>
  openEditorForFile: (entry: DiskEntry) => Promise<void>
  state: FileActionState
}

const isTextEntry = (entry: DiskEntry) => {
  const kind = getFileKind(entry.name, entry.is_dir)
  return kind === 'text' || kind === 'code'
}

const isOfficeEntry = (entry: DiskEntry) => {
  const kind = getFileKind(entry.name, entry.is_dir)
  return kind === 'doc' || kind === 'sheet' || kind === 'slide'
}

const isZipEntry = (entry: DiskEntry) => !entry.is_dir && entry.name.toLowerCase().endsWith('.zip')
const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))
const defaultArchiveName = (entry: DiskEntry) => {
  const name = (entry.name || '').trim() || 'archive'
  return name.toLowerCase().endsWith('.zip') ? name : `${name}.zip`
}

export const useFileActionHandlers = (options: UseFileActionHandlersOptions) => {
  const withActionLock = async <T>(key: string, task: () => Promise<T>) => {
    if (options.state.actionLocks.value.has(key)) {
      return null
    }
    options.state.actionLocks.value = new Set(options.state.actionLocks.value).add(key)
    try {
      return await task()
    } finally {
      const next = new Set(options.state.actionLocks.value)
      next.delete(key)
      options.state.actionLocks.value = next
    }
  }

  const handleDelete = (entries: DiskEntry[]) => {
    options.state.deleteBatch.value = entries
    options.state.deleteMode.value = 'trash'
    options.state.deleteConfirm.value = true
  }

  const runDelete = async (mode: DeleteMode) => {
    if (options.state.deleteSubmitting.value) {
      return
    }
    options.state.deleteSubmitting.value = true
    const targets = options.state.deleteBatch.value
    options.state.deleteMode.value = mode
    options.state.deleteConfirm.value = false
    try {
      if (mode === 'hard') {
        await options.explorer.hardRemoveEntries(targets)
      } else if (targets.length === 1) {
        const [first] = targets
        if (first) {
          await options.explorer.removeEntry(first)
        }
      } else {
        await options.explorer.removeEntries(targets)
      }
      options.selection.clear()
      options.state.deleteBatch.value = []
    } finally {
      options.state.deleteSubmitting.value = false
    }
  }

  const confirmDelete = async () => runDelete('trash')

  const confirmDeletePermanently = async () => runDelete('hard')

  const openUpload = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.onchange = () => {
      const files = input.files ? Array.from(input.files) : []
      if (files.length) {
        options.uploader.enqueue(
          files,
          options.explorer.path.value,
          options.explorer.parentId.value ?? null,
        )
        options.uploader.notifyQueue()
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
        options.uploader.enqueue(
          files,
          options.explorer.path.value,
          options.explorer.parentId.value ?? null,
        )
        options.uploader.notifyQueue()
      }
    }
    input.click()
  }

  const handleOpen = async (entry: DiskEntry) => {
    if (!entry.is_dir) {
      return
    }
    await options.explorer.openEntry(entry)
    options.selection.clear()
    options.state.creatingFolder.value = false
    options.state.renamingEntry.value = null
  }

  const waitArchiveJob = async (
    getStatus: () => Promise<ArchiveStatusResult>,
    timeoutMs = 180000,
  ) => {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
      const result = await getStatus()
      const status = (result.status || '').toLowerCase()
      if (status === 'ready') {
        return
      }
      if (status === 'error') {
        throw new Error(result.message || options.t('fileExplorer.toasts.archiveTaskFailedMessage'))
      }
      await sleep(1000)
    }
    throw new Error(options.t('fileExplorer.toasts.archiveTaskTimeoutMessage'))
  }

  const runCompressJob = async (entry: DiskEntry, name?: string) => {
    const created = await prepareCompress({ file_id: entry.id, ...(name ? { name } : {}) })
    await waitArchiveJob(() => compressStatus(created.job_id))
  }

  const runExtractJob = async (entry: DiskEntry) => {
    if (!isZipEntry(entry)) {
      throw new Error(options.t('fileExplorer.toasts.extractZipOnly'))
    }
    const created = await prepareExtract({ file_id: entry.id })
    await waitArchiveJob(() => extractStatus(created.job_id))
  }

  const handleCompress = async (entry: DiskEntry) => {
    try {
      const suggested = options.explorer.suggestAvailableName(defaultArchiveName(entry))
      const input = await options.requestArchiveName(suggested)
      if (input === null) {
        return
      }
      const nextName = input.trim()
      if (!nextName) {
        options.message.warning(options.t('fileExplorer.toasts.compressNameRequired'))
        return
      }
      options.message.success(
        options.t('fileExplorer.toasts.compressingTitle'),
        options.t('fileExplorer.toasts.compressingMessage'),
      )
      await runCompressJob(entry, nextName)
      await options.explorer.refresh()
      options.message.success(options.t('fileExplorer.toasts.compressDoneTitle'))
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.archiveTaskFailedTitle'),
        normalizeDiskError(error, options.t('fileExplorer.toasts.archiveTaskFailedMessage')),
      )
    }
  }

  const handleExtract = async (entry: DiskEntry) => {
    if (!isZipEntry(entry)) {
      options.message.warning(options.t('fileExplorer.toasts.extractZipOnly'))
      return
    }
    try {
      options.message.success(
        options.t('fileExplorer.toasts.extractingTitle'),
        options.t('fileExplorer.toasts.extractingMessage'),
      )
      await runExtractJob(entry)
      await options.explorer.refresh()
      options.message.success(options.t('fileExplorer.toasts.extractDoneTitle'))
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.archiveTaskFailedTitle'),
        normalizeDiskError(error, options.t('fileExplorer.toasts.archiveTaskFailedMessage')),
      )
    }
  }

  const handleCompressSelected = async () => {
    const targets = options.selection.selectedItems.value
    if (!targets.length) {
      options.message.warning(options.t('fileExplorer.toasts.noSelection'))
      return
    }
    const first = targets[0]
    if (!first) {
      return
    }
    const suggested = options.explorer.suggestAvailableName(defaultArchiveName(first))
    const input = await options.requestArchiveName(suggested)
    if (input === null) {
      return
    }
    const nextName = input.trim()
    if (!nextName) {
      options.message.warning(options.t('fileExplorer.toasts.compressNameRequired'))
      return
    }
    try {
      options.message.success(
        options.t('fileExplorer.toasts.compressingTitle'),
        options.t('fileExplorer.toasts.compressingBatchMessage', { count: targets.length }),
      )
      const created = await prepareCompressBatch({
        file_ids: targets.map((entry) => entry.id),
        name: nextName,
      })
      await waitArchiveJob(() => compressStatus(created.job_id))
      await options.explorer.refresh()
      options.message.success(
        options.t('fileExplorer.toasts.compressDoneTitle'),
        options.t('fileExplorer.toasts.archiveBatchDoneMessage', { count: targets.length }),
      )
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.archiveTaskFailedTitle'),
        normalizeDiskError(error, options.t('fileExplorer.toasts.archiveTaskFailedMessage')),
      )
    }
  }

  const handleExtractSelected = async () => {
    const targets = options.selection.selectedItems.value
    if (!targets.length) {
      options.message.warning(options.t('fileExplorer.toasts.noSelection'))
      return
    }
    const zipTargets = targets.filter((entry) => isZipEntry(entry))
    if (!zipTargets.length) {
      options.message.warning(options.t('fileExplorer.toasts.extractZipOnly'))
      return
    }
    let success = 0
    let failed = 0
    options.message.success(
      options.t('fileExplorer.toasts.extractingTitle'),
      options.t('fileExplorer.toasts.extractingBatchMessage', { count: zipTargets.length }),
    )
    for (const entry of zipTargets) {
      try {
        await runExtractJob(entry)
        success += 1
      } catch {
        failed += 1
      }
    }
    if (success > 0) {
      await options.explorer.refresh()
    }
    if (failed === 0) {
      options.message.success(
        options.t('fileExplorer.toasts.extractDoneTitle'),
        options.t('fileExplorer.toasts.archiveBatchDoneMessage', { count: success }),
      )
      return
    }
    if (success > 0) {
      options.message.warning(
        options.t('fileExplorer.toasts.archiveTaskFailedTitle'),
        options.t('fileExplorer.toasts.archiveBatchPartialMessage', { success, failed }),
      )
      return
    }
    options.message.error(
      options.t('fileExplorer.toasts.archiveTaskFailedTitle'),
      options.t('fileExplorer.toasts.archiveTaskFailedMessage'),
    )
  }

  const handleAction = async (payload: { entry: DiskEntry; action: EntryAction }) => {
    switch (payload.action) {
      case 'download':
        await withActionLock(`download:${payload.entry.id}`, () =>
          options.explorer.downloadEntry(payload.entry),
        )
        return
      case 'rename':
        options.state.openRenameModal(payload.entry)
        return
      case 'move':
        options.state.openMoveModal([payload.entry])
        return
      case 'delete':
        handleDelete([payload.entry])
        return
      case 'share':
        options.openShareModal(payload.entry)
        return
      case 'detail':
        options.state.detailEntry.value = payload.entry
        options.state.detailModal.value = true
        return
      case 'preview':
        await withActionLock(`preview:${payload.entry.id}`, () => options.openPreview(payload.entry))
        return
      case 'edit':
        if (payload.entry.is_dir) {
          await options.openEditorForFolder(payload.entry)
          return
        }
        if (isTextEntry(payload.entry)) {
          await options.openEditorForFile(payload.entry)
          return
        }
        if (isOfficeEntry(payload.entry)) {
          await options.openOfficeEdit(payload.entry)
          return
        }
        options.message.warning(options.t('fileExplorer.toasts.notEditable'))
        return
      case 'compress':
        await withActionLock(`compress:${payload.entry.id}`, () => handleCompress(payload.entry))
        return
      case 'extract':
        await withActionLock(`extract:${payload.entry.id}`, () => handleExtract(payload.entry))
        return
    }
  }

  const handleCreateInline = async (name: string) => {
    const ok = await options.explorer.createFolder(name)
    if (ok) {
      options.state.creatingFolder.value = false
    }
  }

  const handleCreateTextInline = async (name: string) => {
    const filename = name.trim()
    if (!filename) {
      options.message.warning(options.t('fileExplorer.toasts.docNameRequired'))
      return
    }
    try {
      const file = new File([new Blob([''], { type: 'text/plain' })], filename, {
        type: 'text/plain',
      })
      await uploadFiles({
        items: [{ file, filename }],
        parent_id: options.explorer.parentId.value ?? null,
        name: filename,
        overwrite: false,
      })
      options.message.success(options.t('fileExplorer.toasts.docCreated'))
      options.state.creatingText.value = false
      await options.explorer.refresh()
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.createFailedTitle'),
        normalizeDiskError(error, options.t('fileExplorer.toasts.createFailedMessage')),
      )
    }
  }

  const handleRenameInline = async (payload: { entry: DiskEntry; name: string }) => {
    const ok = await options.explorer.renameEntry(payload.entry, payload.name)
    if (ok) {
      options.state.renamingEntry.value = null
    }
  }

  const openMoveSelected = () => {
    const targets = options.selection.selectedItems.value
    if (targets.length === 0) {
      return
    }
    options.state.openMoveModal(targets)
  }

  const confirmMove = async (targetParentId: number | null) => {
    if (options.state.moveSubmitting.value) {
      return
    }
    const targets = options.state.moveEntries.value
    if (!targets.length) {
      return
    }
    options.state.moveSubmitting.value = true
    try {
      await options.explorer.moveEntries(targets, targetParentId)
      options.selection.clear()
      options.state.closeMoveModal()
    } finally {
      options.state.moveSubmitting.value = false
    }
  }

  return {
    handleDelete,
    confirmDelete,
    confirmDeletePermanently,
    openUpload,
    openFolderUpload,
    handleOpen,
    handleAction,
    handleCreateInline,
    handleCreateTextInline,
    handleRenameInline,
    openMoveSelected,
    confirmMove,
    handleCompressSelected,
    handleExtractSelected,
  }
}
