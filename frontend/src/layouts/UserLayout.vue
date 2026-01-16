<template>
  <div class="user-layout">
    <UserSidebar />
    <div class="user-main">
      <main class="user-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import UserSidebar from "../components/UserSidebar.vue";
</script>

<style scoped>
.user-layout {
  height: 100%;
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 0;
}

.user-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.user-content {
  padding: 24px 32px 48px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

@media (max-width: 768px) {
  .user-layout {
    grid-template-columns: 1fr;
  }

  .user-content {
    padding: 16px 16px 32px;
  }
}
</style>
