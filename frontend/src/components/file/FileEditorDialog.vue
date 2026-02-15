<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import TextEditor from '@/components/common/TextEditor.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import Dropdown from '@/components/common/Dropdown.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { listDir } from '@/api/modules/userDisk'
import type { DiskEntry } from '@/types/disk'
import { getFileKind } from '@/utils/fileType'
import {
  ChevronDown,
  ChevronRight,
  Maximize2,
  Minimize2,
  PanelLeftClose,
  PanelLeftOpen,
  Save,
  SlidersHorizontal,
  X,
} from 'lucide-vue-next'

type TreeNode = {
  id: number | null
  name: string
  isDir: boolean
  children: TreeNode[]
  expanded: boolean
  loading: boolean
  loaded: boolean
  editable: boolean
}

const props = withDefaults(
  defineProps<{
    open: boolean
    rootId: number | null
    rootName?: string
    activeId?: number | null
    language?: string
    modelValue: string
    loading?: boolean
    saving?: boolean
    dirty?: boolean
  }>(),
  {
    rootName: '',
    activeId: null,
    language: 'plaintext',
    loading: false,
    saving: false,
    dirty: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'select', payload: { fileId: number; name: string }): void
  (event: 'save'): void
  (event: 'close'): void
}>()

const { t } = useI18n({ useScope: 'global' })

const rootLabel = computed(() => props.rootName || t('files.rootName'))
const sidebarOpen = ref(true)
const searchQuery = ref('')
const theme = ref<'vscode-light' | 'vscode-dark'>('vscode-dark')
const wordWrap = ref(true)
const minimap = ref(false)
const lineNumbers = ref(true)
const indentGuides = ref(true)
const fontSize = ref(13)
const fontSizes = [12, 13, 14, 15, 16]

const unsavedConfirmOpen = ref(false)
const pendingClose = ref(false)
const pendingSelect = ref<{ fileId: number; name: string } | null>(null)
const isFullscreen = ref(false)

const rootNode = ref<TreeNode>({
  id: null,
  name: rootLabel.value,
  isDir: true,
  children: [],
  expanded: true,
  loading: false,
  loaded: false,
  editable: false,
})

const buildNode = (entry: DiskEntry): TreeNode => {
  const kind = getFileKind(entry.name, entry.is_dir)
  return {
    id: entry.id,
    name: entry.name,
    isDir: entry.is_dir,
    children: [],
    expanded: false,
    loading: false,
    loaded: false,
    editable: !entry.is_dir && (kind === 'text' || kind === 'code'),
  }
}

const loadChildren = async (node: TreeNode) => {
  if (node.loading || node.loaded) {
    return
  }
  node.loading = true
  try {
    const data = await listDir(node.id ?? null)
    node.children = (data.items || []).map((item) => buildNode(item))
    node.loaded = true
  } finally {
    node.loading = false
  }
}

const toggleNode = async (node: TreeNode) => {
  if (!node.isDir) {
    return
  }
  if (node.expanded) {
    node.expanded = false
    return
  }
  node.expanded = true
  await loadChildren(node)
}

const resetPendingAction = () => {
  pendingClose.value = false
  pendingSelect.value = null
}

const requestClose = () => {
  if (props.dirty) {
    pendingClose.value = true
    unsavedConfirmOpen.value = true
    return
  }
  emit('close')
}

const requestSelect = (payload: { fileId: number; name: string }) => {
  if (!props.dirty || props.activeId === payload.fileId) {
    emit('select', payload)
    return
  }
  pendingSelect.value = payload
  unsavedConfirmOpen.value = true
}

const confirmDiscardChanges = () => {
  const nextSelect = pendingSelect.value
  const shouldClose = pendingClose.value
  unsavedConfirmOpen.value = false
  resetPendingAction()
  if (nextSelect) {
    emit('select', nextSelect)
    return
  }
  if (shouldClose) {
    emit('close')
  }
}

const cancelDiscardChanges = () => {
  unsavedConfirmOpen.value = false
  resetPendingAction()
}

const onNodeClick = (node: TreeNode) => {
  if (node.isDir) {
    void toggleNode(node)
    return
  }
  if (!node.editable || node.id === null) {
    return
  }
  requestSelect({ fileId: node.id, name: node.name })
}

