<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import IconButton from '@/components/common/IconButton.vue'
import Dropdown from '@/components/common/Dropdown.vue'
import {
  UploadCloud,
  FolderPlus,
  FileText,
  RefreshCw,
  ListChecks,
  ChevronDown,
  FolderInput,
  Trash2,
} from 'lucide-vue-next'

const props = defineProps<{
  selectedCount: number
}>()

const emit = defineEmits<{
  (event: 'upload'): void
  (event: 'upload-folder'): void
  (event: 'new-folder'): void
  (event: 'new-text'): void
  (event: 'refresh'): void
  (event: 'toggle-queue'): void
  (event: 'delete-selected'): void
  (event: 'move-selected'): void
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="toolbar">
    <div class="toolbar__left">
      <Dropdown align="left" :width="180">
        <template #trigger>
          <Button variant="secondary">
            <FolderPlus :size="16" />
            {{ t('fileToolbar.new') }}
            <ChevronDown :size="14" />
          </Button>
        </template>
        <template #content="{ close }">
          <div class="menu">
            <button
              class="menu__item"
              type="button"
              v-permission="'disk:file:mkdir'"
              @click="
                emit('new-folder');
                close();
              "
            >
              {{ t('fileToolbar.folder') }}
            </button>
            <button
              class="menu__item"
              type="button"
              v-permission="'disk:file:upload'"
              @click="
                emit('new-text');
                close();
              "
            >
              {{ t('fileToolbar.textFile') }}
            </button>
          </div>
        </template>
      </Dropdown>
      <Dropdown align="left" :width="180">
        <template #trigger>
          <Button v-permission="'disk:file:upload'">
            <UploadCloud :size="16" />
            {{ t('fileToolbar.upload') }}
            <ChevronDown :size="14" />
          </Button>
        </template>
        <template #content>
          <div class="menu">
            <button class="menu__item" type="button" @click="emit('upload')">
              {{ t('fileToolbar.uploadFile') }}
            </button>
            <button class="menu__item" type="button" @click="emit('upload-folder')">
              {{ t('fileToolbar.uploadDirectory') }}
            </button>
          </div>
        </template>
      </Dropdown>
      <Button
        v-if="selectedCount > 0"
        variant="secondary"
        v-permission="'disk:file:move'"
        @click="emit('move-selected')"
      >
        <FolderInput :size="16" />
        {{ t('fileToolbar.moveSelected', { count: selectedCount }) }}
      </Button>
      <Button
        v-if="selectedCount > 0"
        variant="danger"
        v-permission="'disk:file:delete'"
        @click="emit('delete-selected')"
      >
        <Trash2 :size="16" />
        {{ t('fileToolbar.deleteSelected', { count: selectedCount }) }}
      </Button>
    </div>
    <div class="toolbar__right">
      <IconButton
        :aria-label="t('fileToolbar.uploadQueue')"
        variant="secondary"
        @click="emit('toggle-queue')"
      >
        <ListChecks :size="18" />
      </IconButton>
      <IconButton
        :aria-label="t('fileToolbar.refresh')"
        variant="secondary"
        @click="emit('refresh')"
      >
        <RefreshCw :size="18" />
      </IconButton>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.toolbar__left,
.toolbar__right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

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

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar__left,
  .toolbar__right {
    width: 100%;
  }

  .toolbar__left {
    flex-wrap: wrap;
  }

  .toolbar__left > * {
    flex: 0 1 auto;
    min-width: 0;
  }
}
</style>
