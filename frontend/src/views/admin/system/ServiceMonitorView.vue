<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Select from '@/components/common/Select.vue'
import Table from '@/components/common/Table.vue'
import type { MonitorService } from '@/types/system-monitor'
import { formatBytes, formatTime } from '@/utils/format'
import { useMessage } from '@/stores/message'
import { useSystemMonitorOverview } from '@/composables/useSystemMonitorOverview'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'

const { t } = useI18n({ useScope: 'global' })
const message = useMessage()
const { loading, overview, load } = useSystemMonitorOverview()
const manualRefreshing = ref(false)
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

const services = computed<MonitorService[]>(() => overview.value?.services || [])
const summary = computed(() => overview.value?.services_summary)
const cpu = computed(() => overview.value?.cpu)
const memory = computed(() => overview.value?.memory)
const disk = computed(() => overview.value?.disk)
const server = computed(() => overview.value?.server)
const python = computed(() => overview.value?.python)
const autoRefreshInterval = ref('')
let autoRefreshTimer: number | null = null

const autoRefreshOptions = computed(() => [
  { label: t('admin.monitor.autoRefresh.off'), value: '' },
  { label: t('admin.monitor.autoRefresh.sec1'), value: '1000' },
  { label: t('admin.monitor.autoRefresh.sec5'), value: '5000' },
  { label: t('admin.monitor.autoRefresh.sec10'), value: '10000' },
])

const columns = computed(() => [
  { key: 'name', label: t('admin.monitor.tables.services.columns.name') },
  { key: 'status', label: t('admin.monitor.tables.services.columns.status'), width: '120px' },
  { key: 'latency', label: t('admin.monitor.tables.services.columns.latency'), width: '120px' },
  { key: 'detail', label: t('admin.monitor.tables.services.columns.detail') },
])

const formatUptime = (seconds?: number) => {
  if (!seconds || seconds < 0) {
    return '0m'
  }
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) {
    return `${d}d ${h}h`
  }
  if (h > 0) {
    return `${h}h ${m}m`
  }
  return `${m}m`
}

const statusLabel = (value?: string) => {
  if (value === 'up') {
    return t('admin.monitor.status.up')
  }
  if (value === 'down') {
    return t('admin.monitor.status.down')
  }
  return t('admin.monitor.status.degraded')
}

const statusClass = (value?: string) => {
  if (value === 'up') {
    return 'status status--up'
  }
  if (value === 'down') {
    return 'status status--down'
  }
  return 'status status--degraded'
}

const serviceName = (name?: string) => {
  if (!name) {
    return '-'
  }
  if (name === 'database' || name === 'redis' || name === 'storage') {
    return t(`admin.monitor.serviceName.${name}`)
  }
  return name
}

const refresh = async () => {
  const error = await load()
  await nextTick()
  updateMetrics()
  if (error) {
    message.error(
      t('admin.monitor.toasts.loadFailTitle'),
      error instanceof Error ? error.message : t('admin.monitor.toasts.loadFailMessage'),
    )
  }
}

const refreshByButton = async () => {
  if (manualRefreshing.value) {
    return
  }
  manualRefreshing.value = true
  try {
    await refresh()
  } finally {
    manualRefreshing.value = false
  }
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer !== null) {
    window.clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  const interval = Number(autoRefreshInterval.value)
  if (!interval || interval <= 0) {
    return
  }
  autoRefreshTimer = window.setInterval(() => {
    if (!loading.value) {
      void refresh()
    }
  }, interval)
}

onMounted(() => {
  void refresh()
})

watch(autoRefreshInterval, () => {
  startAutoRefresh()
})

