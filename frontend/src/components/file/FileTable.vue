<script setup lang="ts">
import { Check, Download, MoreHorizontal, Share2, Trash2, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ComponentPublicInstance, VNodeRef } from 'vue'
import type { DiskEntry } from '@/types/disk'
import { formatBytes, formatTime } from '@/utils/format'
import IconButton from '@/components/common/IconButton.vue'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import FileThumbnailIcon from '@/components/file/FileThumbnailIcon.vue'
import {
  useFileEntryActionsMenu,
  type FileEntryAction,
} from '@/components/file/composables/useFileEntryActionsMenu'
import { getFileKind } from '@/utils/fileType'
import { useAuthStore } from '@/stores/auth'

type SortKey = 'name' | 'size' | 'type' | 'updatedAt'
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
  sortKey?: SortKey | null
  sortOrder?: 'asc' | 'desc' | null
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
  (event: 'sort-change', key: SortKey): void
  (event: 'blank-action', action: BlankAction): void
  (event: 'blank-click'): void
  (event: 'bulk-action', action: BulkAction): void
}>()

const { t } = useI18n({ useScope: 'global' })
const authStore = useAuthStore()
const sortableKeys: SortKey[] = ['name', 'size', 'type', 'updatedAt']

const isSortable = (key: SortKey) => sortableKeys.includes(key)

const onSortClick = (key: SortKey) => {
  if (!isSortable(key)) {
    return
  }
  emit('sort-change', key)
}

const sortIndicator = (key: SortKey) => {
  if (props.sortKey !== key) {
    return ''
  }
  return props.sortOrder === 'asc' ? 'asc' : 'desc'
}

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

const isEditing = (entry: DiskEntry) => props.editingEntry?.id === entry.id
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
      const input = renameInputRefs.value.get(String(entry.id))
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
      renameInputRefs.value.set(String(entry.id), input)
    } else {
      renameInputRefs.value.delete(String(entry.id))
    }
  }
}

const contextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  entry: null as DiskEntry | null,
  mode: 'full' as 'full' | 'more',
  width: 228,
})
const contextMenuRef = ref<HTMLElement | null>(null)
const selectionContextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  width: 212,
})
const menuHovering = ref(false)
const menuEntryPath = ref<string | null>(null)
const itemElementRefs = ref(new Map<string, HTMLElement>())
const isDragSelecting = ref(false)
const dragBox = ref({ left: 0, top: 0, width: 0, height: 0 })
const DRAG_ACTIVATION_DISTANCE = 4
let dragStartX = 0
let dragStartY = 0
let dragCurrentClientX = 0
let dragCurrentClientY = 0
let pendingDragSelection = false
let suppressRowClick = false
let suppressBlankClick = false
let closeTimer: number | null = null
const MENU_VIEWPORT_PADDING = 8

const hasPermission = (permission?: string) => {
  if (!permission) {
    return true
  }
  return authStore.hasPerm(permission)
}

const contextMenuItems = useFileEntryActionsMenu({
  entry: computed(() => contextMenu.value.entry),
  mode: computed(() => contextMenu.value.mode),
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
  menuEntryPath.value = null
  if (closeTimer) {
    window.clearTimeout(closeTimer)
    closeTimer = null
  }
}
const isTableBlankTarget = (target: HTMLElement | null) =>
  !!target &&
  !target.closest('.table__row') &&
  !target.closest('.table__header') &&
  !target.closest('.context-menu') &&
  !target.closest('.overlay-scrollbar')

const focusFirstMenuItem = () => {
  void nextTick(() => {
    const first = contextMenuRef.value?.querySelector<HTMLElement>(
      '.context-menu__item[data-menu-item]:not(:disabled):not([hidden])',
    )
    first?.focus()
  })
}

const clampMenuPosition = (x: number, y: number, width: number, height: number) => {
  return {
    x: Math.max(MENU_VIEWPORT_PADDING, Math.min(x, window.innerWidth - width - MENU_VIEWPORT_PADDING)),
    y: Math.max(MENU_VIEWPORT_PADDING, Math.min(y, window.innerHeight - height - MENU_VIEWPORT_PADDING)),
  }
}

const realignContextMenu = () => {
  void nextTick(() => {
    if (!contextMenu.value.open || !contextMenuRef.value) {
      return
    }
    const menuWidth = contextMenuRef.value.offsetWidth || contextMenu.value.width
    const menuHeight = contextMenuRef.value.offsetHeight || 260
    const next = clampMenuPosition(contextMenu.value.x, contextMenu.value.y, menuWidth, menuHeight)
    contextMenu.value = { ...contextMenu.value, ...next, width: menuWidth }
  })
}

const openContextMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.preventDefault()
  closeContextMenu()
  if (props.selectedCount > 1 && props.isSelected(entry) && selectionMenuItems.value.length) {
    const width = 212
    const roughHeight = 220
    const { x, y } = clampMenuPosition(event.clientX, event.clientY, width, roughHeight)
    selectionContextMenu.value = { open: true, x, y, width }
    return
  }
  const width = 228
  const roughHeight = 320
  const { x, y } = clampMenuPosition(event.clientX, event.clientY, width, roughHeight)
  contextMenu.value = { open: true, x, y, entry, mode: 'full', width }
  focusFirstMenuItem()
  realignContextMenu()
}

