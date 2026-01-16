<template>
  <section class="dashboard">
    <div class="hero card">
      <div>
        <div class="hero-label">运行概况</div>
        <h2>欢迎回来，{{ auth.user?.username || "管理员" }}</h2>
        <p>今天的系统状态良好，可以继续进行配置与审核。</p>
        <div class="hero-actions">
          <router-link class="btn accent" to="/admin/disk">进入网盘</router-link>
          <router-link class="btn secondary" to="/admin/user">
            用户管理
          </router-link>
        </div>
      </div>
      <div class="hero-panel">
        <div class="panel-title">重点提醒</div>
        <ul>
          <li>检查角色权限分配是否合理。</li>
          <li>定期清理不再使用的菜单。</li>
          <li>关注网盘容量与目录结构。</li>
        </ul>
      </div>
    </div>

    <div class="grid">
      <div class="card stat">
        <div class="stat-label">今日登录</div>
        <div class="stat-value">36</div>
        <div class="stat-note">+8% 同比</div>
      </div>
      <div class="card stat">
        <div class="stat-label">待处理角色</div>
        <div class="stat-value">4</div>
        <div class="stat-note">集中在系统管理</div>
      </div>
      <div class="card stat">
        <div class="stat-label">网盘占用</div>
        <div class="stat-value">58%</div>
        <div class="stat-note">剩余 42%</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useAdminAuthStore } from "../stores/adminAuth";

const auth = useAdminAuthStore();
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hero {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 24px;
  padding: 28px;
  align-items: center;
  background: linear-gradient(135deg, #fff, #fff7ef);
}

.hero-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--muted);
}

h2 {
  margin: 8px 0;
  font-size: 30px;
  font-family: "Space Grotesk", sans-serif;
}

p {
  color: var(--muted);
  margin: 0 0 18px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-panel {
  background: var(--surface-alt);
  padding: 18px;
  border-radius: var(--radius-md);
}

.hero-panel ul {
  margin: 12px 0 0;
  padding-left: 18px;
  color: var(--muted);
  line-height: 1.6;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.stat {
  padding: 18px;
}

.stat-label {
  font-size: 12px;
  color: var(--muted);
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  margin: 8px 0;
}

.stat-note {
  font-size: 12px;
  color: var(--cool);
}

@media (max-width: 768px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
