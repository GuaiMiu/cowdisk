<script setup lang="ts">
import Modal from './Modal.vue'
import Button from './Button.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    message?: string
    confirmText?: string
    cancelText?: string
    extraText?: string
    extraVariant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  }>(),
  {
    title: '确认操作',
    message: '',
    confirmText: '确认',
    cancelText: '取消',
    extraText: '',
    extraVariant: 'danger',
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
      <Button variant="secondary" @click="emit('close')">{{ cancelText }}</Button>
      <Button variant="primary" @click="emit('confirm')">{{ confirmText }}</Button>
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
