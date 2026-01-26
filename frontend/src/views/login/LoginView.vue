<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const loading = computed(() => authStore.loading)

const onSubmit = async () => {
  await authStore.login({ username: username.value, password: password.value })
  const redirect = route.query.redirect as string | undefined
  await router.replace(redirect || authStore.landingPath())
}
</script>

<template>
  <div class="login">
    <div class="login__panel">
      <div class="login__brand">CowDisk</div>
      <h1 class="login__title">欢迎回来</h1>
      <form class="login__form" @submit.prevent="onSubmit">
        <Input v-model="username" label="账号" placeholder="请输入账号" />
        <Input v-model="password" label="密码" type="password" placeholder="请输入密码" />
        <Button type="submit" block :loading="loading">登录</Button>
      </form>
      <div class="login__footer">
        没有账号？
        <RouterLink to="/register">去注册</RouterLink>
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
