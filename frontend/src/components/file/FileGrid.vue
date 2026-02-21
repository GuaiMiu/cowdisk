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

type BlankAction =
  | 'new-folder'
  | 'new-text'
  | 'new-word'
  | 'new-excel'
  | 'new-ppt'
  | 'upload-file'
  | 'upload-folder'
type BulkAction = 'move' | 'delete' | 'compress' | 'extract'

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
  officeEnabled?: boolean
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
  (event: 'blank-action', action: BlankAction): void
  (event: 'blank-click'): void
  (event: 'bulk-action', action: BulkAction): void
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
const blankContextMenuRef = ref<HTMLElement | null>(null)
const selectionContextMenuRef = ref<HTMLElement | null>(null)
const contextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  entry: null as DiskEntry | null,
  width: 228,
})
const blankContextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  width: 188,
})
const selectionContextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  width: 212,
})
const itemElementRefs = ref(new Map<string, HTMLElement>())
const isDragSelecting = ref(false)
const dragBox = ref({ left: 0, top: 0, width: 0, height: 0 })
const DRAG_ACTIVATION_DISTANCE = 4
let dragStartX = 0
let dragStartY = 0
let dragCurrentClientX = 0
let dragCurrentClientY = 0
let pendingDragSelection = false
let suppressCardClick = false
let suppressBlankClick = false

const onCardClick = (entry: DiskEntry) => {
  if (suppressCardClick) {
    suppressCardClick = false
    return
  }
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
const blankMenuGroups = computed<
  Array<{
    key: string
    label: string
    children: Array<{ key: string; label: string; action: BlankAction }>
  }>
>(() => {
  const groups: Array<{
    key: string
    label: string
    children: Array<{ key: string; label: string; action: BlankAction }>
  }> = []

  const createChildren: Array<{ key: string; label: string; action: BlankAction }> = []
  if (hasPermission('disk:file:mkdir')) {
    createChildren.push({ key: 'new-folder', label: t('fileToolbar.folder'), action: 'new-folder' })
  }
  if (hasPermission('disk:file:upload')) {
    createChildren.push({ key: 'new-text', label: t('fileToolbar.textFile'), action: 'new-text' })
    if (props.officeEnabled) {
      createChildren.push({ key: 'new-word', label: t('fileToolbar.wordFile'), action: 'new-word' })
      createChildren.push({ key: 'new-excel', label: t('fileToolbar.excelFile'), action: 'new-excel' })
      createChildren.push({ key: 'new-ppt', label: t('fileToolbar.pptFile'), action: 'new-ppt' })
    }
  }
  if (createChildren.length) {
    groups.push({ key: 'create', label: t('fileToolbar.new'), children: createChildren })
  }

  if (hasPermission('disk:file:upload')) {
    groups.push({
      key: 'upload',
      label: t('fileToolbar.upload'),
      children: [
        { key: 'upload-file', label: t('fileToolbar.uploadFile'), action: 'upload-file' },
        { key: 'upload-folder', label: t('fileToolbar.uploadDirectory'), action: 'upload-folder' },
      ],
    })
  }
  return groups
})
const selectionMenuItems = computed<Array<{ key: BulkAction; label: string; danger?: boolean }>>(() => {
  const items: Array<{ key: BulkAction; label: string; danger?: boolean }> = []
  if (hasPermission('disk:file:move')) {
    items.push({ key: 'move', label: t('fileTable.actions.move') })
  }
  if (hasPermission('disk:archive:compress')) {
    items.push({ key: 'compress', label: t('fileTable.actions.compress') })
  }
  if (hasPermission('disk:archive:extract')) {
    items.push({ key: 'extract', label: t('fileTable.actions.extract') })
  }
  if (hasPermission('disk:file:delete')) {
    items.push({ key: 'delete', label: t('fileTable.actions.delete'), danger: true })
  }
  return items
})
const closeContextMenu = () => {
  contextMenu.value.open = false
  contextMenu.value.entry = null
  blankContextMenu.value.open = false
  selectionContextMenu.value.open = false
}
const hasOpenContextMenu = () =>
  contextMenu.value.open || blankContextMenu.value.open || selectionContextMenu.value.open

const isMenuElement = (target: Node | null) =>
  !!target &&
  (contextMenuRef.value?.contains(target) ||
    blankContextMenuRef.value?.contains(target) ||
    selectionContextMenuRef.value?.contains(target))

const isGridBlankTarget = (target: HTMLElement | null) =>
  !!target &&
  !target.closest('.card') &&
  !target.closest('.context-menu') &&
  !target.closest('.overlay-scrollbar')
const openContextMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.preventDefault()
  closeContextMenu()
  if (props.selectedCount > 1 && props.isSelected(entry) && selectionMenuItems.value.length) {
    const width = 212
    const roughHeight = 220
    const x = Math.max(8, Math.min(event.clientX, window.innerWidth - width - 8))
    const y = Math.max(8, Math.min(event.clientY, window.innerHeight - roughHeight - 8))
    selectionContextMenu.value = { open: true, x, y, width }
    return
  }
  const width = 228
  const roughHeight = 320
  const x = Math.max(8, Math.min(event.clientX, window.innerWidth - width - 8))
  const y = Math.max(8, Math.min(event.clientY, window.innerHeight - roughHeight - 8))
  contextMenu.value = { open: true, x, y, entry, width }
}
const openMoreMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.preventDefault()
  event.stopPropagation()
  closeContextMenu()
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
const triggerBlankContextAction = (action: BlankAction) => {
  emit('blank-action', action)
  closeContextMenu()
}
const triggerSelectionAction = (action: BulkAction) => {
  emit('bulk-action', action)
  closeContextMenu()
}
const openBlankContextMenu = (event: MouseEvent) => {
  if (!blankMenuGroups.value.length) {
    return
  }
  event.preventDefault()
  const width = 188
  const roughHeight = 320
  const x = Math.max(8, Math.min(event.clientX, window.innerWidth - width - 8))
  const y = Math.max(8, Math.min(event.clientY, window.innerHeight - roughHeight - 8))
  blankContextMenu.value = { open: true, x, y, width }
}
const onGridBodyContextMenu = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  if (!isGridBlankTarget(target)) {
    return
  }
  openBlankContextMenu(event)
}

