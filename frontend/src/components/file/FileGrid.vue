<script setup lang="ts">
import { Check, MoreHorizontal, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { ComponentPublicInstance, VNodeRef } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DiskEntry } from '@/types/disk'
import { formatBytes, formatTime } from '@/utils/format'
import IconButton from '@/components/common/IconButton.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import FileThumbnailIcon from '@/components/file/FileThumbnailIcon.vue'
import {
  useFileEntryActionsMenu,
  type FileEntryAction,
} from '@/components/file/composables/useFileEntryActionsMenu'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  items: DiskEntry[]
  selectedCount: number
  allSelected: boolean
  indeterminate: boolean
  isSelected: (item: DiskEntry) => boolean
  toggle: (item: DiskEntry) => void
  toggleAll: () => void
  creatingFolder?: boolean
  creatingText?: boolean
  editingEntry?: DiskEntry | null
  editingName?: string
}>()

const emit = defineEmits<{
  (event: 'open', entry: DiskEntry): void
  (
    event: 'action',
    payload: {
      entry: DiskEntry
      action: FileEntryAction
    },
  ): void
  (event: 'create-confirm', name: string): void
  (event: 'create-text-confirm', name: string): void
  (event: 'create-cancel'): void
  (event: 'rename-confirm', payload: { entry: DiskEntry; name: string }): void
  (event: 'rename-cancel'): void
}>()

const { t } = useI18n({ useScope: 'global' })
const authStore = useAuthStore()
const {
  scrollRef,
  onScroll,
  onMouseEnter,
  onMouseLeave,
  thumbHeight,
  thumbTop,
  visible,
  isScrollable,
  updateMetrics,
  onThumbMouseDown,
} = useOverlayScrollbar()
const createName = ref('')
const renameValue = ref('')
const createInputRef = ref<HTMLInputElement | null>(null)
const renameInputRefs = ref(new Map<string, HTMLInputElement>())
const selectAllRef = ref<HTMLInputElement | null>(null)
const contextMenuRef = ref<HTMLElement | null>(null)
const contextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  entry: null as DiskEntry | null,
  width: 228,
})

const onCardClick = (entry: DiskEntry) => {
  if (entry.is_dir) {
    emit('open', entry)
    return
  }
  emit('action', { entry, action: 'preview' })
}
const isEditing = (entry: DiskEntry) => props.editingEntry?.id === entry.id
const confirmCreate = () => {
  if (props.creatingText) {
    emit('create-text-confirm', createName.value)
    return
  }
  emit('create-confirm', createName.value)
}
const confirmRename = (entry: DiskEntry) => {
  emit('rename-confirm', { entry, name: renameValue.value })
}
const onCreateKey = (event: KeyboardEvent) => {
  if (event.key === 'Enter') {
    confirmCreate()
  }
  if (event.key === 'Escape') {
    emit('create-cancel')
  }
}
const onRenameKey = (event: KeyboardEvent, entry: DiskEntry) => {
  if (event.key === 'Enter') {
    confirmRename(entry)
  }
  if (event.key === 'Escape') {
    emit('rename-cancel')
  }
}
const setRenameInputRef = (entry: DiskEntry): VNodeRef => {
  return (refNode: Element | ComponentPublicInstance | null) => {
    const input = refNode instanceof HTMLInputElement ? refNode : null
    if (input) {
      renameInputRefs.value.set(String(entry.id), input)
    } else {
      renameInputRefs.value.delete(String(entry.id))
    }
  }
}
const hasPermission = (permission?: string) => {
  if (!permission) {
    return true
  }
  return authStore.hasPerm(permission)
}

const contextMenuItems = useFileEntryActionsMenu({
  entry: computed(() => contextMenu.value.entry),
  mode: computed(() => 'full' as const),
  t,
  hasPermission,
})
const closeContextMenu = () => {
  contextMenu.value.open = false
  contextMenu.value.entry = null
}
const openContextMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.preventDefault()
  const width = 228
  const roughHeight = 320
  const x = Math.max(8, Math.min(event.clientX, window.innerWidth - width - 8))
  const y = Math.max(8, Math.min(event.clientY, window.innerHeight - roughHeight - 8))
  contextMenu.value = { open: true, x, y, entry, width }
}
const openMoreMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.preventDefault()
  event.stopPropagation()
  const button = event.currentTarget as HTMLElement | null
  if (!button) {
    openContextMenu(event, entry)
    return
  }
  const width = 228
  const roughHeight = 320
  const rect = button.getBoundingClientRect()
  const x = Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8))
  const y = Math.max(8, Math.min(rect.bottom + 6, window.innerHeight - roughHeight - 8))
  contextMenu.value = { open: true, x, y, entry, width }
}
const triggerContextMenuAction = (action: FileEntryAction) => {
  const entry = contextMenu.value.entry
  closeContextMenu()
  if (!entry) {
    return
  }
  emit('action', { entry, action })
}
const onWindowPointerDown = (event: MouseEvent) => {
  if (!contextMenu.value.open) {
    return
  }
  const target = event?.target as Node | null
  if (target && contextMenuRef.value?.contains(target)) {
    return
  }
  closeContextMenu()
}
const onWindowKeyDown = (event: KeyboardEvent) => {
  if (!contextMenu.value.open) {
    return
  }
  if (event.key === 'Escape') {
    closeContextMenu()
  }
}

