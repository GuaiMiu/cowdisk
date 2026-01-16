<template>
  <section class="module" @click="handleRootClick">
    <div class="module-head">
      <div>
        <h2>网盘管理</h2>
        <p>浏览、上传、删除与下载文件。</p>
      </div>
      <div class="toolbar">
        <input
          v-model="searchText"
          class="input search-input"
          placeholder="搜索文件/文件夹"
        />
        <div class="toolbar-group">
          <div class="dropdown" @click.stop>
            <button
              class="btn secondary dropdown-trigger"
              type="button"
              @click="toggleUploadMenu"
            >
              上传
            </button>
            <div v-show="showUploadMenu" class="dropdown-menu">
              <label class="dropdown-item">
                文件
                <input
                  type="file"
                  multiple
                  class="file-input"
                  @change="handleUpload"
                />
              </label>
              <label class="dropdown-item">
                目录
                <input
                  ref="uploadFolderInput"
                  type="file"
                  multiple
                  webkitdirectory
                  directory
                  class="file-input"
                  @change="handleFolderUpload"
                />
              </label>
            </div>
          </div>
          <button class="btn ghost" @click="showFolderInput = !showFolderInput">
            新建目录
          </button>
        </div>
      </div>
    </div>

    <DiskBreadcrumb
      :current-path="currentPath"
      @root="goRoot"
      @up="goUp"
      @navigate="goToPath"
    />

    <DiskUploadQueue :items="uploads" />

    <div class="card table-card disk-table">
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr>
              <th class="name-col">名称</th>
              <th class="type-col">类型</th>
              <th class="size-col">大小</th>
              <th class="time-col">更新时间</th>
              <th class="actions-col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="showFolderInput" class="new-folder-row">
              <td class="name-col">
                <div class="new-folder-input">
                  <input
                    ref="newFolderInput"
                    v-model="newFolder"
                    class="input"
                    placeholder="目录名称"
                    @keydown.enter="createFolder"
                  />
                </div>
              </td>
              <td class="type-col">目录</td>
              <td class="size-col">-</td>
              <td class="time-col">-</td>
              <td class="actions actions-col">
                <div class="actions-wrap">
                  <button class="btn accent" @click="createFolder">√</button>
                  <button class="btn ghost" @click="cancelCreateFolder">×</button>
                </div>
              </td>
            </tr>
            <tr v-for="item in filteredEntries" :key="item.path">
              <td class="name-col">
                <button
                  class="link"
                  @click="handleEntryClick(item)"
                >
                  <span class="name-text">{{ item.name }}</span>
                </button>
              </td>
              <td class="type-col">{{ item.is_dir ? "目录" : "文件" }}</td>
              <td class="size-col">{{ item.is_dir ? "-" : formatSize(item.size) }}</td>
              <td class="time-col">{{ formatTime(item.modified_time) }}</td>
              <td class="actions actions-col">
                <div
                  v-if="item.is_dir && isDownloading(item.path)"
                  class="loading-overlay"
                >
                  <span class="spinner" aria-hidden="true"></span>
                  <span>打包中</span>
                </div>
                <div
                  class="actions-wrap"
                  :class="{ hidden: item.is_dir && isDownloading(item.path) }"
                >
                  <button class="btn ghost" @click="promptRename(item)">重命名</button>
                  <button class="btn secondary" @click="remove(item)">删除</button>
                  <button class="btn accent" @click="download(item)">下载</button>
                </div>
              </td>
            </tr>
            <tr v-if="!filteredEntries.length">
              <td colspan="5" class="empty">暂无文件</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="drawer" v-if="showRename">
      <div class="drawer-panel card">
        <div class="drawer-head">
          <div>
            <div class="drawer-title">重命名</div>
            <div class="drawer-subtitle">修改名称或移动目录</div>
          </div>
          <button class="btn ghost" @click="showRename = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="field">
            <label>新路径</label>
            <input v-model="renameTarget" class="input" placeholder="例如: docs/new.txt" />
          </div>
          <div class="drawer-actions">
            <button class="btn secondary" @click="showRename = false">取消</button>
            <button class="btn accent" @click="confirmRename">保存</button>
          </div>
        </div>
      </div>
    </div>

    <div class="error" v-if="error">{{ error }}</div>
    <DiskMediaPreview
      :visible="preview.visible"
      :url="preview.url"
      :type="preview.type"
      :title="preview.title"
      :has-prev="preview.index > 0"
      :has-next="preview.index < preview.items.length - 1"
      @close="closePreview"
      @prev="showPrevPreview"
      @next="showNextPreview"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  deleteDisk,
  createDiskDownloadToken,
  getDiskDownloadStatus,
  initDiskUpload,
  listDisk,
  uploadDiskChunk,
  completeDiskUpload,
  uploadDisk,
  mkdirDisk,
  prepareDiskDownload,
  renameDisk
} from "../../api";
import DiskBreadcrumb from "../../components/DiskBreadcrumb.vue";
import DiskUploadQueue from "../../components/DiskUploadQueue.vue";
import DiskMediaPreview from "../../components/DiskMediaPreview.vue";
import { getAppStorage, setAppStorage } from "../../utils/storage";

