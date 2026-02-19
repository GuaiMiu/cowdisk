<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { previewThumbnail } from '@/api/modules/userDisk'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { getFileKind } from '@/utils/fileType'

const callbacks = new WeakMap<Element, () => void>()
let sharedObserver: IntersectionObserver | null = null

const getObserver = () => {
  if (typeof window === 'undefined' || typeof window.IntersectionObserver === 'undefined') {
    return null
  }
  if (!sharedObserver) {
    sharedObserver = new window.IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) {
          continue
        }
        const callback = callbacks.get(entry.target)
        if (!callback) {
          continue
        }
        callbacks.delete(entry.target)
        sharedObserver?.unobserve(entry.target)
        callback()
      }
    })
  }
  return sharedObserver
}

const observeVisible = (element: Element, callback: () => void) => {
  const observer = getObserver()
  if (!observer) {
    callback()
    return
  }
  callbacks.set(element, callback)
  observer.observe(element)
}

const unobserveVisible = (element: Element | null) => {
  if (!element || !sharedObserver) {
    return
  }
  callbacks.delete(element)
  sharedObserver.unobserve(element)
}

const props = withDefaults(
  defineProps<{
    fileId?: number
    name?: string
    isDir?: boolean
    size?: number
  }>(),
  {
    fileId: undefined,
    name: '',
    isDir: false,
    size: 16,
  },
)

const hostRef = ref<HTMLElement | null>(null)
const thumbUrl = ref('')
const loading = ref(false)
const failed = ref(false)
let requestId = 0
const iconSize = computed(() => props.size)
const requestSize = computed(() => {
  const base = Number(iconSize.value || 16)
  return Math.max(48, Math.min(512, Math.ceil(base * 3)))
})
const isImageEntry = computed(() => getFileKind(props.name, props.isDir) === 'image' && !props.isDir)

const revokeThumb = () => {
  if (!thumbUrl.value) {
    return
  }
  URL.revokeObjectURL(thumbUrl.value)
  thumbUrl.value = ''
}

const loadThumb = async () => {
  if (!isImageEntry.value || !props.fileId || loading.value || thumbUrl.value || failed.value) {
    return
  }
  const currentId = ++requestId
  loading.value = true
  try {
    const result = await previewThumbnail(props.fileId, {
      w: requestSize.value,
      h: requestSize.value,
      fit: 'cover',
      fmt: 'webp',
      quality: 82,
    })
    if (currentId !== requestId) {
      return
    }
    const type = result.contentType || result.blob.type || ''
    if (type && !type.startsWith('image/')) {
      failed.value = true
      return
    }
    thumbUrl.value = URL.createObjectURL(result.blob)
  } catch {
    failed.value = true
  } finally {
    if (currentId === requestId) {
      loading.value = false
    }
  }
}

const observeOrLoad = () => {
  unobserveVisible(hostRef.value)
  if (!isImageEntry.value || thumbUrl.value || failed.value || !hostRef.value) {
    return
  }
  observeVisible(hostRef.value, () => {
    loadThumb()
  })
}

const onThumbError = () => {
  failed.value = true
  revokeThumb()
}

watch(
  () => [props.fileId, props.name, props.isDir] as const,
  () => {
    requestId += 1
    loading.value = false
    failed.value = false
    revokeThumb()
    void nextTick(() => observeOrLoad())
  },
)

onMounted(() => {
  observeOrLoad()
})

onBeforeUnmount(() => {
  requestId += 1
  loading.value = false
  unobserveVisible(hostRef.value)
  revokeThumb()
})
</script>

<template>
  <span ref="hostRef" class="thumb-icon" :style="{ '--thumb-size': `${iconSize}px` }">
    <img
      v-if="isImageEntry && thumbUrl"
      class="thumb-icon__image"
      :src="thumbUrl"
      :alt="name || 'image'"
      loading="lazy"
      decoding="async"
      draggable="false"
      @error="onThumbError"
    />
    <FileTypeIcon v-else :name="name" :is-dir="isDir" :size="iconSize" />
  </span>
</template>

<style scoped>
.thumb-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.thumb-icon__image {
  width: var(--thumb-size);
  height: var(--thumb-size);
  border-radius: 0;
  object-fit: cover;
  border: none;
  background: var(--color-surface-2);
}
</style>
