<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useToastStore } from '@/stores/toast'

const toastStore = useToastStore()
const { items } = storeToRefs(toastStore)

const toneClass = (type: string) => `toast__item toast__item--${type}`
</script>

<template>
  <div class="toast">
    <transition-group name="toast-fade" tag="div" class="toast__stack">
      <div v-for="item in items" :key="item.id" :class="toneClass(item.type)">
        <div class="toast__title">
          <span v-if="item.loading" class="toast__spinner" aria-hidden="true"></span>
          {{ item.title }}
        </div>
        <div v-if="item.message" class="toast__message">{{ item.message }}</div>
        <button class="toast__close" type="button" @click="toastStore.remove(item.id)">
          关闭
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast {
  position: fixed;
  right: var(--space-6);
  top: var(--space-6);
  z-index: var(--z-toast);
}

.toast__stack {
  display: grid;
  gap: var(--space-3);
}

.toast__item {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-primary);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  min-width: 200px;
  display: grid;
  gap: 4px;
}

.toast__item--success {
  border-left-color: var(--color-success);
}

.toast__item--error {
  border-left-color: var(--color-danger);
}

.toast__item--warning {
  border-left-color: var(--color-warning);
}

.toast__item--info {
  border-left-color: var(--color-info);
}

.toast__title {
  font-weight: 600;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.toast__message {
  font-size: 12px;
  color: var(--color-muted);
}

.toast__close {
  justify-self: end;
  font-size: 11px;
  color: var(--color-muted);
  cursor: pointer;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.toast__spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--color-primary);
  border-top-color: transparent;
  animation: toast-spin 0.8s linear infinite;
}

@keyframes toast-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
