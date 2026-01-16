<template>
  <div class="row-actions" :class="{ hidden: isDownloading, active: isActive }">
    <button
      v-if="canDownload"
      class="icon-btn"
      title="下载"
      aria-label="下载"
      @click="$emit('download')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 3v10l3.5-3.5 1.5 1.5L12 18l-5-5 1.5-1.5L11 13V3h1Zm-7 16h14v2H5v-2Z"
          fill="currentColor"
        />
      </svg>
    </button>
    <button
      v-if="canDelete"
      class="icon-btn danger"
      title="删除"
      aria-label="删除"
      @click="$emit('delete')"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M6 7h12l-1 14H7L6 7Zm3-3h6l1 2H8l1-2Z"
          fill="currentColor"
        />
      </svg>
    </button>
    <div class="more-menu">
      <button
        class="icon-btn"
        title="更多"
        aria-label="更多"
        @click.stop="$emit('more', $event)"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="5" cy="12" r="2" fill="currentColor" />
          <circle cx="12" cy="12" r="2" fill="currentColor" />
          <circle cx="19" cy="12" r="2" fill="currentColor" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  canDelete: boolean;
  canDownload: boolean;
  isDownloading: boolean;
  isActive: boolean;
}>();

defineEmits<{
  (e: "download"): void;
  (e: "delete"): void;
  (e: "more", event: MouseEvent): void;
}>();
</script>

<style scoped>
.row-actions {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.92);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}

.row-actions.hidden {
  opacity: 0;
  pointer-events: none;
}

.row-actions.active {
  opacity: 1;
  pointer-events: auto;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid var(--stroke);
  background: var(--surface);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ink);
  cursor: pointer;
}

.icon-btn svg {
  width: 16px;
  height: 16px;
}

.icon-btn.danger {
  color: #b23b2b;
  border-color: rgba(178, 59, 43, 0.24);
  background: rgba(178, 59, 43, 0.08);
}

.more-menu {
  position: relative;
}
</style>
