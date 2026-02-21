<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { getLocale, setLocale } from '@/i18n'

const authStore = useAuthStore()
const appStore = useAppStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n({ useScope: 'global' })
const currentLocale = computed(() => getLocale())
const siteName = computed(() => appStore.siteName || 'CowDisk')

const username = ref('')
const password = ref('')
const loading = computed(() => authStore.loading)
const errors = reactive({
  username: '',
  password: '',
})

const validate = () => {
  errors.username = ''
  errors.password = ''
  const trimmed = username.value.trim()
  if (!trimmed) {
    errors.username = t('auth.login.validation.usernameRequired')
  } else if (trimmed.length < 4 || trimmed.length > 20) {
    errors.username = t('auth.login.validation.usernameLength')
  }
  if (!password.value) {
    errors.password = t('auth.login.validation.passwordRequired')
  } else if (password.value.length < 4 || password.value.length > 20) {
    errors.password = t('auth.login.validation.passwordLength')
  }
  return !errors.username && !errors.password
}

const onSubmit = async () => {
  if (!validate()) {
    return
  }
  await authStore.login({ username: username.value.trim(), password: password.value })
  const redirect = route.query.redirect as string | undefined
  await router.replace(redirect || authStore.landingPath())
}

const switchLocale = async (locale: string) => {
  await setLocale(locale)
}
</script>

<template>
  <div class="login auth-page">
    <div class="login__panel auth-page__panel">
      <div class="login__brand-row">
        <div class="login__brand" :title="siteName">{{ siteName }}</div>
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
      <h1 class="login__title">{{ t('auth.login.title') }}</h1>
      <form class="login__form" @submit.prevent="onSubmit">
        <Input
          v-model="username"
          :label="t('auth.login.username')"
          :placeholder="t('auth.login.usernamePlaceholder')"
          :error="errors.username"
        />
        <Input
          v-model="password"
          :label="t('auth.login.password')"
          type="password"
          :placeholder="t('auth.login.passwordPlaceholder')"
          :error="errors.password"
        />
        <Button type="submit" block :loading="loading">{{ t('auth.login.submit') }}</Button>
      </form>
      <div class="login__links">
        <span>
          {{ t('auth.login.noAccount') }}
          <RouterLink to="/register">{{ t('auth.login.registerLink') }}</RouterLink>
        </span>
        <RouterLink to="/forgot-password">{{ t('auth.login.forgotPassword') }}</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login__brand-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.login__brand {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-primary);
  max-width: min(220px, 52vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.login__title {
  font-size: 32px;
}

.login__form {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-2);
}

.login__links {
  font-size: 12px;
  color: var(--color-muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.login__links a {
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
</style>
