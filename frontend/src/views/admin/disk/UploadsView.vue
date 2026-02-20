<script setup lang="ts">
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { t } = useI18n({ useScope: 'global' })

const goFiles = () => {
  router.push('/app/files')
}
</script>

<template>
  <section class="page">
    <PageHeader :title="t('admin.disk.uploads.title')" :subtitle="t('admin.disk.uploads.subtitle')" />
    <div class="panel">
      <p class="panel__desc">{{ t('admin.disk.uploads.desc') }}</p>
      <Button variant="primary" @click="goFiles">{{ t('admin.disk.uploads.goFiles') }}</Button>
    </div>
  </section>
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-4);
}

.panel {
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  display: grid;
  gap: var(--space-3);
}

.panel__desc {
  color: var(--color-muted);
  font-size: 13px;
}
</style>