onBeforeUnmount(() => {
  stopAutoRefresh()
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.monitor.service.title')" :subtitle="t('admin.monitor.service.subtitle')">
      <template #actions>
        <Select
          v-model="autoRefreshInterval"
          size="sm"
          auto-width
          :options="autoRefreshOptions"
        />
        <Button class="refresh-btn" :loading="loading && manualRefreshing" @click="refreshByButton">{{ t('common.refresh') }}</Button>
      </template>
    </PageHeader>

    <div class="content-wrap" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
      <div ref="scrollRef" class="content-scroll overlay-scroll" @scroll="onScroll">
        <div class="cards">
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.serviceHealth') }}</div>
            <div class="card__value">{{ summary?.up ?? 0 }} / {{ summary?.total ?? 0 }}</div>
          </article>
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.cpuUsage') }}</div>
            <div class="card__value">{{ cpu?.usage_percent ?? '-' }}<span v-if="cpu?.usage_percent !== undefined">%</span></div>
          </article>
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.memoryUsage') }}</div>
            <div class="card__value">
              {{ memory?.usage_percent ?? '-' }}<span v-if="memory?.usage_percent !== undefined">%</span>
            </div>
          </article>
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.diskUsage') }}</div>
            <div class="card__value">{{ disk?.usage_percent ?? '-' }}<span v-if="disk?.usage_percent !== undefined">%</span></div>
          </article>
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.appUptime') }}</div>
            <div class="card__value">{{ formatUptime(overview?.app_uptime_seconds) }}</div>
          </article>
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.serviceDown') }}</div>
            <div class="card__value">{{ summary?.down ?? 0 }}</div>
          </article>
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.serviceDegraded') }}</div>
            <div class="card__value">{{ summary?.degraded ?? 0 }}</div>
          </article>
        </div>

        <Table :columns="columns" :rows="services">
          <template #cell-name="{ row }">{{ serviceName(row.name) }}</template>
          <template #cell-status="{ row }">
            <span :class="statusClass(row.status)">{{ statusLabel(row.status) }}</span>
          </template>
          <template #cell-latency="{ row }">
            {{ row.latency_ms !== undefined && row.latency_ms !== null ? `${row.latency_ms}ms` : '-' }}
          </template>
        </Table>

        <div class="detail-grid">
          <article class="detail-card">
            <div class="detail-card__title">{{ t('admin.monitor.sections.server') }}</div>
            <div class="kv"><span>{{ t('admin.monitor.fields.hostname') }}</span><span>{{ server?.hostname || '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.os') }}</span><span>{{ server?.os || '-' }} {{ server?.os_release || '' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.machine') }}</span><span>{{ server?.machine || '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.processor') }}</span><span>{{ server?.processor || '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.startedAt') }}</span><span>{{ server?.app_start_time ? formatTime(server.app_start_time) : '-' }}</span></div>
          </article>
          <article class="detail-card">
            <div class="detail-card__title">{{ t('admin.monitor.sections.memoryDisk') }}</div>
            <div class="kv"><span>{{ t('admin.monitor.fields.memoryTotal') }}</span><span>{{ formatBytes(memory?.total_bytes ?? NaN) }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.memoryUsed') }}</span><span>{{ formatBytes(memory?.used_bytes ?? NaN) }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.diskPath') }}</span><span>{{ disk?.path || '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.diskFree') }}</span><span>{{ formatBytes(disk?.free_bytes ?? NaN) }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.cpuCores') }}</span><span>{{ cpu?.logical_cores ?? '-' }}</span></div>
          </article>
          <article class="detail-card">
            <div class="detail-card__title">{{ t('admin.monitor.sections.python') }}</div>
            <div class="kv"><span>{{ t('admin.monitor.fields.pythonStatus') }}</span><span>{{ python?.status || '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.pythonVersion') }}</span><span>{{ python?.version || '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.pythonImpl') }}</span><span>{{ python?.implementation || '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.pythonPid') }}</span><span>{{ python?.process_id ?? '-' }}</span></div>
            <div class="kv"><span>{{ t('admin.monitor.fields.pythonCpu') }}</span><span>{{ python?.process_cpu_percent ?? '-' }}<template v-if="python?.process_cpu_percent !== undefined">%</template></span></div>
          </article>
        </div>

        <div class="footnote">
          {{ t('admin.monitor.lastUpdated') }}:
          {{ overview?.generated_at ? formatTime(overview.generated_at) : '-' }}
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
  </section>
</template>

<style scoped>
.page {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: var(--space-4);
  min-height: 0;
  height: 100%;
  overflow: hidden;
  align-content: start;
}

.content-wrap {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: color-mix(in srgb, var(--color-surface-2) 28%, var(--color-surface));
  padding: var(--space-3);
}

.content-scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: var(--space-4);
  align-content: start;
  -webkit-overflow-scrolling: touch;
  padding-right: 6px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
  align-items: start;
}

.card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
}

.card__label {
  color: var(--color-muted);
  font-size: 12px;
}

.card__value {
  margin-top: var(--space-1);
  font-size: 24px;
  font-weight: 600;
}

.status {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
}

.status--up {
  color: #0f5132;
  background: #d1e7dd;
  border-color: #badbcc;
}

.status--down {
  color: #842029;
  background: #f8d7da;
  border-color: #f5c2c7;
}

.status--degraded {
  color: #664d03;
  background: #fff3cd;
  border-color: #ffecb5;
}

.footnote {
  color: var(--color-muted);
  font-size: 12px;
}

.detail-grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  align-items: start;
}

.detail-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: var(--space-3) var(--space-4);
  display: grid;
  gap: var(--space-2);
}

.detail-card__title {
  font-size: 14px;
  font-weight: 600;
}

.kv {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: 13px;
}

.refresh-btn {
  align-self: end;
}
</style>