const currentPath = ref("");
const entries = ref<any[]>([]);
const error = ref("");
const showFolderInput = ref(false);
const newFolder = ref("");
const showRename = ref(false);
const renameTarget = ref("");
const renameSource = ref("");
const downloadingPaths = ref<Set<string>>(new Set());
const downloadPollers = ref<Record<string, number>>({});
const uploads = ref<
  Array<{ id: string; name: string; progress: number; status: string }>
>([]);
const newFolderInput = ref<HTMLInputElement | null>(null);
const preview = ref({
  visible: false,
  url: "",
  type: "other" as "image" | "video" | "other",
  title: "",
  items: [] as any[],
  index: 0
});
const uploadFolderInput = ref<HTMLInputElement | null>(null);
const searchText = ref("");
const showUploadMenu = ref(false);

const load = async () => {
  error.value = "";
  try {
    const { data } = await listDisk(currentPath.value);
    entries.value = data?.data?.items || [];
    searchText.value = "";
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "加载失败";
  }
};

const enter = (item: any) => {
  if (!item.is_dir) return;
  currentPath.value = item.path;
  load();
};

const goRoot = () => {
  currentPath.value = "";
  load();
};

const goUp = () => {
  if (!currentPath.value) return;
  const parts = currentPath.value.split("/").filter(Boolean);
  parts.pop();
  currentPath.value = parts.join("/");
  load();
};

const goToPath = (path: string) => {
  currentPath.value = path;
  load();
};

const updateUploadTask = (id: string, patch: Partial<(typeof uploads.value)[0]>) => {
  const next = uploads.value.map((item) =>
    item.id === id ? { ...item, ...patch } : item
  );
  uploads.value = next;
};

const removeUploadTask = (id: string) => {
  uploads.value = uploads.value.filter((item) => item.id !== id);
};

const CHUNK_SIZE = 5 * 1024 * 1024;
const CHUNK_THRESHOLD = 50 * 1024 * 1024;
const CHUNK_RETRY = 3;

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const uploadFileDirect = async (file: File, path: string) => {
  const taskId = `${file.name}-${file.size}-${file.lastModified}`;
  uploads.value = [
    ...uploads.value,
    { id: taskId, name: file.name, progress: 0, status: "上传中" }
  ];
  try {
    await uploadDisk([file], path, true, (event) => {
      const loaded = event.loaded || 0;
      const overall = Math.min(loaded, file.size);
      const percent = file.size
        ? Math.floor((overall / file.size) * 100)
        : 100;
      updateUploadTask(taskId, { progress: percent });
    });
    updateUploadTask(taskId, { progress: 100, status: "完成" });
    setTimeout(() => removeUploadTask(taskId), 1500);
  } catch (err: any) {
    updateUploadTask(taskId, { status: "失败" });
    throw err;
  }
};

