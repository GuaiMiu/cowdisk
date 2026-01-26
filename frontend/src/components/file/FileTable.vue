<script setup lang="ts">
import { Check, Download, MoreHorizontal, Trash2, X } from 'lucide-vue-next'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ComponentPublicInstance, VNodeRef } from 'vue'
import type { DiskEntry } from '@/types/disk'
import { formatBytes, formatTime } from '@/utils/format'
import IconButton from '@/components/common/IconButton.vue'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { getFileKind } from '@/utils/fileType'

const props = defineProps<{
  items: DiskEntry[]
  selected: Set<string>
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
  (event: 'action', payload: { entry: DiskEntry; action: 'download' | 'rename' | 'delete' | 'share' | 'detail' | 'preview' | 'move' | 'edit' }): void
  (event: 'create-confirm', name: string): void
  (event: 'create-text-confirm', name: string): void
  (event: 'create-cancel'): void
  (event: 'rename-confirm', payload: { entry: DiskEntry; name: string }): void
  (event: 'rename-cancel'): void
}>()

const { t } = useI18n({ useScope: 'global' })

const createName = ref('')
const renameValue = ref('')
const createInputRef = ref<HTMLInputElement | null>(null)
const renameInputRefs = ref(new Map<string, HTMLInputElement>())
const tableRef = ref<HTMLDivElement | null>(null)
const headerRef = ref<HTMLDivElement | null>(null)
const bodyHeight = ref(0)
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

const isEditing = (entry: DiskEntry) => props.editingEntry?.path === entry.path
const isEditableFile = (entry: DiskEntry | null) => {
  if (!entry || entry.is_dir) {
    return false
  }
  const kind = getFileKind(entry.name, entry.is_dir)
  return kind === 'text' || kind === 'code'
}

watch(
  [() => props.creatingFolder, () => props.creatingText],
  ([creatingFolder, creatingText]) => {
    if (creatingFolder || creatingText) {
      createName.value = creatingFolder
        ? t('fileTable.createFolderName')
        : t('fileTable.createTextFileName')
      void nextTick(() => {
        createInputRef.value?.focus()
        createInputRef.value?.select()
      })
    }
  },
)

watch(
  [() => props.editingEntry, () => props.editingName],
  ([entry, name]) => {
    if (!entry) {
      return
    }
    renameValue.value = name ?? entry.name ?? ''
    void nextTick(() => {
      const input = renameInputRefs.value.get(entry.path)
      input?.focus()
      input?.select()
    })
  },
  { immediate: true },
)

watch(
  () => props.items.length,
  () => {
    void nextTick(() => {
      updateMetrics()
    })
  },
)

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
  return (ref: Element | ComponentPublicInstance | null) => {
    const input = ref instanceof HTMLInputElement ? ref : null
    if (input) {
      renameInputRefs.value.set(entry.path, input)
    } else {
      renameInputRefs.value.delete(entry.path)
    }
  }
}

const contextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  entry: null as DiskEntry | null,
  mode: 'full' as 'full' | 'more',
  width: 180,
})
const menuHovering = ref(false)
const menuEntryPath = ref<string | null>(null)
let closeTimer: number | null = null

const closeContextMenu = () => {
  contextMenu.value.open = false
  contextMenu.value.entry = null
  menuEntryPath.value = null
  if (closeTimer) {
    window.clearTimeout(closeTimer)
    closeTimer = null
  }
}

const openContextMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.preventDefault()
  const width = 180
  const height = 210
  const x = Math.min(event.clientX, window.innerWidth - width - 8)
  const y = Math.min(event.clientY, window.innerHeight - height - 8)
  contextMenu.value = { open: true, x, y, entry, mode: 'full', width }
}

const openMoreMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.stopPropagation()
  const width = 140
  const height = 160
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const x = Math.min(rect.left + rect.width / 2 - width / 2, window.innerWidth - width - 8)
  const y = Math.min(rect.bottom + 6, window.innerHeight - height - 8)
  contextMenu.value = { open: true, x, y, entry, mode: 'more', width }
  menuEntryPath.value = entry.path
}

const onMenuEnter = () => {
  menuHovering.value = true
  if (closeTimer) {
    window.clearTimeout(closeTimer)
    closeTimer = null
  }
}

