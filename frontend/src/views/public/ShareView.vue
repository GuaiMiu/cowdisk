<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Table from '@/components/common/Table.vue'
import ImagePreview from '@/components/common/ImagePreview.vue'
import PdfPreview from '@/components/common/PdfPreview.vue'
import VideoPreview from '@/components/common/VideoPreview.vue'
import IconButton from '@/components/common/IconButton.vue'
import FileBreadcrumb from '@/components/file/FileBreadcrumb.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { usePublicShare } from '@/composables/usePublicShare'
import { useSelection } from '@/composables/useSelection'
import { formatBytes, formatTime } from '@/utils/format'
import { getFileKind } from '@/utils/fileType'
import type { ShareEntry } from '@/types/share'
import { previewShare } from '@/api/modules/shares'
import { Download } from 'lucide-vue-next'

const route = useRoute()
const token = route.params.token as string
const share = usePublicShare(token)
const unlockCode = ref('')
const autoCode = computed(() => {
  const value = route.query.code || route.query.pwd
  return typeof value === 'string' ? value.trim() : ''
})
const redirectCount = ref(5)
let redirectTimer: number | null = null
const asEntry = (row: unknown) => row as ShareEntry
const { t } = useI18n({ useScope: 'global' })
const shareMeta = computed(() => {
  const current = share.share.value
  const rawFileId = (current as { fileId?: unknown } | null)?.fileId
  return {
    name: current?.name || '',
    ownerName: current?.ownerName || '-',
    expiresAt: current?.expiresAt ?? null,
    fileId: typeof rawFileId === 'number' ? rawFileId : 0,
  }
})
const rootDirName = computed(() => shareMeta.value.name || t('sharePublic.list.title'))
const enteredRoot = ref(false)
const previewOpen = ref(false)
const previewItems = ref<Array<{ src: string; name?: string }>>([])
const previewIndex = ref(0)
const previewUrls = ref<string[]>([])
const previewEntries = ref<Array<{ id: number; name: string; path?: string }>>([])
const previewLoading = ref(new Set<number>())
const pdfOpen = ref(false)
const pdfSrc = ref<string | null>(null)
const pdfName = ref('')
const pdfUrls = ref<string[]>([])
const videoOpen = ref(false)
const videoSrc = ref<string | null>(null)
const videoName = ref('')
const videoType = ref<string | null>(null)
const videoUrls = ref<string[]>([])
const selectAllRef = ref<HTMLInputElement | null>(null)
const selection = useSelection(() => share.items.value, (item) => String(item.id))
const shareStack = ref<Array<{ id: number; name: string }>>([])
const goHome = () => {
  window.location.href = '/'
}

const columns = computed(() => [
  { key: 'select', label: '', width: '32px', align: 'center' as const },
  { key: 'name', label: t('sharePublic.columns.name') },
  { key: 'size', label: t('sharePublic.columns.size'), width: '110px' },
  { key: 'type', label: t('sharePublic.columns.type'), width: '90px' },
])

const rootFolderId = computed(() => (shareMeta.value.fileId > 0 ? shareMeta.value.fileId : null))
const breadcrumbItems = computed(() => {
  if (share.locked.value || share.isFile.value || share.errorMessage.value) {
    return []
  }
  const items = [{ id: null as number | null, label: t('fileBreadcrumb.root') }]
  if (!enteredRoot.value) {
    return items
  }
  if (rootFolderId.value !== null) {
    items.push({ id: rootFolderId.value, label: rootDirName.value })
  }
  shareStack.value.forEach((item) => {
    items.push({ id: item.id, label: item.name })
  })
  return items
})

const getVideoMime = (name: string) => {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    mp4: 'video/mp4',
    webm: 'video/webm',
    mov: 'video/quicktime',
    mkv: 'video/x-matroska',
    avi: 'video/x-msvideo',
    flv: 'video/x-flv',
    wmv: 'video/x-ms-wmv',
    m4v: 'video/x-m4v',
  }
  return map[ext] || 'video/mp4'
}

