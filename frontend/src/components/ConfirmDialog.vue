<template>
  <div class="confirm-backdrop" @click="handleCancel">
    <div class="confirm-card card" @click.stop>
      <div class="confirm-title">{{ title }}</div>
      <div class="confirm-message">{{ message }}</div>
      <div class="confirm-actions">
        <button class="btn secondary" @click="handleCancel">取消</button>
        <button class="btn accent" @click="handleConfirm">确认</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  title?: string;
  message?: string;
}>();

const emit = defineEmits<{
  (e: "confirm"): void;
  (e: "cancel"): void;
}>();

const handleConfirm = () => emit("confirm");
const handleCancel = () => emit("cancel");
</script>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(20, 22, 27, 0.4);
  display: grid;
  place-items: center;
  z-index: 50;
}

.confirm-card {
  width: min(380px, 90vw);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.confirm-title {
  font-size: 18px;
  font-weight: 700;
}

.confirm-message {
  font-size: 14px;
  color: var(--muted);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
