<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, ExternalLink, Maximize, Minimize, X } from 'lucide-vue-next'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'
import { isMobileLikeDevice } from '@/utils/device'

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

let renderToken = 0
let activeDoc: { destroy: () => Promise<void> } | null = null
let renderRafId = 0
let viewportResizeObserver: ResizeObserver | null = null
let viewportClientWidth = 0
let pdfjsRuntimePromise: Promise<
  readonly [typeof import('pdfjs-dist'), { default: string }]
> | null = null

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

const destroyActiveDoc = () => {
  if (!activeDoc) {
    return
  }
  void activeDoc.destroy()
  activeDoc = null
}

const clearCanvasHost = () => {
  if (canvasHost.value) {
    canvasHost.value.innerHTML = ''
  }
  updateMetrics()
}

const getPdfContainerWidth = (host: HTMLDivElement) => {
  const width = canvasViewport.value?.clientWidth || host.clientWidth || window.innerWidth
  return Math.max(1, Math.floor(width) - 2)
}

const cancelPdfRenderRequest = () => {
  if (!renderRafId) {
    return
  }
  window.cancelAnimationFrame(renderRafId)
  renderRafId = 0
}

const requestPdfRender = () => {
  if (typeof window === 'undefined') {
    return
  }
  cancelPdfRenderRequest()
  renderRafId = window.requestAnimationFrame(() => {
    renderRafId = 0
    void renderPdfByPdfjs()
  })
}

const loadPdfjsRuntime = async () => {
  if (!pdfjsRuntimePromise) {
    pdfjsRuntimePromise = Promise.all([
      import('pdfjs-dist'),
      import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
    ]) as Promise<readonly [typeof import('pdfjs-dist'), { default: string }]>
  }
  return pdfjsRuntimePromise
}

const clearPdfjsView = () => {
  cancelPdfRenderRequest()
  renderToken += 1
  pdfjsLoading.value = false
  pdfjsError.value = ''
  clearCanvasHost()
  destroyActiveDoc()
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
  clearCanvasHost()
  destroyActiveDoc()

  try {
    const [pdfjs, workerModule] = await loadPdfjsRuntime()
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

    const containerWidth = getPdfContainerWidth(host)
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
      if (pageNumber === 1 || pageNumber === doc.numPages) {
        updateMetrics()
      }
    }
    if (token !== renderToken) {
      return
    }
    pdfjsLoading.value = false
    updateMetrics()
  } catch {
    if (token !== renderToken) {
      return
    }
    pdfjsLoading.value = false
    pdfjsError.value = t('fileExplorer.toasts.previewFailedMessage')
  }
}

const disconnectViewportResizeObserver = () => {
  if (!viewportResizeObserver) {
    return
  }
  viewportResizeObserver.disconnect()
  viewportResizeObserver = null
}

const onViewportResize = () => {
  const width = canvasViewport.value?.clientWidth ?? 0
  if (width <= 0 || width === viewportClientWidth) {
    return
  }
  viewportClientWidth = width
  updateMetrics()
  if (props.open && usePdfjs.value) {
    requestPdfRender()
  }
}

const bindViewportResizeObserver = (node: HTMLDivElement | null) => {
  disconnectViewportResizeObserver()
  viewportClientWidth = node?.clientWidth ?? 0
  if (!node || typeof ResizeObserver === 'undefined') {
    return
  }
  viewportResizeObserver = new ResizeObserver(() => {
    onViewportResize()
  })
  viewportResizeObserver.observe(node)
}

watch(
  [() => props.open, () => props.src, usePdfjs],
  () => {
    requestPdfRender()
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
    bindViewportResizeObserver(node)
    updateMetrics()
  },
  { immediate: true },
)

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  isMobile.value = isMobileLikeDevice()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  disconnectViewportResizeObserver()
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
  display: flex;
  flex-direction: column;
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
  flex: 1;
  padding: 0 var(--space-5) var(--space-5);
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.pdf-preview__viewport {
  width: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
}

.pdf-preview__viewport--scrollable {
  overflow-x: hidden;
  overflow-y: auto;
}

.pdf-preview__frame {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.pdf-preview__pdfjs {
  width: 100%;
  min-height: 100%;
  min-width: 0;
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