const getTypeLabel = (name: string, isDir: boolean) => {
  if (isDir) {
    return t('common.folder')
  }
  const kind = getFileKind(name, false)
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

const sortKey = ref<'name' | 'size' | 'type' | null>(null)
const sortOrder = ref<'asc' | 'desc'>('asc')

const setSort = (key: 'name' | 'size' | 'type') => {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortKey.value = key
  sortOrder.value = 'asc'
}

const sortIndicator = (key: 'name' | 'size' | 'type') => {
  if (sortKey.value !== key) {
    return ''
  }
  return sortOrder.value === 'asc' ? 'asc' : 'desc'
}

const sortedShareItems = computed(() => {
  if (!sortKey.value) {
    return share.items.value
  }
  const next = [...share.items.value]
  const order = sortOrder.value === 'asc' ? 1 : -1
  next.sort((a, b) => {
    if (a.is_dir !== b.is_dir) {
      return a.is_dir ? -1 : 1
    }
    if (sortKey.value === 'name') {
      return order * a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
    }
    if (sortKey.value === 'size') {
      return order * ((a.size || 0) - (b.size || 0))
    }
    const kindA = getFileKind(a.name, a.is_dir)
    const kindB = getFileKind(b.name, b.is_dir)
    return order * kindA.localeCompare(kindB, undefined, { numeric: true, sensitivity: 'base' })
  })
  return next
})

const clearImagePreview = () => {
  previewUrls.value.forEach((url) => URL.revokeObjectURL(url))
  previewUrls.value = []
  previewItems.value = []
  previewOpen.value = false
  previewIndex.value = 0
  previewEntries.value = []
  previewLoading.value = new Set()
}

const clearPdfPreview = () => {
  pdfUrls.value.forEach((url) => URL.revokeObjectURL(url))
  pdfUrls.value = []
  pdfSrc.value = null
  pdfName.value = ''
  pdfOpen.value = false
}

const clearVideoPreview = () => {
  videoUrls.value.forEach((url) => URL.revokeObjectURL(url))
  videoUrls.value = []
  videoSrc.value = null
  videoName.value = ''
  videoType.value = null
  videoOpen.value = false
}

const ensureImagePreview = async (index: number) => {
  if (index < 0 || index >= previewEntries.value.length) {
    return
  }
  if (previewItems.value[index]?.src) {
    return
  }
  if (previewLoading.value.has(index)) {
    return
  }
  const entry = previewEntries.value[index]
  if (!entry) {
    return
  }
  previewLoading.value = new Set(previewLoading.value).add(index)
  try {
    const result = await previewShare(
      token,
      { file_id: entry.id },
      share.accessToken.value ?? undefined,
    )
    const url = URL.createObjectURL(result.blob)
    previewUrls.value = [...previewUrls.value, url]
    const next = [...previewItems.value]
    next[index] = { src: url, name: entry.name }
    previewItems.value = next
  } finally {
    const next = new Set(previewLoading.value)
    next.delete(index)
    previewLoading.value = next
  }
}

const openImagePreview = async (name: string, fileId?: number, path?: string) => {
  clearImagePreview()
  const entries = share.items.value
    .filter((item) => !item.is_dir && getFileKind(item.name, false) === 'image')
    .map((item) => ({ id: item.id, name: item.name, path: item.path as string | undefined }))
  const list = entries.length ? entries : [{ id: fileId ?? 0, name, path }]
  previewEntries.value = list
  previewItems.value = list.map((entry) => ({ src: '', name: entry.name }))
  const currentIndex = Math.max(0, list.findIndex((entry) => entry.id === fileId))
  previewIndex.value = currentIndex
  previewOpen.value = true
  await ensureImagePreview(currentIndex)
  await Promise.all([ensureImagePreview(currentIndex - 1), ensureImagePreview(currentIndex + 1)])
}

const openPreviewForFile = async (entry: ShareEntry) => {
  const kind = getFileKind(entry.name, false)
  if (kind === 'image') {
    await openImagePreview(entry.name, entry.id, entry.path)
    return
  }
  if (kind === 'pdf') {
    const result = await previewShare(
      token,
      { file_id: entry.id },
      share.accessToken.value ?? undefined,
    )
    const url = URL.createObjectURL(result.blob)
    pdfUrls.value = [url]
    pdfSrc.value = url
    pdfName.value = entry.name
    pdfOpen.value = true
    return
  }
  if (kind === 'video') {
    const result = await previewShare(
      token,
      { file_id: entry.id },
      share.accessToken.value ?? undefined,
    )
    const url = URL.createObjectURL(result.blob)
    videoUrls.value = [url]
    videoSrc.value = url
    videoName.value = entry.name
    videoType.value = getVideoMime(entry.name)
    videoOpen.value = true
    return
  }
  await share.preview(entry.id)
}

const handlePreviewChange = async (index: number) => {
  await ensureImagePreview(index)
  await Promise.all([ensureImagePreview(index - 1), ensureImagePreview(index + 1)])
}

onMounted(async () => {
  await share.loadShare()
  if (share.locked.value && autoCode.value) {
    unlockCode.value = autoCode.value
    void share.unlock(autoCode.value)
  }
  if (!share.locked.value && !share.isFile.value && !share.errorMessage.value) {
    showRootCard()
  }
})

watch(unlockCode, () => {
  share.clearUnlockError()
})

watch(
  () => share.errorMessage.value,
  (value) => {
    if (!value) {
      if (redirectTimer) {
        window.clearInterval(redirectTimer)
        redirectTimer = null
      }
      return
    }
    redirectCount.value = 5
    if (redirectTimer) {
      window.clearInterval(redirectTimer)
    }
    redirectTimer = window.setInterval(() => {
      redirectCount.value -= 1
      if (redirectCount.value <= 0) {
        window.location.href = '/'
      }
    }, 1000)
  },
)

watch(
  () => [share.locked.value, share.isFile.value, share.errorMessage.value, share.share.value],
  () => {
    if (!share.locked.value && !share.isFile.value && !share.errorMessage.value && !enteredRoot.value) {
      showRootCard()
    }
  },
)

watch(
  () => selection.indeterminate.value,
  (value) => {
    if (selectAllRef.value) {
      selectAllRef.value.indeterminate = value
    }
  },
  { immediate: true },
)

watch(
  () => share.items.value,
  (items) => {
    const valid = new Set(items.map((item) => String(item.id)))
    const next = new Set<string>()
    selection.selected.value.forEach((key) => {
      if (valid.has(key)) {
        next.add(key)
      }
    })
    if (next.size !== selection.selected.value.size) {
      selection.selected.value = next
    }
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (redirectTimer) {
    window.clearInterval(redirectTimer)
  }
})

const showRootCard = () => {
  enteredRoot.value = false
  shareStack.value = []
  const rootId = shareMeta.value.fileId
  share.items.value = [
    {
      id: rootId,
      name: rootDirName.value,
      path: '',
      parent_id: null,
      is_dir: true,
      size: 0,
    },
  ]
}

const openRootDirectory = async () => {
  enteredRoot.value = true
  shareStack.value = []
  const rootId = rootFolderId.value
  await share.loadEntries(rootId ?? null)
}

const openDirectory = async (entry: ShareEntry) => {
  if (!entry.is_dir) {
    return
  }
  if (!enteredRoot.value) {
    await openRootDirectory()
    return
  }
  shareStack.value = [...shareStack.value, { id: entry.id, name: entry.name }]
  await share.loadEntries(entry.id)
}

const handleBreadcrumbNavigate = async (targetId: number | string | null) => {
  if (targetId === null) {
    showRootCard()
    return
  }
  if (typeof targetId === 'string') {
    return
  }
  if (targetId === rootFolderId.value) {
    await openRootDirectory()
    return
  }
  const index = shareStack.value.findIndex((item) => item.id === targetId)
  if (index >= 0) {
    shareStack.value = shareStack.value.slice(0, index + 1)
  } else {
    shareStack.value = []
  }
  enteredRoot.value = true
  await share.loadEntries(targetId)
}
</script>

<template>
  <section
    class="share"
    :class="{
      'share--locked': share.locked.value || !!share.errorMessage.value,
      'share--file': share.isFile.value,
      'share--dir': !share.locked.value && !share.isFile.value && !share.errorMessage.value,
    }"
  >
    <div v-if="share.errorMessage.value" class="notice">
      <div class="notice__card">
        <div class="notice__title">{{ t('sharePublic.unavailable.title') }}</div>
        <div class="notice__desc">{{ share.errorMessage.value }}</div>
        <div class="notice__hint">
          {{ t('sharePublic.unavailable.redirectHint', { count: redirectCount }) }}
        </div>
        <Button variant="secondary" @click="goHome">{{
          t('sharePublic.unavailable.backHome')
        }}</Button>
      </div>
    </div>
    <div v-else-if="share.locked.value" class="unlock">
      <div class="unlock__card">
        <div class="unlock__title">{{ t('sharePublic.unlock.title') }}</div>
        <div class="unlock__subtitle">{{ t('sharePublic.unlock.subtitle') }}</div>
        <div class="unlock__meta">
          <span
            >{{ t('sharePublic.labels.owner') }}：{{
              shareMeta.ownerName
            }}</span
          >
          <span>
            {{ t('sharePublic.labels.expires') }}：{{
              shareMeta.expiresAt
                ? formatTime(shareMeta.expiresAt)
                : t('sharePublic.permanent')
            }}
          </span>
        </div>
        <div class="unlock__form">
          <Input
            v-model="unlockCode"
            :label="t('sharePublic.unlock.codeLabel')"
            :placeholder="t('sharePublic.unlock.codePlaceholder')"
          />
          <Button :loading="share.loading.value" @click="share.unlock(unlockCode)">
            {{ t('sharePublic.unlock.button') }}
          </Button>
        </div>
        <div v-if="share.unlockError.value" class="unlock__error">
          {{ share.unlockError.value }}
        </div>
        <div class="unlock__hint">{{ t('sharePublic.unlock.hint') }}</div>
      </div>
    </div>

    <div v-else-if="share.isFile.value" class="file-card">
      <div class="file-card__header">
        <FileTypeIcon
          class="file-card__icon"
          :name="shareMeta.name"
          :is-dir="false"
          :size="28"
        />
        <div class="file-card__header-info">
          <div class="file-card__title" :title="shareMeta.name">
            <span class="file-card__name">{{ shareMeta.name }}</span>
          </div>
          <div class="file-card__subtitle">
            {{ t('sharePublic.labels.owner') }}：{{ shareMeta.ownerName }}
          </div>
        </div>
      </div>
        <div class="file-card__meta">
        <div class="file-card__meta-item">
          <span class="file-card__meta-label">{{ t('sharePublic.labels.size') }}</span>
          <span class="file-card__meta-value">
            {{ share.fileMeta.value?.size ? formatBytes(share.fileMeta.value.size) : '-' }}
          </span>
        </div>
        <div class="file-card__meta-item">
          <span class="file-card__meta-label">{{ t('sharePublic.labels.type') }}</span>
          <span class="file-card__meta-value">
            {{ getTypeLabel(shareMeta.name, false) }}
          </span>
        </div>
        <div class="file-card__meta-item">
          <span class="file-card__meta-label">{{ t('sharePublic.labels.expires') }}</span>
          <span class="file-card__meta-value">
            {{
              shareMeta.expiresAt
                ? formatTime(shareMeta.expiresAt)
                : t('sharePublic.permanent')
            }}
          </span>
        </div>
      </div>
      <div class="file-card__actions">
        <Button
          variant="secondary"
          @click="openPreviewForFile({
            id: shareMeta.fileId,
            name: shareMeta.name || 'file',
            parent_id: null,
            is_dir: false,
            size: 0,
          })"
        >{{
          t('sharePublic.actions.preview')
        }}</Button>
        <Button @click="share.download(shareMeta.fileId)">
          {{ t('sharePublic.actions.download') }}
        </Button>
      </div>
    </div>

    <div v-else class="share__body">
      <div class="share__panel">
        <div class="share__bar">
          <div class="share__header">
            <FileTypeIcon
              class="share__header-icon"
              :name="shareMeta.name"
              :is-dir="!share.isFile.value"
              :size="48"
            />
            <div class="share__header-info">
              <div class="share__title">
                {{ shareMeta.name || t('sharePublic.list.title') }}
              </div>
              <div class="share__meta">
                <span
                  >{{ t('sharePublic.labels.owner') }}：{{
                    shareMeta.ownerName
                  }}</span
                >
                <span>
                  {{ t('sharePublic.labels.expires') }}：{{
                    shareMeta.expiresAt
                      ? formatTime(shareMeta.expiresAt)
                      : t('sharePublic.permanent')
                  }}
                </span>
              </div>
            </div>
          </div>
          <FileBreadcrumb
            :items="breadcrumbItems"
            @navigate="handleBreadcrumbNavigate"
          />
        </div>
        <div class="share__table">
          <Table :columns="columns" :rows="sortedShareItems" :min-rows="10" scrollable fill>
            <template #head-select>
              <div class="select-cell">
                <input
                  ref="selectAllRef"
                  type="checkbox"
                  :checked="selection.allSelected.value"
                  @change="selection.toggleAll()"
                />
              </div>
            </template>
            <template #head-name>
              <button
                type="button"
                class="table__sort"
                :class="[`is-${sortIndicator('name')}`, { 'is-active': sortKey === 'name' }]"
                @click="setSort('name')"
              >
                {{ t('sharePublic.columns.name') }}
                <span class="table__sort-indicator"></span>
              </button>
            </template>
            <template #head-size>
              <button
                type="button"
                class="table__sort"
                :class="[`is-${sortIndicator('size')}`, { 'is-active': sortKey === 'size' }]"
                @click="setSort('size')"
              >
                {{ t('sharePublic.columns.size') }}
                <span class="table__sort-indicator"></span>
              </button>
            </template>
            <template #head-type>
              <button
                type="button"
                class="table__sort"
                :class="[`is-${sortIndicator('type')}`, { 'is-active': sortKey === 'type' }]"
                @click="setSort('type')"
              >
                {{ t('sharePublic.columns.type') }}
                <span class="table__sort-indicator"></span>
              </button>
            </template>
            <template #cell-select="{ row }">
              <div class="select-cell">
                <input
                  type="checkbox"
                  :checked="selection.isSelected(asEntry(row))"
                  @click.stop
                  @change="selection.toggle(asEntry(row))"
                />
              </div>
            </template>
            <template #cell-name="{ row }">
              <button
                type="button"
                class="name name--clickable"
                @click="asEntry(row).is_dir
                  ? openDirectory(asEntry(row))
                  : openPreviewForFile(asEntry(row))"
              >
                <FileTypeIcon :name="asEntry(row).name" :is-dir="asEntry(row).is_dir" />
                <span class="name__text">{{ asEntry(row).name }}</span>
              </button>
              <div v-if="!asEntry(row).is_dir" class="share-row-actions">
                <IconButton
                  size="sm"
                  variant="ghost"
                  :aria-label="t('sharePublic.table.download')"
                  @click="share.download(asEntry(row).id)"
                >
                  <Download :size="14" />
                </IconButton>
              </div>
            </template>
            <template #cell-size="{ row }">
              {{ asEntry(row).is_dir ? '-' : formatBytes(asEntry(row).size as number) }}
            </template>
            <template #cell-type="{ row }">
              {{ getTypeLabel(asEntry(row).name, asEntry(row).is_dir) }}
            </template>
          </Table>
        </div>
      </div>
    </div>
  </section>

  <ImagePreview
    :open="previewOpen"
    :images="previewItems"
    :start-index="previewIndex"
    @change="handlePreviewChange"
    @update:open="(value) => { if (!value) clearImagePreview() }"
    @close="clearImagePreview"
  />

  <PdfPreview
    :open="pdfOpen"
    :src="pdfSrc"
    :name="pdfName"
    @update:open="(value) => { if (!value) clearPdfPreview() }"
    @close="clearPdfPreview"
  />

  <VideoPreview
    :open="videoOpen"
    :src="videoSrc"
    :name="videoName"
    :type="videoType"
    @update:open="(value) => { if (!value) clearVideoPreview() }"
    @close="clearVideoPreview"
  />