const blankContextMenu = ref({
  open: false,
  x: 0,
  y: 0,
  width: 188,
})

const openBlankContextMenu = (event: MouseEvent) => {
  if (!blankMenuGroups.value.length) {
    return
  }
  event.preventDefault()
  closeContextMenu()
  const width = 188
  const roughHeight = 320
  const { x, y } = clampMenuPosition(event.clientX, event.clientY, width, roughHeight)
  blankContextMenu.value = { open: true, x, y, width }
}

const onTableContextMenu = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  if (!isTableBlankTarget(target)) {
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
    suppressRowClick = true
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

const onTablePointerDown = (event: PointerEvent) => {
  if (event.button !== 0) {
    return
  }
  const target = event.target as HTMLElement | null
  if (
    !target ||
    target.closest('.table__row') ||
    target.closest('.table__header') ||
    target.closest('input') ||
    target.closest('button') ||
    target.closest('.context-menu')
  ) {
    return
  }
  dragStartX = event.clientX
  dragStartY = event.clientY
  dragCurrentClientX = event.clientX
  dragCurrentClientY = event.clientY
  pendingDragSelection = true
  suppressRowClick = false
  window.addEventListener('pointermove', onDragPointerMove)
  window.addEventListener('pointerup', stopDragSelection)
  event.preventDefault()
}

const onTableBlankClick = (event: MouseEvent) => {
  if (suppressBlankClick) {
    suppressBlankClick = false
    return
  }
  const target = event.target as HTMLElement | null
  if (!isTableBlankTarget(target)) {
    return
  }
  emit('blank-click')
}

const onTableClick = (event: MouseEvent) => {
  closeContextMenu()
  onTableBlankClick(event)
}

const dragBoxStyle = computed(() => ({
  left: `${dragBox.value.left}px`,
  top: `${dragBox.value.top}px`,
  width: `${dragBox.value.width}px`,
  height: `${dragBox.value.height}px`,
}))

const openContextMenuAtElement = (element: HTMLElement, entry: DiskEntry, mode: 'full' | 'more') => {
  closeContextMenu()
  const width = mode === 'more' ? 212 : 228
  const roughHeight = mode === 'more' ? 260 : 320
  const rect = element.getBoundingClientRect()
  const anchorX = rect.left + rect.width / 2 - width / 2
  const anchorY = rect.bottom + 6
  const { x, y } = clampMenuPosition(anchorX, anchorY, width, roughHeight)
  contextMenu.value = { open: true, x, y, entry, mode, width }
  menuEntryPath.value = String(entry.id)
  focusFirstMenuItem()
  realignContextMenu()
}

const openMoreMenu = (event: MouseEvent, entry: DiskEntry) => {
  event.stopPropagation()
  closeContextMenu()
  const width = 212
  const roughHeight = 260
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const x = Math.max(
    MENU_VIEWPORT_PADDING,
    Math.min(rect.right - width, window.innerWidth - width - MENU_VIEWPORT_PADDING),
  )
  const spaceBelow = window.innerHeight - rect.bottom
  const spaceAbove = rect.top
  const preferTop = spaceBelow < roughHeight + 12 && spaceAbove > spaceBelow
  const y = preferTop
    ? Math.max(rect.top - roughHeight - 6, MENU_VIEWPORT_PADDING)
    : Math.min(rect.bottom + 6, window.innerHeight - roughHeight - MENU_VIEWPORT_PADDING)
  contextMenu.value = { open: true, x, y, entry, mode: 'more', width }
  menuEntryPath.value = String(entry.id)
  focusFirstMenuItem()
  realignContextMenu()
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
  if (contextMenu.value.mode === 'more') {
    closeContextMenu()
  }
}

const onRowLeave = (entry: DiskEntry) => {
  if (
    contextMenu.value.open &&
    contextMenu.value.entry?.id === entry.id &&
    contextMenu.value.mode === 'more' &&
    !menuHovering.value
  ) {
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
  const kind = getFileKind(entry.name, entry.is_dir)
  const map: Record<string, string> = {
    image: t('fileTable.types.image'),
    video: t('fileTable.types.video'),
    audio: t('fileTable.types.audio'),
    pdf: t('fileTable.types.pdf'),
    doc: t('fileTable.types.doc'),
    sheet: t('fileTable.types.sheet'),
    slide: t('fileTable.types.slide'),
    archive: t('fileTable.types.archive'),
    code: t('fileTable.types.code'),
    text: t('fileTable.types.text'),
    other: t('fileTable.types.other'),
  }
  return map[kind] || t('fileTable.types.other')
}

const onNameClick = (entry: DiskEntry) => {
  if (entry.is_dir) {
    emit('open', entry)
    return
  }
  emit('action', { entry, action: 'preview' })
}

const onRowClick = (entry: DiskEntry) => {
  if (suppressRowClick) {
    suppressRowClick = false
    return
  }
  props.toggle(entry)
}

const onRowKeyDown = (event: KeyboardEvent, entry: DiskEntry) => {
  const current = event.target as HTMLElement | null
  if (!current) {
    return
  }
  if (
    current.closest('button') ||
    current.closest('input') ||
    current.closest('textarea') ||
    current.closest('select')
  ) {
    return
  }
  if (event.key === ' ') {
    event.preventDefault()
    props.toggle(entry)
    return
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    onNameClick(entry)
    return
  }
  if ((event.shiftKey && event.key === 'F10') || event.key === 'ContextMenu') {
    event.preventDefault()
    openContextMenuAtElement(event.currentTarget as HTMLElement, entry, 'full')
  }
}

const onContextMenuKeyDown = (event: KeyboardEvent) => {
  if (!contextMenu.value.open) {
    return
  }
  const items = Array.from(
    contextMenuRef.value?.querySelectorAll<HTMLElement>(
      '.context-menu__item[data-menu-item]:not(:disabled):not([hidden])',
    ) ?? [],
  )
  if (!items.length) {
    return
  }
  const active = document.activeElement as HTMLElement | null
  const currentIndex = items.findIndex((item) => item === active)
  const safeIndex = currentIndex < 0 ? 0 : currentIndex
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    const next = (safeIndex + 1) % items.length
    items[next]?.focus()
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    const next = (safeIndex - 1 + items.length) % items.length
    items[next]?.focus()
    return
  }
  if (event.key === 'Home') {
    event.preventDefault()
    items[0]?.focus()
    return
  }
  if (event.key === 'End') {
    event.preventDefault()
    items[items.length - 1]?.focus()
    return
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    closeContextMenu()
  }
}

const onWindowKey = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    closeContextMenu()
  }
}

