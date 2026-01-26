<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Modal from '@/components/common/Modal.vue'
import Button from '@/components/common/Button.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { listDir } from '@/api/modules/userDisk'
import type { DiskEntry } from '@/types/disk'
import { toRelativePath } from '@/utils/path'

type TreeNode = {
  name: string
  path: string
  children: TreeNode[]
  expanded: boolean
  loading: boolean
  loaded: boolean
}

const props = defineProps<{
  open: boolean
  entries: DiskEntry[]
  currentPath: string
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'confirm', targetPath: string): void
}>()

const { t, locale } = useI18n({ useScope: 'global' })

const rootNode = ref<TreeNode>({
  name: '',
  path: '',
  children: [],
  expanded: true,
  loading: false,
  loaded: false,
})
const selectedPath = ref('')

const normalizedCurrentPath = computed(() => toRelativePath(props.currentPath || '/'))
const rootName = computed(() => t('files.rootName'))

const buildNode = (entry: DiskEntry): TreeNode => ({
  name: entry.name,
  path: entry.path,
  children: [],
  expanded: false,
  loading: false,
  loaded: false,
})

const loadChildren = async (node: TreeNode) => {
  if (node.loading || node.loaded) {
    return
  }
  node.loading = true
  try {
    const data = await listDir(node.path)
    node.children = (data.items || [])
      .filter((item) => item.is_dir)
      .map((item) => buildNode(item))
    node.loaded = true
  } finally {
    node.loading = false
  }
}

const toggleNode = async (node: TreeNode) => {
  if (node.expanded) {
    node.expanded = false
    return
  }
  node.expanded = true
  await loadChildren(node)
}

const selectNode = (node: TreeNode) => {
  selectedPath.value = node.path
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

const invalidReason = computed(() => {
  if (!props.entries.length) {
    return t('fileMoveDialog.noneSelected')
  }
  const target = selectedPath.value
  const current = normalizedCurrentPath.value
  if (target === current) {
    return t('fileMoveDialog.sameFolder')
  }
  for (const entry of props.entries) {
    if (entry.is_dir) {
      const selfPath = entry.path
      if (target === selfPath) {
        return t('fileMoveDialog.moveToSelf')
      }
      if (selfPath && target.startsWith(`${selfPath}/`)) {
        return t('fileMoveDialog.moveToChild')
      }
    }
  }
  return ''
})

const canSubmit = computed(() => !invalidReason.value)

watch(
  () => props.open,
  (open) => {
    if (!open) {
      return
    }
    selectedPath.value = normalizedCurrentPath.value
    rootNode.value = {
      name: rootName.value,
      path: '',
      children: [],
      expanded: true,
      loading: false,
      loaded: false,
    }
    void loadChildren(rootNode.value)
  },
)

watch(locale, () => {
  if (rootNode.value.path === '') {
    rootNode.value.name = rootName.value
  }
})
</script>

<template>
  <Modal :open="open" :title="t('fileMoveDialog.title')" @close="emit('close')">
    <div class="move">
      <div class="move__meta">{{ t('fileMoveDialog.selectedCount', { count: props.entries.length }) }}</div>
      <div class="move__tree">
        <div
          v-for="{ node, level } in flatNodes"
          :key="`${node.path || 'root'}`"
          class="move__row"
          :class="{ 'is-selected': selectedPath === node.path }"
          @click="selectNode(node)"
        >
          <button
            type="button"
            class="move__toggle"
            :style="{ marginLeft: `${level * 16}px` }"
            @click.stop="toggleNode(node)"
          >
            <span v-if="node.children.length || !node.loaded">
              {{ node.expanded ? '▾' : '▸' }}
            </span>
          </button>
          <div class="move__label">
            <FileTypeIcon :is-dir="true" />
            <span class="move__name" :title="node.name">{{ node.name }}</span>
          </div>
          <span v-if="node.loading" class="move__loading">{{ t('fileMoveDialog.loading') }}</span>
        </div>
      </div>
      <div v-if="invalidReason" class="move__hint">{{ invalidReason }}</div>
    </div>
    <template #footer>
      <Button variant="ghost" @click="emit('close')">{{ t('fileMoveDialog.cancel') }}</Button>
      <Button :disabled="!canSubmit" @click="emit('confirm', selectedPath)">{{ t('fileMoveDialog.move') }}</Button>
    </template>
  </Modal>
</template>

<style scoped>
.move {
  display: grid;
  gap: var(--space-3);
}

.move__tree {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2);
  max-height: 360px;
  overflow: auto;
}

.move__meta {
  font-size: 12px;
  color: var(--color-muted);
}

.move__row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.move__row:hover {
  background: var(--color-surface-2);
}

.move__row.is-selected {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.move__toggle {
  width: 20px;
  height: 20px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--color-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.move__toggle:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.move__label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.move__name {
  font-size: 13px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.move__loading {
  font-size: 12px;
  color: var(--color-muted);
}

.move__hint {
  font-size: 12px;
  color: var(--color-muted);
}
</style>
