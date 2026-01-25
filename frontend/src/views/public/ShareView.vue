<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Table from '@/components/common/Table.vue'
import FileBreadcrumb from '@/components/file/FileBreadcrumb.vue'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import { usePublicShare } from '@/composables/usePublicShare'
import { formatBytes, formatTime } from '@/utils/format'
import type { DiskEntry } from '@/types/disk'

const route = useRoute()
const token = route.params.token as string
const share = usePublicShare(token)
const unlockCode = ref('')
const redirectCount = ref(5)
let redirectTimer: number | null = null
const asEntry = (row: unknown) => row as DiskEntry
const goHome = () => {
  window.location.href = '/'
}

const columns = [
  { key: 'name', label: '名称' },
  { key: 'size', label: '大小' },
  { key: 'actions', label: '操作' },
]

onMounted(() => {
  void share.loadShare()
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

onBeforeUnmount(() => {
  if (redirectTimer) {
    window.clearInterval(redirectTimer)
  }
})
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
        <div class="notice__title">分享不可用</div>
        <div class="notice__desc">{{ share.errorMessage.value }}</div>
        <div class="notice__hint">{{ redirectCount }} 秒后返回首页</div>
        <Button variant="secondary" @click="goHome">返回首页</Button>
      </div>
    </div>
    <div v-else-if="share.locked.value" class="unlock">
      <div class="unlock__card">
        <div class="unlock__title">需要提取码</div>
        <div class="unlock__subtitle">输入分享提取码以访问内容</div>
        <div class="unlock__meta">
          <span>分享人：{{ (share.share.value as any)?.ownerName || '-' }}</span>
          <span>
            有效期：{{
              (share.share.value as any)?.expiresAt
                ? formatTime((share.share.value as any)?.expiresAt)
                : '永久'
            }}
          </span>
        </div>
        <div class="unlock__form">
          <Input v-model="unlockCode" label="提取码" placeholder="请输入 4 位提取码" />
          <Button :loading="share.loading.value" @click="share.unlock(unlockCode)">解锁</Button>
        </div>
        <div v-if="share.unlockError.value" class="unlock__error">{{ share.unlockError.value }}</div>
        <div class="unlock__hint">若无法获取提取码，请联系分享者</div>
      </div>
    </div>

    <div v-else-if="share.isFile.value" class="file-card">
      <div class="file-card__title">{{ (share.share.value as any)?.name }}</div>
      <div class="file-card__meta">
        <span>大小：{{ share.fileMeta.value?.size ? formatBytes(share.fileMeta.value.size) : '-' }}</span>
        <span>类型：{{ share.fileMeta.value?.mime || '-' }}</span>
        <span>分享人：{{ (share.share.value as any)?.ownerName || '-' }}</span>
        <span>
          有效期：{{
            (share.share.value as any)?.expiresAt
              ? formatTime((share.share.value as any)?.expiresAt)
              : '永久'
          }}
        </span>
      </div>
      <div class="file-card__actions">
        <Button variant="secondary" @click="share.preview()">预览</Button>
        <Button @click="share.download()">下载</Button>
      </div>
    </div>

    <div v-else class="share__body">
      <div class="share__panel">
        <div class="share__bar">
          <div class="share__title">{{ (share.share.value as any)?.name || '分享内容' }}</div>
          <div class="share__meta">
            <span>分享人：{{ (share.share.value as any)?.ownerName || '-' }}</span>
            <span>
              有效期：{{
                (share.share.value as any)?.expiresAt
                  ? formatTime((share.share.value as any)?.expiresAt)
                  : '永久'
              }}
            </span>
          </div>
          <FileBreadcrumb
            :path="share.currentPath.value || '/'"
            @navigate="(path) => share.loadEntries(path === '/' ? undefined : path)"
          />
        </div>
        <div class="share__table">
        <Table :columns="columns" :rows="share.items.value" :min-rows="10" scrollable fill>
          <template #cell-name="{ row }">
            <button
              v-if="asEntry(row).is_dir"
              type="button"
              class="name name--clickable"
              @click="share.loadEntries(asEntry(row).path as string)"
            >
              <FileTypeIcon :name="asEntry(row).name" :is-dir="asEntry(row).is_dir" />
              <span class="name__text">{{ asEntry(row).name }}</span>
            </button>
            <div v-else class="name">
              <FileTypeIcon :name="asEntry(row).name" :is-dir="asEntry(row).is_dir" />
              <span class="name__text">{{ asEntry(row).name }}</span>
            </div>
          </template>
          <template #cell-size="{ row }">
            {{ asEntry(row).is_dir ? '-' : formatBytes(asEntry(row).size as number) }}
          </template>
          <template #cell-actions="{ row }">
            <div class="actions">
              <Button
                v-if="!asEntry(row).is_dir"
                size="sm"
                variant="secondary"
                @click="share.download(asEntry(row).path as string)"
              >
                下载
              </Button>
              <Button v-if="!asEntry(row).is_dir" size="sm" variant="ghost" @click="share.preview(asEntry(row).path as string)">
                预览
              </Button>
            </div>
          </template>
          </Table>
        </div>
      </div>
    </div>
  </section>
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
  width: min(1200px, 96vw);
  height: min(78vh, 100%);
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

.name {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  color: var(--color-text);
}

.name__text {
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.file-card__title {
  font-size: 20px;
  font-weight: 600;
}

.file-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  color: var(--color-muted);
  font-size: 13px;
}

.file-card__actions {
  display: flex;
  gap: var(--space-2);
}

.actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .share {
    padding: var(--space-4);
  }
}
</style>
