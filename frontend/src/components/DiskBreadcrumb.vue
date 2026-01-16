<template>
  <div class="path-bar card">
    <button class="btn ghost" @click="$emit('up')" :disabled="!currentPath">
      上级
    </button>
    <div class="breadcrumb">
      <button class="crumb" @click="$emit('root')">根目录</button>
      <template v-for="crumb in breadcrumbs" :key="crumb.path">
        <span class="crumb-sep">/</span>
        <button class="crumb" @click="$emit('navigate', crumb.path)">
          {{ crumb.name }}
        </button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ currentPath: string }>();

const breadcrumbs = computed(() => {
  if (!props.currentPath) return [];
  const parts = props.currentPath.split("/").filter(Boolean);
  let acc = "";
  return parts.map((name) => {
    acc = acc ? `${acc}/${name}` : name;
    return { name, path: acc };
  });
});
</script>

<style scoped>
.path-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--muted);
  flex-wrap: wrap;
}

.crumb {
  border: none;
  background: transparent;
  color: var(--cool);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 6px;
}

.crumb:hover {
  background: var(--surface-alt);
}

.crumb-sep {
  color: var(--muted);
}
</style>
