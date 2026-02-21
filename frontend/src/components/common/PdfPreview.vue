<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, ExternalLink, Maximize, Minimize, X } from 'lucide-vue-next'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'

const props = withDefaults(
  defineProps<{
    open: boolean
    src: string | null
    name?: string
  }>(),
  {
    name: '',
  },
)

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'close'): void
}>()

const { t } = useI18n({ useScope: 'global' })
const isMobile = ref(false)
const previewRef = ref<HTMLDivElement | null>(null)
const canvasHost = ref<HTMLDivElement | null>(null)
const canvasViewport = ref<HTMLDivElement | null>(null)
const pdfjsLoading = ref(false)
const pdfjsError = ref('')
const fullscreenActive = ref(false)
const usePdfjs = computed(() => isMobile.value)
const {
  scrollRef,
  onScroll,
  onMouseEnter,
  onMouseLeave,
  thumbHeight,
  thumbTop,
  visible,
  isScrollable,
  updateMetrics,
  onThumbMouseDown,
} = useOverlayScrollbar()

let mobileQuery: MediaQueryList | null = null
let renderToken = 0
let activeDoc: { destroy: () => Promise<void> } | null = null

const close = () => {
  if (document.fullscreenElement) {
    void document.exitFullscreen()
  }
  emit('update:open', false)
  emit('close')
}

const downloadCurrent = () => {
  if (!props.src) {
    return
  }
  const link = document.createElement('a')
  link.href = props.src
  link.download = props.name || 'document.pdf'
  link.click()
}

const openInNewTab = () => {
  if (!props.src) {
    return
  }
  window.open(props.src, '_blank', 'noopener')
}

const onKeyDown = (event: KeyboardEvent) => {
  if (!props.open) {
    return
  }
  if (event.key === 'Escape') {
    close()
  }
}

const toggleFullscreen = async () => {
  const target = previewRef.value
  if (!target) {
    return
  }
  if (!document.fullscreenElement) {
    await target.requestFullscreen()
    return
  }
  await document.exitFullscreen()
}

const onFullscreenChange = () => {
  fullscreenActive.value = !!document.fullscreenElement
}

const updateViewport = () => {
  isMobile.value = mobileQuery?.matches ?? window.innerWidth <= 768
}

const clearPdfjsView = () => {
  renderToken += 1
  pdfjsLoading.value = false
  pdfjsError.value = ''
  if (canvasHost.value) {
    canvasHost.value.innerHTML = ''
  }
  updateMetrics()
  if (activeDoc) {
    void activeDoc.destroy()
    activeDoc = null
  }
}

const renderPdfByPdfjs = async () => {
  if (!props.open || !props.src || !usePdfjs.value) {
    clearPdfjsView()
    return
  }

  const token = ++renderToken
  pdfjsLoading.value = true
  pdfjsError.value = ''

  await nextTick()
  const host = canvasHost.value
  if (!host) {
    if (token === renderToken) {
      pdfjsLoading.value = false
    }
    return
  }
  host.innerHTML = ''
  updateMetrics()
  if (activeDoc) {
    void activeDoc.destroy()
    activeDoc = null
  }

  try {
    const [pdfjs, workerModule] = await Promise.all([
      import('pdfjs-dist'),
      import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
    ])
    if (token !== renderToken) {
      return
    }
    pdfjs.GlobalWorkerOptions.workerSrc = workerModule.default

    const loadingTask = pdfjs.getDocument({ url: props.src })
    const doc = await loadingTask.promise
    if (token !== renderToken) {
      await doc.destroy()
      return
    }
    activeDoc = doc

    const containerWidth = host.clientWidth || Math.max(320, window.innerWidth - 40)
    const dpr = window.devicePixelRatio || 1

    for (let pageNumber = 1; pageNumber <= doc.numPages; pageNumber += 1) {
      if (token !== renderToken) {
        break
      }
      const page = await doc.getPage(pageNumber)
      const baseViewport = page.getViewport({ scale: 1 })
      const pageScale = containerWidth / baseViewport.width
      const viewport = page.getViewport({ scale: pageScale })
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')
      if (!context) {
        continue
      }
      canvas.className = 'pdf-preview__page-canvas'
      canvas.width = Math.floor(viewport.width * dpr)
      canvas.height = Math.floor(viewport.height * dpr)
      canvas.style.width = `${Math.floor(viewport.width)}px`
      canvas.style.height = `${Math.floor(viewport.height)}px`
      host.appendChild(canvas)

      await page
        .render({
          canvas,
          canvasContext: context,
          viewport,
          transform: dpr === 1 ? undefined : [dpr, 0, 0, dpr, 0, 0],
        })
        .promise
      updateMetrics()
    }
    if (token !== renderToken) {
      return
    }
    pdfjsLoading.value = false
  } catch {
    if (token !== renderToken) {
      return
    }
    pdfjsLoading.value = false
    pdfjsError.value = t('fileExplorer.toasts.previewFailedMessage')
  }
}

