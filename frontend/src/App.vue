<script setup lang="ts">
import { RouterView } from 'vue-router'
import Message from '@/components/common/Message.vue'
import Notification from '@/components/common/Notification.vue'
</script>

<template>
  <RouterView />
  <Message />
  <Notification />
</template>
