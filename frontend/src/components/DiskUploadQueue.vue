<template>
  <div v-if="items.length" class="upload-panel card">
    <div v-for="item in items" :key="item.id" class="upload-item">
      <div class="upload-name">{{ item.name }}</div>
      <div class="upload-bar">
        <span :style="{ width: `${item.progress}%` }"></span>
      </div>
      <div class="upload-status">
        {{ item.progress }}% {{ item.status }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  items: Array<{ id: string; name: string; progress: number; status: string }>;
}>();
</script>

<style scoped>
.upload-panel {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.upload-item {
  display: grid;
  grid-template-columns: minmax(120px, 1fr) minmax(120px, 2fr) auto;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.upload-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-bar {
  height: 6px;
  background: var(--surface-alt);
  border-radius: 999px;
  overflow: hidden;
}

.upload-bar span {
  display: block;
  height: 100%;
  background: var(--accent);
  width: 0%;
}

.upload-status {
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
}
</style>