const onMenuLeave = () => {
  menuHovering.value = false
  menuEntryPath.value = null
  closeContextMenu()
}

const onRowLeave = (entry: DiskEntry) => {
  if (contextMenu.value.open && contextMenu.value.entry?.path === entry.path && !menuHovering.value) {
    if (closeTimer) {
      window.clearTimeout(closeTimer)
    }
    closeTimer = window.setTimeout(() => {
      closeContextMenu()
    }, 120)
  }
}

const formatEntryType = (entry: DiskEntry) => {
  if (entry.is_dir) {
    return t('common.folder')
  }
  const name = entry.name || ''
  const parts = name.split('.')
  const ext = parts.length > 1 ? parts[parts.length - 1] : ''
  return ext ? ext.toUpperCase() : t('common.file')
}

const onNameClick = (entry: DiskEntry) => {
  if (entry.is_dir) {
    emit('open', entry)
    return
  }
  emit('action', { entry, action: 'preview' })
}

const onWindowKey = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    closeContextMenu()
  }
}

onMounted(() => {
  window.addEventListener('click', closeContextMenu)
  window.addEventListener('scroll', closeContextMenu, true)
  window.addEventListener('keydown', onWindowKey)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeContextMenu)
  window.removeEventListener('scroll', closeContextMenu, true)
  window.removeEventListener('keydown', onWindowKey)
})

const updateBodyHeight = () => {
  if (!tableRef.value || !headerRef.value) {
    bodyHeight.value = 0
    return
  }
  const next = tableRef.value.clientHeight - headerRef.value.clientHeight
  bodyHeight.value = Math.max(next, 0)
  void nextTick(() => {
    updateMetrics()
  })
}

let observer: ResizeObserver | null = null

onMounted(() => {
  updateBodyHeight()
  observer = new ResizeObserver(updateBodyHeight)
  if (tableRef.value) {
    observer.observe(tableRef.value)
  }
  window.addEventListener('resize', updateBodyHeight)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('resize', updateBodyHeight)
})
</script>

