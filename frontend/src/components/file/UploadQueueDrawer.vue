<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from '@/components/common/Drawer.vue'
import Button from '@/components/common/Button.vue'
import Progress from '@/components/common/Progress.vue'
import { useUploadsStore } from '@/stores/uploads'
import { useUploader } from '@/composables/useUploader'
import { formatBytes } from '@/utils/format'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

const uploadsStore = useUploadsStore()
const { retry, cancel, pause, resume } = useUploader()
const { t } = useI18n({ useScope: 'global' })

const hasProcessing = computed(() =>
  uploadsStore.items.some((item) => ['queued', 'uploading'].includes(item.status)),
)
const hasActionable = computed(() =>
  uploadsStore.items.some((item) => ['paused', 'error'].includes(item.status)),
)

const wasProcessing = ref(hasProcessing.value)

// 仅在“处理中 -> 全部结束”且无可操作项（暂停/失败）时自动关闭
watch(hasProcessing, (processing) => {
  if (wasProcessing.value && !processing && !hasActionable.value && props.open) {
    emit('close')
  }
  wasProcessing.value = processing
})

const statusLabelMap: Record<string, string> = {
  queued: t('uploadQueue.status.queued'),
  uploading: t('uploadQueue.status.uploading'),
  paused: t('uploadQueue.status.paused'),
  success: t('uploadQueue.status.success'),
  error: t('uploadQueue.status.error'),
  cancelled: t('uploadQueue.status.cancelled'),
}

const getStatusLabel = (status: string) => statusLabelMap[status] || status
</script>

<template>
  <Drawer :open="open" :title="t('uploadQueue.title')" :width="460" @close="emit('close')">
    <div v-if="uploadsStore.items.length === 0" class="empty">{{ t('uploadQueue.empty') }}</div>
    <div v-else class="queue">
      <div v-for="item in uploadsStore.items" :key="item.id" class="queue__item">
        <div class="queue__meta">
          <div class="queue__name">{{ item.file.name }}</div>
          <div class="queue__status">
            <span>{{ getStatusLabel(item.status) }}</span>
            <span v-if="item.status === 'uploading'" class="queue__speed">
              {{ formatBytes(item.speed ?? 0) }}/s
            </span>
          </div>
        </div>
        <Progress :value="item.progress" />
        <div class="queue__actions">
          <div class="queue__error" v-if="item.error">{{ item.error }}</div>
          <div class="queue__buttons">
            <Button
              v-if="item.status === 'error'"
              size="sm"
              variant="secondary"
              @click="retry(item.id)"
            >
              {{ t('uploadQueue.retry') }}
            </Button>
            <Button
              v-if="item.status === 'uploading'"
              size="sm"
              variant="secondary"
              @click="pause(item.id)"
            >
              {{ t('uploadQueue.pause') }}
            </Button>
            <Button
              v-if="item.status === 'paused'"
              size="sm"
              variant="secondary"
              @click="resume(item.id)"
            >
              {{ t('uploadQueue.resume') }}
            </Button>
            <Button
              v-if="
                item.status === 'uploading' || item.status === 'queued' || item.status === 'paused'
              "
              size="sm"
              variant="ghost"
              @click="cancel(item.id)"
            >
              {{ t('uploadQueue.cancel') }}
            </Button>
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <Button variant="secondary" @click="uploadsStore.clearDone()">{{
        t('uploadQueue.clearDone')
      }}</Button>
      <Button variant="ghost" @click="emit('close')">{{ t('uploadQueue.close') }}</Button>
    </template>
  </Drawer>
</template>

<style scoped>
.queue {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.queue__item {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  min-width: 0;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-base),
    transform var(--transition-fast),
    background var(--transition-base);
}

.queue__item:hover {
  border-color: var(--color-primary-soft-strong);
  background: var(--color-surface-2);
  box-shadow: var(--shadow-xs);
  transform: var(--interaction-hover-lift);
}

.queue__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.queue__name {
  font-weight: 600;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  transition: color var(--transition-fast);
}

.queue__item:hover .queue__name {
  color: var(--color-primary);
}

.queue__status {
  font-size: 11px;
  color: var(--color-muted);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
  flex-shrink: 0;
}

.queue__speed {
  font-size: 11px;
  color: var(--color-text);
}

.queue__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  justify-content: space-between;
  min-width: 0;
}

.queue__error {
  font-size: 12px;
  color: var(--color-danger);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  animation: queueErrorFadeIn var(--duration-base) var(--ease-standard);
}

.queue__buttons {
  display: inline-flex;
  gap: var(--space-2);
  align-items: center;
}

.empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--color-muted);
}

@keyframes queueErrorFadeIn {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