const flatNodes = computed(() => {
  const rows: Array<{ node: TreeNode; level: number }> = []
  const walk = (nodes: TreeNode[], level: number) => {
    nodes.forEach((node) => {
      rows.push({ node, level })
      if (node.expanded && node.children.length) {
        walk(node.children, level + 1)
      }
    })
  }
  walk([rootNode.value], 0)
  return rows
})

const visibleNodes = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) {
    return flatNodes.value
  }
  return flatNodes.value.filter(({ node }) => node.name.toLowerCase().includes(keyword))
})

const activeFileName = computed(() => {
  const hit = flatNodes.value.find(({ node }) => node.id === props.activeId)
  return hit?.node.name || ''
})

const activeTabTitle = computed(() =>
  props.activeId ? activeFileName.value || 'untitled' : t('fileEditorDialog.placeholderSelect'),
)

const findNodePath = (node: TreeNode, fileId: number): string[] | null => {
  if (node.id === fileId) {
    return [node.name]
  }
  for (const child of node.children) {
    const childPath = findNodePath(child, fileId)
    if (childPath) {
      return [node.name, ...childPath]
    }
  }
  return null
}

const breadcrumbItems = computed(() => {
  if (!props.activeId) {
    return [rootLabel.value]
  }
  const path = findNodePath(rootNode.value, props.activeId)
  if (!path || !path.length) {
    return [rootLabel.value, activeFileName.value || '']
  }
  return path[0] === rootLabel.value ? path : [rootLabel.value, ...path]
})

const onKeyDown = (event: KeyboardEvent) => {
  if (!props.open) {
    return
  }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'b') {
    event.preventDefault()
    sidebarOpen.value = !sidebarOpen.value
    return
  }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    emit('save')
    return
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    requestClose()
  }
}

const toggleFullscreen = async () => {
  isFullscreen.value = !isFullscreen.value
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      window.addEventListener('keydown', onKeyDown)
      document.body.style.overflow = 'hidden'
    } else {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
      isFullscreen.value = false
    }
  },
  { immediate: true },
)

watch(rootLabel, (value) => {
  if (rootNode.value.id === (props.rootId ?? null)) {
    rootNode.value.name = value
  }
})

watch(
  () => [props.open, props.rootId, props.rootName],
  ([open]) => {
    if (!open) {
      return
    }
    rootNode.value = {
      id: props.rootId ?? null,
      name: rootLabel.value,
      isDir: true,
      children: [],
      expanded: true,
      loading: false,
      loaded: false,
      editable: false,
    }
    void loadChildren(rootNode.value)
  },
)

watch(
  () => props.open,
  (open) => {
    if (!open) {
      unsavedConfirmOpen.value = false
      resetPendingAction()
    }
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  document.body.style.overflow = ''
})
</script>