</template>

<style scoped>
.share {
  height: 100vh;
  display: grid;
  gap: var(--space-4);
  grid-template-rows: 1fr;
  padding: var(--space-6);
  overflow: hidden;
}

.share--locked {
  grid-template-rows: 1fr;
  place-items: center;
}

.share--file {
  grid-template-rows: 1fr;
  place-items: center;
}

.share--dir {
  place-items: center;
}

.unlock {
  display: grid;
  place-items: center;
  padding: 0;
}

.unlock__card {
  width: min(420px, 100%);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: grid;
  gap: var(--space-4);
  box-shadow: var(--shadow-sm);
  animation: cardLiftIn var(--duration-slow) var(--ease-standard);
}

.notice {
  display: grid;
  place-items: center;
}

.notice__card {
  width: min(420px, 100%);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: grid;
  gap: var(--space-4);
  box-shadow: var(--shadow-sm);
  text-align: center;
  animation: cardLiftIn var(--duration-slow) var(--ease-standard);
}

.notice__title {
  font-size: 18px;
  font-weight: 600;
}

.notice__desc {
  font-size: 13px;
  color: var(--color-muted);
}

.notice__hint {
  font-size: 12px;
  color: var(--color-muted);
}

.unlock__title {
  font-size: 18px;
  font-weight: 600;
}

