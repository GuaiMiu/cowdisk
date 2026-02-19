<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, ExternalLink, X } from 'lucide-vue-next'

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
      <div v-if="open" class="pdf-preview" @click.self="close">
        <div class="pdf-preview__top">
          <div class="pdf-preview__title">{{ name || t('preview.pdfTitle') }}</div>
          <div class="pdf-preview__top-actions">
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

        <div class="pdf-preview__canvas">
          <iframe v-if="src" class="pdf-preview__frame" :src="src" title="PDF Preview"></iframe>
          <div v-else class="pdf-preview__placeholder">{{ t('common.loadingEllipsis') }}</div>
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
}

.pdf-preview__frame {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-surface);
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