<template>
  <teleport to="body">
    <div v-if="open" class="vscode-overlay" :class="{ 'is-maximized': isFullscreen }">
      <div class="vscode-window" :class="{ 'is-light': theme === 'vscode-light', 'is-maximized': isFullscreen }">
        <header class="titlebar">
          <div class="titlebar__left">CowDisk Editor</div>
          <div class="titlebar__center" :title="activeTabTitle">{{ activeTabTitle }}</div>
          <div class="titlebar__right">
            <Dropdown align="right" :width="260">
              <template #trigger>
                <button
                  class="titlebar__btn"
                  type="button"
                  :title="t('fileEditorDialog.tooltipSettings')"
                  :aria-label="t('fileEditorDialog.tooltipSettings')"
                >
                  <SlidersHorizontal :size="14" />
                </button>
              </template>
              <template #content>
                <div class="settings-menu" @click.stop>
                  <label class="settings-menu__select">
                    <span>{{ t('fileEditorDialog.theme') }}</span>
                    <select v-model="theme">
                      <option value="vscode-dark">{{ t('fileEditorDialog.themeDark') }}</option>
                      <option value="vscode-light">{{ t('fileEditorDialog.themeLight') }}</option>
                    </select>
                  </label>
                  <label class="settings-menu__select">
                    <span>{{ t('fileEditorDialog.fontSize') }}</span>
                    <select v-model.number="fontSize">
                      <option v-for="size in fontSizes" :key="size" :value="size">{{ size }}</option>
                    </select>
                  </label>
                  <label class="settings-menu__switch">
                    <input v-model="wordWrap" type="checkbox" />
                    <span>{{ t('fileEditorDialog.wordWrap') }}</span>
                  </label>
                  <label class="settings-menu__switch">
                    <input v-model="lineNumbers" type="checkbox" />
                    <span>{{ t('fileEditorDialog.lineNumbers') }}</span>
                  </label>
                  <label class="settings-menu__switch">
                    <input v-model="indentGuides" type="checkbox" />
                    <span>{{ t('fileEditorDialog.indentGuides') }}</span>
                  </label>
                  <label class="settings-menu__switch">
                    <input v-model="minimap" type="checkbox" />
                    <span>{{ t('fileEditorDialog.minimap') }}</span>
                  </label>
                </div>
              </template>
            </Dropdown>
            <button
              class="titlebar__btn"
              type="button"
              :title="t('fileEditorDialog.tooltipSave')"
              :aria-label="t('fileEditorDialog.tooltipSave')"
              :disabled="!activeId"
              @click="emit('save')"
            >
              <Save :size="14" />
            </button>
            <button
              class="titlebar__btn"
              type="button"
              :title="
                isFullscreen
                  ? t('fileEditorDialog.tooltipExitFullscreen')
                  : t('fileEditorDialog.tooltipFullscreen')
              "
              :aria-label="
                isFullscreen
                  ? t('fileEditorDialog.tooltipExitFullscreen')
                  : t('fileEditorDialog.tooltipFullscreen')
              "
              @click="toggleFullscreen"
            >
              <Minimize2 v-if="isFullscreen" :size="14" />
              <Maximize2 v-else :size="14" />
            </button>
            <button
              class="titlebar__btn"
              type="button"
              :title="t('fileEditorDialog.tooltipClose')"
              :aria-label="t('fileEditorDialog.tooltipClose')"
              @click="requestClose"
            >
              <X :size="14" />
            </button>
          </div>
        </header>

        <section class="workbench" :class="{ 'workbench--no-sidebar': !sidebarOpen }">
          <aside v-if="sidebarOpen" class="sidebar">
            <div class="sidebar__search">
              <input
                v-model="searchQuery"
                class="sidebar__search-input"
                type="text"
                :placeholder="t('fileEditorDialog.searchPlaceholder')"
              />
            </div>
            <div class="sidebar__tree">
              <div
                v-for="{ node, level } in visibleNodes"
                :key="`${node.id ?? 'root'}`"
                class="tree-row"
                :class="{
                  'is-selected': activeId === node.id,
                  'is-disabled': !node.isDir && !node.editable,
                }"
                @click="onNodeClick(node)"
              >
                <span class="tree-row__indent" :style="{ width: `${level * 14}px` }"></span>
                <button
                  class="tree-row__toggle"
                  type="button"
                  :disabled="!node.isDir"
                  @click.stop="toggleNode(node)"
                >
                  <ChevronDown v-if="node.isDir && node.expanded" :size="12" />
                  <ChevronRight v-else-if="node.isDir" :size="12" />
                </button>
                <FileTypeIcon :name="node.name" :is-dir="node.isDir" />
                <span class="tree-row__name" :title="node.name">{{ node.name }}</span>
                <span v-if="node.loading" class="tree-row__loading">{{ t('fileEditorDialog.loading') }}</span>
              </div>
            </div>
          </aside>

          <button
            class="sidebar-divider-btn"
            type="button"
            :title="
              sidebarOpen
                ? t('fileEditorDialog.tooltipHideFileBrowser')
                : t('fileEditorDialog.tooltipShowFileBrowser')
            "
            :aria-label="
              sidebarOpen
                ? t('fileEditorDialog.tooltipHideFileBrowser')
                : t('fileEditorDialog.tooltipShowFileBrowser')
            "
            @click="sidebarOpen = !sidebarOpen"
          >
            <PanelLeftClose v-if="sidebarOpen" :size="12" />
            <PanelLeftOpen v-else :size="12" />
          </button>

          <section class="editor-pane">
            <div class="editor-pane__tabbar">
              <div class="editor-tab" :class="{ 'is-empty': !activeId }">
                <FileTypeIcon class="editor-tab__icon" :name="activeFileName || 'file.txt'" :is-dir="false" />
                <span class="editor-tab__name">{{ activeTabTitle }}</span>
                <span v-if="dirty" class="editor-tab__dirty"></span>
              </div>
            </div>
            <div class="editor-pane__breadcrumbs">
              <span
                v-for="(part, index) in breadcrumbItems"
                :key="`${part}-${index}`"
                class="editor-pane__crumb"
              >
                <span>{{ part }}</span>
                <span v-if="index < breadcrumbItems.length - 1" class="editor-pane__crumb-sep">/</span>
              </span>
            </div>

            <div v-if="!activeId" class="editor-pane__placeholder">
              {{ t('fileEditorDialog.placeholderSelect') }}
            </div>
            <div v-else-if="loading" class="editor-pane__placeholder">
              {{ t('fileEditorDialog.placeholderLoading') }}
            </div>
            <TextEditor
              v-else
              class="editor-pane__body"
              :model-value="modelValue"
              :language="language"
              :theme="theme"
              :word-wrap="wordWrap"
              :minimap="minimap"
              :line-numbers="lineNumbers"
              :indent-guides="indentGuides"
              :font-size="fontSize"
              @update:modelValue="emit('update:modelValue', $event)"
            />
          </section>
        </section>

        <footer class="statusbar">
          <span class="statusbar__item">{{ activeFileName || '-' }}</span>
          <span class="statusbar__item">{{ language || 'plaintext' }}</span>
          <span class="statusbar__item">{{ wordWrap ? 'Wrap' : 'No Wrap' }}</span>
          <span class="statusbar__item">UTF-8</span>
          <span class="statusbar__item">{{ saving ? 'Saving...' : 'Ready' }}</span>
        </footer>
      </div>
    </div>
  </teleport>

  <ConfirmDialog
    :open="unsavedConfirmOpen"
    :title="t('fileEditorDialog.unsavedTitle')"
    :message="t('fileEditorDialog.unsavedMessage')"
    @close="cancelDiscardChanges"
    @confirm="confirmDiscardChanges"
  />
