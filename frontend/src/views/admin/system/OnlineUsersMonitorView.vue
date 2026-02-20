<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Select from '@/components/common/Select.vue'
import Table from '@/components/common/Table.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import type { MonitorOnlineSession } from '@/types/system-monitor'
import { formatTime } from '@/utils/format'
import { useMessage } from '@/stores/message'
import { useSystemMonitorOverview } from '@/composables/useSystemMonitorOverview'
import { useOverlayScrollbar } from '@/composables/useOverlayScrollbar'
import { forceLogoutOnlineSession } from '@/api/modules/adminSystem'

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
const forceOpen = ref(false)
const forceSession = ref<MonitorOnlineSession | null>(null)
const forcing = ref(false)
const autoRefreshInterval = ref('')
const isMobile = ref(false)
let autoRefreshTimer: number | null = null
let mobileQuery: MediaQueryList | null = null

const sessions = computed<MonitorOnlineSession[]>(() => overview.value?.online_users?.sessions || [])
const online = computed(() => overview.value?.online_users)
const autoRefreshOptions = computed(() => [
  { label: t('admin.monitor.autoRefresh.off'), value: '' },
  { label: t('admin.monitor.autoRefresh.sec1'), value: '1000' },
  { label: t('admin.monitor.autoRefresh.sec5'), value: '5000' },
  { label: t('admin.monitor.autoRefresh.sec10'), value: '10000' },
])

const columns = computed(() => {
  const baseColumns: Array<{ key: string; label: string; width?: string }> = [
    {
      key: 'username',
      label: t('admin.monitor.tables.online.columns.user'),
      width: isMobile.value ? '86px' : '120px',
    },
    {
      key: 'login_ip',
      label: t('admin.monitor.tables.online.columns.ip'),
      width: isMobile.value ? '170px' : '190px',
    },
    {
      key: 'token_ttl',
      label: t('admin.monitor.tables.online.columns.ttl'),
      width: isMobile.value ? '76px' : '140px',
    },
  ]
  if (!isMobile.value) {
    baseColumns.push({ key: 'user_agent', label: t('admin.monitor.tables.online.columns.device') })
  }
  baseColumns.push({
    key: 'actions',
    label: t('admin.monitor.tables.online.columns.actions'),
    width: isMobile.value ? '94px' : '120px',
  })
  return baseColumns
})

const formatTtl = (value?: number | null) => {
  if (value === null || value === undefined || value < 0) {
    return '-'
  }
  if (value < 60) {
    return `${value}s`
  }
  if (value < 3600) {
    return `${Math.floor(value / 60)}m`
  }
  return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`
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
    if (!loading.value && !forcing.value) {
      void refresh()
    }
  }, interval)
}

const askForceLogout = (session: MonitorOnlineSession) => {
  forceSession.value = session
  forceOpen.value = true
}

const doForceLogout = async () => {
  if (!forceSession.value?.session_id || forcing.value) {
    return
  }
  forcing.value = true
  try {
    await forceLogoutOnlineSession(forceSession.value.session_id)
    message.success(t('admin.monitor.toasts.forceSuccess'))
    forceOpen.value = false
    forceSession.value = null
    await refresh()
  } catch (error) {
    message.error(
      t('admin.monitor.toasts.forceFailTitle'),
      error instanceof Error ? error.message : t('admin.monitor.toasts.forceFailMessage'),
    )
  } finally {
    forcing.value = false
  }
}

const updateViewport = () => {
  isMobile.value = mobileQuery?.matches ?? window.innerWidth <= 768
}

onMounted(() => {
  mobileQuery = window.matchMedia('(max-width: 768px)')
  updateViewport()
  if (typeof mobileQuery.addEventListener === 'function') {
    mobileQuery.addEventListener('change', updateViewport)
  } else {
    mobileQuery.addListener(updateViewport)
  }
  void refresh()
})

watch(autoRefreshInterval, () => {
  startAutoRefresh()
})

onBeforeUnmount(() => {
  stopAutoRefresh()
  if (!mobileQuery) {
    return
  }
  if (typeof mobileQuery.removeEventListener === 'function') {
    mobileQuery.removeEventListener('change', updateViewport)
  } else {
    mobileQuery.removeListener(updateViewport)
  }
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.monitor.online.title')" :subtitle="t('admin.monitor.online.subtitle')">
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
            <div class="card__label">{{ t('admin.monitor.cards.onlineUsers') }}</div>
            <div class="card__value">{{ online?.total_users ?? 0 }}</div>
          </article>
          <article class="card">
            <div class="card__label">{{ t('admin.monitor.cards.onlineSessions') }}</div>
            <div class="card__value">{{ online?.total_sessions ?? 0 }}</div>
          </article>
        </div>

        <Table :columns="columns" :rows="sessions">
          <template #cell-username="{ row }">{{ row.username || `#${row.user_id}` }}</template>
          <template #cell-token_ttl="{ row }">{{ formatTtl(row.token_ttl_seconds) }}</template>
          <template #cell-user_agent="{ row }">
            <span class="cell-ellipsis" :title="row.user_agent || '-'">{{ row.user_agent || '-' }}</span>
          </template>
          <template #cell-actions="{ row }">
            <Button size="sm" variant="danger" v-permission="'cfg:core:write'" @click="askForceLogout(row)">
              {{ t('admin.monitor.actions.forceLogout') }}
            </Button>
          </template>
        </Table>

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

    <ConfirmDialog
      :open="forceOpen"
      :title="t('admin.monitor.confirm.forceTitle')"
      :message="t('admin.monitor.confirm.forceMessage')"
      :confirm-text="t('admin.monitor.actions.forceLogout')"
      :confirm-loading="forcing"
      :cancel-disabled="forcing"
      @close="forceOpen = false"
      @confirm="doForceLogout"
    />
  </section>
</template>

<style scoped>
.page {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: var(--space-4);
  height: 100%;
  min-height: 0;
  overflow: hidden;
  align-content: start;
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

.footnote {
  color: var(--color-muted);
  font-size: 12px;
}

.refresh-btn {
  align-self: end;
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

.cell-ellipsis {
  display: block;
  min-width: 0;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
