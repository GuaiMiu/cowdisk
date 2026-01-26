<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n({ useScope: 'global' })

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
</script>

<template>
  <div class="login">
    <div class="login__panel">
      <div class="login__brand">CowDisk</div>
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
      <div class="login__footer">
        {{ t('auth.login.noAccount') }}
        <RouterLink to="/register">{{ t('auth.login.registerLink') }}</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--space-9);
  overflow: auto;
}

.login__panel {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  padding: var(--space-7);
  display: grid;
  gap: var(--space-4);
  box-shadow: var(--shadow-md);
  width: min(420px, 100%);
}

.login__brand {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-primary);
}

.login__title {
  font-size: 32px;
}

.login__form {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-2);
}

.login__footer {
  font-size: 12px;
  color: var(--color-muted);
}

.login__footer a {
  color: inherit;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 1024px) {
  .login {
    padding: var(--space-7);
  }
}

@media (max-width: 768px) {
  .login {
    padding: var(--space-5);
  }
}
</style>
