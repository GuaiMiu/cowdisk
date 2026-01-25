import { ref } from 'vue'
import { useUploadsStore } from '@/stores/uploads'
import { initChunkUpload, uploadChunk, completeChunkUpload, uploadFiles } from '@/api/modules/userDisk'
import { useToastStore } from '@/stores/toast'
import { joinPath, toRelativePath } from '@/utils/path'

const CHUNK_SIZE = 5 * 1024 * 1024
const CHUNK_THRESHOLD = 10 * 1024 * 1024
const MAX_CONCURRENT_UPLOADS = 3

const sharedRunning = ref(false)
const sharedAbortMap = new Map<string, AbortController>()

export const useUploader = () => {
  const uploadsStore = useUploadsStore()
  const toast = useToastStore()
  const running = sharedRunning
  const abortMap = sharedAbortMap

  const enqueue = (files: File[], path: string) => {
    const items = uploadsStore.enqueue(files, path)
    void processQueue()
    return items
  }

  const cancel = (id: string) => {
    const controller = abortMap.get(id)
    if (controller) {
      controller.abort()
    }
    uploadsStore.update(id, { status: 'cancelled', error: '已取消' })
  }

  const retry = (id: string) => {
    uploadsStore.update(id, { status: 'queued', progress: 0, error: undefined })
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
          const next = uploadsStore.items.find((item) => item.status === 'queued')
          if (!next) {
            break
          }
          const task = uploadItem(next.id).finally(() => {
            active.delete(task)
          })
          active.add(task)
        }
        if (active.size === 0) {
          const hasQueued = uploadsStore.items.some((item) => item.status === 'queued')
          if (!hasQueued) {
            break
          }
        }
        if (active.size > 0) {
          await Promise.race(active)
        }
      }
    } finally {
      running.value = false
    }
  }

  const uploadItem = async (id: string) => {
    const item = uploadsStore.items.find((entry) => entry.id === id)
    if (!item) {
      return
    }
    uploadsStore.update(id, { status: 'uploading', progress: 0, error: undefined })
    const controller = new AbortController()
    abortMap.set(id, controller)
    try {
      if (item.file.size >= CHUNK_THRESHOLD) {
        await uploadChunked(item, controller.signal)
      } else {
        await uploadSingle(item, controller.signal)
      }
      uploadsStore.update(id, { status: 'success', progress: 100 })
    } catch (error) {
      if (controller.signal.aborted) {
        uploadsStore.update(id, { status: 'cancelled', error: '已取消' })
      } else {
        uploadsStore.update(id, {
          status: 'error',
          error: error instanceof Error ? error.message : '上传失败',
        })
      }
    } finally {
      abortMap.delete(id)
    }
  }

  const uploadSingle = async (item: typeof uploadsStore.items[number], signal: AbortSignal) => {
    const filename = getRelativeFilename(item.file)
    let lastTick = 0
    let lastProgress = 0
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
          if (progress === lastProgress) {
            return
          }
          if (progress < 100 && now - lastTick < 120) {
            return
          }
          lastTick = now
          lastProgress = progress
          uploadsStore.update(item.id, { progress })
        },
      },
    )
  }

  const uploadChunked = async (item: typeof uploadsStore.items[number], signal: AbortSignal) => {
    const totalChunks = Math.ceil(item.file.size / CHUNK_SIZE)
    const filename = getRelativeFilename(item.file)
    const init = await initChunkUpload({
      path: toRelativePath(item.path),
      filename: filename || item.file.name,
      size: item.file.size,
      total_chunks: totalChunks,
      overwrite: false,
    })
    const uploadId = init.upload_id
    for (let index = 0; index < totalChunks; index += 1) {
      if (signal.aborted) {
        throw new Error('取消上传')
      }
      const start = index * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, item.file.size)
      const chunk = item.file.slice(start, end)
      await uploadChunk({ upload_id: uploadId, index, chunk })
      const progress = Math.round(((index + 1) / totalChunks) * 100)
      uploadsStore.update(item.id, { progress })
    }
    await completeChunkUpload({ upload_id: uploadId })
  }

  const createFolderTarget = (base: string, name: string) => joinPath(base || '/', name)

  const notifyQueue = () => {
    const queued = uploadsStore.items.filter((item) => item.status === 'queued').length
    if (queued > 0) {
      toast.info('上传队列已更新', `待上传文件 ${queued} 个`)
    }
  }

  return {
    running,
    enqueue,
    cancel,
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
