import type { Ref } from 'vue'
import type { DiskEntry } from '@/types/disk'
import { useFileActionHandlers } from './useFileActionHandlers'
import { useFileActionState } from './useFileActionState'

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

type UseFileActionsOptions = {
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
}

export const useFileActions = (options: UseFileActionsOptions) => {
  const state = useFileActionState()
  const handlers = useFileActionHandlers({
    ...options,
    state,
  })

  return {
    deleteConfirm: state.deleteConfirm,
    detailModal: state.detailModal,
    detailEntry: state.detailEntry,
    moveModal: state.moveModal,
    moveEntries: state.moveEntries,
    creatingFolder: state.creatingFolder,
    creatingText: state.creatingText,
    renamingEntry: state.renamingEntry,
    renamingName: state.renamingName,
    openFolderModal: state.openFolderModal,
    openNewTextInline: state.openNewTextInline,
    closeMoveModal: state.closeMoveModal,
    closeDetailModal: state.closeDetailModal,
    closeDeleteConfirm: state.closeDeleteConfirm,
    cancelCreateInline: state.cancelCreateInline,
    cancelRenameInline: state.cancelRenameInline,
    handleDelete: handlers.handleDelete,
    confirmDelete: handlers.confirmDelete,
    confirmDeletePermanently: handlers.confirmDeletePermanently,
    openUpload: handlers.openUpload,
    openFolderUpload: handlers.openFolderUpload,
    handleOpen: handlers.handleOpen,
    handleAction: handlers.handleAction,
    handleCreateInline: handlers.handleCreateInline,
    handleCreateTextInline: handlers.handleCreateTextInline,
    handleCreateOfficeInline: handlers.handleCreateOfficeInline,
    handleRenameInline: handlers.handleRenameInline,
    openMoveSelected: handlers.openMoveSelected,
    confirmMove: handlers.confirmMove,
    handleCompressSelected: handlers.handleCompressSelected,
    handleExtractSelected: handlers.handleExtractSelected,
  }
}
