<script setup lang="ts">
import Drawer from '@/components/common/Drawer.vue'
import Button from '@/components/common/Button.vue'
import Progress from '@/components/common/Progress.vue'
import { useUploadsStore } from '@/stores/uploads'
import { useUploader } from '@/composables/useUploader'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

const uploadsStore = useUploadsStore()
const { retry, cancel } = useUploader()
</script>

<template>
  <Drawer :open="open" title="上传队列" :width="460" @close="emit('close')">
    <div v-if="uploadsStore.items.length === 0" class="empty">暂无上传任务</div>
    <div v-else class="queue">
      <div v-for="item in uploadsStore.items" :key="item.id" class="queue__item">
        <div class="queue__meta">
          <div class="queue__name">{{ item.file.name }}</div>
          <div class="queue__status">{{ item.status }}</div>
        </div>
        <Progress :value="item.progress" />
        <div class="queue__actions">
          <Button v-if="item.status === 'error'" size="sm" variant="secondary" @click="retry(item.id)">
            重试
          </Button>
          <Button v-if="item.status === 'uploading' || item.status === 'queued'" size="sm" variant="ghost" @click="cancel(item.id)">
            取消
          </Button>
          <span v-if="item.error" class="queue__error">{{ item.error }}</span>
        </div>
      </div>
    </div>
    <template #footer>
      <Button variant="secondary" @click="uploadsStore.clearDone()">清理已完成</Button>
      <Button variant="ghost" @click="emit('close')">关闭</Button>
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
}

.queue__status {
  font-size: 11px;
  color: var(--color-muted);
}

.queue__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.queue__error {
  font-size: 12px;
  color: var(--color-danger);
  margin-left: auto;
}

.empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--color-muted);
}
</style>
