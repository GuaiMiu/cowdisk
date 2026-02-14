<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Dropdown from '@/components/common/Dropdown.vue'
import Button from '@/components/common/Button.vue'
import type { DiskEntry } from '@/types/disk'

const props = defineProps<{
  entry: DiskEntry
}>()

const emit = defineEmits<{
  (event: 'action', action: 'download' | 'rename' | 'delete' | 'share'): void
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <Dropdown align="right" :width="160">
    <template #trigger>
      <slot>
        <Button variant="ghost" size="sm">{{ t('fileActionsMenu.more') }}</Button>
      </slot>
    </template>
    <template #content>
      <div class="menu">
        <button
          class="menu__item"
          type="button"
          v-permission="'disk:file:move'"
          @click="emit('action', 'rename')"
        >
          {{ t('fileActionsMenu.rename') }}
        </button>
        <button
          class="menu__item"
          type="button"
          v-permission="'disk:file:download'"
          @click="emit('action', 'share')"
        >
          {{ t('fileActionsMenu.share') }}
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