const triggerContextMenuAction = (action: FileEntryAction) => {
  if (!contextMenu.value.entry) {
    return
  }
  emit('action', { entry: contextMenu.value.entry, action })
  closeContextMenu()
}

const triggerBlankContextAction = (action: BlankAction) => {
  emit('blank-action', action)
  closeContextMenu()
}
const triggerSelectionAction = (action: BulkAction) => {
  emit('bulk-action', action)
  closeContextMenu()
}

onMounted(() => {
  window.addEventListener('click', closeContextMenu)
  window.addEventListener('scroll', closeContextMenu, true)
  window.addEventListener('keydown', onWindowKey)
})

onBeforeUnmount(() => {
  stopDragSelection()
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
  <div
    ref="tableRef"
    class="table"
    :class="{ 'is-drag-selecting': isDragSelecting || pendingDragSelection }"
    @click="onTableClick"
    @contextmenu="onTableContextMenu"
  >
    <div ref="headerRef" class="table__header">
      <label class="table__cell table__cell--check">
        <input
          type="checkbox"
          :checked="allSelected"
          :indeterminate.prop="indeterminate"
          @change="toggleAll"
        />
      </label>
      <div class="table__cell">
        <button
          type="button"
          class="table__sort"
          :class="[`is-${sortIndicator('name')}`, { 'is-active': props.sortKey === 'name' }]"
          @click="onSortClick('name')"
        >
          {{ t('fileTable.headers.name') }}
          <span class="table__sort-indicator"></span>
        </button>
      </div>
      <div class="table__cell table__cell--size">
        <button
          type="button"
          class="table__sort"
          :class="[`is-${sortIndicator('size')}`, { 'is-active': props.sortKey === 'size' }]"
          @click="onSortClick('size')"
        >
          {{ t('fileTable.headers.size') }}
          <span class="table__sort-indicator"></span>
        </button>
      </div>
      <div class="table__cell table__cell--type">
        <button
          type="button"
          class="table__sort"
          :class="[`is-${sortIndicator('type')}`, { 'is-active': props.sortKey === 'type' }]"
          @click="onSortClick('type')"
        >
          {{ t('fileTable.headers.type') }}
          <span class="table__sort-indicator"></span>
        </button>
      </div>
      <div class="table__cell table__cell--time">
        <button
          type="button"
          class="table__sort"
          :class="[`is-${sortIndicator('updatedAt')}`, { 'is-active': props.sortKey === 'updatedAt' }]"
          @click="onSortClick('updatedAt')"
        >
          {{ t('fileTable.headers.updatedAt') }}
          <span class="table__sort-indicator"></span>
        </button>
      </div>
    </div>
    <div
      v-if="items.length || creatingFolder || creatingText"
      class="table__body"
      :style="bodyHeight ? { height: `${bodyHeight}px` } : undefined"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
    >
      <div
        ref="scrollRef"
        class="table__scroll overlay-scroll"
        :class="{ 'table__scroll--drag-selecting': isDragSelecting || pendingDragSelection }"
        @scroll="onScroll"
        @pointerdown="onTablePointerDown"
      >
        <div v-if="creatingFolder || creatingText" class="table__row table__row--edit">
          <label class="table__cell table__cell--check">
            <input type="checkbox" disabled />
          </label>
          <div class="table__cell table__cell--name">
            <div class="name name--edit name--inline">
              <FileTypeIcon
                class="name__icon"
                :name="creatingText ? 'new.txt' : undefined"
                :is-dir="creatingFolder"
                :size="24"
              />
              <input
                v-model="createName"
                ref="createInputRef"
                class="name__input"
                :placeholder="t('fileTable.placeholders.newFolder')"
                autofocus
                @keydown="onCreateKey"
              />
              <div class="name__actions">
                <IconButton
                  size="sm"
                  variant="secondary"
                  :aria-label="t('fileTable.aria.confirm')"
                  @click="confirmCreate"
                >
                  <Check :size="14" />
                </IconButton>
                <IconButton
                  size="sm"
                  variant="ghost"
                  :aria-label="t('fileTable.aria.cancel')"
                  @click="emit('create-cancel')"
                >
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
          :key="item.id"
          :ref="setItemElementRef(item)"
          :class="[
            'table__row',
            isEditing(item) ? 'table__row--edit' : '',
            isSelected(item) ? 'table__row--selected' : '',
          ]"
          :tabindex="isEditing(item) ? -1 : 0"
          @click="onRowClick(item)"
          @keydown="onRowKeyDown($event, item)"
          @contextmenu="openContextMenu($event, item)"
          @mouseleave="onRowLeave(item)"
        >
          <label class="table__cell table__cell--check" @click.stop>
            <input type="checkbox" :checked="isSelected(item)" @click.stop @change="toggle(item)" />
          </label>
          <div class="table__cell table__cell--name">
            <button
              v-if="!isEditing(item)"
              class="name"
              type="button"
              @click.stop="onNameClick(item)"
            >
              <FileThumbnailIcon
                class="name__icon"
                :file-id="item.id"
                :name="item.name"
                :is-dir="item.is_dir"
                :size="24"
              />
              <span class="name__text" :title="item.name">{{ item.name }}</span>
            </button>
            <div v-else class="name name--edit name--inline">
              <FileThumbnailIcon
                class="name__icon"
                :file-id="item.id"
                :name="item.name"
                :is-dir="item.is_dir"
                :size="24"
              />
              <input
                v-model="renameValue"
                :ref="setRenameInputRef(item)"
                class="name__input"
                :placeholder="t('fileTable.placeholders.rename')"
                autofocus
                @keydown="(event) => onRenameKey(event, item)"
              />
              <div class="name__actions">
                <IconButton
                  size="sm"
                  variant="secondary"
                  :aria-label="t('fileTable.aria.confirm')"
                  @click="confirmRename(item)"
                >
                  <Check :size="14" />
                </IconButton>
                <IconButton
                  size="sm"
                  variant="ghost"
                  :aria-label="t('fileTable.aria.cancel')"
                  @click="emit('rename-cancel')"
                >
                  <X :size="14" />
                </IconButton>
              </div>
            </div>
          </div>
          <div class="table__cell table__cell--size">
            {{ item.is_dir ? '-' : formatBytes(item.size) }}
          </div>
          <div class="table__cell table__cell--type">{{ formatEntryType(item) }}</div>
          <div class="table__cell table__cell--time">{{ formatTime(item.updated_at) }}</div>
          <div
            v-if="!isEditing(item)"
            class="table__row-actions"
            :class="{ 'is-hovered': menuHovering && menuEntryPath === String(item.id) }"
            @click.stop
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
              :aria-label="t('fileTable.actions.share')"
              v-permission="'disk:file:download'"
              @click="emit('action', { entry: item, action: 'share' })"
            >
              <Share2 :size="14" />
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
        <div
          v-if="isDragSelecting"
          class="table__selection-box"
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
    <div v-else class="table__empty">{{ t('fileTable.empty') }}</div>

    <div
      v-if="contextMenu.open && contextMenu.entry"
      ref="contextMenuRef"
      class="context-menu"
      role="menu"
      :aria-label="t('common.actions')"
      :style="{
        left: `${contextMenu.x}px`,
        top: `${contextMenu.y}px`,
        width: `${contextMenu.width}px`,
      }"
      @keydown="onContextMenuKeyDown"
      @mouseenter="onMenuEnter"
      @mouseleave="onMenuLeave"
      @click.stop
    >
      <template v-for="item in contextMenuItems" :key="item.key">
        <div v-if="item.dividerBefore" class="context-menu__separator"></div>
        <button
          class="context-menu__item"
          :class="{ 'context-menu__item--danger': item.danger }"
          type="button"
          role="menuitem"
          data-menu-item
          :disabled="item.disabled"
          @click="triggerContextMenuAction(item.action)"
        >
          <span class="context-menu__label">{{ item.label }}</span>
        </button>
      </template>
    </div>

    <div
      v-if="blankContextMenu.open"
      class="context-menu"
      role="menu"
      :aria-label="t('common.actions')"
      :style="{
        left: `${blankContextMenu.x}px`,
        top: `${blankContextMenu.y}px`,
        width: `${blankContextMenu.width}px`,
      }"
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
      class="context-menu"
      role="menu"
      :aria-label="t('common.actions')"
      :style="{
        left: `${selectionContextMenu.x}px`,
        top: `${selectionContextMenu.y}px`,
        width: `${selectionContextMenu.width}px`,
      }"
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
  transition: background var(--transition-fast);
}

