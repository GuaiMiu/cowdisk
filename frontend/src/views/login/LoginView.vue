<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
      <p class="login__subtitle">统一认证，切换用户或管理员身份。</p>
      <form class="login__form" @submit.prevent="onSubmit">
        <Input v-model="username" label="账号" placeholder="请输入账号" />
        <Input v-model="password" label="密码" type="password" placeholder="请输入密码" />
        <Button type="submit" block :loading="loading">登录</Button>
      </form>
      <div class="login__hint">首次登录将自动创建默认配置</div>
    </div>
    <div class="login__aside">
      <div class="login__card">
        <div class="login__card-title">产品级网盘管理台</div>
        <div class="login__card-desc">
          统一入口覆盖用户与管理员，支持上传、分享、任务协作与权限治理。
        </div>
      </div>
      <div class="login__stats">
        <div class="login__stat">
          <div class="login__stat-value">3s</div>
          <div class="login__stat-label">秒级检索</div>
        </div>
        <div class="login__stat">
          <div class="login__stat-value">100%</div>
          <div class="login__stat-label">全链路审计</div>
        </div>
        <div class="login__stat">
          <div class="login__stat-value">RBAC</div>
          <div class="login__stat-label">权限矩阵</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(320px, 420px) 1fr;
  gap: var(--space-8);
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
}

.login__brand {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-primary);
}

.login__title {
  font-size: 32px;
}

.login__subtitle {
  color: var(--color-muted);
}

.login__form {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-2);
}

.login__hint {
  font-size: 12px;
  color: var(--color-muted);
}

.login__aside {
  display: grid;
  align-content: center;
  gap: var(--space-6);
}

.login__card {
  padding: var(--space-7);
  border-radius: var(--radius-xl);
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-soft-strong);
  display: grid;
  gap: var(--space-3);
}

.login__card-title {
  font-size: 20px;
  font-weight: 600;
}

.login__card-desc {
  color: var(--color-muted);
}

.login__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.login__stat {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  padding: var(--space-4);
  box-shadow: var(--shadow-xs);
  display: grid;
  gap: var(--space-1);
}

.login__stat-value {
  font-size: 18px;
  font-weight: 600;
}

.login__stat-label {
  font-size: 12px;
  color: var(--color-muted);
}

@media (max-width: 1024px) {
  .login {
    grid-template-columns: 1fr;
    padding: var(--space-7);
  }
}

@media (max-width: 768px) {
  .login {
    padding: var(--space-5);
  }

  .login__stats {
    grid-template-columns: 1fr;
  }
}
</style>
