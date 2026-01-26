<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ChevronLeft,
  ChevronRight,
  Download,
  RefreshCcw,
  RotateCcw,
  RotateCw,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-vue-next'

type ImageItem = { src: string; name?: string }

const props = withDefaults(
  defineProps<{
    open: boolean
    images: Array<ImageItem | string>
    startIndex?: number
  }>(),
  {
    startIndex: 0,
  },
)

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'close'): void
  (event: 'change', index: number): void
}>()

const items = computed<ImageItem[]>(() =>
  props.images.map((item) => (typeof item === 'string' ? { src: item } : item)),
)

const { t } = useI18n({ useScope: 'global' })

const index = ref(0)
const scale = ref(1)
const rotate = ref(0)
const offsetX = ref(0)
const offsetY = ref(0)
const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0, ox: 0, oy: 0 })

const current = computed(() => items.value[index.value])
const canNavigate = computed(() => items.value.length > 1)

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

const resetTransform = () => {
  scale.value = 1
  rotate.value = 0
  offsetX.value = 0
  offsetY.value = 0
}

const setIndex = (next: number) => {
  const total = items.value.length
  if (!total) {
    return
  }
  const normalized = ((next % total) + total) % total
  index.value = normalized
  emit('change', normalized)
  resetTransform()
}

const close = () => {
  emit('update:open', false)
  emit('close')
}

const downloadCurrent = () => {
  if (!current.value?.src) {
    return
  }
  const link = document.createElement('a')
  link.href = current.value.src
  link.download = current.value.name || 'image'
  link.click()
}

const zoomBy = (delta: number) => {
  scale.value = clamp(Number((scale.value + delta).toFixed(2)), 0.2, 5)
}

const rotateBy = (delta: number) => {
  rotate.value = (rotate.value + delta) % 360
}

const onWheel = (event: WheelEvent) => {
  event.preventDefault()
  zoomBy(event.deltaY < 0 ? 0.1 : -0.1)
}

const onPointerDown = (event: PointerEvent) => {
  event.preventDefault()
  dragging.value = true
  dragStart.value = {
    x: event.clientX,
    y: event.clientY,
    ox: offsetX.value,
    oy: offsetY.value,
  }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

const onPointerMove = (event: PointerEvent) => {
  if (!dragging.value) {
    return
  }
  offsetX.value = dragStart.value.ox + (event.clientX - dragStart.value.x)
  offsetY.value = dragStart.value.oy + (event.clientY - dragStart.value.y)
}

const onPointerUp = (event: PointerEvent) => {
  if (!dragging.value) {
    return
  }
  dragging.value = false
  ;(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId)
}

const onKeyDown = (event: KeyboardEvent) => {
  if (!props.open) {
    return
  }
  if (event.key === 'Escape') {
    close()
    return
  }
  if (event.key === 'ArrowLeft' && canNavigate.value) {
    setIndex(index.value - 1)
  }
  if (event.key === 'ArrowRight' && canNavigate.value) {
    setIndex(index.value + 1)
  }
}

watch(
  () => props.open,
  (value) => {
    if (!value) {
      return
    }
    setIndex(props.startIndex ?? 0)
  },
)

watch(
  () => props.startIndex,
  (value) => {
    if (props.open) {
      setIndex(value ?? 0)
    }
  },
)

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
})

const imageStyle = computed(() => ({
  transform: `translate(${offsetX.value}px, ${offsetY.value}px) scale(${scale.value}) rotate(${rotate.value}deg)`,
}))
</script>

<template>
  <Teleport to="body">
    <transition name="preview-fade">
      <div v-if="open" class="preview" @click.self="close">
        <div class="preview__top">
          <div class="preview__title">{{ current?.name || t('preview.imageTitle') }}</div>
          <div class="preview__top-actions">
            <button type="button" class="preview__top-btn" :title="t('common.close')" @click="close">
              <X :size="18" />
            </button>
          </div>
        </div>

        <div v-if="canNavigate" class="preview__counter">
          {{ index + 1 }} / {{ items.length }}
        </div>

        <button
          v-if="canNavigate"
          type="button"
          class="preview__arrow preview__arrow--left"
          :title="t('preview.previous')"
          @click="setIndex(index - 1)"
        >
          <ChevronLeft :size="26" />
        </button>
        <button
          v-if="canNavigate"
          type="button"
          class="preview__arrow preview__arrow--right"
          :title="t('preview.next')"
          @click="setIndex(index + 1)"
        >
          <ChevronRight :size="26" />
        </button>

        <div class="preview__canvas" @wheel="onWheel">
          <img
            v-if="current?.src"
            class="preview__image"
            :class="{ 'is-dragging': dragging }"
            :src="current.src"
            :alt="current.name || 'preview'"
            :style="imageStyle"
            draggable="false"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointerleave="onPointerUp"
          />
          <div v-else class="preview__placeholder">{{ t('common.loadingEllipsis') }}</div>
        </div>

        <div class="preview__toolbar">
          <button type="button" class="preview__tool" :title="t('preview.zoomOut')" @click="zoomBy(-0.2)">
            <ZoomOut :size="16" />
          </button>
          <button type="button" class="preview__tool" :title="t('preview.zoomIn')" @click="zoomBy(0.2)">
            <ZoomIn :size="16" />
          </button>
          <button type="button" class="preview__tool" :title="t('preview.reset')" @click="resetTransform">
            <RefreshCcw :size="16" />
          </button>
          <button type="button" class="preview__tool" :title="t('preview.rotateLeft')" @click="rotateBy(-90)">
            <RotateCcw :size="16" />
          </button>
          <button type="button" class="preview__tool" :title="t('preview.rotateRight')" @click="rotateBy(90)">
            <RotateCw :size="16" />
          </button>
          <button
            type="button"
            class="preview__tool"
            :title="t('common.download')"
            :disabled="!current?.src"
            @click="downloadCurrent"
          >
            <Download :size="16" />
          </button>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.preview {
  position: fixed;
  inset: 0;
  background: var(--color-overlay-strong);
  display: grid;
  place-items: center;
  z-index: var(--z-overlay);
}

.preview__canvas {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.preview__image {
  max-width: 80vw;
  max-height: 80vh;
  object-fit: contain;
  user-select: none;
  cursor: grab;
  transition: transform var(--transition-fast);
}

.preview__image.is-dragging {
  cursor: grabbing;
}

.preview__placeholder {
  color: var(--color-overlay-text);
  font-size: 14px;
  letter-spacing: 0.08em;
}

.preview__top {
  position: absolute;
  top: 20px;
  left: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--color-overlay-text);
  gap: var(--space-3);
}

.preview__title {
  font-size: 13px;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview__top-actions {
  display: inline-flex;
  gap: var(--space-2);
}

.preview__top-btn {
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

.preview__top-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.preview__counter {
  position: absolute;
  top: 28px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--color-overlay-text);
  font-size: 13px;
  letter-spacing: 0.04em;
}

.preview__arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid var(--color-overlay-line);
  background: var(--color-overlay-soft);
  color: var(--color-overlay-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.preview__arrow--left {
  left: 24px;
}

.preview__arrow--right {
  right: 24px;
}

.preview__toolbar {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: 999px;
  border: 1px solid var(--color-overlay-line);
  background: var(--color-overlay-soft);
}

.preview__tool {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 0;
  background: transparent;
  color: var(--color-overlay-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.preview__tool:hover {
  background: rgba(255, 255, 255, 0.12);
}

.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity var(--transition-base);
}

.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .preview__arrow {
    width: 36px;
    height: 36px;
  }

  .preview__toolbar {
    bottom: 18px;
  }
}
</style>
