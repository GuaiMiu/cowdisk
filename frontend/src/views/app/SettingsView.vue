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
}
</style>
