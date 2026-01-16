<template>
  <div class="toast-stack">
    <transition-group name="toast" tag="div">
      <div
        v-for="item in notify.items"
        :key="item.id"
        class="toast"
        :class="item.type"
      >
        <span>{{ item.message }}</span>
        <button class="toast-close" @click="notify.remove(item.id)">×</button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { useNotifyStore } from "../stores/notify";

const notify = useNotifyStore();
</script>

<style scoped>
.toast-stack {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 60;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toast {
  min-width: 220px;
  max-width: 360px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid var(--stroke);
  background: var(--surface);
  box-shadow: var(--shadow);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toast.success {
  border-color: rgba(46, 125, 90, 0.35);
  color: #2e7d5a;
}

.toast.error {
  border-color: rgba(178, 59, 43, 0.35);
  color: #b23b2b;
}

.toast.info {
  border-color: rgba(44, 93, 118, 0.35);
  color: #2c5d76;
}

.toast.warn {
  border-color: rgba(179, 118, 35, 0.35);
  color: #b37623;
}

.toast-close {
  border: none;
  background: transparent;
  cursor: pointer;
  color: inherit;
  font-size: 16px;
  line-height: 1;
}

.toast-enter-active,
.toast-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
