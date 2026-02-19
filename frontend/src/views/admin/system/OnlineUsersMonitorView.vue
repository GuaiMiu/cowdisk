<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import Table from '@/components/common/Table.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import type { MonitorOnlineSession } from '@/types/system-monitor'
import { formatTime } from '@/utils/format'
import { useMessage } from '@/stores/message'
import { useSystemMonitorOverview } from '@/composables/useSystemMonitorOverview'
import { forceLogoutOnlineSession } from '@/api/modules/adminSystem'

const { t } = useI18n({ useScope: 'global' })
const message = useMessage()
const { loading, overview, load } = useSystemMonitorOverview()
const forceOpen = ref(false)
const forceSession = ref<MonitorOnlineSession | null>(null)
const forcing = ref(false)

const sessions = computed<MonitorOnlineSession[]>(() => overview.value?.online_users?.sessions || [])
const online = computed(() => overview.value?.online_users)

const columns = computed(() => [
  { key: 'username', label: t('admin.monitor.tables.online.columns.user') },
  { key: 'login_ip', label: t('admin.monitor.tables.online.columns.ip'), width: '150px' },
  { key: 'token_ttl', label: t('admin.monitor.tables.online.columns.ttl'), width: '140px' },
  { key: 'user_agent', label: t('admin.monitor.tables.online.columns.device') },
  { key: 'actions', label: t('admin.monitor.tables.online.columns.actions'), width: '120px' },
])

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
  if (error) {
    message.error(
      t('admin.monitor.toasts.loadFailTitle'),
      error instanceof Error ? error.message : t('admin.monitor.toasts.loadFailMessage'),
    )
  }
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

onMounted(() => {
  void refresh()
})
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.monitor.online.title')" :subtitle="t('admin.monitor.online.subtitle')">
      <template #actions>
        <Button :loading="loading" @click="refresh">{{ t('common.refresh') }}</Button>
      </template>
    </PageHeader>

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

    <ConfirmDialog
      :open="forceOpen"
      :title="t('admin.monitor.confirm.forceTitle')"
      :message="t('admin.monitor.confirm.forceMessage')"
      :confirm-text="forcing ? t('common.loading') : t('admin.monitor.actions.forceLogout')"
      @close="forceOpen = false"
      @confirm="doForceLogout"
    />
  </section>
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-4);
  min-height: 0;
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
</style>
