<script setup lang="ts">
import PageHeader from '@/components/common/PageHeader.vue'
import Button from '@/components/common/Button.vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const goFiles = () => {
  router.push('/app/files')
}
</script>

<template>
  <section class="page">
    <PageHeader title="归档管理" subtitle="压缩与解压请在网盘文件页操作" />
    <div class="panel">
      <p class="panel__desc">归档任务从网盘文件页发起，任务状态会在文件列表中体现。</p>
      <Button variant="primary" @click="goFiles">前往网盘文件</Button>
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
