<script setup lang="ts">
import { computed } from 'vue'
import {
  File,
  FileArchive,
  FileCode,
  FileImage,
  FileMusic,
  FileSpreadsheet,
  FileText,
  FileType,
  FileVideoCamera,
  Folder,
} from 'lucide-vue-next'
import { getFileKind, type FileKind } from '@/utils/fileType'

const props = defineProps<{
  name?: string
  isDir?: boolean
  resourceType?: string
  size?: number
}>()

const kind = computed<FileKind>(() => getFileKind(props.name, props.isDir, props.resourceType))

const iconMap: Record<FileKind, unknown> = {
  folder: Folder,
  image: FileImage,
  video: FileVideoCamera,
  audio: FileMusic,
  pdf: FileType,
  doc: FileType,
  sheet: FileSpreadsheet,
  slide: FileType,
  archive: FileArchive,
  code: FileCode,
  text: FileText,
  other: File,
}

const icon = computed(() => iconMap[kind.value] ?? File)
</script>

<template>
  <span class="file-icon" :class="`file-icon--${kind}`">
    <component :is="icon" :size="16" />
  </span>
</template>

<style scoped>
.file-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--color-surface-2);
  color: var(--color-muted);
  flex-shrink: 0;
}

.file-icon--folder {
  color: var(--color-primary);
}

.file-icon--image {
  color: var(--color-info);
}

.file-icon--video {
  color: var(--color-warning);
}

.file-icon--audio {
  color: var(--color-warning);
}

.file-icon--pdf,
.file-icon--doc,
.file-icon--slide {
  color: var(--color-danger);
}

.file-icon--sheet {
  color: var(--color-success);
}

.file-icon--archive {
  color: var(--color-muted);
}

.file-icon--code {
  color: var(--color-primary);
}

.file-icon--text {
  color: var(--color-info);
}
</style>