</template>

<style scoped>
.vscode-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay);
  background: rgba(0, 0, 0, 0.55);
  padding: 20px;
  display: grid;
  place-items: center;
}

.vscode-overlay.is-maximized {
  padding: 0;
}

.vscode-window {
  --bg: #1e1e1e;
  --panel: #252526;
  --panel-2: #2d2d30;
  --border: #3c3c3c;
  --text: #cccccc;
  --muted: #8b8b8b;
  --active: #37373d;
  --blue: #007acc;
  width: min(1180px, 92vw);
  height: min(760px, 84vh);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  display: grid;
  grid-template-rows: 36px 1fr 24px;
  background: var(--bg);
  color: var(--text);
}

.vscode-window.is-maximized {
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
  border-radius: 0;
  border: none;
}

.vscode-window.is-light {
  --bg: #f7f8fa;
  --panel: #ffffff;
  --panel-2: #f4f5f7;
  --border: #d9dde3;
  --text: #1f2328;
  --muted: #667085;
  --active: #e9edf2;
  --blue: #0078d4;
}

.titlebar {
  background: #3c3c3c;
  border-bottom: 1px solid var(--border);
  display: grid;
  grid-template-columns: 180px 1fr auto;
  align-items: center;
  min-width: 0;
}

.vscode-window.is-light .titlebar {
  background: #ffffff;
}

.titlebar__left {
  padding: 0 10px;
  font-size: 12px;
  color: #d0d0d0;
}

.titlebar__center {
  font-size: 12px;
  color: #d0d0d0;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.titlebar__right {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-right: 6px;
}

.titlebar__btn {
  width: 24px;
  height: 24px;
  border: 1px solid transparent;
  background: transparent;
  color: #d0d0d0;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.vscode-window.is-light .titlebar__btn,
.vscode-window.is-light .titlebar__left,
.vscode-window.is-light .titlebar__center {
  color: var(--text);
}

.titlebar__btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
}

.titlebar__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.titlebar__right :deep(.dropdown),
.titlebar__right :deep(.dropdown__trigger) {
  display: inline-flex;
  align-items: center;
}

.workbench {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 0;
  position: relative;
}

.workbench--no-sidebar {
  grid-template-columns: 1fr;
}

.sidebar-divider-btn {
  position: absolute;
  top: 50%;
  left: 260px;
  transform: translate(-50%, -50%);
  width: 18px;
  height: 44px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
}

.workbench--no-sidebar .sidebar-divider-btn {
  left: 0;
  transform: translate(-10%, -50%);
}

.sidebar-divider-btn:hover {
  color: var(--text);
  background: var(--active);
}

.sidebar {
  background: var(--panel);
  border-right: 1px solid var(--border);
  display: grid;
  grid-template-rows: 36px 1fr;
  min-height: 0;
}

.sidebar__search {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border);
}

