<script setup lang="ts">
import Dropdown from '@/components/common/Dropdown.vue'
import Button from '@/components/common/Button.vue'
import type { DiskEntry } from '@/types/disk'

const props = defineProps<{
  entry: DiskEntry
}>()

const emit = defineEmits<{
  (event: 'action', action: 'download' | 'rename' | 'delete' | 'share'): void
}>()
</script>

<template>
  <Dropdown align="right" :width="160">
    <template #trigger>
      <slot>
        <Button variant="ghost" size="sm">更多</Button>
      </slot>
    </template>
    <template #content>
      <div class="menu">
        <button class="menu__item" type="button" v-permission="'disk:file:rename'" @click="emit('action', 'rename')">
          重命名
        </button>
        <button class="menu__item" type="button" v-permission="'disk:file:download'" @click="emit('action', 'share')">
          分享
        </button>
      </div>
    </template>
  </Dropdown>
</template>

<style scoped>
.menu {
  display: grid;
  gap: var(--space-1);
}

.menu__item {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text);
}

.menu__item:hover {
  background: var(--color-surface-2);
}

.menu__item--danger {
  color: var(--color-danger);
}
</style>