const setItemElementRef = (entry: DiskEntry): VNodeRef => {
  return (refNode: Element | ComponentPublicInstance | null) => {
    const element = refNode instanceof HTMLElement ? refNode : null
    const key = String(entry.id)
    if (element) {
      itemElementRefs.value.set(key, element)
      return
    }
    itemElementRefs.value.delete(key)
  }
}

const intersect = (
  a: { left: number; top: number; right: number; bottom: number },
  b: { left: number; top: number; right: number; bottom: number },
) => a.left <= b.right && a.right >= b.left && a.top <= b.bottom && a.bottom >= b.top

const applySelectionState = (selectedKeys: Set<string>) => {
  for (const item of props.items) {
    const key = String(item.id)
    const next = selectedKeys.has(key)
    if (props.isSelected(item) !== next) {
      props.toggle(item)
    }
  }
}

const getContentPoint = (clientX: number, clientY: number) => {
  const container = scrollRef.value
  if (!container) {
    return { x: 0, y: 0 }
  }
  const rect = container.getBoundingClientRect()
  return {
    x: clientX - rect.left + container.scrollLeft,
    y: clientY - rect.top + container.scrollTop,
  }
}

const updateDragSelection = () => {
  const container = scrollRef.value
  if (!container) {
    return
  }
  const startPoint = getContentPoint(dragStartX, dragStartY)
  const currentPoint = getContentPoint(dragCurrentClientX, dragCurrentClientY)
  const left = Math.min(startPoint.x, currentPoint.x)
  const top = Math.min(startPoint.y, currentPoint.y)
  const right = Math.max(startPoint.x, currentPoint.x)
  const bottom = Math.max(startPoint.y, currentPoint.y)
  dragBox.value = {
    left,
    top,
    width: Math.max(0, right - left),
    height: Math.max(0, bottom - top),
  }
  const selectedKeys = new Set<string>()
  const containerRect = container.getBoundingClientRect()
  for (const item of props.items) {
    const key = String(item.id)
    const element = itemElementRefs.value.get(key)
    if (!element) {
      continue
    }
    const rect = element.getBoundingClientRect()
    const itemRect = {
      left: rect.left - containerRect.left + container.scrollLeft,
      top: rect.top - containerRect.top + container.scrollTop,
      right: rect.right - containerRect.left + container.scrollLeft,
      bottom: rect.bottom - containerRect.top + container.scrollTop,
    }
    if (intersect({ left, top, right, bottom }, itemRect)) {
      selectedKeys.add(key)
    }
  }
  applySelectionState(selectedKeys)
}

const onDragPointerMove = (event: PointerEvent) => {
  if (!pendingDragSelection && !isDragSelecting.value) {
    return
  }
  dragCurrentClientX = event.clientX
  dragCurrentClientY = event.clientY
  if (!isDragSelecting.value) {
    const distance = Math.hypot(dragCurrentClientX - dragStartX, dragCurrentClientY - dragStartY)
    if (distance < DRAG_ACTIVATION_DISTANCE) {
      return
    }
    isDragSelecting.value = true
    suppressCardClick = true
    suppressBlankClick = true
    closeContextMenu()
  }
  updateDragSelection()
  event.preventDefault()
}

const stopDragSelection = () => {
  pendingDragSelection = false
  isDragSelecting.value = false
  window.removeEventListener('pointermove', onDragPointerMove)
  window.removeEventListener('pointerup', stopDragSelection)
}

