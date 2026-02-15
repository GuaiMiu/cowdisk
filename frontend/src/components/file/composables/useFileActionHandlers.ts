import type { Ref } from 'vue'
import { uploadFiles } from '@/api/modules/userDisk'
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
  createFolder: (name: string) => Promise<boolean>
  renameEntry: (entry: DiskEntry, name: string) => Promise<boolean>
  removeEntry: (entry: DiskEntry) => Promise<unknown>
  removeEntries: (entries: DiskEntry[]) => Promise<unknown>
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

type EntryAction = 'download' | 'rename' | 'delete' | 'share' | 'detail' | 'preview' | 'move' | 'edit'

type UseFileActionHandlersOptions = {
  t: Translate
  message: MessageApi
  explorer: ExplorerApi
  selection: SelectionApi
  uploader: UploaderApi
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
    options.state.deleteConfirm.value = true
  }

  const confirmDelete = async () => {
    if (options.state.deleteSubmitting.value) {
      return
    }
    options.state.deleteSubmitting.value = true
    const targets = options.state.deleteBatch.value
    options.state.deleteConfirm.value = false
    try {
      if (targets.length === 1) {
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
    openUpload,
    openFolderUpload,
    handleOpen,
    handleAction,
    handleCreateInline,
    handleCreateTextInline,
    handleRenameInline,
    openMoveSelected,
    confirmMove,
  }
}
