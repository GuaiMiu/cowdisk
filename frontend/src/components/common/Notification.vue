<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useNotification } from '@/stores/notification'

const notificationStore = useNotification()
const { items } = storeToRefs(notificationStore)

const toneClass = (type: string) => `notification__item notification__item--${type}`
</script>

<template>
  <div class="notification">
    <transition-group name="notification-fade" tag="div" class="notification__stack">
      <div v-for="item in items" :key="item.id" :class="toneClass(item.type)">
        <span class="notification__icon" aria-hidden="true"></span>
        <div class="notification__content">
          <div class="notification__title">{{ item.title }}</div>
          <div v-if="item.message" class="notification__message">{{ item.message }}</div>
        </div>
        <button
          class="notification__close"
          type="button"
          @click="notificationStore.remove(item.id)"
        >
          ×
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.notification {
  position: fixed;
  right: var(--space-6);
  top: var(--space-6);
  z-index: var(--z-toast);
  pointer-events: none;
}

.notification__stack {
  display: grid;
  gap: var(--space-3);
}

.notification__item {
  pointer-events: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  min-width: 280px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-3);
  padding: 12px 14px;
}

.notification__content {
  display: grid;
  gap: 4px;
}

.notification__title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.2;
}

.notification__message {
  font-size: 12px;
  color: var(--color-muted);
}

.notification__close {
  font-size: 14px;
  color: var(--color-muted);
  cursor: pointer;
}

.notification__icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-info);
}

.notification__item--success .notification__icon {
  background: var(--color-success);
}

.notification__item--error .notification__icon {
  background: var(--color-danger);
}

.notification__item--warning .notification__icon {
  background: var(--color-warning);
}

.notification__item--info .notification__icon {
  background: var(--color-info);
}

.notification-fade-enter-active,
.notification-fade-leave-active {
  transition:
    opacity var(--transition-base),
    transform var(--transition-base);
}

.notification-fade-enter-from,
.notification-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
