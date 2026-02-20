<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import Modal from '@/components/common/Modal.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ConfigGroupForm from '@/views/admin/system/config-center/ConfigGroupForm.vue'
import AuditLogPanel from '@/views/admin/system/config-center/AuditLogPanel.vue'
import { useConfigGroupForm } from '@/views/admin/system/config-center/useConfigGroupForm'
import { useMessage } from '@/stores/message'
import { cleanupAuditLogs, exportAuditLogs, getAuditLogs } from '@/api/modules/audit'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'
import { useAsync } from '@/composables/useAsync'
import type { AuditLogItem } from '@/types/config-center'

const { state, load, save, updateValue, enableSecretEdit, buildRulesHint, dirtyCount } =
  useConfigGroupForm('audit')

const { t } = useI18n({ useScope: 'global' })
const message = useMessage()
const { pending: auditLoading, run: runAuditTask } = useAsync()
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
type AuditTabKey = 'logs' | 'config'

const activeTab = ref<AuditTabKey>('logs')
const tabs = computed<Array<{ key: AuditTabKey; label: string }>>(() => [
  { key: 'logs', label: t('admin.audit.tabs.logs') },
  { key: 'config', label: t('admin.audit.tabs.config') },
])

const auditFilters = reactive({
  start: '',
  end: '',
  action: '',
  status: '',
  user_id: '',
  q: '',
  page: 1,
  page_size: 20,
})

const auditTotal = ref(0)
const auditRows = ref<AuditLogItem[]>([])
const auditDetailOpen = ref(false)
const auditDetailPayload = ref('')
const cleanupConfirm = ref(false)

const auditColumns = computed(() => [
  { key: 'created_at', label: t('admin.audit.columns.createdAt'), width: '160px' },
  { key: 'user_id', label: t('admin.audit.columns.userId'), width: '80px' },
  { key: 'action', label: t('admin.audit.columns.action'), width: '120px' },
  { key: 'status', label: t('admin.audit.columns.status'), width: '100px' },
  { key: 'path', label: t('admin.audit.columns.path') },
  { key: 'ip', label: t('admin.audit.columns.ip'), width: '140px' },
  { key: 'detail', label: t('admin.audit.columns.detail'), width: '120px' },
])

const actionOptions = computed(() => [
  { label: t('admin.audit.options.allAction'), value: '' },
  { label: 'LOGIN', value: 'LOGIN' },
  { label: 'LOGOUT', value: 'LOGOUT' },
  { label: 'UPLOAD', value: 'UPLOAD' },
  { label: 'DOWNLOAD', value: 'DOWNLOAD' },
  { label: 'DELETE', value: 'DELETE' },
  { label: 'SHARE_CREATE', value: 'SHARE_CREATE' },
  { label: 'SHARE_ACCESS', value: 'SHARE_ACCESS' },
  { label: 'RENAME', value: 'RENAME' },
  { label: 'MOVE', value: 'MOVE' },
  { label: 'MKDIR', value: 'MKDIR' },
])

const statusOptions = computed(() => [
  { label: t('admin.audit.options.allStatus'), value: '' },
  { label: 'SUCCESS', value: 'SUCCESS' },
  { label: 'FAIL', value: 'FAIL' },
])

const buildAuditParams = () => ({
  start: auditFilters.start || undefined,
  end: auditFilters.end || undefined,
  action: auditFilters.action || undefined,
  status: auditFilters.status || undefined,
  user_id: auditFilters.user_id || undefined,
  q: auditFilters.q || undefined,
  page: auditFilters.page,
  page_size: auditFilters.page_size,
})

const updateAuditFilter = (payload: { key: keyof typeof auditFilters; value: string | number }) => {
  auditFilters[payload.key] = payload.value as never
}

const fetchAuditLogs = async () => {
  const result = await runAuditTask(
    () => getAuditLogs(buildAuditParams()),
    {
      errorTitle: t('admin.audit.toasts.loadFailTitle'),
      retryActionLabel: t('common.retry'),
      onRetry: () => {
        void fetchAuditLogs()
      },
    },
  )
  if (result) {
    auditRows.value = result.items || []
    auditTotal.value = result.total || 0
  }
}

const resetAuditFilters = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 7)

  auditFilters.start = start.toISOString().slice(0, 10)
  auditFilters.end = end.toISOString().slice(0, 10)
  auditFilters.action = ''
  auditFilters.status = ''
  auditFilters.user_id = ''
  auditFilters.q = ''
  auditFilters.page = 1
  auditFilters.page_size = 20

  void fetchAuditLogs()
}

const openDetail = (item: AuditLogItem) => {
  auditDetailPayload.value = item.detail ? String(item.detail) : ''
  auditDetailOpen.value = true
}

const handleExport = async () => {
  try {
    const { blob, filename } = await exportAuditLogs(buildAuditParams())
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    message.error(
      t('admin.audit.toasts.exportFailTitle'),
      error instanceof Error ? error.message : t('admin.audit.toasts.exportFailMessage'),
    )
  }
}