.unlock__subtitle {
  font-size: 13px;
  color: var(--color-muted);
}

.unlock__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  font-size: 12px;
  color: var(--color-muted);
}

.unlock__form {
  display: grid;
  gap: var(--space-3);
}

.unlock__hint {
  font-size: 12px;
  color: var(--color-muted);
}

.unlock__error {
  font-size: 12px;
  color: var(--color-danger);
}

.file-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  width: min(600px, 100%);
  animation: cardLiftIn var(--duration-slow) var(--ease-standard);
}

.share__body {
  min-height: 0;
  height: 100%;
  display: grid;
  place-items: center;
  padding: 0;
}

.share--dir .share__body {
  align-items: start;
  padding-top: var(--space-2);
}

.share__panel {
  height: min(78vh, 100%);
  width: min(90vw, 1200px);
  display: grid;
  gap: var(--space-3);
  grid-template-rows: auto 1fr;
}

.share__bar {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-base),
    background var(--transition-base);
}

.share__bar:hover {
  border-color: var(--color-primary-soft-strong);
  box-shadow: var(--shadow-xs);
}

.share__header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.share__header-icon {
  flex: 0 0 auto;

  transform-origin: center;
  background: transparent;
}

.share__header-info {
  display: grid;
  gap: var(--space-1);
}

