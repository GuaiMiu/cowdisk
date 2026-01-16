<template>
  <div class="app-shell">
    <div class="app-glow"></div>
    <router-view />
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import ToastContainer from "./components/ToastContainer.vue";
</script>

<style scoped>
.app-shell {
  height: 100vh;
  background:
    radial-gradient(circle at 10% 20%, rgba(255, 255, 255, 0.3), transparent 40%),
    radial-gradient(circle at 90% 10%, rgba(255, 235, 206, 0.45), transparent 45%),
    radial-gradient(circle at 70% 80%, rgba(190, 219, 255, 0.35), transparent 45%),
    linear-gradient(135deg, #f8f5ef 0%, #f1efe8 35%, #f4f7fb 100%);
  position: relative;
  overflow: hidden;
}

.app-glow {
  position: absolute;
  inset: -20% -10% auto;
  height: 50%;
  pointer-events: none;
  filter: blur(50px);
  animation: drift 12s ease-in-out infinite;
}

@keyframes drift {
  0%,
  100% {
    transform: translateY(-5%) rotate(0deg);
  }
  50% {
    transform: translateY(5%) rotate(2deg);
  }
}
</style>