watch(
  () => props.items.length,
  () => {
    void nextTick(() => updateMetrics())
  },
)
watch(
  () => props.indeterminate,
  (value) => {
    if (selectAllRef.value) {
      selectAllRef.value.indeterminate = value
    }
  },
  { immediate: true },
)
watch([() => props.creatingFolder, () => props.creatingText], ([creatingFolder, creatingText]) => {
  if (creatingFolder || creatingText) {
    createName.value = creatingFolder
      ? t('fileTable.createFolderName')
      : t('fileTable.createTextFileName')
    void nextTick(() => {
      createInputRef.value?.focus()
      createInputRef.value?.select()
    })
  }
})
watch(
  [() => props.editingEntry, () => props.editingName],
  ([entry, name]) => {
    if (!entry) {
      return
    }
    renameValue.value = name ?? entry.name ?? ''
    void nextTick(() => {
      renameInputRefs.value.get(String(entry.id))?.focus()
      renameInputRefs.value.get(String(entry.id))?.select()
    })
  },
  { immediate: true },
)

onMounted(() => {
  void nextTick(() => updateMetrics())
  window.addEventListener('mousedown', onWindowPointerDown)
  window.addEventListener('keydown', onWindowKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('mousedown', onWindowPointerDown)
  window.removeEventListener('keydown', onWindowKeyDown)
})

</script>

<template>
  <div class="grid-shell" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
    <div v-if="items.length" class="grid__bulk">
      <label class="grid__bulk-check">
        <input
          ref="selectAllRef"
          type="checkbox"
          :checked="allSelected"
          @change="toggleAll"
        />
        <span>{{ t('fileGrid.selectAll') }}</span>
      </label>
      <span v-if="selectedCount > 0" class="grid__bulk-selected">
        {{ t('fileGrid.selectedCount', { count: selectedCount }) }}
      </span>
    </div>
    <div class="grid__body">
      <div
        ref="scrollRef"
        class="grid overlay-scroll"
        :class="{ 'grid--empty': !items.length && !creatingFolder && !creatingText }"
        @scroll="onScroll"
      >
        <article v-if="creatingFolder || creatingText" class="card card--edit" @click.stop>
          <div class="card__top card__top--static"></div>
          <div class="card__thumb">
            <FileTypeIcon :name="creatingText ? 'new.txt' : undefined" :is-dir="creatingFolder" :size="64" />
          </div>
          <input
            v-model="createName"
            ref="createInputRef"
            class="card__input"
            :placeholder="t('fileTable.placeholders.newFolder')"
            autofocus
            @keydown="onCreateKey"
          />
          <div class="card__meta-line card__meta-line--actions">
            <IconButton size="sm" variant="secondary" :aria-label="t('fileTable.aria.confirm')" @click="confirmCreate">
              <Check :size="12" />
            </IconButton>
            <IconButton size="sm" variant="ghost" :aria-label="t('fileTable.aria.cancel')" @click="emit('create-cancel')">
              <X :size="12" />
            </IconButton>
          </div>
        </article>
        <template v-if="items.length">
          <article
            v-for="item in items"
            :key="item.id"
            class="card"
            :class="{ 'is-selected': isSelected(item), 'card--edit': isEditing(item) }"
            @click="isEditing(item) ? undefined : onCardClick(item)"
            @contextmenu="openContextMenu($event, item)"
          >
            <div class="card__top">
              <label class="card__check" @click.stop>
                <input type="checkbox" :checked="isSelected(item)" @change="toggle(item)" />
              </label>
              <div class="card__actions" @click.stop>
              <IconButton
                size="sm"
                variant="ghost"
                :aria-label="t('fileTable.aria.more')"
                @click="openMoreMenu($event, item)"
              >
                <MoreHorizontal :size="16" />
              </IconButton>
            </div>
          </div>
            <div class="card__thumb">
              <FileThumbnailIcon :file-id="item.id" :name="item.name" :is-dir="item.is_dir" :size="64" />
            </div>
            <div v-if="!isEditing(item)" class="card__name" :title="item.name">{{ item.name }}</div>
            <input
              v-else
              v-model="renameValue"
              :ref="setRenameInputRef(item)"
              class="card__input"
              :placeholder="t('fileTable.placeholders.rename')"
              autofocus
              @keydown="(event) => onRenameKey(event, item)"
            />
            <div class="card__meta-line">{{ item.is_dir ? formatTime(item.updated_at) : formatBytes(item.size) }}</div>
            <div v-if="isEditing(item)" class="card__meta-line card__meta-line--actions">
              <IconButton size="sm" variant="secondary" :aria-label="t('fileTable.aria.confirm')" @click="confirmRename(item)">
                <Check :size="12" />
              </IconButton>
              <IconButton size="sm" variant="ghost" :aria-label="t('fileTable.aria.cancel')" @click="emit('rename-cancel')">
                <X :size="12" />
              </IconButton>
            </div>
          </article>
        </template>
        <div v-else-if="!creatingFolder && !creatingText" class="grid__empty">{{ t('fileTable.empty') }}</div>
      </div>
      <div v-if="isScrollable" class="overlay-scrollbar" :class="{ 'is-visible': visible }">
        <div
          class="overlay-scrollbar__thumb"
          :style="{ height: `${thumbHeight}px`, transform: `translateY(${thumbTop}px)` }"
          @mousedown="onThumbMouseDown"
        ></div>
      </div>
    </div>
    <div
      v-if="contextMenu.open && contextMenu.entry"
      ref="contextMenuRef"
      class="context-menu"
      role="menu"
      :aria-label="t('common.actions')"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px`, width: `${contextMenu.width}px` }"
      @click.stop
    >
      <template v-for="item in contextMenuItems" :key="item.key">
        <div v-if="item.dividerBefore" class="context-menu__separator"></div>
        <button
          class="context-menu__item"
          :class="{ 'context-menu__item--danger': item.danger }"
          type="button"
          role="menuitem"
          :disabled="item.disabled"
          @click="triggerContextMenuAction(item.action)"
        >
          <span class="context-menu__label">{{ item.label }}</span>
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.grid-shell {
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr;
  height: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  overflow: hidden;
  background: var(--color-surface);
}

.grid__body {
  position: relative;
  min-height: 0;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(136px, 1fr));
  grid-auto-rows: max-content;
  align-content: start;
  gap: 6px;
  min-height: 0;
  height: 100%;
  overflow: auto;
  padding: 6px;
  background: transparent;
}

.grid--empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.grid__bulk {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.grid__bulk-check {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text);
  font-size: 13px;
}

.grid__bulk-selected {
  color: var(--color-muted);
  font-size: 12px;
}

.card {
  position: relative;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  padding: 6px;
  display: grid;
  gap: 4px;
  align-content: start;
  cursor: pointer;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    transform var(--transition-fast);
}

.card--edit {
  background: var(--color-surface-2);
  border-color: var(--color-border);
}

.card:hover {
  background: var(--color-surface-2);
  border-color: var(--color-primary-soft-strong);
  box-shadow: none;
  transform: none;
}

.card.is-selected {
  background: var(--color-surface-2);
  border-color: var(--color-primary);
  box-shadow: none;
}

.card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
}

.card__top--static {
  min-height: 28px;
}

.card__check {
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-fast);
}

.card__check input,
.grid__bulk-check input {
  width: 16px;
  height: 16px;
}

.card:hover .card__check,
.card:focus-within .card__check,
.card.is-selected .card__check {
  opacity: 1;
  pointer-events: auto;
}

.card__thumb {
  display: grid;
  place-items: center;
  min-height: 66px;
  width: 64px;
  justify-self: center;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.card__thumb :deep(.thumb-icon__image) {
  border-radius: var(--radius-md);
}

.card__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.35;
  min-height: calc(1.35em * 2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 64px;
  justify-self: center;
  text-align: center;
}

.card__meta-line {
  color: var(--color-muted);
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 64px;
  justify-self: center;
  text-align: center;
}

.card__meta-line--actions {
  display: inline-flex;
  width: 64px;
  justify-self: center;
  justify-content: center;
  gap: 4px;
}

.card__input {
  width: 100%;
  justify-self: stretch;
  box-sizing: border-box;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 4px 6px;
  font-size: 12px;
  line-height: 1.25;
}

.card__input:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--interaction-focus-ring);
}

.card__actions {
  display: inline-flex;
  gap: 2px;
  opacity: 0;
  pointer-events: none;
  transform: translateY(-2px);
  transition:
    opacity var(--transition-fast),
    transform var(--transition-fast);
}

.card__actions :deep(.icon-btn) {
  color: var(--color-success);
  width: 26px;
  height: 26px;
}

.card:hover .card__actions,
.card:focus-within .card__actions {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.grid__empty {
  text-align: center;
  color: var(--color-muted);
}

.context-menu {
  position: fixed;
  z-index: 100;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-2);
  display: grid;
  gap: var(--space-1);
}

.context-menu__item {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid transparent;
  text-align: left;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text);
}

.context-menu__item:hover {
  background: var(--color-surface-2);
}

.context-menu__item:disabled {
  cursor: not-allowed;
  color: var(--color-muted);
  opacity: 0.72;
}

.context-menu__item:disabled:hover {
  background: transparent;
}

.context-menu__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-menu__separator {
  height: 1px;
  margin: var(--space-1) 0;
  background: var(--color-border);
}

.context-menu__item--danger {
  color: var(--color-danger);
}
</style>
