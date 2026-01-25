<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Modal from '@/components/common/Modal.vue'
import Button from '@/components/common/Button.vue'
import TextEditor from '@/components/common/TextEditor.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { listDir } from '@/api/modules/userDisk'
import type { DiskEntry } from '@/types/disk'
import { getFileKind } from '@/utils/fileType'
import { toRelativePath } from '@/utils/path'

type TreeNode = {
  name: string
  path: string
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
    rootPath: string
    rootName?: string
    activePath?: string | null
    language?: string
    modelValue: string
    loading?: boolean
    saving?: boolean
  }>(),
  {
    rootName: '我的网盘',
    activePath: null,
    language: 'plaintext',
    loading: false,
    saving: false,
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'select', payload: { path: string; name: string }): void
  (event: 'save'): void
  (event: 'close'): void
}>()

const rootNode = ref<TreeNode>({
  name: props.rootName || '我的网盘',
  path: '',
  isDir: true,
  children: [],
  expanded: true,
  loading: false,
  loaded: false,
  editable: false,
})

const normalizedRootPath = computed(() => toRelativePath(props.rootPath || '/'))

const rootLabel = computed(() => props.rootName || '我的网盘')
const sidebarOpen = ref(true)
const searchQuery = ref('')
const theme = ref<'vs' | 'vs-dark'>('vs')
const wordWrap = ref(true)
const minimap = ref(false)
const lineNumbers = ref(true)
const indentGuides = ref(true)
const fontSize = ref(13)

const fontSizes = [12, 13, 14, 15, 16]

const buildNode = (entry: DiskEntry): TreeNode => {
  const kind = getFileKind(entry.name, entry.is_dir)
  const editable = !entry.is_dir && (kind === 'text' || kind === 'code')
  return {
    name: entry.name,
    path: entry.path,
    isDir: entry.is_dir,
    children: [],
    expanded: false,
    loading: false,
    loaded: false,
    editable,
  }
}

