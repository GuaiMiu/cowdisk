<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Message from '@/components/common/Message.vue'
import Notification from '@/components/common/Notification.vue'

const route = useRoute()
const showThemeLayer = computed(() => {
  const path = route.path || ''
  return path.startsWith('/app')
})
</script>

<template>
  <div class="app-shell">
    <div v-if="showThemeLayer" class="app-shell__theme" aria-hidden="true"></div>
    <div v-if="showThemeLayer" class="app-shell__wash" aria-hidden="true"></div>
    <div class="app-shell__content">
      <RouterView />
      <Message />
      <Notification />
    </div>
  </div>
</template>

<style>
.app-shell {
  position: relative;
  height: 100%;
}

.app-shell__theme {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.app-shell__wash {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  background:
    radial-gradient(1200px 680px at 20% -10%, color-mix(in srgb, var(--color-bg) 20%, transparent), transparent 56%),
    linear-gradient(
      to bottom,
      color-mix(in srgb, var(--color-bg) 30%, transparent),
      color-mix(in srgb, var(--color-bg) 44%, transparent)
    );
}

.app-shell__theme::before,
.app-shell__theme::after {
  content: '';
  position: absolute;
  inset: 0;
}

.app-shell__theme::before {
  background-image: var(--theme-artwork-image);
  background-repeat: var(--theme-artwork-repeat);
  background-size: var(--theme-artwork-size);
  background-position: var(--theme-artwork-position);
  opacity: var(--theme-artwork-opacity);
  filter: saturate(var(--theme-artwork-saturate)) contrast(var(--theme-artwork-contrast))
    brightness(var(--theme-artwork-brightness));
}

.app-shell__theme::after {
  background: var(--theme-artwork-veil);
}

.app-shell__content {
  position: relative;
  z-index: 2;
  height: 100%;
}
</style>