const uploadFileInChunks = async (file: File, path: string) => {
  const taskId = `${file.name}-${file.size}-${file.lastModified}`;
  uploads.value = [
    ...uploads.value,
    { id: taskId, name: file.name, progress: 0, status: "上传中" }
  ];
  try {
    const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));
    const { data } = await initDiskUpload({
      path,
      filename: file.name,
      size: file.size,
      total_chunks: totalChunks,
      overwrite: true
    });
    const uploadId = data?.data?.upload_id;
    if (!uploadId) {
      throw new Error("初始化上传失败");
    }
    for (let index = 0; index < totalChunks; index += 1) {
      const start = index * CHUNK_SIZE;
      const end = Math.min(file.size, start + CHUNK_SIZE);
      const chunk = file.slice(start, end);
      let attempt = 0;
      while (true) {
        try {
          await uploadDiskChunk(uploadId, index, chunk, (event) => {
            const loaded = event.loaded || 0;
            const overall = Math.min(start + loaded, file.size);
            const percent = file.size
              ? Math.floor((overall / file.size) * 100)
              : 100;
            updateUploadTask(taskId, { progress: percent });
          });
          break;
        } catch (err: any) {
          attempt += 1;
          if (attempt >= CHUNK_RETRY) {
            throw err;
          }
          await delay(800 * attempt);
        }
      }
    }
    await completeDiskUpload(uploadId);
    updateUploadTask(taskId, { progress: 100, status: "完成" });
    setTimeout(() => removeUploadTask(taskId), 1500);
  } catch (err: any) {
    updateUploadTask(taskId, { status: "失败" });
    throw err;
  }
};

const uploadFile = async (file: File, path: string) => {
  if (file.size > CHUNK_THRESHOLD) {
    await uploadFileInChunks(file, path);
  } else {
    await uploadFileDirect(file, path);
  }
};

const getTargetPath = (file: File, basePath: string) => {
  const rel = (file as any).webkitRelativePath as string | undefined;
  if (!rel) return basePath;
  const parts = rel.split("/").filter(Boolean);
  parts.pop();
  const relDir = parts.join("/");
  if (!relDir) return basePath;
  return basePath ? `${basePath}/${relDir}` : relDir;
};

const uploadFiles = async (files: File[], path: string) => {
  for (const file of files) {
    const targetPath = getTargetPath(file, path);
    await uploadFile(file, targetPath);
  }
};

const createFolder = async () => {
  if (!newFolder.value.trim()) return;
  const path = currentPath.value
    ? `${currentPath.value}/${newFolder.value.trim()}`
    : newFolder.value.trim();
  try {
    await mkdirDisk(path);
    newFolder.value = "";
    showFolderInput.value = false;
    load();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "创建失败";
  }
};

const cancelCreateFolder = () => {
  showFolderInput.value = false;
  newFolder.value = "";
};

const handleUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (!input.files || !input.files.length) return;
  const files = Array.from(input.files);
  try {
    await uploadFiles(files, currentPath.value);
    input.value = "";
    load();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "上传失败";
  }
};

const handleFolderUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (!input.files || !input.files.length) return;
  const files = Array.from(input.files);
  try {
    await uploadFiles(files, currentPath.value);
    input.value = "";
    load();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "上传失败";
  }
};

const toggleUploadMenu = () => {
  showUploadMenu.value = !showUploadMenu.value;
};

const handleRootClick = () => {
  showUploadMenu.value = false;
};


const remove = async (item: any) => {
  try {
    await deleteDisk(item.path, item.is_dir);
    load();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "删除失败";
  }
};

const promptRename = (item: any) => {
  renameSource.value = item.path;
  renameTarget.value = item.path;
  showRename.value = true;
};

const confirmRename = async () => {
  try {
    await renameDisk(renameSource.value, renameTarget.value, true);
    showRename.value = false;
    load();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "重命名失败";
  }
};

