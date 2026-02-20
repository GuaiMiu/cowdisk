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
import { i18n } from '@/i18n'
import { AppError } from '@/api/errors'
import type { DiskUploadPolicyOut } from '@/types/disk'

const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024

const sharedRunning = ref(false)
const sharedAbortMap = new Map<string, AbortController>()
const speedMeterMap = new Map<string, UploadSpeedMeter>()
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
    clearSpeedMeter(id)
    uploadsStore.update(id, { status: 'cancelled', error: t('uploadQueue.status.cancelled'), speed: 0 })
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
    clearSpeedMeter(id)
    uploadsStore.update(id, { status: 'paused', error: undefined, speed: 0 })
  }

  const resume = (id: string) => {
    clearSpeedMeter(id)
    uploadsStore.update(id, { status: 'queued', error: undefined, speed: 0 })
    void processQueue()
  }

  const retry = (id: string) => {
    clearSpeedMeter(id)
    uploadsStore.update(id, { status: 'queued', progress: 0, error: undefined, speed: 0 })
    void processQueue()
  }

  const processQueue = async () => {
    if (running.value) {
      return
    }
    running.value = true
    try {
      const queueConcurrency = await resolveQueueConcurrency()
      const active = new Set<Promise<void>>()
      while (true) {
        while (active.size < queueConcurrency) {
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
    clearSpeedMeter(item.id)
    uploadsStore.update(item.id, { status: 'uploading', progress: 0, error: undefined, speed: 0 })
    const controller = new AbortController()
    abortMap.set(item.id, controller)
    try {
      const policy = await ensureUploadPolicy(controller.signal)
      const thresholdMb = Number(policy?.chunk_upload_threshold_mb ?? 10)
      const chunkThresholdBytes = Math.max(1, thresholdMb) * 1024 * 1024
      if (item.file.size >= chunkThresholdBytes) {
        await uploadChunked(item, controller.signal, policy)
      } else {
        uploadsStore.resetChunkState(item.id)
        await uploadSingle(item, controller.signal)
      }
      flushUploadStats(uploadsStore, item.id, 100, true)
      uploadsStore.update(item.id, { status: 'success', progress: 100, speed: 0 })
    } catch (error) {
      if (controller.signal.aborted) {
        if (item.status === 'paused') {
          uploadsStore.update(item.id, { speed: 0 })
        } else {
          uploadsStore.update(item.id, { status: 'cancelled', error: t('uploadQueue.status.cancelled'), speed: 0 })
        }
      } else {
        uploadsStore.update(item.id, {
          status: 'error',
          error: error instanceof Error ? error.message : t('uploadQueue.status.error'),
          speed: 0,
        })
      }
    } finally {
      clearSpeedMeter(item.id)
      abortMap.delete(item.id)
    }
  }

  const uploadSingle = async (item: (typeof uploadsStore.items)[number], signal: AbortSignal) => {
    const filename = getRelativeFilename(item.file)
    const target = await resolveTarget(item, filename)
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
          const meter = getSpeedMeter(item.id)
          const now = Date.now()
          const progress = Math.round((event.loaded / event.total) * 100)
          const deltaBytes = Math.max(0, event.loaded - lastLoaded)
          if (deltaBytes > 0) {
            meter.record(deltaBytes, now)
          }
          if (progress === lastProgress && !shouldFlushSpeed(item.id, now, false)) {
            lastLoaded = event.loaded
            return
          }
          lastProgress = progress
          lastLoaded = event.loaded
          flushUploadStats(uploadsStore, item.id, progress, progress >= 100)
        },
      },
    )
  }

  const uploadChunked = async (
    item: (typeof uploadsStore.items)[number],
    signal: AbortSignal,
    policy: DiskUploadPolicyOut | null,
  ) => {
    if (signal.aborted) {
      throw new Error(t('uploadQueue.status.cancelled'))
    }
    const totalChunks = Math.ceil(item.file.size / DEFAULT_CHUNK_SIZE)
    const filename = getRelativeFilename(item.file)
    const target = await resolveTarget(item, filename)
    let uploadId = item.uploadId
    let partSize = DEFAULT_CHUNK_SIZE
    let totalParts = totalChunks
    let maxParallelChunks = 1
    let resumableEnabled = true
    let effectivePolicy = policy
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
      effectivePolicy = init.upload_config || policy
      const policyParallel = Number(init.upload_config?.max_parallel_chunks || 1)
      maxParallelChunks = Math.max(1, policyParallel)
      resumableEnabled = init.upload_config?.enable_resumable !== false
      uploadsStore.update(item.id, {
        uploadId,
        totalChunks: totalParts,
        uploadedChunks: [],
      })
    }
    const retryPolicy = normalizeRetryPolicy(effectivePolicy)
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
      flushUploadStats(uploadsStore, item.id, progress, true)
    }
    const pendingParts: number[] = []
    for (let partNumber = 1; partNumber <= totalParts; partNumber += 1) {
      if (!uploadedSet.has(partNumber)) {
        pendingParts.push(partNumber)
      }
    }
    let cursor = 0
    let fatalError: unknown = null
    const uploadOnePart = async () => {
      while (cursor < pendingParts.length && !fatalError) {
        if (signal.aborted) {
          throw new Error(t('uploadQueue.status.cancelled'))
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
        try {
          await uploadChunkWithRetry(
            { upload_id: uploadId, part_number: partNumber, chunk },
            { signal },
            retryPolicy,
          )
          const now = Date.now()
          getSpeedMeter(item.id).record(chunk.size, now)
          uploadsStore.markChunkUploaded(item.id, partNumber)
          uploadedSet.add(partNumber)
          const progress = Math.round((uploadedSet.size / totalParts) * 100)
          flushUploadStats(uploadsStore, item.id, progress, progress >= 100)
        } catch (error) {
          fatalError = error
          return
        }
      }
    }
    const workers = Array.from({ length: Math.min(maxParallelChunks, pendingParts.length || 1) }, () =>
      uploadOnePart(),
    )
    await Promise.all(workers)
    if (fatalError) {
      throw fatalError
    }
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
          throw new Error(t('uploadQueue.createFolderFailed', { name }))
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
    const pending = uploadsStore.items.reduce(
      (count, item) =>
        count + (item.status === 'queued' || item.status === 'uploading' || item.status === 'paused' ? 1 : 0),
      0,
    )
    if (pending > 0) {
      message.info(
        t('uploadQueue.queueUpdatedTitle'),
        t('uploadQueue.queueUpdatedMessage', { count: pending }),
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

const shouldFlushSpeed = (id: string, now: number, force: boolean) => {
  if (force) {
    return true
  }
  const meter = speedMeterMap.get(id)
  if (!meter) {
    return true
  }
  return now - meter.lastFlushAt >= 1000
}

const flushUploadStats = (
  uploadsStore: ReturnType<typeof useUploadsStore>,
  id: string,
  progress: number,
  force = false,
) => {
  const now = Date.now()
  if (!shouldFlushSpeed(id, now, force)) {
    return
  }
  const meter = getSpeedMeter(id)
  meter.lastFlushAt = now
  uploadsStore.update(id, { progress, speed: Math.round(meter.getRate(now)) })
}

const getSpeedMeter = (id: string) => {
  const existing = speedMeterMap.get(id)
  if (existing) {
    return existing
  }
  const created = new UploadSpeedMeter(5000, 0.25)
  speedMeterMap.set(id, created)
  return created
}

const clearSpeedMeter = (id: string) => {
  speedMeterMap.delete(id)
}

class UploadSpeedMeter {
  private samples: Array<{ at: number; bytes: number }> = []
  private smoothedRate = 0
  private readonly windowMs: number
  private readonly emaAlpha: number
  lastFlushAt = 0

  constructor(windowMs: number, emaAlpha: number) {
    this.windowMs = windowMs
    this.emaAlpha = emaAlpha
  }

  record(bytes: number, at: number) {
    if (bytes <= 0) {
      return
    }
    this.samples.push({ at, bytes })
    this.prune(at)
    const rawRate = this.computeRawRate(at)
    if (rawRate <= 0) {
      return
    }
    this.smoothedRate =
      this.smoothedRate > 0
        ? this.emaAlpha * rawRate + (1 - this.emaAlpha) * this.smoothedRate
        : rawRate
  }

  getRate(at: number) {
    this.prune(at)
    if (this.samples.length === 0) {
      return 0
    }
    return this.smoothedRate > 0 ? this.smoothedRate : this.computeRawRate(at)
  }

  private prune(at: number) {
    const minTs = at - this.windowMs
    while (this.samples.length > 0 && this.samples[0]!.at < minTs) {
      this.samples.shift()
    }
    if (this.samples.length === 0) {
      this.smoothedRate = 0
    }
  }

  private computeRawRate(at: number) {
    if (this.samples.length === 0) {
      return 0
    }
    let totalBytes = 0
    for (const sample of this.samples) {
      totalBytes += sample.bytes
    }
    const firstAt = this.samples[0]!.at
    const durationMs = Math.max(1000, Math.min(this.windowMs, at - firstAt))
    return totalBytes / (durationMs / 1000)
  }
}

const uploadChunkWithRetry = async (
  payload: { upload_id: string; part_number: number; chunk: Blob },
  options: { signal: AbortSignal },
  retryPolicy: { maxRetries: number; baseDelayMs: number; maxDelayMs: number },
) => {
  let attempt = 0
  while (true) {
    try {
      await uploadChunk(payload, options)
      return
    } catch (error) {
      if (options.signal.aborted) {
        throw error
      }
      if (!isRetriableUploadError(error) || attempt >= retryPolicy.maxRetries) {
        throw error
      }
      const delay = computeRetryDelay(attempt, retryPolicy)
      await sleep(delay, options.signal)
      attempt += 1
    }
  }
}

const isRetriableUploadError = (error: unknown) => {
  if (error instanceof AppError) {
    return (
      error.transient === true ||
      error.code === 408 ||
      error.code === 429 ||
      (typeof error.code === 'number' && error.code >= 500)
    )
  }
  if (!(error instanceof Error)) {
    return false
  }
  return /network|timeout|timed out/i.test(error.message)
}

const computeRetryDelay = (
  attempt: number,
  retryPolicy: { maxRetries: number; baseDelayMs: number; maxDelayMs: number },
) => {
  const base = retryPolicy.baseDelayMs * 2 ** attempt
  const jitter = Math.floor(Math.random() * 250)
  return Math.min(base + jitter, retryPolicy.maxDelayMs)
}

const normalizeRetryPolicy = (policy: DiskUploadPolicyOut | null) => {
  const maxRetries = Math.max(0, Number(policy?.chunk_retry_max ?? 3))
  const baseDelayMs = Math.max(100, Number(policy?.chunk_retry_base_ms ?? 600))
  const maxDelayMs = Math.max(baseDelayMs, Number(policy?.chunk_retry_max_ms ?? 6000))
  return { maxRetries, baseDelayMs, maxDelayMs }
}

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => {
      cleanup()
      resolve()
    }, ms)
    const onAbort = () => {
      cleanup()
      reject(new Error(i18n.global.t('uploadQueue.status.cancelled')))
    }
    const cleanup = () => {
      clearTimeout(timer)
      signal.removeEventListener('abort', onAbort)
    }
    signal.addEventListener('abort', onAbort, { once: true })
  })

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

const resolveQueueConcurrency = async () => {
  const policy = await ensureUploadPolicy()
  return Math.max(1, Number(policy?.max_concurrency_per_user || 1))
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

