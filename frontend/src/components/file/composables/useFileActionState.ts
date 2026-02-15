import { ref } from 'vue'
import type { DiskEntry } from '@/types/disk'

export const useFileActionState = () => {
  const deleteConfirm = ref(false)
  const deleteBatch = ref<DiskEntry[]>([])
  const deleteSubmitting = ref(false)

  const detailModal = ref(false)
  const detailEntry = ref<DiskEntry | null>(null)

  const moveModal = ref(false)
  const moveEntries = ref<DiskEntry[]>([])
  const moveSubmitting = ref(false)

  const creatingFolder = ref(false)
  const creatingText = ref(false)
  const renamingEntry = ref<DiskEntry | null>(null)
  const renamingName = ref('')
  const actionLocks = ref(new Set<string>())

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

  const closeMoveModal = () => {
    moveModal.value = false
    moveEntries.value = []
  }

  const closeDetailModal = () => {
    detailModal.value = false
    detailEntry.value = null
  }

  const closeDeleteConfirm = () => {
    deleteConfirm.value = false
  }

  const cancelCreateInline = () => {
    creatingFolder.value = false
    creatingText.value = false
  }

  const cancelRenameInline = () => {
    renamingEntry.value = null
  }

  return {
    deleteConfirm,
    deleteBatch,
    deleteSubmitting,
    detailModal,
    detailEntry,
    moveModal,
    moveEntries,
    moveSubmitting,
    creatingFolder,
    creatingText,
    renamingEntry,
    renamingName,
    actionLocks,
    openFolderModal,
    openNewTextInline,
    openRenameModal,
    openMoveModal,
    closeMoveModal,
    closeDetailModal,
    closeDeleteConfirm,
    cancelCreateInline,
    cancelRenameInline,
  }
}

export type FileActionState = ReturnType<typeof useFileActionState>
