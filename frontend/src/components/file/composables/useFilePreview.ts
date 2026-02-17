import { ref, type Ref } from 'vue'
import type { DiskEntry } from '@/types/disk'
import { getVideoMime } from '@/utils/fileMeta'
import { getFileKind } from '@/utils/fileType'

type Translate = (key: string, params?: Record<string, unknown>) => string

type MessageApi = {
  warning: (title: string, message?: string) => number
  error: (title: string, message?: string) => number
}

type PreviewFileResult = {
  blob: Blob
  contentType?: string | null
}

type UseFilePreviewOptions = {
  items: Ref<DiskEntry[]>
  t: Translate
  message: MessageApi
  previewFile: (fileId: number) => Promise<PreviewFileResult>
  issuePreviewUrl: (fileId: number) => Promise<{ url: string }>
  issueOfficeUrl: (fileId: number, mode: 'view' | 'edit') => Promise<{ url: string }>
  openTextPreview: (entry: DiskEntry) => Promise<void>
}

export const useFilePreview = (options: UseFilePreviewOptions) => {
  const previewOpen = ref(false)
  const previewItems = ref<Array<{ src: string; name?: string }>>([])
  const previewIndex = ref(0)
  const previewUrls = ref<string[]>([])
  const previewEntries = ref<DiskEntry[]>([])
  const previewLoading = ref(new Set<number>())
  const previewSessionId = ref(0)

  const pdfOpen = ref(false)
  const pdfSrc = ref<string | null>(null)
  const pdfName = ref('')
  const pdfUrls = ref<string[]>([])
  const pdfRequestId = ref(0)

  const videoOpen = ref(false)
  const videoSrc = ref<string | null>(null)
  const videoName = ref('')
  const videoType = ref<string | null>(null)
  const videoRequestId = ref(0)
  const officeOpen = ref(false)
  const officeSrc = ref<string | null>(null)
  const officeName = ref('')

  const isImageEntry = (entry: DiskEntry) => getFileKind(entry.name, entry.is_dir) === 'image'
  const isPdfEntry = (entry: DiskEntry) => getFileKind(entry.name, entry.is_dir) === 'pdf'
  const isVideoEntry = (entry: DiskEntry) => getFileKind(entry.name, entry.is_dir) === 'video'
  const isTextEntry = (entry: DiskEntry) => {
    const kind = getFileKind(entry.name, entry.is_dir)
    return kind === 'text' || kind === 'code'
  }
  const isOfficeEntry = (entry: DiskEntry) => {
    const kind = getFileKind(entry.name, entry.is_dir)
    return kind === 'doc' || kind === 'sheet' || kind === 'slide'
  }

  const clearPreview = () => {
    previewSessionId.value += 1
    previewUrls.value.forEach((url) => URL.revokeObjectURL(url))
    previewUrls.value = []
    previewItems.value = []
    previewOpen.value = false
    previewIndex.value = 0
    previewEntries.value = []
    previewLoading.value = new Set()
  }

  const clearPdfPreview = () => {
    pdfRequestId.value += 1
    pdfUrls.value.forEach((url) => URL.revokeObjectURL(url))
    pdfUrls.value = []
    pdfSrc.value = null
    pdfName.value = ''
    pdfOpen.value = false
  }

  const clearVideoPreview = () => {
    videoRequestId.value += 1
    if (videoSrc.value && videoSrc.value.startsWith('blob:')) {
      URL.revokeObjectURL(videoSrc.value)
    }
    videoSrc.value = null
    videoName.value = ''
    videoType.value = null
    videoOpen.value = false
  }

  const clearOfficePreview = () => {
    officeSrc.value = null
    officeName.value = ''
    officeOpen.value = false
  }

  const ensurePreview = async (index: number, sessionId: number) => {
    if (sessionId !== previewSessionId.value) {
      return
    }
    if (index < 0 || index >= previewEntries.value.length) {
      return
    }
    if (previewItems.value[index]?.src || previewLoading.value.has(index)) {
      return
    }
    const entry = previewEntries.value[index]
    if (!entry) {
      return
    }
    previewLoading.value = new Set(previewLoading.value).add(index)
    try {
      const result = await options.previewFile(entry.id)
      if (sessionId !== previewSessionId.value) {
        return
      }
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

  const openImagePreview = async (entry: DiskEntry) => {
    const sessionId = previewSessionId.value + 1
    try {
      previewSessionId.value = sessionId
      clearPreview()
      previewSessionId.value = sessionId
      const images = options.items.value.filter((item) => !item.is_dir && isImageEntry(item))
      previewEntries.value = images
      previewItems.value = images.map((item) => ({ src: '', name: item.name }))
      const currentIndex = Math.max(
        0,
        images.findIndex((item) => item.id === entry.id),
      )
      previewIndex.value = currentIndex
      previewOpen.value = true
      await ensurePreview(currentIndex, sessionId)
      await Promise.all([
        ensurePreview(currentIndex - 1, sessionId),
        ensurePreview(currentIndex + 1, sessionId),
      ])
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.previewFailedTitle'),
        error instanceof Error
          ? error.message
          : options.t('fileExplorer.toasts.previewFailedMessage'),
      )
      clearPreview()
    }
  }

  const openPdfPreview = async (entry: DiskEntry) => {
    const requestId = ++pdfRequestId.value
    try {
      clearPdfPreview()
      pdfRequestId.value = requestId
      const result = await options.previewFile(entry.id)
      if (requestId !== pdfRequestId.value) {
        return
      }
      const url = URL.createObjectURL(result.blob)
      pdfUrls.value = [url]
      pdfSrc.value = url
      pdfName.value = entry.name || options.t('fileExplorer.pdfPreviewDefault')
      pdfOpen.value = true
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.previewFailedTitle'),
        error instanceof Error
          ? error.message
          : options.t('fileExplorer.toasts.previewFailedMessage'),
      )
      clearPdfPreview()
    }
  }

  const openVideoPreview = async (entry: DiskEntry) => {
    const requestId = ++videoRequestId.value
    try {
      clearVideoPreview()
      videoRequestId.value = requestId
      const result = await options.issuePreviewUrl(entry.id)
      if (requestId !== videoRequestId.value) {
        return
      }
      const base = import.meta.env.VITE_API_BASE_URL || ''
      const href = base ? new URL(result.url, base).toString() : result.url
      videoSrc.value = href
      videoName.value = entry.name || options.t('fileExplorer.videoPreviewDefault')
      videoType.value = getVideoMime(entry.name || '')
      videoOpen.value = true
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.previewFailedTitle'),
        error instanceof Error
          ? error.message
          : options.t('fileExplorer.toasts.previewFailedMessage'),
      )
      clearVideoPreview()
    }
  }

  const openOfficePreview = async (entry: DiskEntry, mode: 'view' | 'edit' = 'view') => {
    try {
      clearOfficePreview()
      const result = await options.issueOfficeUrl(entry.id, mode)
      officeSrc.value = result.url
      officeName.value = entry.name || options.t('preview.officeTitle')
      officeOpen.value = true
    } catch (error) {
      options.message.error(
        options.t('fileExplorer.toasts.previewFailedTitle'),
        error instanceof Error
          ? error.message
          : options.t('fileExplorer.toasts.previewFailedMessage'),
      )
    }
  }

  const openPreview = async (entry: DiskEntry) => {
    if (entry.is_dir) {
      options.message.warning(options.t('fileExplorer.toasts.folderNoPreview'))
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
      await options.openTextPreview(entry)
      return
    }
    if (isOfficeEntry(entry)) {
      await openOfficePreview(entry, 'view')
      return
    }
    options.message.warning(options.t('fileExplorer.toasts.fileNoPreview'))
  }

  const openOfficeEdit = async (entry: DiskEntry) => {
    await openOfficePreview(entry, 'edit')
  }

  const handlePreviewChange = async (index: number) => {
    const sessionId = previewSessionId.value
    await ensurePreview(index, sessionId)
    await Promise.all([ensurePreview(index - 1, sessionId), ensurePreview(index + 1, sessionId)])
  }

  const clearAllPreviews = () => {
    clearPreview()
    clearPdfPreview()
    clearVideoPreview()
    clearOfficePreview()
  }

  return {
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
    officeOpen,
    officeSrc,
    officeName,
    openPreview,
    openOfficeEdit,
    handlePreviewChange,
    clearPreview,
    clearPdfPreview,
    clearVideoPreview,
    clearOfficePreview,
    clearAllPreviews,
  }
}

