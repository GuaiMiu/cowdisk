import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUploadsStore } from '@/stores/uploads'
import {
  initChunkUpload,
  uploadChunk,
  completeChunkUpload,
  uploadFiles,
  cancelChunkUpload,
  getUploadStatus,
  getUploadPolicy,
  listDir,
  mkdir,
} from '@/api/modules/userDisk'
import { useMessage } from '@/stores/message'
import type { DiskUploadPolicyOut } from '@/types/disk'

const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024
const MAX_CONCURRENT_UPLOADS = Math.min(
  6,
  Math.max(3, Number(import.meta.env.VITE_UPLOAD_CONCURRENCY ?? 4)),
)

const sharedRunning = ref(false)
const sharedAbortMap = new Map<string, AbortController>()
let uploadPolicyCache: DiskUploadPolicyOut | null = null
let uploadPolicyInFlight: Promise<DiskUploadPolicyOut | null> | null = null

export const useUploader = () => {
  const { t } = useI18n({ useScope: 'global' })
  const uploadsStore = useUploadsStore()
  const message = useMessage()
  const running = sharedRunning
  const abortMap = sharedAbortMap
  const folderIdCache = new Map<string, number>()
  const folderIdInflight = new Map<string, Promise<number>>()

  const enqueue = async (files: File[], path: string, parent_id: number | null) => {
    const items =
      files.length > 200
        ? await uploadsStore.enqueueBatched(files, path, parent_id, 200)
        : uploadsStore.enqueue(files, path, parent_id)
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
      void cancelChunkUpload(item.uploadId)
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
      const policy = await ensureUploadPolicy(controller.signal)
      const thresholdMb = Number(policy?.chunk_upload_threshold_mb ?? 10)
      const chunkThresholdBytes = Math.max(1, thresholdMb) * 1024 * 1024
      if (item.file.size >= chunkThresholdBytes) {
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
    const target = await resolveTarget(item, filename)
    let lastTick = 0
    let lastProgress = 0
    let lastLoaded = 0
    await uploadFiles(
      {
        items: [{ file: item.file, filename: target.filename }],
        parent_id: target.parent_id,
        name: target.filename,
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
    const totalChunks = Math.ceil(item.file.size / DEFAULT_CHUNK_SIZE)
    const filename = getRelativeFilename(item.file)
    const target = await resolveTarget(item, filename)
    let uploadId = item.uploadId
    let partSize = DEFAULT_CHUNK_SIZE
    let totalParts = totalChunks
    let maxParallelChunks = 1
    let resumableEnabled = true
    if (!uploadId || item.totalChunks !== totalChunks) {
      const init = await initChunkUpload(
        {
          parent_id: target.parent_id,
          name: target.filename || item.file.name,
          size: item.file.size,
          mime_type: item.file.type || null,
          part_size: DEFAULT_CHUNK_SIZE,
          overwrite: false,
        },
        { signal },
      )
      uploadId = init.upload_id
      partSize = init.part_size || DEFAULT_CHUNK_SIZE
      totalParts = init.total_parts || totalChunks
      maxParallelChunks = Math.max(1, Math.min(Number(init.upload_config?.max_parallel_chunks || 1), 8))
      resumableEnabled = init.upload_config?.enable_resumable !== false
      uploadsStore.update(item.id, {
        uploadId,
        totalChunks: totalParts,
        uploadedChunks: [],
      })
    }
    const uploadedSet = new Set(item.uploadedChunks ?? [])
    if (resumableEnabled && uploadId && uploadedSet.size === 0) {
      try {
        const status = await getUploadStatus(uploadId, { signal })
        const existing = status.uploaded_parts || []
        existing.forEach((part) => uploadedSet.add(part))
        uploadsStore.update(item.id, {
          totalChunks: status.total_parts || totalParts,
          uploadedChunks: existing,
        })
      } catch {
        // ignore status errors; treat as new session
      }
    }
    if (uploadedSet.size > 0) {
      const progress = Math.round((uploadedSet.size / totalParts) * 100)
      uploadsStore.update(item.id, { progress })
    }
    const pendingParts: number[] = []
    for (let partNumber = 1; partNumber <= totalParts; partNumber += 1) {
      if (!uploadedSet.has(partNumber)) {
        pendingParts.push(partNumber)
      }
    }
    let cursor = 0
    const uploadOnePart = async () => {
      while (cursor < pendingParts.length) {
        if (signal.aborted) {
          throw new Error('取消上传')
        }
        const index = cursor
        cursor += 1
        const partNumber = pendingParts[index]
        if (partNumber === undefined) {
          return
        }
        const start = (partNumber - 1) * partSize
        const end = Math.min(start + partSize, item.file.size)
        const chunk = item.file.slice(start, end)
        const startedAt = Date.now()
        await uploadChunk({ upload_id: uploadId, part_number: partNumber, chunk }, { signal })
        const elapsed = Math.max(1, Date.now() - startedAt)
        const speed = Math.round(chunk.size / (elapsed / 1000))
        uploadsStore.markChunkUploaded(item.id, partNumber)
        uploadedSet.add(partNumber)
        const progress = Math.round((uploadedSet.size / totalParts) * 100)
        uploadsStore.update(item.id, { progress, speed })
      }
    }
    const workers = Array.from({ length: Math.min(maxParallelChunks, pendingParts.length || 1) }, () =>
      uploadOnePart(),
    )
    await Promise.all(workers)
    await completeChunkUpload(
      uploadId,
      {
        parent_id: target.parent_id,
        name: target.filename || item.file.name,
        overwrite: false,
        mime_type: item.file.type || null,
        total_parts: totalParts,
      },
      { signal },
    )
    uploadsStore.resetChunkState(item.id)
  }

  const resolveFolderId = async (parentId: number | null, name: string) => {
    const key = `${parentId ?? 'root'}:${name}`
    const cached = folderIdCache.get(key)
    if (cached !== undefined) {
      return cached
    }
    const inflight = folderIdInflight.get(key)
    if (inflight) {
      return inflight
    }
    const task = (async () => {
      try {
        const entry = await mkdir({ parent_id: parentId ?? null, name })
        folderIdCache.set(key, entry.id)
        return entry.id
      } catch {
        const list = await listDir(parentId ?? null)
        const found = list.items.find((item) => item.is_dir && item.name === name)
        if (!found) {
          throw new Error(`无法创建目录: ${name}`)
        }
        folderIdCache.set(key, found.id)
        return found.id
      } finally {
        folderIdInflight.delete(key)
      }
    })()
    folderIdInflight.set(key, task)
    return task
  }

  const resolveTarget = async (
    item: (typeof uploadsStore.items)[number],
    filename: string,
  ): Promise<{ parent_id: number | null; filename: string }> => {
    if (!filename.includes('/')) {
      return { parent_id: item.parent_id ?? null, filename }
    }
    const parts = filename.split('/').filter(Boolean)
    const leaf = parts.pop() || item.file.name
    let current = item.parent_id ?? null
    for (const segment of parts) {
      current = await resolveFolderId(current, segment)
    }
    return { parent_id: current, filename: leaf }
  }

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
    notifyQueue,
  }
}

const ensureUploadPolicy = async (signal?: AbortSignal): Promise<DiskUploadPolicyOut | null> => {
  if (uploadPolicyCache) {
    return uploadPolicyCache
  }
  if (uploadPolicyInFlight) {
    return uploadPolicyInFlight
  }
  uploadPolicyInFlight = getUploadPolicy({ signal })
    .then((policy) => {
      uploadPolicyCache = policy
      return policy
    })
    .catch(() => null)
    .finally(() => {
      uploadPolicyInFlight = null
    })
  return uploadPolicyInFlight
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
