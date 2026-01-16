<template>
  <span class="icon" :class="type">
    <svg v-if="type === 'dir'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M3 6.5h6l2 2H21a2 2 0 0 1 2 2V18a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8.5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
    </svg>
    <svg v-else-if="type === 'img'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M4 5h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <circle cx="8.5" cy="9" r="1.5" fill="#fff" />
      <path d="M6 17l4-4 3 3 3-3 4 4H6Z" fill="#fff" />
    </svg>
    <svg v-else-if="type === 'vid'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M4 6h11a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M10 9l5 3-5 3V9Z" fill="#fff" />
      <path d="M19 10l4-2v8l-4-2v-4Z" fill="currentColor" />
    </svg>
    <svg v-else-if="type === 'aud'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M4 8h6l6-4v16l-6-4H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M19 9a4 4 0 0 1 0 6" stroke="#fff" stroke-width="2" />
    </svg>
    <svg v-else-if="type === 'zip'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path
        d="M12 3v6h6"
        stroke="#fff"
        stroke-width="2"
        fill="none"
      />
      <path
        d="M10 9h4M10 12h4M10 15h4"
        stroke="#fff"
        stroke-width="2"
      />
    </svg>
    <svg v-else-if="type === 'pdf'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M12 3v6h6" stroke="#fff" stroke-width="2" fill="none" />
      <path
        d="M8 15c2-4 4-4 6 0"
        stroke="#fff"
        stroke-width="2"
        fill="none"
      />
    </svg>
    <svg v-else-if="type === 'doc'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M12 3v6h6" stroke="#fff" stroke-width="2" fill="none" />
      <path d="M8 13h8M8 16h6" stroke="#fff" stroke-width="2" />
    </svg>
    <svg v-else-if="type === 'xls'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M12 3v6h6" stroke="#fff" stroke-width="2" fill="none" />
      <path d="M8 12h8M8 15h8M8 18h8" stroke="#fff" stroke-width="2" />
    </svg>
    <svg v-else-if="type === 'ppt'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M12 3v6h6" stroke="#fff" stroke-width="2" fill="none" />
      <path d="M8 14h6l-3-3v6" stroke="#fff" stroke-width="2" />
    </svg>
    <svg v-else-if="type === 'txt'" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M12 3v6h6" stroke="#fff" stroke-width="2" fill="none" />
      <path d="M8 12h8M8 15h8" stroke="#fff" stroke-width="2" />
    </svg>
    <svg v-else viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M6 3h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        fill="currentColor"
      />
      <path d="M12 3v6h6" stroke="#fff" stroke-width="2" fill="none" />
    </svg>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  name?: string;
  isDir?: boolean;
}>();

const type = computed(() => {
  if (props.isDir) return "dir";
  const ext = (props.name?.split(".").pop() || "").toLowerCase();
  if (["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)) return "img";
  if (["zip", "rar", "7z", "tar", "gz"].includes(ext)) return "zip";
  if (["pdf"].includes(ext)) return "pdf";
  if (["mp3", "wav", "flac", "aac"].includes(ext)) return "aud";
  if (["mp4", "mov", "avi", "mkv"].includes(ext)) return "vid";
  if (["doc", "docx"].includes(ext)) return "doc";
  if (["xls", "xlsx", "csv"].includes(ext)) return "xls";
  if (["ppt", "pptx"].includes(ext)) return "ppt";
  if (["txt", "md"].includes(ext)) return "txt";
  return "file";
});
</script>

<style scoped>
.icon {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--ink);
  background: var(--surface-alt);
  border: 1px solid var(--stroke);
}

.icon svg {
  width: 16px;
  height: 16px;
}

.icon.dir {
  color: var(--cool);
}

.icon.img {
  color: var(--accent);
}

.icon.vid {
  color: #3a587a;
}

.icon.aud {
  color: #3f6f5a;
}

.icon.zip {
  color: var(--accent-strong);
}

.icon.pdf {
  color: #8b2f2a;
}

.icon.doc,
.icon.xls,
.icon.ppt,
.icon.txt,
.icon.file {
  color: var(--muted);
}
</style>
