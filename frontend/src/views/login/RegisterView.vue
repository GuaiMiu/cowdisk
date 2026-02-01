<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import { useAuthStore } from '@/stores/auth'
import { useMessage } from '@/stores/message'
import { register as registerApi } from '@/api/modules/auth'
import { getLocale, setLocale } from '@/i18n'

const authStore = useAuthStore()
const message = useMessage()
const router = useRouter()
const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const currentLocale = computed(() => getLocale())

const username = ref('')
const mail = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const errors = reactive({
  username: '',
  mail: '',
  password: '',
  confirmPassword: '',
})

const canSubmit = computed(() => {
  return (
    username.value.trim() &&
    mail.value.trim() &&
    password.value.trim() &&
    confirmPassword.value.trim()
  )
})

const isEmailValid = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
const isPasswordValid = (value: string) =>
  /^[A-Za-z0-9!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]+$/.test(value)

const validate = () => {
  errors.username = ''
  errors.mail = ''
  errors.password = ''
  errors.confirmPassword = ''
  const trimmed = username.value.trim()
  if (!trimmed) {
    errors.username = t('auth.register.validation.usernameRequired')
  } else if (trimmed.length < 4 || trimmed.length > 20) {
    errors.username = t('auth.register.validation.usernameLength')
  }
  const mailValue = mail.value.trim()
  if (!mailValue) {
    errors.mail = t('auth.register.validation.emailRequired')
  } else if (!isEmailValid(mailValue)) {
    errors.mail = t('auth.register.validation.emailInvalid')
  }
  if (!password.value) {
    errors.password = t('auth.register.validation.passwordRequired')
  } else if (password.value.length < 4 || password.value.length > 20) {
    errors.password = t('auth.register.validation.passwordLength')
  } else if (!isPasswordValid(password.value)) {
    errors.password = t('auth.register.validation.passwordIllegal')
  } else if (password.value === trimmed) {
    errors.password = t('auth.register.validation.passwordSame')
  }
  if (!confirmPassword.value) {
    errors.confirmPassword = t('auth.register.validation.confirmRequired')
  } else if (confirmPassword.value !== password.value) {
    errors.confirmPassword = t('auth.register.validation.passwordMismatch')
  }
  return !errors.username && !errors.mail && !errors.password && !errors.confirmPassword
}

const onSubmit = async () => {
  if (!canSubmit.value || !validate()) {
    return
  }
  submitting.value = true
  try {
    await registerApi({
      username: username.value.trim(),
      password: password.value,
      mail: mail.value.trim(),
    })
    await authStore.login({ username: username.value.trim(), password: password.value })
    const redirect = route.query.redirect as string | undefined
    await router.replace(redirect || authStore.landingPath())
  } catch (error) {
    message.error(
      t('auth.register.errorTitle'),
      error instanceof Error ? error.message : t('auth.register.errorFallback'),
    )
  } finally {
    submitting.value = false
  }
}

const switchLocale = async (locale: string) => {
  await setLocale(locale)
}
</script>

<template>
  <div class="register">
    <div class="register__panel">
      <div class="register__brand-row">
        <div class="register__brand">CowDisk</div>
        <div class="lang-switch">
          <button
            type="button"
            class="lang-switch__btn"
            :class="{ 'is-active': currentLocale === 'zh-CN' }"
            @click="switchLocale('zh-CN')"
          >
            {{ t('layout.userMenu.langZh') }}
          </button>
          <button
            type="button"
            class="lang-switch__btn"
            :class="{ 'is-active': currentLocale === 'en-US' }"
            @click="switchLocale('en-US')"
          >
            {{ t('layout.userMenu.langEn') }}
          </button>
        </div>
      </div>
      <h1 class="register__title">{{ t('auth.register.title') }}</h1>
      <form class="register__form" @submit.prevent="onSubmit">
        <Input
          v-model="username"
          :label="t('auth.register.username')"
          :placeholder="t('auth.register.usernamePlaceholder')"
          :error="errors.username"
        />
        <Input
          v-model="mail"
          :label="t('auth.register.email')"
          type="email"
          :placeholder="t('auth.register.emailPlaceholder')"
          :error="errors.mail"
        />
        <Input
          v-model="password"
          :label="t('auth.register.password')"
          type="password"
          :placeholder="t('auth.register.passwordPlaceholder')"
          :error="errors.password"
        />
        <Input
          v-model="confirmPassword"
          :label="t('auth.register.confirmPassword')"
          type="password"
          :placeholder="t('auth.register.confirmPasswordPlaceholder')"
          :error="errors.confirmPassword"
        />
        <Button type="submit" block :loading="submitting">{{ t('auth.register.submit') }}</Button>
      </form>
      <div class="register__footer">
        {{ t('auth.register.hasAccount') }}
        <RouterLink to="/login">{{ t('auth.register.loginLink') }}</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--space-9);
  overflow: auto;
}

.register__panel {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  padding: var(--space-7);
  display: grid;
  gap: var(--space-4);
  box-shadow: var(--shadow-md);
  width: min(440px, 100%);
}

.register__brand-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.register__brand {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-primary);
}

.register__title {
  font-size: 30px;
}

.register__form {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-2);
}

.register__footer {
  font-size: 12px;
  color: var(--color-muted);
}

.register__footer a {
  color: inherit;
  font-weight: 600;
  text-decoration: none;
}

.lang-switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.lang-switch__btn {
  border: none;
  background: transparent;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--color-muted);
  cursor: pointer;
}

.lang-switch__btn.is-active {
  background: var(--color-primary);
  color: var(--color-primary-contrast);
}

@media (max-width: 1024px) {
  .register {
    padding: var(--space-7);
  }
}

@media (max-width: 768px) {
  .register {
    padding: var(--space-5);
  }
}
</style>
