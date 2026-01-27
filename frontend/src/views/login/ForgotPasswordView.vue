<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import { useToastStore } from '@/stores/toast'

const { t } = useI18n({ useScope: 'global' })
const toast = useToastStore()
const mail = ref('')
const submitting = ref(false)
const errors = reactive({
  mail: '',
})

const isEmailValid = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)

const canSubmit = computed(() => mail.value.trim().length > 0)

const validate = () => {
  errors.mail = ''
  const mailValue = mail.value.trim()
  if (!mailValue) {
    errors.mail = t('auth.forgot.validation.emailRequired')
  } else if (!isEmailValid(mailValue)) {
    errors.mail = t('auth.forgot.validation.emailInvalid')
  }
  return !errors.mail
}

const onSubmit = async () => {
  if (!canSubmit.value || !validate()) {
    return
  }
  submitting.value = true
  try {
    toast.info(t('auth.forgot.unavailableTitle'), t('auth.forgot.unavailableMessage'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="forgot">
    <div class="forgot__panel">
      <div class="forgot__brand">CowDisk</div>
      <h1 class="forgot__title">{{ t('auth.forgot.title') }}</h1>
      <p class="forgot__subtitle">{{ t('auth.forgot.subtitle') }}</p>
      <form class="forgot__form" @submit.prevent="onSubmit">
        <Input
          v-model="mail"
          :label="t('auth.forgot.email')"
          type="email"
          :placeholder="t('auth.forgot.emailPlaceholder')"
          :error="errors.mail"
        />
        <Button type="submit" block :loading="submitting">{{ t('auth.forgot.submit') }}</Button>
      </form>
      <div class="forgot__footer">
        <RouterLink to="/login">{{ t('auth.forgot.backToLogin') }}</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.forgot {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--space-9);
  overflow: auto;
}

.forgot__panel {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  padding: var(--space-7);
  display: grid;
  gap: var(--space-4);
  box-shadow: var(--shadow-md);
  width: min(420px, 100%);
}

.forgot__brand {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-primary);
}

.forgot__title {
  font-size: 28px;
}

.forgot__subtitle {
  font-size: 13px;
  color: var(--color-muted);
}

.forgot__form {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-1);
}

.forgot__footer {
  font-size: 12px;
  color: var(--color-muted);
}

.forgot__footer a {
  color: inherit;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 1024px) {
  .forgot {
    padding: var(--space-7);
  }
}

@media (max-width: 768px) {
  .forgot {
    padding: var(--space-5);
  }
}
</style>