const setDownloading = (path: string, downloading: boolean) => {
  const next = new Set(downloadingPaths.value);
  if (downloading) {
    next.add(path);
  } else {
    next.delete(path);
  }
  downloadingPaths.value = next;
};

const stopDownloadPoll = (path: string) => {
  const timer = downloadPollers.value[path];
  if (timer) {
    window.clearInterval(timer);
  }
  const next = { ...downloadPollers.value };
  delete next[path];
  downloadPollers.value = next;
};

const startDownloadPoll = (path: string, jobId: string) => {
  stopDownloadPoll(path);
  const poll = async () => {
    try {
      const { data } = await getDiskDownloadStatus(jobId);
      const status = data?.data?.status;
      if (status === "ready") {
        stopDownloadPoll(path);
        setDownloading(path, false);
        const base = import.meta.env.VITE_API_BASE || "/api/v1";
        const tokenRes = await createDiskDownloadToken({ job_id: jobId });
        const token = tokenRes?.data?.data?.token;
        if (!token) {
          throw new Error("下载令牌生成失败");
        }
        const url = `${base}/disk/download/job?token=${encodeURIComponent(token)}`;
        const link = document.createElement("a");
        link.href = url;
        link.rel = "noopener";
        link.download = "";
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else if (status === "error") {
        stopDownloadPoll(path);
        setDownloading(path, false);
        error.value = data?.data?.message || "打包失败";
      }
    } catch (err: any) {
      stopDownloadPoll(path);
      setDownloading(path, false);
      error.value = err?.response?.data?.msg || err?.message || "打包失败";
    }
  };
  poll();
  const timer = window.setInterval(poll, 1000);
  downloadPollers.value = { ...downloadPollers.value, [path]: timer };
};

const download = async (item: any) => {
  const base = import.meta.env.VITE_API_BASE || "/api/v1";
  if (item.is_dir) {
    if (downloadingPaths.value.has(item.path)) return;
    setDownloading(item.path, true);
    try {
      const { data } = await prepareDiskDownload(item.path);
      const jobId = data?.data?.job_id;
      if (!jobId) {
        throw new Error("打包任务创建失败");
      }
      startDownloadPoll(item.path, jobId);
    } catch (err: any) {
      setDownloading(item.path, false);
      error.value = err?.response?.data?.msg || err?.message || "打包失败";
    }
    return;
  }
  try {
    const tokenRes = await createDiskDownloadToken({ path: item.path });
    const token = tokenRes?.data?.data?.token;
    if (!token) {
      error.value = "下载令牌生成失败";
      return;
    }
    const url = `${base}/disk/download?token=${encodeURIComponent(token)}`;
    const link = document.createElement("a");
    link.href = url;
    link.rel = "noopener";
    link.download = "";
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "下载失败";
  }
};

const handleEntryClick = (item: any) => {
  if (item.is_dir) {
    enter(item);
    return;
  }
  if (canPreview(item)) {
    openPreview(item);
  }
};

const previewableExts = {
  image: new Set([".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]),
  video: new Set([".mp4", ".webm", ".ogg", ".mov", ".m4v"])
};

const getPreviewType = (name: string) => {
  const lower = name.toLowerCase();
  const ext = lower.includes(".") ? lower.slice(lower.lastIndexOf(".")) : "";
  if (previewableExts.image.has(ext)) return "image";
  if (previewableExts.video.has(ext)) return "video";
  return "other";
};

const canPreview = (item: any) => !item.is_dir && getPreviewType(item.name) !== "other";

const buildPreviewItems = (type: "image" | "video") =>
  entries.value.filter(
    (entry) => !entry.is_dir && getPreviewType(entry.name) === type
  );

const loadPreviewAt = async (items: any[], index: number) => {
  const target = items[index];
  if (!target) return;
  const base = import.meta.env.VITE_API_BASE || "/api/v1";
  const tokenRes = await createDiskDownloadToken({ path: target.path });
  const token = tokenRes?.data?.data?.token;
  if (!token) {
    error.value = "预览令牌生成失败";
    return;
  }
  preview.value = {
    visible: true,
    url: `${base}/disk/preview?token=${encodeURIComponent(token)}`,
    type: getPreviewType(target.name),
    title: target.name,
    items,
    index
  };
};

const openPreview = async (item: any) => {
  try {
    const type = getPreviewType(item.name);
    if (type === "other") return;
    const items = buildPreviewItems(type);
    const index = items.findIndex((entry) => entry.path === item.path);
    await loadPreviewAt(items, Math.max(index, 0));
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "预览失败";
  }
};

const showPrevPreview = async () => {
  if (preview.value.index <= 0) return;
  await loadPreviewAt(preview.value.items, preview.value.index - 1);
};

const showNextPreview = async () => {
  if (preview.value.index >= preview.value.items.length - 1) return;
  await loadPreviewAt(preview.value.items, preview.value.index + 1);
};

const closePreview = () => {
  preview.value.visible = false;
  preview.value.url = "";
  preview.value.title = "";
  preview.value.type = "other";
  preview.value.items = [];
  preview.value.index = 0;
};

const formatSize = (size: number) => {
  if (!size) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let idx = 0;
  let value = size;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(1)} ${units[idx]}`;
};

const formatTime = (value: string) => {
  if (!value) return "-";
  const date = new Date(value);
  return date.toLocaleString();
};

const isDownloading = (path: string) => downloadingPaths.value.has(path);

const filteredEntries = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  if (!keyword) return entries.value;
  return entries.value.filter((entry) =>
    String(entry.name || "").toLowerCase().includes(keyword)
  );
});

onMounted(() => {
  const saved = getAppStorage().disk?.legacyPath;
  if (typeof saved === "string") {
    currentPath.value = saved;
  }
  load();
});

watch(currentPath, (value) => {
  setAppStorage({ disk: { legacyPath: value } });
});

watch(showFolderInput, async (visible) => {
  if (!visible) return;
  await nextTick();
  newFolderInput.value?.focus();
});

onBeforeUnmount(() => {
  Object.values(downloadPollers.value).forEach((timer) =>
    window.clearInterval(timer)
  );
});
</script>

<style scoped>
.module {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.module-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h2 {
  margin: 0;
  font-size: 24px;
}

p {
  margin: 4px 0 0;
  color: var(--muted);
}

.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: nowrap;
  align-items: center;
}

.toolbar-group {
  display: flex;
  gap: 12px;
  flex-wrap: nowrap;
  align-items: center;
  margin-left: auto;
}

.dropdown {
  position: relative;
}

.dropdown-trigger {
  min-width: 88px;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  background: var(--surface);
  border: 1px solid var(--stroke);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 6px;
  min-width: 96px;
  width: max-content;
  z-index: 10;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}

.dropdown-item:hover {
  background: var(--surface-alt);
}

.search-input {
  max-width: 240px;
  min-width: 120px;
  flex: 1 1 140px;
}

.file-input {
  display: none;
}

.disk-table {
  background: var(--bg);
  --disk-table-bg: var(--bg);
  --disk-table-row-hover: var(--surface-alt);
}

.drawer {
  position: fixed;
  inset: 0;
  background: rgba(20, 22, 27, 0.35);
  display: flex;
  justify-content: flex-end;
  z-index: 20;
}

.drawer-panel {
  width: min(420px, 100%);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-title {
  font-size: 20px;
  font-weight: 700;
}

.drawer-subtitle {
  font-size: 12px;
  color: var(--muted);
}

@media (max-width: 768px) {
  .module-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .toolbar {
    flex-wrap: wrap;
  }

  .toolbar-group {
    margin-left: 0;
  }
}

.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.error {
  color: #b23b2b;
  font-size: 13px;
}
</style>
