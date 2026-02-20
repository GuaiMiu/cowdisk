<script setup lang="ts">
import Button from '@/components/common/Button.vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="status">
    <div class="status__card">
      <div class="status__code">404</div>
      <h1 class="status__title">{{ t('statusPage.notFoundTitle') }}</h1>
      <p class="status__desc">{{ t('statusPage.notFoundDesc') }}</p>
      <Button variant="secondary" @click="$router.push('/app/files')">
        {{ t('statusPage.backHome') }}
      </Button>
    </div>
  </div>
</template>

<style scoped>
.status {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--space-6);
}

.status__card {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  padding: var(--space-8);
  text-align: center;
  display: grid;
  gap: var(--space-3);
  box-shadow: var(--shadow-sm);
}

.status__code {
  font-size: 48px;
  font-weight: 700;
  color: var(--color-primary);
}

.status__desc {
  color: var(--color-muted);
}
</style>