.share__title {
  font-size: 14px;
  font-weight: 600;
}

.share__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  font-size: 12px;
  color: var(--color-muted);
}

.share__table {
  min-height: 0;
  height: 100%;
}

.share__table :deep(.table) {
  --table-columns: 32px minmax(220px, 1fr) 110px 90px;
  width: 100%;
  min-width: 0;
}

.share__table :deep(.table__cell--head) {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--color-muted);
}

.share__table :deep(.table__sort) {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: transparent;
  border: 0;
  padding: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
  transition: color var(--transition-fast);
}

.share__table :deep(.table__sort:hover) {
  color: var(--color-primary);
}

.share__table :deep(.table__sort-indicator) {
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 6px solid var(--color-muted);
  opacity: 0;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.share__table :deep(.table__sort.is-active) .table__sort-indicator {
  opacity: 1;
}

.share__table :deep(.table__sort.is-asc) .table__sort-indicator {
  transform: rotate(180deg);
}

.share__table :deep(.table__sort.is-desc) .table__sort-indicator {
  transform: rotate(0deg);
}

.share__table :deep(.table__cell:nth-child(3)),
.share__table :deep(.table__cell:nth-child(4)) {
  justify-self: start;
  text-align: left;
  font-size: 12px;
  color: var(--color-muted);
}

.share__table :deep(.table__cell:first-child) {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.share__table :deep(.table__cell) {
  min-width: 0;
}

.share__table :deep(.table__row) {
  position: relative;
}

.share__table :deep(.table__row:hover) {
  background: var(--color-surface-2);
}

.share-row-actions {
  position: absolute;
  right: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  opacity: 1;
  pointer-events: auto;
}

.share__table :deep(.table__cell:nth-child(2)) {
  padding-right: 56px;
}

.share-row-actions :deep(.icon-btn) {
  color: var(--color-success);
}

.select-cell {
  display: inline-flex;
  align-items: center;
  height: 100%;
}

.name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  color: var(--color-text);
}

.name__text {
  font-weight: 500;
  font-size: 14px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--transition-fast);
}

