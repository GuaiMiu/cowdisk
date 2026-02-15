import { ref, watch, type Ref } from 'vue'
import type { DiskEntry } from '@/types/disk'
import { getTextLanguage } from '@/utils/fileMeta'

type Translate = (key: string, params?: Record<string, unknown>) => string

type MessageApi = {
  success: (title: string, message?: string) => number
  error: (title: string, message?: string) => number
}

type UseFileEditorOptions = {
  t: Translate
  message: MessageApi
  rootLabel: Ref<string>
  folderStack: Ref<Array<{ id: number; name: string }>>
  readFile: (fileId: number) => Promise<{ content?: string | null }>
  saveFile: (fileId: number, payload: { content: string; overwrite: boolean }) => Promise<unknown>
  refresh: () => Promise<unknown>
}

export const useFileEditor = (options: UseFileEditorOptions) => {
  const editorOpen = ref(false)
  const editorRootId = ref<number | null>(null)
  const editorRootName = ref(options.rootLabel.value)
  const editorFileId = ref<number | null>(null)
  const editorFileName = ref('')
  const editorContent = ref('')
  const editorLanguage = ref('plaintext')
  const editorLoading = ref(false)
  const editorSaving = ref(false)
  const requestId = ref(0)

  const clearEditor = () => {
    requestId.value += 1
    editorOpen.value = false
    editorRootId.value = null
    editorRootName.value = options.rootLabel.value
    editorFileId.value = null
    editorFileName.value = ''
    editorContent.value = ''
    editorLanguage.value = 'plaintext'
    editorLoading.value = false
    editorSaving.value = false
  }

  const openEditorForFolder = async (entry: DiskEntry) => {
    clearEditor()
    editorRootId.value = entry.id
    editorRootName.value = entry.name || options.rootLabel.value
    editorFileId.value = null
    editorOpen.value = true
  }

  const openEditorForFile = async (entry: DiskEntry) => {
    const currentRequestId = ++requestId.value
    try {
      clearEditor()
      requestId.value = currentRequestId
      editorRootId.value = entry.parent_id ?? null
      const parentName = options.folderStack.value.slice(-1)[0]?.name || ''
      editorRootName.value = parentName || options.rootLabel.value
      editorFileId.value = entry.id
      editorFileName.value = entry.name || ''
      editorLanguage.value = getTextLanguage(entry.name || '')
      editorLoading.value = true
      editorOpen.value = true
      const data = await options.readFile(entry.id)
      if (currentRequestId !== requestId.value) {
        return
      }
      editorContent.value = data.content || ''
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.readFailedTitle'),
        error instanceof Error ? error.message : options.t('fileExplorer.toasts.readFailedMessage'),
      )
      clearEditor()
    } finally {
      editorLoading.value = false
    }
  }

  const selectEditorFile = async (payload: { fileId: number; name: string }) => {
    const currentRequestId = ++requestId.value
    try {
      editorFileId.value = payload.fileId
      editorFileName.value = payload.name
      editorLanguage.value = getTextLanguage(payload.name)
      editorLoading.value = true
      const data = await options.readFile(payload.fileId)
      if (currentRequestId !== requestId.value) {
        return
      }
      editorContent.value = data.content || ''
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.readFailedTitle'),
        error instanceof Error ? error.message : options.t('fileExplorer.toasts.readFailedMessage'),
      )
    } finally {
      editorLoading.value = false
    }
  }

  const saveEditor = async () => {
    if (!editorFileId.value || editorSaving.value) {
      return
    }
    editorSaving.value = true
    try {
      await options.saveFile(editorFileId.value, {
        content: editorContent.value,
        overwrite: true,
      })
      options.message.success(options.t('fileExplorer.toasts.saveSuccess'))
      await options.refresh()
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.saveFailedTitle'),
        error instanceof Error ? error.message : options.t('fileExplorer.toasts.saveFailedMessage'),
      )
    } finally {
      editorSaving.value = false
    }
  }

  watch(options.rootLabel, (label) => {
    if (editorRootId.value === null) {
      editorRootName.value = label
    }
  })

  return {
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
  }
}