<template>
  <div ref="tableRef" class="table" @click="closeContextMenu">
    <div ref="headerRef" class="table__header">
      <label class="table__cell table__cell--check">
        <input
          type="checkbox"
          :checked="allSelected"
          :indeterminate.prop="indeterminate"
          @change="toggleAll"
        />
      </label>
      <div class="table__cell">{{ t('fileTable.headers.name') }}</div>
      <div class="table__cell table__cell--size">{{ t('fileTable.headers.size') }}</div>
      <div class="table__cell table__cell--type">{{ t('fileTable.headers.type') }}</div>
      <div class="table__cell table__cell--time">{{ t('fileTable.headers.updatedAt') }}</div>
    </div>
    <div
      v-if="items.length || creatingFolder || creatingText"
      class="table__body"
      :style="bodyHeight ? { height: `${bodyHeight}px` } : undefined"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
    >
      <div ref="scrollRef" class="table__scroll overlay-scroll" @scroll="onScroll">
        <div v-if="creatingFolder || creatingText" class="table__row table__row--edit">
          <label class="table__cell table__cell--check">
            <input type="checkbox" disabled />
          </label>
          <div class="table__cell table__cell--name">
            <div class="name name--edit name--inline">
              <FileTypeIcon class="name__icon" :name="creatingText ? 'new.txt' : undefined" :is-dir="creatingFolder" />
              <input
                v-model="createName"
                ref="createInputRef"
                class="name__input"
                :placeholder="t('fileTable.placeholders.newFolder')"
                autofocus
                @keydown="onCreateKey"
              />
              <div class="name__actions">
                <IconButton size="sm" variant="secondary" :aria-label="t('fileTable.aria.confirm')" @click="confirmCreate">
                  <Check :size="14" />
                </IconButton>
                <IconButton size="sm" variant="ghost" :aria-label="t('fileTable.aria.cancel')" @click="emit('create-cancel')">
                  <X :size="14" />
                </IconButton>
              </div>
            </div>
          </div>
          <div class="table__cell table__cell--size">-</div>
          <div class="table__cell table__cell--type">{{ t('common.folder') }}</div>
          <div class="table__cell table__cell--time">-</div>
        </div>

        <div
          v-for="item in items"
          :key="item.path"
          :class="['table__row', isEditing(item) ? 'table__row--edit' : '']"
          @contextmenu="openContextMenu($event, item)"
          @mouseleave="onRowLeave(item)"
        >
          <label class="table__cell table__cell--check">
            <input type="checkbox" :checked="isSelected(item)" @change="toggle(item)" />
          </label>
          <div class="table__cell table__cell--name">
            <button v-if="!isEditing(item)" class="name" type="button" @click="onNameClick(item)">
            <FileTypeIcon class="name__icon" :name="item.name" :is-dir="item.is_dir" />
            <span class="name__text" :title="item.name">{{ item.name }}</span>
          </button>
          <div v-else class="name name--edit name--inline">
            <FileTypeIcon class="name__icon" :name="item.name" :is-dir="item.is_dir" />
            <input
              v-model="renameValue"
              :ref="setRenameInputRef(item)"
              class="name__input"
              :placeholder="t('fileTable.placeholders.rename')"
              autofocus
              @keydown="(event) => onRenameKey(event, item)"
            />
            <div class="name__actions">
              <IconButton size="sm" variant="secondary" :aria-label="t('fileTable.aria.confirm')" @click="confirmRename(item)">
                <Check :size="14" />
              </IconButton>
              <IconButton size="sm" variant="ghost" :aria-label="t('fileTable.aria.cancel')" @click="emit('rename-cancel')">
                <X :size="14" />
              </IconButton>
            </div>
          </div>
          </div>
          <div class="table__cell table__cell--size">{{ item.is_dir ? '-' : formatBytes(item.size) }}</div>
          <div class="table__cell table__cell--type">{{ formatEntryType(item) }}</div>
          <div class="table__cell table__cell--time">{{ formatTime(item.modified_time) }}</div>
          <div
            v-if="!isEditing(item)"
            class="table__row-actions"
            :class="{ 'is-hovered': menuHovering && menuEntryPath === item.path }"
          >
            <IconButton
              size="sm"
              variant="ghost"
              :aria-label="t('fileTable.aria.download')"
              v-permission="'disk:file:download'"
              @click="emit('action', { entry: item, action: 'download' })"
            >
              <Download :size="14" />
            </IconButton>
            <IconButton
              size="sm"
              variant="ghost"
              :aria-label="t('fileTable.aria.delete')"
              v-permission="'disk:file:delete'"
              @click="emit('action', { entry: item, action: 'delete' })"
            >
              <Trash2 :size="14" />
            </IconButton>
            <IconButton
              size="sm"
              variant="ghost"
              :aria-label="t('fileTable.aria.more')"
              @mouseenter="openMoreMenu($event, item)"
              @click="openMoreMenu($event, item)"
            >
              <MoreHorizontal :size="14" />
            </IconButton>
          </div>
        </div>
      </div>
      <div v-if="isScrollable" class="overlay-scrollbar" :class="{ 'is-visible': visible }">
        <div
          class="overlay-scrollbar__thumb"
          :style="{ height: `${thumbHeight}px`, transform: `translateY(${thumbTop}px)` }"
          @mousedown="onThumbMouseDown"
        ></div>
      </div>
    </div>
    <div v-else class="table__empty">{{ t('fileTable.empty') }}</div>

    <div
      v-if="contextMenu.open && contextMenu.entry"
      class="context-menu"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px`, width: `${contextMenu.width}px` }"
      @mouseenter="onMenuEnter"
      @mouseleave="onMenuLeave"
      @click.stop
    >
      <button
        class="context-menu__item"
        type="button"
        @click="emit('action', { entry: contextMenu.entry, action: 'detail' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.details') }}
      </button>
      <button
        class="context-menu__item"
        type="button"
        v-permission="'disk:file:download'"
        @click="emit('action', { entry: contextMenu.entry, action: 'preview' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.preview') }}
      </button>
      <button
        v-if="contextMenu.entry?.is_dir"
        class="context-menu__item"
        type="button"
        v-permission="'disk:file:list'"
        @click="emit('action', { entry: contextMenu.entry, action: 'edit' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.openEditor') }}
      </button>
      <button
        v-else-if="isEditableFile(contextMenu.entry)"
        class="context-menu__item"
        type="button"
        v-permission="'disk:file:download'"
        @click="emit('action', { entry: contextMenu.entry, action: 'edit' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.edit') }}
      </button>
      <button
        v-if="contextMenu.mode === 'full'"
        class="context-menu__item"
        type="button"
        v-permission="'disk:file:download'"
        @click="emit('action', { entry: contextMenu.entry, action: 'download' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.download') }}
      </button>
      <button
        class="context-menu__item"
        type="button"
        v-permission="'disk:file:rename'"
        @click="emit('action', { entry: contextMenu.entry, action: 'rename' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.rename') }}
      </button>
      <button
        class="context-menu__item"
        type="button"
        v-permission="'disk:file:rename'"
        @click="emit('action', { entry: contextMenu.entry, action: 'move' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.move') }}
      </button>
      <button
        class="context-menu__item"
        type="button"
        v-permission="'disk:file:download'"
        @click="emit('action', { entry: contextMenu.entry, action: 'share' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.share') }}
      </button>
      <button
        v-if="contextMenu.mode === 'full'"
        class="context-menu__item context-menu__item--danger"
        type="button"
        v-permission="'disk:file:delete'"
        @click="emit('action', { entry: contextMenu.entry, action: 'delete' }); closeContextMenu()"
      >
        {{ t('fileTable.actions.delete') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.table {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface);
  height: 100%;
}

.table__header,
.table__row {
  display: grid;
  grid-template-columns: 32px minmax(220px, 1fr) 110px 72px 160px;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.table__row {
  height: 48px;
  position: relative;
}

.table__row:hover {
  background: var(--color-surface-2);
}

.table__header {
  font-size: 11px;
  color: var(--color-muted);
  letter-spacing: 0.06em;
}

.table__body {
  display: grid;
  gap: 0;
  position: relative;
  overflow: hidden;
  min-height: 0;
  height: 100%;
  align-content: start;
}

.table__scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: 0;
  align-content: start;
  grid-auto-rows: 48px;
}

.table__cell--check {
  display: flex;
  justify-content: center;
}

.table__cell--name {
  display: flex;
}

.table__cell--type {
  color: var(--color-muted);
  font-size: 12px;
}

.table__cell--size {
  justify-self: start;
  text-align: left;
  font-size: 12px;
  color: var(--color-muted);
}

.table__cell--time {
  font-size: 12px;
  color: var(--color-muted);
}

.name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  color: var(--color-text);
  min-width: 0;
  max-width: 100%;
}

.name--edit {
  width: 100%;
  cursor: default;
}

.name--inline {
  align-items: center;
}

.name__text {
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.name__input {
  flex: 1;
  min-width: 140px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 6px var(--space-3);
  background: var(--color-surface);
  font-size: 14px;
  line-height: 1.2;
}

.name__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: var(--space-3);
}

.table__empty {
  padding: var(--space-7);
  border-top: 1px dashed var(--color-border);
  text-align: center;
  color: var(--color-muted);
}

.table__row--edit {
  background: var(--color-surface-2);
}

.table__row-actions {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-base);
}

.table__row-actions .icon-btn {
  color: var(--color-success);
}

.table__row:hover .table__row-actions,
.table__row--edit .table__row-actions,
.table__row-actions.is-hovered {
  opacity: 1;
  pointer-events: auto;
}

.context-menu {
  position: fixed;
  z-index: 100;
  width: 180px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-2);
  display: grid;
  gap: var(--space-1);
}

.context-menu__item {
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

.context-menu__item--danger {
  color: var(--color-danger);
}

@media (max-width: 1024px) {
  .table__header,
  .table__row {
    grid-template-columns: 32px 1fr 110px 72px;
  }

  .table__cell:nth-child(5) {
    display: none;
  }
}

@media (max-width: 768px) {
  .table__header,
  .table__row {
    grid-template-columns: 32px 1fr;
    padding: var(--space-2) var(--space-3);
  }

  .table__cell:nth-child(3),
  .table__cell:nth-child(4),
  .table__cell:nth-child(5) {
    display: none;
  }

  .table__cell--name {
    padding-right: 92px;
  }

  .table__row-actions {
    position: absolute;
    right: var(--space-3);
    left: auto;
    transform: translateY(-50%);
    opacity: 1;
    pointer-events: auto;
  }
}
</style>
