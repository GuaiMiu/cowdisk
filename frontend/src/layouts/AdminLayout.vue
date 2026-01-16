<template>
  <div class="layout">
    <SidebarNav />
    <div class="layout-main">
      <TopBar />
      <main class="layout-content">
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
import SidebarNav from "../components/SidebarNav.vue";
import TopBar from "../components/TopBar.vue";
</script>

<style scoped>
.layout {
  height: 100%;
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 0;
}

.layout-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.layout-content {
  padding: 24px 32px 48px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

@media (max-width: 768px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .layout-content {
    padding: 16px 16px 32px;
  }
}
</style>