.name--clickable {
  cursor: pointer;
  background: transparent;
  border: 0;
  padding: 0;
}

.name--clickable:hover .name__text {
  color: var(--color-primary);
}

.name--clickable:active {
  transform: var(--interaction-press-scale);
}

.file-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.file-card__header-info {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}

.file-card__title {
  font-size: 18px;
  font-weight: 600;
  min-width: 0;
}

.file-card__subtitle {
  font-size: 12px;
  color: var(--color-muted);
}

.file-card__icon {
  background: transparent;
}

.file-card__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.file-card__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-muted);
  font-size: 12px;
}

.file-card__meta-item {
  display: grid;
  gap: var(--space-1);
}

.file-card__meta-label {
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.file-card__meta-value {
  font-size: 13px;
  color: var(--color-text);
}

.file-card__actions {
  display: flex;
  gap: var(--space-2);
  justify-content: space-between;
}

@keyframes cardLiftIn {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.99);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 768px) {
  .share {
    padding: var(--space-4);
  }

  .file-card {
    width: 100%;
  }

  .file-card__title {
    font-size: 16px;
  }

  .file-card__meta {
    grid-template-columns: 1fr;
  }

  .file-card__header :deep(.file-icon) {
    width: 22px;
    height: 22px;
  }

  .file-card__header :deep(.file-icon svg) {
    width: 14px;
    height: 14px;
  }

  .share__table :deep(.table) {
    --table-columns: 32px minmax(0, 1fr);
  }

  .share__table :deep(.table__cell:nth-child(3)) {
    display: none;
  }

  .share__table :deep(.table__cell:nth-child(4)) {
    display: none;
  }
}
</style>
