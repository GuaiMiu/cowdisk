<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { previewThumbnail } from '@/api/modules/userDisk'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { getFileKind } from '@/utils/fileType'

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
const iconSize = computed(() => props.size)
const requestSize = computed(() => {
  const base = Number(iconSize.value || 16)
  return Math.max(48, Math.min(512, Math.ceil(base * 3)))
})
const isImageEntry = computed(() => getFileKind(props.name, props.isDir) === 'image' && !props.isDir)
let observer: IntersectionObserver | null = null
let requestId = 0

const revokeThumb = () => {
  if (thumbUrl.value) {
    URL.revokeObjectURL(thumbUrl.value)
    thumbUrl.value = ''
  }
}

const stopObserve = () => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
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
  stopObserve()
  if (!isImageEntry.value || thumbUrl.value || failed.value || !hostRef.value) {
    return
  }
  if (typeof window === 'undefined' || typeof window.IntersectionObserver === 'undefined') {
    void loadThumb()
    return
  }
  observer = new window.IntersectionObserver((entries) => {
    const visible = entries.some((entry) => entry.isIntersecting)
    if (!visible) {
      return
    }
    stopObserve()
    void loadThumb()
  })
  observer.observe(hostRef.value)
}

watch(
  () => [props.fileId, props.name, props.isDir] as const,
  () => {
    requestId += 1
    failed.value = false
    loading.value = false
    revokeThumb()
    void nextTick(() => observeOrLoad())
  },
)

onMounted(() => {
  observeOrLoad()
})

onBeforeUnmount(() => {
  requestId += 1
  stopObserve()
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
