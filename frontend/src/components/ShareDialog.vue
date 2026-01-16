<template>
  <div class="share-backdrop" @click="emit('close')">
    <div class="share-card card" @click.stop>
      <div class="share-head">
        <div>
          <div class="share-title">分享链接</div>
          <div class="share-subtitle">复制后发送给对方</div>
        </div>
        <button class="btn ghost" @click="emit('close')">关闭</button>
      </div>
      <div class="share-body">
        <input class="input" readonly :value="url" />
        <button class="btn accent" @click="emit('copy')">复制链接</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  url: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "copy"): void;
}>();
</script>

<style scoped>
.share-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(20, 22, 27, 0.4);
  display: grid;
  place-items: center;
  z-index: 50;
}

.share-card {
  width: min(480px, 92vw);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.share-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.share-title {
  font-size: 18px;
  font-weight: 700;
}

.share-subtitle {
  font-size: 12px;
  color: var(--muted);
}

.share-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 768px) {
  .share-card {
    padding: 16px;
  }
}
</style>