const confirmCleanup = () => {
  cleanupConfirm.value = true
}

const handleCleanup = async () => {
  cleanupConfirm.value = false
  const result = await runAuditTask(
    () => cleanupAuditLogs(),
    {
      errorTitle: t('admin.audit.toasts.cleanupFailTitle'),
      retryActionLabel: t('common.retry'),
      onRetry: () => {
        void handleCleanup()
      },
    },
  )
  if (result !== undefined) {
    message.success(t('admin.audit.toasts.cleanupSuccess'))
    auditFilters.page = 1
    await fetchAuditLogs()
  }
}

const handleAuditPageChange = (value: number) => {
  auditFilters.page = value
  void fetchAuditLogs()
}

const handleAuditSearch = () => {
  auditFilters.page = 1
  void fetchAuditLogs()
}

const handleAuditSizeChange = (value: number) => {
  auditFilters.page_size = value
  auditFilters.page = 1
  void fetchAuditLogs()
}

onMounted(() => {
  void load()
  resetAuditFilters()
  void nextTick(() => {
    updateMetrics()
  })
})

watch(
  [
    () => activeTab.value,
    () => auditRows.value.length,
    () => auditLoading.value,
    () => state.items.length,
    () => state.loading,
  ],
  async () => {
    await nextTick()
    updateMetrics()
  },
)
</script>

<template>
  <div class="config-page">
    <PageHeader :title="t('admin.audit.title')" :subtitle="t('admin.audit.subtitle')">
      <template #actions>
        <div class="tabs" role="tablist" :aria-label="t('admin.audit.aria.tablist')">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="tab"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.key"
            :class="{ 'tab--active': activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </template>
    </PageHeader>

    <div
      class="page-body"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
    >
      <div ref="scrollRef" class="page-body__scroll overlay-scroll" @scroll="onScroll">
        <AuditLogPanel
          v-if="activeTab === 'logs'"
          :filters="auditFilters"
          :loading="auditLoading"
          :rows="auditRows"
          :total="auditTotal"
          :columns="auditColumns"
          :page="auditFilters.page"
          :page-size="auditFilters.page_size"
          :action-options="actionOptions"
          :status-options="statusOptions"
          @update-filter="updateAuditFilter"
          @search="handleAuditSearch"
          @reset="resetAuditFilters"
          @export="handleExport"
          @cleanup="confirmCleanup"
          @open-detail="openDetail"
          @page-change="handleAuditPageChange"
          @size-change="handleAuditSizeChange"
        />

        <ConfigGroupForm
          v-else
          flat
          :items="state.items"
          :form="state.form"
          :errors="state.errors"
          :editing-secrets="state.editingSecrets"
          :loading="state.loading"
          :saving="state.saving"
          :dirty-count="dirtyCount()"
          :build-rules-hint="buildRulesHint"
          :save-label="t('admin.audit.configSaveLabel')"
          @save="save"
          @edit-secret="enableSecretEdit"
          @update="updateValue"
        />
      </div>
      <div v-if="isScrollable" class="overlay-scrollbar" :class="{ 'is-visible': visible }">
        <div
          class="overlay-scrollbar__thumb"
          :style="{ height: `${thumbHeight}px`, transform: `translateY(${thumbTop}px)` }"
          @mousedown="onThumbMouseDown"
        ></div>
      </div>
    </div>

    <Modal :open="auditDetailOpen" :title="t('admin.audit.detail.title')" @close="auditDetailOpen = false">
      <pre class="audit-detail">{{ auditDetailPayload || t('admin.audit.detail.empty') }}</pre>
    </Modal>

    <ConfirmDialog
      :open="cleanupConfirm"
      :title="t('admin.audit.cleanup.title')"
      :message="t('admin.audit.cleanup.message')"
      :confirm-text="t('admin.audit.cleanup.confirmText')"
      @confirm="handleCleanup"
      @close="cleanupConfirm = false"
    />
  </div>
</template>

<style scoped>
.config-page {
  display: grid;
  gap: var(--space-4);
  height: 100%;
  min-height: 0;
  grid-template-rows: auto 1fr;
  overflow: hidden;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: 6px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.tab {
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: 6px 14px;
  background: transparent;
  color: var(--color-muted);
  transition: all var(--transition-fast);
  white-space: nowrap;
  cursor: pointer;
}

.tab--active {
  background: var(--color-surface-2);
  color: var(--color-text);
  border-color: var(--color-border);
}

.page-body {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: color-mix(in srgb, var(--color-surface-2) 28%, var(--color-surface));
  padding: var(--space-3);
}

.page-body__scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  padding-right: 6px;
}

.audit-detail {
  max-height: 320px;
  overflow: auto;
  background: var(--color-surface-2);
  padding: var(--space-4);
  border-radius: var(--radius-sm);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