const onGridPointerDown = (event: PointerEvent) => {
  if (event.button !== 0) {
    return
  }
  const target = event.target as HTMLElement | null
  if (
    !target ||
    target.closest('.card') ||
    target.closest('input') ||
    target.closest('button') ||
    target.closest('.context-menu')
  ) {
    return
  }
  closeContextMenu()
  dragStartX = event.clientX
  dragStartY = event.clientY
  dragCurrentClientX = event.clientX
  dragCurrentClientY = event.clientY
  pendingDragSelection = true
  suppressCardClick = false
  window.addEventListener('pointermove', onDragPointerMove)
  window.addEventListener('pointerup', stopDragSelection)
  event.preventDefault()
}

const onGridBodyClick = (event: MouseEvent) => {
  if (suppressBlankClick) {
    suppressBlankClick = false
    return
  }
  const target = event.target as HTMLElement | null
  if (!isGridBlankTarget(target)) {
    return
  }
  closeContextMenu()
  emit('blank-click')
}

const dragBoxStyle = computed(() => ({
  left: `${dragBox.value.left}px`,
  top: `${dragBox.value.top}px`,
  width: `${dragBox.value.width}px`,
  height: `${dragBox.value.height}px`,
}))

const onWindowPointerDown = (event: MouseEvent) => {
  if (!hasOpenContextMenu()) {
    return
  }
  const target = event?.target as Node | null
  if (isMenuElement(target)) {
    return
  }
  closeContextMenu()
}
const onWindowKeyDown = (event: KeyboardEvent) => {
  if (!hasOpenContextMenu()) {
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
  stopDragSelection()
  window.removeEventListener('mousedown', onWindowPointerDown)
  window.removeEventListener('keydown', onWindowKeyDown)
})

</script>

<template>
  <div
    class="grid-shell"
    :class="{ 'is-drag-selecting': isDragSelecting || pendingDragSelection }"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
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
    <div class="grid__body" @contextmenu="onGridBodyContextMenu" @click="onGridBodyClick">
      <div
        ref="scrollRef"
        class="grid overlay-scroll"
        :class="{
          'grid--empty': !items.length && !creatingFolder && !creatingText,
          'grid--drag-selecting': isDragSelecting || pendingDragSelection,
        }"
        @scroll="onScroll"
        @pointerdown="onGridPointerDown"
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
            :ref="setItemElementRef(item)"
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
        <div
          v-if="isDragSelecting"
          class="grid__selection-box"
          :style="dragBoxStyle"
        ></div>
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
    <div
      v-if="blankContextMenu.open"
      ref="blankContextMenuRef"
      class="context-menu"
      role="menu"
      :aria-label="t('common.actions')"
      :style="{ left: `${blankContextMenu.x}px`, top: `${blankContextMenu.y}px`, width: `${blankContextMenu.width}px` }"
      @click.stop
    >
      <div
        v-for="group in blankMenuGroups"
        :key="group.key"
        class="context-menu__item context-menu__item--submenu"
        role="menuitem"
        tabindex="0"
      >
        <span class="context-menu__label">{{ group.label }}</span>
        <span class="context-menu__arrow">›</span>
        <div class="context-menu__submenu">
          <button
            v-for="item in group.children"
            :key="item.key"
            class="context-menu__item"
            type="button"
            role="menuitem"
            @click="triggerBlankContextAction(item.action)"
          >
            <span class="context-menu__label">{{ item.label }}</span>
          </button>
        </div>
      </div>
    </div>
    <div
      v-if="selectionContextMenu.open"
      ref="selectionContextMenuRef"
      class="context-menu"
      role="menu"
      :aria-label="t('common.actions')"
      :style="{ left: `${selectionContextMenu.x}px`, top: `${selectionContextMenu.y}px`, width: `${selectionContextMenu.width}px` }"
      @click.stop
    >
      <button
        v-for="item in selectionMenuItems"
        :key="item.key"
        class="context-menu__item"
        :class="{ 'context-menu__item--danger': item.danger }"
        type="button"
        role="menuitem"
        @click="triggerSelectionAction(item.key)"
      >
        <span class="context-menu__label">{{ item.label }}</span>
      </button>
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
  position: relative;
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

.grid__selection-box {
  position: absolute;
  z-index: 2;
  border: 1px solid var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 22%, transparent);
  pointer-events: none;
}

.grid--drag-selecting {
  user-select: none;
  -webkit-user-select: none;
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
  overflow-wrap: anywhere;
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

.grid-shell.is-drag-selecting .card__actions {
  opacity: 0 !important;
  pointer-events: none !important;
  transform: translateY(-2px) !important;
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

.context-menu__item--submenu {
  position: relative;
}

.context-menu__arrow {
  color: var(--color-muted);
}

.context-menu__submenu {
  position: absolute;
  left: 100%;
  top: -6px;
  min-width: 156px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-2);
  display: none;
  gap: var(--space-1);
}

.context-menu__item--submenu:hover .context-menu__submenu,
.context-menu__item--submenu:focus-within .context-menu__submenu {
  display: grid;
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
