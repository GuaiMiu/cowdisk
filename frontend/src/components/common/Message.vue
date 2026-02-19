<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useMessage } from '@/stores/message'

const messageStore = useMessage()
const { items } = storeToRefs(messageStore)

const toneClass = (type: string) => `message__item message__item--${type}`
</script>

<template>
  <div class="message">
    <transition-group name="message-fade" tag="div" class="message__stack">
      <div v-for="item in items" :key="item.id" :class="toneClass(item.type)">
        <span v-if="item.loading" class="message__spinner" aria-hidden="true"></span>
        <span v-else class="message__icon" aria-hidden="true"></span>
        <div class="message__content">
          <div class="message__title">{{ item.title }}</div>
          <div v-if="item.message" class="message__desc">{{ item.message }}</div>
        </div>
        <button class="message__close" type="button" @click="messageStore.remove(item.id)">
          ×
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.message {
  position: fixed;
  top: var(--space-6);
  left: 50%;
  transform: translateX(-50%);
  z-index: var(--z-toast);
  pointer-events: none;
}

.message__stack {
  display: grid;
  gap: var(--space-2);
}

.message__item {
  pointer-events: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  min-width: 260px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-3);
  padding: 10px 12px;
}

.message__content {
  display: grid;
  gap: 2px;
}

.message__title {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.2;
}

.message__desc {
  font-size: 12px;
  color: var(--color-muted);
}

.message__close {
  font-size: 14px;
  color: var(--color-muted);
  cursor: pointer;
}

.message__spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--color-primary);
  border-top-color: transparent;
  animation: message-spin 0.8s linear infinite;
}

.message__icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-info);
}

.message__item--success .message__icon {
  background: var(--color-success);
}

.message__item--error .message__icon {
  background: var(--color-danger);
}

.message__item--warning .message__icon {
  background: var(--color-warning);
}

.message__item--info .message__icon {
  background: var(--color-info);
}

.message-fade-enter-active,
.message-fade-leave-active {
  transition:
    opacity var(--transition-base),
    transform var(--transition-base);
}

.message-fade-enter-from,
.message-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@keyframes message-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