.sidebar__search-input {
  width: 100%;
  height: 24px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: #3c3c3c;
  color: var(--text);
  font-size: 11px;
  padding: 0 6px;
}

.vscode-window.is-light .sidebar__search-input {
  background: #ffffff;
}

.sidebar__tree {
  overflow: auto;
  min-height: 0;
  padding: 6px;
}

.tree-row {
  display: grid;
  grid-template-columns: auto auto auto 1fr auto;
  align-items: center;
  min-width: 0;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
}

.tree-row:hover {
  background: var(--active);
}

.tree-row.is-selected {
  background: var(--active);
}

.tree-row.is-disabled {
  opacity: 0.55;
  cursor: default;
}

.tree-row__toggle {
  width: 14px;
  height: 14px;
  border: none;
  background: transparent;
  color: var(--muted);
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.tree-row__toggle:disabled {
  opacity: 0;
  cursor: default;
}

.tree-row__name {
  font-size: 12px;
  padding-left: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-row__loading {
  font-size: 11px;
  color: var(--muted);
}

.editor-pane {
  background: var(--bg);
  display: grid;
  grid-template-rows: 34px 26px 1fr;
  min-height: 0;
}

.editor-pane__tabbar {
  background: var(--panel-2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: stretch;
}

.editor-tab {
  min-width: 180px;
  max-width: 360px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border-right: 1px solid var(--border);
  background: #1f1f1f;
  font-size: 12px;
}

.vscode-window.is-light .editor-tab {
  background: #ffffff;
}

.editor-tab.is-empty {
  opacity: 0.85;
}

.editor-tab__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-tab__dirty {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ffffff;
  margin-left: auto;
}

.editor-pane__breadcrumbs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 10px;
  background: #252526;
  border-bottom: 1px solid var(--border);
  font-size: 11px;
  color: var(--muted);
  overflow: hidden;
  white-space: nowrap;
}

.vscode-window.is-light .editor-pane__breadcrumbs {
  background: #ffffff;
}

.editor-pane__crumb {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.editor-pane__crumb span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
}

.editor-pane__crumb-sep {
  color: #6d6d6d;
}

.vscode-window.is-light .editor-pane__crumb-sep {
  color: #9aa0a6;
}

.settings-menu {
  display: grid;
  gap: 8px;
}

:deep(.dropdown__content) {
  background: var(--panel-2);
  border: 1px solid var(--border);
  color: var(--text);
}

.settings-menu__select {
  display: grid;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
}

.settings-menu__select select {
  height: 24px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: #3c3c3c;
  color: var(--text);
  font-size: 11px;
  padding: 0 6px;
}

.vscode-window.is-light .settings-menu__select select {
  background: #ffffff;
}

.settings-menu__switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text);
}

.editor-pane__placeholder {
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 13px;
}

.editor-pane__body {
  min-height: 0;
}

.statusbar {
  background: var(--blue);
  color: #ffffff;
  border-top: 1px solid #0a4f7a;
  display: inline-flex;
  align-items: center;
  gap: 14px;
  padding: 0 10px;
  font-size: 11px;
}

.statusbar__item {
  white-space: nowrap;
}

:deep(.tree-row .file-icon) {
  width: 18px;
  height: 18px;
}

:deep(.tree-row .file-icon svg) {
  width: 12px;
  height: 12px;
}

:deep(.editor-tab .file-icon) {
  width: 16px;
  height: 16px;
}

:deep(.editor-tab .file-icon svg) {
  width: 11px;
  height: 11px;
}

:deep(.editor-pane__body .text-editor) {
  border: none;
  border-radius: 0;
}

@media (max-width: 1024px) {
  .workbench {
    grid-template-columns: 220px 1fr;
  }

  .sidebar-divider-btn {
    left: 220px;
  }
}

@media (max-width: 768px) {
  .vscode-overlay {
    padding: 0;
  }

  .vscode-window {
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .titlebar {
    grid-template-columns: 120px 1fr auto;
  }

  .workbench {
    grid-template-columns: 1fr;
  }

  .sidebar-divider-btn {
    left: 0;
    transform: translate(-10%, -50%);
  }

  .sidebar {
    position: absolute;
    z-index: 3;
    left: 0;
    top: 36px;
    bottom: 24px;
    width: min(78vw, 300px);
    box-shadow: 8px 0 24px rgba(0, 0, 0, 0.35);
  }
}
</style>
