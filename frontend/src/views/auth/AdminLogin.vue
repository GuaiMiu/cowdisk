<template>
  <div class="page login">
    <div class="login-grid">
      <div class="login-hero card">
        <div class="hero-tag">Admin Access</div>
        <h1>管理从这里开始。</h1>
        <p>登录后台后可管理用户、角色、菜单与全局网盘。</p>
        <div class="hero-metrics">
          <div>
            <div class="metric-label">控制中心</div>
            <div class="metric-value">系统管理</div>
          </div>
          <div>
            <div class="metric-label">安全等级</div>
            <div class="metric-value">高</div>
          </div>
          <div>
            <div class="metric-label">服务版本</div>
            <div class="metric-value">v0.1</div>
          </div>
        </div>
      </div>
      <form class="login-card card" @submit.prevent="submit">
        <div class="card-head">
          <div class="title">管理员登录</div>
          <div class="subtitle">进入管理控制台</div>
        </div>
        <div class="field">
          <label>用户名</label>
          <input v-model="form.username" class="input" placeholder="请输入用户名" />
        </div>
        <div class="field">
          <label>密码</label>
          <input
            v-model="form.password"
            class="input"
            type="password"
            placeholder="请输入密码"
          />
        </div>
        <div class="error" v-if="error">{{ error }}</div>
        <button class="btn accent" :disabled="loading">
          {{ loading ? "登录中..." : "登录" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAdminAuthStore } from "../../stores/adminAuth";

const router = useRouter();
const auth = useAdminAuthStore();
const loading = ref(false);
const error = ref("");
const form = reactive({
  username: "",
  password: ""
});

const submit = async () => {
  error.value = "";
  loading.value = true;
  try {
    await auth.login(form.username.trim(), form.password);
    router.push("/admin");
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "登录失败";
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-grid {
  width: min(1100px, 100%);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 28px;
}

.login-hero {
  padding: 40px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.8), #fff);
}

.hero-tag {
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--cool-soft);
  color: var(--cool);
  font-size: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

h1 {
  font-size: 36px;
  margin: 0;
  font-family: "Space Grotesk", sans-serif;
}

p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  background: var(--surface-alt);
  padding: 16px;
  border-radius: var(--radius-md);
}

.metric-label {
  font-size: 12px;
  color: var(--muted);
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  margin-top: 4px;
}

.login-card {
  padding: 36px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-head .title {
  font-size: 24px;
  font-weight: 700;
}

.card-head .subtitle {
  font-size: 13px;
  color: var(--muted);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.error {
  color: #b23b2b;
  font-size: 13px;
}

@media (max-width: 768px) {
  .login-grid {
    grid-template-columns: 1fr;
  }
}
</style>
