<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { register as registerApi } from '@/api/modules/auth'

const authStore = useAuthStore()
const toast = useToastStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const mail = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)

const canSubmit = computed(() => {
  return username.value.trim() && mail.value.trim() && password.value.trim() && confirmPassword.value.trim()
})

const onSubmit = async () => {
  if (!canSubmit.value) {
    return
  }
  if (password.value !== confirmPassword.value) {
    toast.error('注册失败', '两次输入的密码不一致')
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
    toast.error('注册失败', error instanceof Error ? error.message : '请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="register">
    <div class="register__panel">
      <div class="register__brand">CowDisk</div>
      <h1 class="register__title">创建账号</h1>
      <form class="register__form" @submit.prevent="onSubmit">
        <Input v-model="username" label="账号" placeholder="请输入账号" />
        <Input v-model="mail" label="邮箱" type="email" placeholder="请输入邮箱" />
        <Input v-model="password" label="密码" type="password" placeholder="请输入密码" />
        <Input v-model="confirmPassword" label="确认密码" type="password" placeholder="请再次输入密码" />
        <Button type="submit" block :loading="submitting">注册并登录</Button>
      </form>
      <div class="register__footer">
        已有账号？
        <RouterLink to="/login">去登录</RouterLink>
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