const loadChildren = async (node: TreeNode) => {
  if (node.loading || node.loaded) {
    return
  }
  node.loading = true
  try {
    const data = await listDir(node.path)
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

const onNodeClick = (node: TreeNode) => {
  if (node.isDir) {
    void toggleNode(node)
    return
  }
  if (!node.editable) {
    return
  }
  emit('select', { path: node.path, name: node.name })
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

const searchMode = computed(() => searchQuery.value.trim().length > 0)

const visibleNodes = computed(() => {
  if (!searchMode.value) {
    return flatNodes.value
  }
  const keyword = searchQuery.value.trim().toLowerCase()
  return flatNodes.value.filter(({ node }) => node.name.toLowerCase().includes(keyword))
})

const onKeyDown = (event: KeyboardEvent) => {
  if (!props.open) {
    return
  }
  const isSave = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's'
  if (isSave) {
    event.preventDefault()
    emit('save')
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      window.addEventListener('keydown', onKeyDown)
    } else {
      window.removeEventListener('keydown', onKeyDown)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
})

watch(
  () => [props.open, props.rootPath, props.rootName],
  ([open]) => {
    if (!open) {
      return
    }
    rootNode.value = {
      name: rootLabel.value,
      path: normalizedRootPath.value,
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
</script>

<template>
  <Modal :open="open" :title="rootLabel" :width="1080" @close="emit('close')">
    <div class="editor" :class="{ 'editor--collapsed': !sidebarOpen }">
      <aside v-if="sidebarOpen" class="editor__sidebar">
        <div class="editor__sidebar-head">
          <div class="editor__sidebar-title">{{ rootLabel }}</div>
        </div>
        <div class="editor__sidebar-search">
          <input
            v-model="searchQuery"
            class="editor__search"
            type="text"
            placeholder="搜索文件"
          />
        </div>
        <div class="editor__tree">
          <div
            v-for="{ node, level } in visibleNodes"
            :key="`${node.path || 'root'}`"
            class="editor__row"
            :class="{
              'is-selected': activePath === node.path,
              'is-file': !node.isDir,
              'is-disabled': !node.isDir && !node.editable,
              'is-search': searchMode,
            }"
            @click="onNodeClick(node)"
          >
            <span class="editor__indent" :style="{ width: `${level * 16}px` }"></span>
            <button
              class="editor__toggle"
              type="button"
              :disabled="!node.isDir"
              @click.stop="toggleNode(node)"
            >
              <span v-if="node.isDir">
                {{ node.expanded ? '▾' : '▸' }}
              </span>
            </button>
            <FileTypeIcon :name="node.name" :is-dir="node.isDir" />
            <span class="editor__name" :title="node.name">{{ node.name }}</span>
            <span v-if="node.loading" class="editor__loading">加载中</span>
          </div>
        </div>
      </aside>

      <section class="editor__main">
        <div class="editor__settings">
          <div class="editor__group">
            <button class="editor__collapse" type="button" @click="sidebarOpen = !sidebarOpen">
              <ChevronLeft v-if="sidebarOpen" :size="12" />
              <ChevronRight v-else :size="12" />
            </button>
            <label class="editor__switch">
              <input v-model="wordWrap" type="checkbox" />
              <span>自动换行</span>
            </label>
            <label class="editor__switch">
              <input v-model="lineNumbers" type="checkbox" />
              <span>行号</span>
            </label>
            <label class="editor__switch">
              <input v-model="indentGuides" type="checkbox" />
              <span>缩进线</span>
            </label>
            <label class="editor__switch">
              <input v-model="minimap" type="checkbox" />
              <span>Minimap</span>
            </label>
          </div>
          <div class="editor__group">
            <label class="editor__select">
              <span>主题</span>
              <select v-model="theme">
                <option value="vs">亮色</option>
                <option value="vs-dark">暗色</option>
              </select>
            </label>
            <label class="editor__select">
              <span>字号</span>
              <select v-model.number="fontSize">
                <option v-for="size in fontSizes" :key="size" :value="size">{{ size }}</option>
              </select>
            </label>
          </div>
        </div>

        <div v-if="!activePath" class="editor__placeholder">选择一个文本文件进行编辑</div>
        <div v-else-if="loading" class="editor__placeholder">加载中...</div>
        <TextEditor
          v-else
          class="editor__body"
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
    </div>

    <template #footer>
      <Button variant="ghost" @click="emit('close')">取消</Button>
      <Button :loading="saving" :disabled="!activePath" @click="emit('save')">保存</Button>
    </template>
  </Modal>
</template>

<style scoped>
.editor {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr);
  gap: 0;
  min-height: 0;
  height: 80vh;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface);
}

.editor--collapsed {
  grid-template-columns: minmax(0, 1fr);
}

.editor__sidebar {
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  overflow: hidden;
  display: grid;
  grid-template-rows: 32px 36px minmax(0, 1fr);
  min-height: 0;
}

.editor__sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-2);
  border-bottom: 1px solid var(--color-border);
  height: 32px;
}

.editor__sidebar-title {
  font-size: 11px;
  color: var(--color-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.editor__collapse {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  padding: 0;
}

.editor__collapse:hover {
  color: var(--color-text);
  background: var(--color-surface-2);
}


.editor__sidebar-search {
  padding: 6px var(--space-2);
  border-bottom: 1px solid var(--color-border);
  height: 36px;
}

.editor__search {
  width: 100%;
  height: 24px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  padding: 0 6px;
  font-size: 11px;
  color: var(--color-text);
  background: var(--color-surface);
}

.editor__tree {
  min-height: 0;
  overflow: auto;
  padding: var(--space-2);
}

.editor__row {
  display: grid;
  grid-template-columns: auto auto auto 1fr auto;
  align-items: center;
  border-radius: var(--radius-sm);
  cursor: pointer;
  min-width: 0;
  height: 24px;
}

.editor__row:hover {
  background: var(--color-surface-2);
}

.editor__row.is-selected {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.editor__row.is-disabled {
  opacity: 0.5;
  cursor: default;
}

.editor__row.is-search .editor__indent {
  width: 0 !important;
}

.editor__toggle {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--color-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.editor__toggle:disabled {
  opacity: 0;
  cursor: default;
}

.editor__name {
  font-size: 11px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-left: 4px;
}

.editor__loading {
  font-size: 11px;
  color: var(--color-muted);
}

:deep(.editor__row .file-icon) {
  width: 20px;
  height: 20px;
}

:deep(.editor__row .file-icon svg) {
  width: 12px;
  height: 12px;
}

.editor__main {
  display: grid;
  min-height: 0;
  grid-template-rows: auto 1fr;
  gap: 0;
}

.editor__body {
  height: 100%;
  min-height: 0;
}

.editor__placeholder {
  display: grid;
  place-items: center;
  height: 100%;
  min-height: 0;
  border: 1px dashed var(--color-border);
  border-radius: 0;
  color: var(--color-muted);
  font-size: 13px;
}

.editor__indent {
  display: inline-block;
}

@media (max-width: 1024px) {
  .editor {
    grid-template-columns: 150px minmax(0, 1fr);
  }
}

@media (max-width: 768px) {
  .editor {
    grid-template-columns: 1fr;
  }

  .editor__sidebar {
    max-height: 200px;
  }

  .editor__settings {
    flex-direction: column;
    align-items: flex-start;
  }
}


.editor__settings {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  height: 32px;
}

.editor__group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.editor__switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-muted);
}

.editor__switch input {
  width: 12px;
  height: 12px;
}

.editor__select {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-muted);
}

.editor__select select {
  height: 24px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
  padding: 0 6px;
}

:deep(.editor__body .text-editor) {
  border: none;
  border-radius: 0;
}
</style>
