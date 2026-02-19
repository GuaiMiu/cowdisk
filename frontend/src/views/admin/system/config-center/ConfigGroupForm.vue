<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'
import Switch from '@/components/common/Switch.vue'
import type { ConfigSpec } from '@/types/config-center'

const props = defineProps<{
  items: ConfigSpec[]
  form: Record<string, unknown>
  errors: Record<string, string>
  editingSecrets: Record<string, boolean>
  loading: boolean
  saving: boolean
  dirtyCount: number
  saveLabel?: string
  panelTitle?: string
  panelSubtitle?: string
  buildRulesHint: (item: ConfigSpec) => string
}>()

const emit = defineEmits<{
  (event: 'save'): void
  (event: 'update', payload: { key: string; value: unknown }): void
  (event: 'edit-secret', key: string): void
}>()
const { t } = useI18n({ useScope: 'global' })

const totalItems = computed(() => props.items.length)

const handleUpdate = (key: string, value: unknown) => {
  emit('update', { key, value })
}

const enableSecret = (key: string) => {
  emit('edit-secret', key)
}

const isReadonly = (item: ConfigSpec) => item.editable === false
</script>

<template>
  <div class="config-panel">
    <div class="panel-actions">
      <div class="panel-meta">
        <div class="panel-title">{{ panelTitle || t('admin.configShared.form.itemsTitle') }}</div>
        <div class="panel-subtitle">
          {{ panelSubtitle || t('admin.configShared.form.totalItems', { total: totalItems }) }}
          <span v-if="dirtyCount > 0">
            {{ t('admin.configShared.form.dirtyItems', { count: dirtyCount }) }}
          </span>
        </div>
      </div>
      <div class="panel-buttons">
        <Button
          variant="primary"
          :disabled="dirtyCount === 0"
          :loading="saving"
          @click="emit('save')"
        >
          {{ saveLabel || t('common.save') }}
        </Button>
      </div>
    </div>

    <div v-if="loading" class="panel-loading">{{ t('common.loadingEllipsis') }}</div>
    <div v-else class="config-scroll">
      <div class="config-grid">
        <div v-for="item in items" :key="item.key" class="config-item">
          <div class="config-meta">
            <div class="config-title">{{ item.key }}</div>
            <div class="config-desc">{{ item.description || t('admin.configShared.form.noDescription') }}</div>
            <div class="config-hint">{{ buildRulesHint(item) }}</div>
          </div>
          <div class="config-field">
            <div v-if="item.is_secret && !editingSecrets[item.key]" class="config-secret">
              <span class="config-secret__mask">******</span>
              <Button
                variant="secondary"
                size="sm"
                :disabled="isReadonly(item)"
                @click="enableSecret(item.key)"
                >{{ t('common.edit') }}</Button
              >
            </div>
            <Switch
              v-else-if="item.value_type === 'bool'"
              :model-value="Boolean(form[item.key])"
              :disabled="isReadonly(item)"
              @update:model-value="(value) => handleUpdate(item.key, value)"
            />
            <Select
              v-else-if="item.value_type === 'string' && item.rules?.enum?.length"
              :model-value="String(form[item.key] ?? '')"
              :options="item.rules.enum.map((value) => ({ label: value, value }))"
              :error="errors[item.key]"
              :disabled="isReadonly(item)"
              @update:model-value="(value) => handleUpdate(item.key, value)"
            />
            <Input
              v-else-if="item.value_type === 'int'"
              type="number"
              :model-value="String(form[item.key] ?? '')"
              :error="errors[item.key]"
              :disabled="isReadonly(item)"
              @update:model-value="(value) => handleUpdate(item.key, value)"
            />
            <div v-else-if="item.value_type === 'json'" class="config-json">
              <textarea
                :value="String(form[item.key] ?? '')"
                :class="['config-json__input', errors[item.key] ? 'is-error' : '']"
                rows="6"
                :disabled="isReadonly(item)"
                @input="
                  (event) =>
                    handleUpdate(item.key, (event.target as HTMLTextAreaElement).value)
                "
              />
              <div v-if="errors[item.key]" class="config-error">
                {{ errors[item.key] }}
              </div>
            </div>
            <Input
              v-else
              :model-value="String(form[item.key] ?? '')"
              :error="errors[item.key]"
              :disabled="isReadonly(item)"
              @update:model-value="(value) => handleUpdate(item.key, value)"
            />
            <div v-if="isReadonly(item)" class="config-readonly">
              {{ t('admin.configShared.form.readonlyByEnv') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-panel {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  display: grid;
  gap: var(--space-6);
}

.panel-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.panel-meta {
  display: grid;
  gap: 6px;
}

.panel-title {
  font-weight: 700;
  letter-spacing: 0.02em;
}

.panel-subtitle {
  color: var(--color-muted);
  font-size: 13px;
}

.panel-loading {
  color: var(--color-muted);
}

.config-grid {
  display: grid;
  gap: 0;
}

.config-scroll {
  overflow: visible;
}

.config-item {
  display: grid;
  grid-template-columns: minmax(240px, 1.15fr) minmax(240px, 1fr);
  gap: var(--space-6);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-border);
}

.config-meta {
  display: grid;
  gap: var(--space-2);
}

.config-title {
  font-weight: 600;
}

.config-desc {
  color: var(--color-muted);
  font-size: 13px;
}

.config-hint {
  color: var(--color-muted);
  font-size: 12px;
}

.config-field {
  display: grid;
  align-content: start;
}

.config-secret {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.config-secret__mask {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  color: var(--color-muted);
}

.config-json__input {
  width: 100%;
  min-height: 120px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  padding: var(--space-3);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  background: var(--color-surface);
}

.config-json__input.is-error {
  border-color: var(--color-danger);
}

.config-error {
  margin-top: var(--space-2);
  color: var(--color-danger);
  font-size: 12px;
}

.config-readonly {
  margin-top: var(--space-2);
  color: var(--color-muted);
  font-size: 12px;
}

@media (max-width: 960px) {
  .config-item {
    grid-template-columns: 1fr;
  }
}

.config-item:last-child {
  border-bottom: none;
}
</style>
