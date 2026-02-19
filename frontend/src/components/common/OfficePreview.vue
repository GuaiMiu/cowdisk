<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { ExternalLink, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

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
      <div v-if="open" class="office-preview" @click.self="close">
        <div class="office-preview__top">
          <div class="office-preview__title">{{ name || t('preview.officeTitle') }}</div>
          <div class="office-preview__top-actions">
            <button
              type="button"
              class="office-preview__top-btn"
              :title="t('preview.openInNewWindow')"
              :disabled="!src"
              @click="openInNewTab"
            >
              <ExternalLink :size="18" />
            </button>
            <button
              type="button"
              class="office-preview__top-btn"
              :title="t('common.close')"
              @click="close"
            >
              <X :size="18" />
            </button>
          </div>
        </div>

        <div class="office-preview__canvas">
          <iframe v-if="src" class="office-preview__frame" :src="src" title="Office Preview"></iframe>
          <div v-else class="office-preview__placeholder">{{ t('common.loadingEllipsis') }}</div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.office-preview {
  position: fixed;
  inset: 0;
  background: var(--color-overlay-strong);
  display: grid;
  grid-template-rows: auto 1fr;
  z-index: var(--z-overlay);
}

.office-preview__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  color: var(--color-overlay-text);
  gap: var(--space-3);
}

.office-preview__title {
  font-size: 13px;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.office-preview__top-actions {
  display: inline-flex;
  gap: var(--space-2);
}

.office-preview__top-btn {
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

.office-preview__top-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.office-preview__canvas {
  position: relative;
  padding: 0 var(--space-5) var(--space-5);
  min-height: 0;
}

.office-preview__frame {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.office-preview__placeholder {
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
