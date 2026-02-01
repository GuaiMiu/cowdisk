<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Input from '@/components/common/Input.vue'
import Select from '@/components/common/Select.vue'

export type ShareFormValue = {
  expiresInDays: number | null
  expiresAt: string | null
  requiresCode: boolean
  code: string
}

const props = defineProps<{
  modelValue: ShareFormValue
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: ShareFormValue): void
}>()

const { t } = useI18n({ useScope: 'global' })

const baseOptions = computed(() => [
  { label: t('shareForm.expiresOptions.permanent'), value: 'permanent' },
  { label: t('shareForm.expiresOptions.days1'), value: '1' },
  { label: t('shareForm.expiresOptions.days7'), value: '7' },
  { label: t('shareForm.expiresOptions.days30'), value: '30' },
  { label: t('shareForm.expiresOptions.days90'), value: '90' },
  { label: t('shareForm.expiresOptions.custom'), value: 'custom' },
])

const resolvedDays = computed(() => {
  if (props.modelValue.expiresAt) {
    return 'custom'
  }
  if (!props.modelValue.expiresInDays || props.modelValue.expiresInDays <= 0) {
    return 'permanent'
  }
  const value = String(props.modelValue.expiresInDays)
  const preset = ['1', '7', '30', '90']
  if (preset.includes(value)) {
    return value
  }
  return 'custom'
})

const options = computed(() => baseOptions.value)

const toLocalInputValue = (date: Date) => {
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const updateExpires = (value: string | number) => {
  if (value === 'permanent') {
    emit('update:modelValue', { ...props.modelValue, expiresInDays: null, expiresAt: null })
    return
  }
  if (value === 'custom') {
    const fallback =
      props.modelValue.expiresAt || toLocalInputValue(new Date(Date.now() + 86400000))
    emit('update:modelValue', { ...props.modelValue, expiresInDays: null, expiresAt: fallback })
    return
  }
  const days = Number(value)
  emit('update:modelValue', {
    ...props.modelValue,
    expiresInDays: Number.isFinite(days) ? days : null,
    expiresAt: null,
  })
}

const updateCustomDate = (value: string) => {
  emit('update:modelValue', {
    ...props.modelValue,
    expiresInDays: null,
    expiresAt: value,
  })
}

const customDateTime = computed(() => props.modelValue.expiresAt ?? '')

const updateCode = (value: string) => {
  const digits = value.replace(/\D/g, '').slice(0, 4)
  emit('update:modelValue', { ...props.modelValue, code: digits })
}

const generateCode = () => String(Math.floor(1000 + Math.random() * 9000))

const updateRequiresCode = (value: boolean) => {
  if (value && !props.modelValue.code) {
    emit('update:modelValue', { ...props.modelValue, requiresCode: value, code: generateCode() })
    return
  }
  if (!value) {
    emit('update:modelValue', { ...props.modelValue, requiresCode: value, code: '' })
    return
  }
  emit('update:modelValue', { ...props.modelValue, requiresCode: value })
}

watch(
  () => props.modelValue.requiresCode,
  (value) => {
    if (value && !props.modelValue.code) {
      emit('update:modelValue', { ...props.modelValue, code: generateCode() })
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="share-form">
    <div class="share-form__row">
      <Select
        size="sm"
        :label="t('shareForm.labels.expiresIn')"
        :model-value="resolvedDays"
        :options="options"
        @update:modelValue="updateExpires"
      />
      <Input
        v-if="resolvedDays === 'custom'"
        type="datetime-local"
        :label="t('shareForm.labels.expiresAt')"
        :model-value="customDateTime"
        @update:modelValue="updateCustomDate"
      />
    </div>
    <Input
      :label="t('shareForm.labels.code')"
      :model-value="modelValue.code"
      :placeholder="t('shareForm.labels.codePlaceholder')"
      :disabled="!modelValue.requiresCode"
      @update:modelValue="updateCode"
    />
    <label class="share-form__toggle">
      <input
        type="checkbox"
        :checked="modelValue.requiresCode"
        @change="updateRequiresCode(($event.target as HTMLInputElement).checked)"
      />
      <span>{{ t('shareForm.labels.requireCode') }}</span>
    </label>
  </div>
</template>

<style scoped>
.share-form {
  display: grid;
  gap: var(--space-4);
}

.share-form__row {
  display: grid;
  gap: var(--space-3);
}

.share-form__toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  color: var(--color-text);
}
</style>