watch(
  [() => props.open, () => props.src, usePdfjs],
  () => {
    void renderPdfByPdfjs()
  },
  { immediate: true },
)

watch(
  () => props.open,
  (open) => {
    if (!open && document.fullscreenElement) {
      void document.exitFullscreen()
    }
  },
)

watch(
  canvasViewport,
  (node) => {
    scrollRef.value = node
    updateMetrics()
  },
  { immediate: true },
)

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  mobileQuery = window.matchMedia('(max-width: 768px)')
  updateViewport()
  if (typeof mobileQuery.addEventListener === 'function') {
    mobileQuery.addEventListener('change', updateViewport)
  } else {
    mobileQuery.addListener(updateViewport)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  if (mobileQuery) {
    if (typeof mobileQuery.removeEventListener === 'function') {
      mobileQuery.removeEventListener('change', updateViewport)
    } else {
      mobileQuery.removeListener(updateViewport)
    }
  }
  clearPdfjsView()
})
</script>

<template>
  <Teleport to="body">
    <transition name="preview-fade">
      <div v-if="open" ref="previewRef" class="pdf-preview" @click.self="close">
        <div class="pdf-preview__top">
          <div class="pdf-preview__title">{{ name || t('preview.pdfTitle') }}</div>
          <div class="pdf-preview__top-actions">
            <button
              type="button"
              class="pdf-preview__top-btn"
              :title="fullscreenActive ? t('vidstack.Exit Fullscreen') : t('vidstack.Fullscreen')"
              @click="toggleFullscreen"
            >
              <Minimize v-if="fullscreenActive" :size="18" />
              <Maximize v-else :size="18" />
            </button>
            <button
              type="button"
              class="pdf-preview__top-btn"
              :title="t('common.openInNewTab')"
              @click="openInNewTab"
            >
              <ExternalLink :size="18" />
            </button>
            <button
              type="button"
              class="pdf-preview__top-btn"
              :title="t('common.download')"
              :disabled="!src"
              @click="downloadCurrent"
            >
              <Download :size="18" />
            </button>
            <button
              type="button"
              class="pdf-preview__top-btn"
              :title="t('common.close')"
              @click="close"
            >
              <X :size="18" />
            </button>
          </div>
        </div>

        <div class="pdf-preview__canvas" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
          <div
            ref="canvasViewport"
            class="pdf-preview__viewport"
            :class="{
              'pdf-preview__viewport--scrollable': usePdfjs,
              'overlay-scroll': usePdfjs,
            }"
            @scroll="onScroll"
          >
            <template v-if="src">
              <template v-if="usePdfjs">
                <div ref="canvasHost" class="pdf-preview__pdfjs"></div>
                <div v-if="pdfjsLoading" class="pdf-preview__placeholder">
                  {{ t('common.loadingEllipsis') }}
                </div>
                <div v-else-if="pdfjsError" class="pdf-preview__placeholder">{{ pdfjsError }}</div>
              </template>
              <iframe v-else class="pdf-preview__frame" :src="src" title="PDF Preview"></iframe>
            </template>
            <div v-else class="pdf-preview__placeholder">{{ t('common.loadingEllipsis') }}</div>
          </div>
          <div
            v-if="usePdfjs && isScrollable"
            class="overlay-scrollbar"
            :class="{ 'is-visible': visible }"
          >
            <div
              class="overlay-scrollbar__thumb"
              :style="{ height: `${thumbHeight}px`, transform: `translateY(${thumbTop}px)` }"
              @mousedown="onThumbMouseDown"
            ></div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.pdf-preview {
  position: fixed;
  inset: 0;
  background: var(--color-overlay-strong);
  display: grid;
  grid-template-rows: auto 1fr;
  z-index: var(--z-overlay);
}

.pdf-preview__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  color: var(--color-overlay-text);
  gap: var(--space-3);
}

.pdf-preview__title {
  font-size: 13px;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pdf-preview__top-actions {
  display: inline-flex;
  gap: var(--space-2);
}

.pdf-preview__top-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--color-overlay-line);
  background: var(--color-overlay-soft);
  color: var(--color-overlay-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.pdf-preview__top-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pdf-preview__canvas {
  position: relative;
  padding: 0 var(--space-5) var(--space-5);
  min-height: 0;
  overflow: hidden;
}

.pdf-preview__viewport {
  height: 100%;
  overflow: hidden;
}

.pdf-preview__viewport--scrollable {
  overflow: auto;
}

.pdf-preview__frame {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.pdf-preview__pdfjs {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

:deep(.pdf-preview__page-canvas) {
  display: block;
  max-width: 100%;
  border-radius: var(--radius-sm);
  background: #fff;
}

.pdf-preview__placeholder {
  color: var(--color-overlay-text);
  font-size: 14px;
  letter-spacing: 0.08em;
  display: grid;
  place-items: center;
  height: 100%;
}

.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity var(--transition-base);
}

.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}
</style>
