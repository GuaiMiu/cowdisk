<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { Download, ExternalLink, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import 'vidstack/player'
import 'vidstack/player/ui'
import 'vidstack/player/layouts/default'
import 'vidstack/player/styles/base.css'
import 'vidstack/player/styles/default/theme.css'
import 'vidstack/player/styles/default/layouts/video.css'

const props = withDefaults(
  defineProps<{
    open: boolean
    src: string | null
    name?: string
    type?: string | null
  }>(),
  {
    name: '',
  },
)

const { locale, messages, t } = useI18n({ useScope: 'global' })
const vidstackTranslations = computed(() => {
  const allMessages = messages.value as Record<string, { vidstack?: Record<string, string> }>
  const currentMessages = allMessages?.[locale.value]
  return currentMessages?.vidstack ?? {}
})

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'close'): void
}>()

const close = () => {
  emit('update:open', false)
  emit('close')
}

const downloadCurrent = () => {
  if (!props.src) {
    return
  }
  const link = document.createElement('a')
  link.href = props.src
  link.download = props.name || 'video'
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

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <Teleport to="body">
    <transition name="preview-fade">
      <div v-if="open" class="video-preview" @click.self="close">
        <div class="video-preview__top">
          <div class="video-preview__title">{{ name || t('preview.videoTitle') }}</div>
          <div class="video-preview__top-actions">
            <button
              type="button"
              class="video-preview__top-btn"
              :title="t('common.openInNewTab')"
              @click="openInNewTab"
            >
              <ExternalLink :size="18" />
            </button>
            <button
              type="button"
              class="video-preview__top-btn"
              :title="t('common.download')"
              :disabled="!src"
              @click="downloadCurrent"
            >
              <Download :size="18" />
            </button>
            <button
              type="button"
              class="video-preview__top-btn"
              :title="t('common.close')"
              @click="close"
            >
              <X :size="18" />
            </button>
          </div>
        </div>

        <div class="video-preview__canvas">
          <media-player class="video-preview__player" playsinline crossorigin load="eager">
            <media-provider>
              <source v-if="src" :src="src" :type="type || undefined" />
            </media-provider>
            <media-video-layout :translations="vidstackTranslations"></media-video-layout>
          </media-player>
          <div v-if="!src" class="video-preview__placeholder">
            {{ t('common.loadingEllipsis') }}
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.video-preview {
  position: fixed;
  inset: 0;
  background: var(--color-overlay-strong);
  display: grid;
  grid-template-rows: auto 1fr;
  z-index: var(--z-overlay);
  width: 100vw;
  height: 100dvh;
}

.video-preview__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  color: var(--color-overlay-text);
  gap: var(--space-3);
}

.video-preview__title {
  font-size: 13px;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-preview__top-actions {
  display: inline-flex;
  gap: var(--space-2);
}

.video-preview__top-btn {
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

.video-preview__top-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.video-preview__canvas {
  position: relative;
  padding: 0 var(--space-5) var(--space-5);
  min-height: 0;
  height: 100%;
  width: 100vw;
}

.video-preview__player {
  width: 100%;
  height: 100%;
  display: block;
  background: var(--color-overlay-strong);
  border-radius: var(--radius-md);
  overflow: hidden;
  position: relative;
  max-width: 100vw;
}

.video-preview__placeholder {
  position: absolute;
  inset: 0;
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

@media (max-width: 768px) {
  .video-preview__top {
    padding: var(--space-3) var(--space-4);
  }

  .video-preview__canvas {
    padding: 0;
    height: calc(100dvh - 56px);
  }

  .video-preview__player {
    border-radius: 0;
  }
}
</style>
