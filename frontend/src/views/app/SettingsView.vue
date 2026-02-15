<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <section class="page">
    <PageHeader :title="t('settings.title')" :subtitle="t('settings.subtitle')" />
    <div class="settings__placeholder">{{ t('settings.subtitle') }}</div>
  </section>
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-4);
  grid-template-rows: auto 1fr;
  min-height: 0;
}

.settings__placeholder {
  padding: var(--space-6);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-muted);
  font-size: 13px;
  transition:
    border-color var(--transition-fast),
    background var(--transition-base),
    transform var(--transition-fast);
  animation: settingsFadeIn var(--duration-slow) var(--ease-standard);
}

.settings__placeholder:hover {
  border-color: var(--color-primary-soft-strong);
  background: var(--color-surface-2);
  transform: var(--interaction-hover-lift);
}

@keyframes settingsFadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
