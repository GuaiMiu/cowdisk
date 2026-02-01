import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUploadsStore } from '@/stores/uploads'
import {
  initChunkUpload,
  uploadChunk,
  completeChunkUpload,
  uploadFiles,
  cancelChunkUpload,
} from '@/api/modules/userDisk'
import { useMessage } from '@/stores/message'
import { joinPath, toRelativePath } from '@/utils/path'

const CHUNK_SIZE = 5 * 1024 * 1024
const CHUNK_THRESHOLD = 10 * 1024 * 1024
const MAX_CONCURRENT_UPLOADS = Math.min(
  6,
  Math.max(3, Number(import.meta.env.VITE_UPLOAD_CONCURRENCY ?? 4)),
)

const sharedRunning = ref(false)
const sharedAbortMap = new Map<string, AbortController>()

export const useUploader = () => {
  const { t } = useI18n({ useScope: 'global' })
  const uploadsStore = useUploadsStore()
  const message = useMessage()
  const running = sharedRunning
  const abortMap = sharedAbortMap

  const enqueue = async (files: File[], path: string) => {
    const items =
      files.length > 200
        ? await uploadsStore.enqueueBatched(files, path, 200)
        : uploadsStore.enqueue(files, path)
    void processQueue()
    return items
  }

  const cancel = (id: string) => {
    const controller = abortMap.get(id)
    if (controller) {
      controller.abort()
    }
    uploadsStore.update(id, { status: 'cancelled', error: '已取消', speed: 0 })
    const item = uploadsStore.items.find((entry) => entry.id === id)
    if (item?.uploadId) {
      void cancelChunkUpload({ upload_id: item.uploadId })
    }
    uploadsStore.resetChunkState(id)
  }

  const pause = (id: string) => {
    const controller = abortMap.get(id)
    if (controller) {
      controller.abort()
    }
    uploadsStore.update(id, { status: 'paused', error: undefined, speed: 0 })
  }

  const resume = (id: string) => {
    uploadsStore.update(id, { status: 'queued', error: undefined, speed: 0 })
    void processQueue()
  }

  const retry = (id: string) => {
    uploadsStore.update(id, { status: 'queued', progress: 0, error: undefined, speed: 0 })
    void processQueue()
  }

  const processQueue = async () => {
    if (running.value) {
      return
    }
    running.value = true
    try {
      const active = new Set<Promise<void>>()
      while (true) {
        while (active.size < MAX_CONCURRENT_UPLOADS) {
          const next = uploadsStore.takeNextQueued()
          if (!next) {
            break
          }
          const task = uploadItem(next).finally(() => {
            active.delete(task)
          })
          active.add(task)
        }
        if (active.size === 0) {
          if (!uploadsStore.hasQueued()) {
            break
          }
          // 避免空转死循环，主动让出事件循环
          await yieldToMain()
        }
        if (active.size > 0) {
          await Promise.race(active)
        }
      }
    } finally {
      running.value = false
    }
  }

  const uploadItem = async (item: (typeof uploadsStore.items)[number]) => {
    uploadsStore.update(item.id, { status: 'uploading', progress: 0, error: undefined, speed: 0 })
    const controller = new AbortController()
    abortMap.set(item.id, controller)
    try {
      if (item.file.size >= CHUNK_THRESHOLD) {
        await uploadChunked(item, controller.signal)
      } else {
        uploadsStore.resetChunkState(item.id)
        await uploadSingle(item, controller.signal)
      }
      uploadsStore.update(item.id, { status: 'success', progress: 100, speed: 0 })
    } catch (error) {
      if (controller.signal.aborted) {
        if (item.status === 'paused') {
          uploadsStore.update(item.id, { speed: 0 })
        } else {
          uploadsStore.update(item.id, { status: 'cancelled', error: '已取消', speed: 0 })
        }
      } else {
        uploadsStore.update(item.id, {
          status: 'error',
          error: error instanceof Error ? error.message : '上传失败',
          speed: 0,
        })
      }
    } finally {
      abortMap.delete(item.id)
    }
  }

  const uploadSingle = async (item: (typeof uploadsStore.items)[number], signal: AbortSignal) => {
    const filename = getRelativeFilename(item.file)
    let lastTick = 0
    let lastProgress = 0
    let lastLoaded = 0
    await uploadFiles(
      {
        items: [{ file: item.file, filename }],
        path: toRelativePath(item.path),
        overwrite: false,
      },
      {
        signal,
        onUploadProgress: (event) => {
          if (!event.total) {
            return
          }
          const progress = Math.round((event.loaded / event.total) * 100)
          const now = Date.now()
          const deltaBytes = event.loaded - lastLoaded
          const deltaTime = now - lastTick
          const speed = deltaTime > 0 ? Math.max(0, Math.round(deltaBytes / (deltaTime / 1000))) : 0
          if (progress === lastProgress) {
            return
          }
          if (progress < 100 && now - lastTick < 120) {
            return
          }
          lastTick = now
          lastProgress = progress
          lastLoaded = event.loaded
          uploadsStore.update(item.id, { progress, speed })
        },
      },
    )
  }

  const uploadChunked = async (item: (typeof uploadsStore.items)[number], signal: AbortSignal) => {
    if (signal.aborted) {
      throw new Error('取消上传')
    }
    const totalChunks = Math.ceil(item.file.size / CHUNK_SIZE)
    const filename = getRelativeFilename(item.file)
    let uploadId = item.uploadId
    if (!uploadId || item.totalChunks !== totalChunks) {
      const init = await initChunkUpload(
        {
          path: toRelativePath(item.path),
          filename: filename || item.file.name,
          size: item.file.size,
          total_chunks: totalChunks,
          overwrite: false,
        },
        { signal },
      )
      uploadId = init.upload_id
      uploadsStore.update(item.id, {
        uploadId,
        totalChunks,
        uploadedChunks: [],
      })
    }
    const uploadedSet = new Set(item.uploadedChunks ?? [])
    if (uploadedSet.size > 0) {
      const progress = Math.round((uploadedSet.size / totalChunks) * 100)
      uploadsStore.update(item.id, { progress })
    }
    for (let index = 0; index < totalChunks; index += 1) {
      if (signal.aborted) {
        throw new Error('取消上传')
      }
      if (uploadedSet.has(index)) {
        continue
      }
      const start = index * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, item.file.size)
      const chunk = item.file.slice(start, end)
      const startedAt = Date.now()
      await uploadChunk({ upload_id: uploadId, index, chunk }, { signal })
      const elapsed = Math.max(1, Date.now() - startedAt)
      const speed = Math.round(chunk.size / (elapsed / 1000))
      uploadsStore.markChunkUploaded(item.id, index)
      uploadedSet.add(index)
      const progress = Math.round((uploadedSet.size / totalChunks) * 100)
      uploadsStore.update(item.id, { progress, speed })
    }
    await completeChunkUpload({ upload_id: uploadId }, { signal })
    uploadsStore.resetChunkState(item.id)
  }

  const createFolderTarget = (base: string, name: string) => joinPath(base || '/', name)

  const notifyQueue = () => {
    const queued = uploadsStore.items.reduce(
      (count, item) => count + (item.status === 'queued' ? 1 : 0),
      0,
    )
    if (queued > 0) {
      message.info(
        t('uploadQueue.queueUpdatedTitle'),
        t('uploadQueue.queueUpdatedMessage', { count: queued }),
      )
    }
  }

  return {
    running,
    enqueue,
    cancel,
    pause,
    resume,
    retry,
    processQueue,
    createFolderTarget,
    notifyQueue,
  }
}

const getRelativeFilename = (file: File) => {
  const relative = (file as File & { webkitRelativePath?: string }).webkitRelativePath
  if (relative) {
    return relative.replace(/^\/+/, '')
  }
  return file.name
}

const yieldToMain = () =>
  new Promise<void>((resolve) => {
    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      ;(window as Window & { requestIdleCallback: (cb: () => void) => number }).requestIdleCallback(
        () => resolve(),
      )
      return
    }
    setTimeout(resolve, 0)
  })
