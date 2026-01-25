<script setup lang="ts">
import FileExplorer from '@/components/file/FileExplorer.vue'
</script>

<template>
  <section class="files">
    <FileExplorer />
  </section>
</template>

<style scoped>
.files {
  height: 100%;
  min-height: 0;
}
</style>
