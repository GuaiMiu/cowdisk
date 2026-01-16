<template>
  <div v-if="visible" class="preview-mask" @click.self="$emit('close')">
    <div class="preview-panel card">
      <div class="preview-head">
        <div class="preview-title">{{ title }}</div>
        <div class="preview-actions">
          <button class="btn ghost" @click="$emit('prev')" :disabled="!hasPrev">
            上一个
          </button>
          <button class="btn ghost" @click="$emit('next')" :disabled="!hasNext">
            下一个
          </button>
          <button class="btn ghost" @click="$emit('close')">关闭</button>
        </div>
      </div>
      <div class="preview-body">
        <img v-if="type === 'image'" :src="url" :alt="title" />
        <video
          v-else-if="type === 'video'"
          :src="url"
          controls
          playsinline
        ></video>
        <div v-else class="preview-empty">暂不支持预览</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  visible: boolean;
  url: string;
  type: "image" | "video" | "other";
  title?: string;
  hasPrev?: boolean;
  hasNext?: boolean;
}>();
</script>

<style scoped>
.preview-mask {
  position: fixed;
  inset: 0;
  background: rgba(20, 22, 27, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 40;
}

.preview-panel {
  width: min(960px, 100%);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.preview-title {
  font-size: 16px;
  font-weight: 600;
}

.preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview-body {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-alt);
  border-radius: 12px;
  padding: 12px;
}

img,
video {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 10px;
}

.preview-empty {
  color: var(--muted);
  font-size: 13px;
}
</style>
