<script setup lang="ts">
import Modal from './Modal.vue'
import Button from './Button.vue'
import { i18n } from '@/i18n'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    message?: string
    confirmText?: string
    cancelText?: string
    extraText?: string
    extraVariant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    confirmLoading?: boolean
    confirmDisabled?: boolean
    cancelDisabled?: boolean
  }>(),
  {
    title: i18n.global.t('common.confirmAction'),
    message: '',
    confirmText: i18n.global.t('common.confirm'),
    cancelText: i18n.global.t('common.cancel'),
    extraText: '',
    extraVariant: 'danger',
    confirmLoading: false,
    confirmDisabled: false,
    cancelDisabled: false,
  },
)

const emit = defineEmits<{
  (event: 'confirm'): void
  (event: 'extra'): void
  (event: 'close'): void
}>()
</script>

<template>
  <Modal :open="open" :title="title" @close="emit('close')">
    <p class="confirm__message">{{ message }}</p>
    <template #footer>
      <Button
        v-if="extraText"
        class="confirm__extra"
        :variant="extraVariant"
        @click="emit('extra')"
      >
        {{ extraText }}
      </Button>
      <Button variant="secondary" :disabled="cancelDisabled || confirmLoading" @click="emit('close')">{{ cancelText }}</Button>
      <Button
        variant="primary"
        :loading="confirmLoading"
        :disabled="confirmDisabled"
        @click="emit('confirm')"
      >
        {{ confirmText }}
      </Button>
    </template>
  </Modal>
</template>

<style scoped>
.confirm__message {
  color: var(--color-muted);
  line-height: 1.6;
}

.confirm__extra {
  margin-right: auto;
}
</style>