.table__row:hover {
  background: var(--color-surface-2);
}

.table__row--selected {
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
}

.table__row:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
  background: var(--color-surface-2);
}

.table__header {
  font-size: 11px;
  color: var(--color-muted);
  letter-spacing: 0.06em;
}

.table__sort {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: transparent;
  border: 0;
  padding: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.table__sort-indicator {
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 6px solid var(--color-muted);
  opacity: 0;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.table__sort.is-active .table__sort-indicator {
  opacity: 1;
}

.table__sort.is-asc .table__sort-indicator {
  transform: rotate(180deg);
}

.table__sort.is-desc .table__sort-indicator {
  transform: rotate(0deg);
}

.table__body {
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  position: relative;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.table__scroll {
  position: relative;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: 0;
  align-content: start;
  grid-auto-rows: 48px;
}

.table__selection-box {
  position: absolute;
  z-index: 2;
  border: 1px solid var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 22%, transparent);
  pointer-events: none;
}

.table__scroll--drag-selecting {
  user-select: none;
  -webkit-user-select: none;
}

.table__cell--check {
  display: flex;
  justify-content: center;
}

.table__cell--name {
  display: flex;
  overflow: hidden;
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
  transition: color var(--transition-fast);
}

.name:hover .name__text {
  color: var(--color-primary);
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
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    background var(--transition-base);
}

.name__input:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--interaction-focus-ring);
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
  transform: translate(-50%, -50%) scale(0.96);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  opacity: 0;
  pointer-events: none;
  transition:
    opacity var(--transition-base),
    transform var(--transition-base);
}

.table__row-actions .icon-btn {
  color: var(--color-success);
}

.table__row:hover .table__row-actions,
.table__row--edit .table__row-actions,
.table__row-actions.is-hovered {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
  pointer-events: auto;
}

.table.is-drag-selecting .table__row-actions {
  opacity: 0 !important;
  pointer-events: none !important;
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
  transition:
    background var(--transition-fast),
    color var(--transition-fast);
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

.context-menu__item:focus-visible {
  outline: none;
  border-color: var(--color-primary-soft-strong);
  background: var(--color-surface-2);
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

  .table__row:hover .table__row-actions,
  .table__row--edit .table__row-actions,
  .table__row-actions.is-hovered {
    transform: translateY(-50%);
  }
}
</style>
