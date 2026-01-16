<template>
  <section class="module" @click="handleRootClick">
    <div class="module-head">
      <div>
        <h2>网盘管理</h2>
        <p>管理员可查看与维护任意用户的网盘数据。</p>
      </div>
      <div class="toolbar">
        <input
          v-model="searchText"
          class="input search-input"
          placeholder="搜索文件/文件夹"
        />
        <div class="user-select">
          <label>用户ID</label>
          <input v-model.number="userId" class="input" type="number" min="1" />
        </div>
        <div class="toolbar-group">
          <div v-if="canUpload" class="dropdown" @click.stop>
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
                  ref="uploadInput"
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
          <button
            v-if="canDelete && hasSelection"
            class="btn secondary"
            @click="batchDelete"
          >
            批量删除 ({{ selectedCount }})
          </button>
          <button
            v-if="canMkdir"
            class="btn ghost"
            @click="showFolderInput = !showFolderInput"
          >
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

    <div
      class="card table-card disk-table"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @contextmenu.prevent="openContextMenu($event, null)"
    >
      <div class="table-scroll">
        <table class="table">
          <thead>
            <tr>
              <th class="select-col">
                <input
                  type="checkbox"
                  :checked="allSelected"
                  @change="toggleSelectAll($event)"
                />
              </th>
              <th class="name-col">名称</th>
              <th class="type-col">类型</th>
              <th class="size-col">大小</th>
              <th class="time-col">更新时间</th>
              <th class="actions-col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="showFolderInput && canMkdir" class="new-folder-row">
              <td class="select-col"></td>
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
            <tr
              v-for="item in filteredEntries"
              :key="item.path"
              :draggable="canRename"
              @dragstart="handleDragStart(item, $event)"
              @contextmenu.prevent="openContextMenu($event, item)"
              @dragover.prevent="item.is_dir && (canRename || canUpload)"
              @drop.prevent="item.is_dir && handleMoveDrop(item, $event)"
            >
              <td class="select-col">
                <input
                  type="checkbox"
                  :checked="isSelected(item.path)"
                  @change="toggleSelect(item.path, $event)"
                />
              </td>
              <td class="name-col">
                <button
                  class="link"
                  @click="handleEntryClick(item)"
                >
                  <FileIcon :name="item.name" :is-dir="item.is_dir" />
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
                  <button
                    v-if="canRename"
                    class="btn ghost"
                    @click="promptRename(item)"
                  >
                    重命名
                  </button>
                  <button v-if="canRename" class="btn ghost" @click="promptMove(item)">
                    移动
                  </button>
                  <button v-if="canDelete" class="btn secondary" @click="remove(item)">
                    删除
                  </button>
                  <button
                    v-if="canDownload"
                    class="btn accent"
                    @click="download(item)"
                  >
                    下载
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!filteredEntries.length">
              <td colspan="6" class="empty">暂无文件</td>
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
            <div class="drawer-subtitle">修改名称</div>
          </div>
          <button class="btn ghost" @click="showRename = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="field">
            <label>新路径</label>
            <input v-model="renameTarget" class="input" placeholder="新名称" />
          </div>
          <div class="drawer-actions">
            <button class="btn secondary" @click="showRename = false">取消</button>
            <button class="btn accent" @click="confirmRename">保存</button>
          </div>
        </div>
      </div>
    </div>

    <div class="drawer" v-if="showMove">
      <div class="drawer-panel card">
        <div class="drawer-head">
          <div>
            <div class="drawer-title">移动到</div>
            <div class="drawer-subtitle">选择目标目录</div>
          </div>
          <button class="btn ghost" @click="showMove = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="tree-root" @click="selectMoveTarget('')">根目录</div>
          <div class="tree-list">
            <div
              v-for="item in treeFlat"
              :key="item.node.path"
              class="tree-node"
              :style="{ paddingLeft: `${item.depth * 16}px` }"
            >
              <button class="tree-toggle" @click="toggleNode(item.node)">
                {{ item.node.isExpanded ? "-" : "+" }}
              </button>
              <button
                class="tree-label"
                @click="selectMoveTarget(item.node.path)"
              >
                {{ item.node.name }}
              </button>
            </div>
          </div>
          <div class="tree-selected">目标：/{{ moveTarget || "" }}</div>
          <div class="drawer-actions">
            <button class="btn secondary" @click="showMove = false">取消</button>
            <button class="btn accent" @click="confirmMove">移动</button>
          </div>
        </div>
      </div>
    </div>

    <div class="drawer" v-if="showDetails">
      <div class="drawer-panel card">
        <div class="drawer-head">
          <div>
            <div class="drawer-title">详情</div>
            <div class="drawer-subtitle">文件信息</div>
          </div>
          <button class="btn ghost" @click="showDetails = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="detail-row">
            <span>名称</span>
            <strong>{{ detailItem?.name }}</strong>
          </div>
          <div class="detail-row">
            <span>路径</span>
            <strong>/{{ detailItem?.path }}</strong>
          </div>
          <div class="detail-row">
            <span>类型</span>
            <strong>{{ detailItem?.is_dir ? "目录" : "文件" }}</strong>
          </div>
          <div class="detail-row">
            <span>大小</span>
            <strong>
              {{ detailItem?.is_dir ? "-" : formatSize(detailItem?.size || 0) }}
            </strong>
          </div>
          <div class="detail-row">
            <span>更新时间</span>
            <strong>{{ formatTime(detailItem?.modified_time) }}</strong>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      @click.stop
    >
      <button
        v-if="contextMenu.item && canRename"
        class="context-item"
        @click="promptRename(contextMenu.item)"
      >
        重命名
      </button>
      <button
        v-if="contextMenu.item && canRename"
        class="context-item"
        @click="promptMove(contextMenu.item)"
      >
        移动
      </button>
      <button
        v-if="contextMenu.item && canDelete"
        class="context-item"
        @click="remove(contextMenu.item)"
      >
        删除
      </button>
      <button
        v-if="contextMenu.item && canDownload"
        class="context-item"
        @click="download(contextMenu.item)"
      >
        下载
      </button>
      <button
        v-if="contextMenu.item"
        class="context-item"
        @click="openDetails(contextMenu.item)"
      >
        详情
      </button>
      <button
        v-if="!contextMenu.item && canMkdir"
        class="context-item"
        @click="openNewFolder"
      >
        新建文件夹
      </button>
      <button
        v-if="!contextMenu.item && canUpload"
        class="context-item"
        @click="triggerUpload"
      >
        上传
      </button>
      <button v-if="!contextMenu.item" class="context-item" @click="load">
        刷新
      </button>
    </div>

    <ConfirmDialog
      v-if="confirmState.visible"
      :title="confirmState.title"
      :message="confirmState.message"
      @confirm="confirmState.onConfirm"
      @cancel="closeConfirm"
    />
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
  deleteAdminDisk,
  createAdminDiskDownloadToken,
  getAdminDiskDownloadStatus,
  initAdminDiskUpload,
  listAdminDisk,
  uploadAdminDiskChunk,
  completeAdminDiskUpload,
  uploadAdminDisk,
  mkdirAdminDisk,
  prepareAdminDiskDownload,
  renameAdminDisk
} from "../../api/admin";
import { useAdminAuthStore } from "../../stores/adminAuth";
import FileIcon from "../../components/FileIcon.vue";
import DiskBreadcrumb from "../../components/DiskBreadcrumb.vue";
import DiskUploadQueue from "../../components/DiskUploadQueue.vue";
import DiskMediaPreview from "../../components/DiskMediaPreview.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { useNotifyStore } from "../../stores/notify";
import { getAppStorage, setAppStorage } from "../../utils/storage";

const userId = ref<number>(1);
const currentPath = ref("");
const entries = ref<any[]>([]);
const error = ref("");
const showFolderInput = ref(false);
const newFolder = ref("");
const showRename = ref(false);
const renameTarget = ref("");
const renameSource = ref("");
const showMove = ref(false);
const moveSource = ref<any | null>(null);
const moveTarget = ref("");
const treeRoots = ref<TreeNode[]>([]);
const showDetails = ref(false);
const detailItem = ref<any | null>(null);
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  item: null as any | null
});
const uploadInput = ref<HTMLInputElement | null>(null);
const uploadFolderInput = ref<HTMLInputElement | null>(null);
const dragSourcePath = ref("");
const selectedPaths = ref<Set<string>>(new Set());
const downloadingPaths = ref<Set<string>>(new Set());
const downloadPollers = ref<Record<string, number>>({});
const confirmState = ref({
  visible: false,
  title: "",
  message: "",
  onConfirm: () => {}
});
const uploads = ref<
  Array<{ id: string; name: string; progress: number; status: string }>
>([]);
const newFolderInput = ref<HTMLInputElement | null>(null);
const searchText = ref("");
const showUploadMenu = ref(false);
const preview = ref({
  visible: false,
  url: "",
  type: "other" as "image" | "video" | "other",
  title: "",
  items: [] as any[],
  index: 0
});
const auth = useAdminAuthStore();
const notify = useNotifyStore();
const canList = computed(() => auth.hasPerm("disk:file:list"));
const canUpload = computed(() => auth.hasPerm("disk:file:upload"));
const canMkdir = computed(() => auth.hasPerm("disk:file:mkdir"));
const canDelete = computed(() => auth.hasPerm("disk:file:delete"));
const canRename = computed(() => auth.hasPerm("disk:file:rename"));
const canDownload = computed(() => auth.hasPerm("disk:file:download"));
const selectedCount = computed(() => selectedPaths.value.size);
const hasSelection = computed(() => selectedPaths.value.size > 0);
const allSelected = computed(
  () =>
    entries.value.length > 0 &&
    entries.value.every((entry) => selectedPaths.value.has(entry.path))
);
const filteredEntries = computed(() => {
  const keyword = searchText.value.trim().toLowerCase();
  if (!keyword) return entries.value;
  return entries.value.filter((entry) =>
    String(entry.name || "").toLowerCase().includes(keyword)
  );
});
type TreeNode = {
  name: string;
  path: string;
  isExpanded: boolean;
  isLoaded: boolean;
  children: TreeNode[];
};

const treeFlat = computed(() => flattenTree(treeRoots.value));

const load = async () => {
  if (!canList.value) {
    error.value = "无权限查看网盘";
    entries.value = [];
    return;
  }
  closeContextMenu();
  if (!userId.value) {
    error.value = "请先输入用户ID";
    entries.value = [];
    return;
  }
  error.value = "";
  try {
    const { data } = await listAdminDisk(userId.value, currentPath.value);
    entries.value = data?.data?.items || [];
    selectedPaths.value = new Set();
    searchText.value = "";
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "加载失败";
    notify.error(error.value);
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
  if (!userId.value) return;
  const taskId = `${file.name}-${file.size}-${file.lastModified}`;
  uploads.value = [
    ...uploads.value,
    { id: taskId, name: file.name, progress: 0, status: "上传中" }
  ];
  try {
    await uploadAdminDisk(userId.value, [file], path, true, (event) => {
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
  if (!userId.value) return;
  const taskId = `${file.name}-${file.size}-${file.lastModified}`;
  uploads.value = [
    ...uploads.value,
    { id: taskId, name: file.name, progress: 0, status: "上传中" }
  ];
  try {
    const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));
    const { data } = await initAdminDiskUpload(userId.value, {
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
          await uploadAdminDiskChunk(uploadId, index, chunk, userId.value, (event) => {
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
    await completeAdminDiskUpload(userId.value, uploadId);
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
  if (!newFolder.value.trim() || !userId.value) return;
  const path = currentPath.value
    ? `${currentPath.value}/${newFolder.value.trim()}`
    : newFolder.value.trim();
  try {
    await mkdirAdminDisk(userId.value, path);
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
  if (!input.files || !input.files.length || !userId.value) return;
  const files = Array.from(input.files);
  try {
    await uploadFiles(files, currentPath.value);
    input.value = "";
    load();
    notify.success("上传成功");
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "上传失败";
    notify.error(error.value);
  }
};

const handleFolderUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (!input.files || !input.files.length || !userId.value) return;
  const files = Array.from(input.files);
  try {
    await uploadFiles(files, currentPath.value);
    input.value = "";
    load();
    notify.success("上传成功");
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "上传失败";
    notify.error(error.value);
  }
};

const remove = (item: any) => {
  if (!userId.value) return;
  closeContextMenu();
  confirmAction("确认删除", `确定删除 ${item.name} 吗？`, async () => {
    await deleteAdminDisk(userId.value, item.path, item.is_dir);
    load();
  }, "删除成功");
};

const promptRename = (item: any) => {
  renameSource.value = item.path;
  renameTarget.value = item.name;
  showRename.value = true;
  closeContextMenu();
};

const promptMove = async (item: any) => {
  moveSource.value = item;
  moveTarget.value = currentPath.value;
  showMove.value = true;
  await ensureTreeRoot();
  closeContextMenu();
};

const confirmRename = async () => {
  if (!userId.value) return;
  try {
    const cleaned = renameTarget.value.trim();
    if (!cleaned) {
      error.value = "请输入新名称";
      return;
    }
    const base = currentPath.value ? `${currentPath.value}/` : "";
    confirmAction("确认重命名", `确定重命名为 ${cleaned} 吗？`, async () => {
      await renameAdminDisk(
        userId.value,
        renameSource.value,
        `${base}${cleaned}`,
        true
      );
      showRename.value = false;
      load();
    }, "重命名成功");
  } catch (err: any) {
    error.value = err?.response?.data?.msg || err?.message || "重命名失败";
    notify.error(error.value);
  }
};

const confirmMove = async () => {
  if (!userId.value || !moveSource.value) return;
  const sourcePath = moveSource.value.path;
  const targetBase = moveTarget.value.trim();
  const name = moveSource.value.name;
  const dstPath = targetBase ? `${targetBase}/${name}` : name;
  if (dstPath === sourcePath) {
    error.value = "目标与源相同";
    return;
  }
  if (
    moveSource.value.is_dir &&
    (targetBase === sourcePath || targetBase.startsWith(`${sourcePath}/`))
  ) {
    error.value = "不能移动到自身或子目录";
    return;
  }
  confirmAction("确认移动", `移动到 /${targetBase || ""} 吗？`, async () => {
    await renameAdminDisk(userId.value, sourcePath, dstPath, true);
    showMove.value = false;
    load();
  }, "移动成功");
};

const ensureTreeRoot = async () => {
  if (!userId.value || treeRoots.value.length) return;
  const { data } = await listAdminDisk(userId.value, "");
  const items = data?.data?.items || [];
  treeRoots.value = items
    .filter((item: any) => item.is_dir)
    .map((item: any) => toNode(item));
};

const toggleNode = async (node: TreeNode) => {
  if (!userId.value) return;
  if (!node.isLoaded) {
    const { data } = await listAdminDisk(userId.value, node.path);
    const items = data?.data?.items || [];
    node.children = items
      .filter((item: any) => item.is_dir)
      .map((item: any) => toNode(item));
    node.isLoaded = true;
  }
  node.isExpanded = !node.isExpanded;
};

const selectMoveTarget = (path: string) => {
  moveTarget.value = path;
};

const toNode = (item: any): TreeNode => ({
  name: item.name,
  path: item.path,
  isExpanded: false,
  isLoaded: false,
  children: []
});

const flattenTree = (nodes: TreeNode[], depth = 0, acc: any[] = []) => {
  nodes.forEach((node) => {
    acc.push({ node, depth });
    if (node.isExpanded && node.children.length) {
      flattenTree(node.children, depth + 1, acc);
    }
  });
  return acc;
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
      if (!userId.value) return;
      const { data } = await getAdminDiskDownloadStatus(userId.value, jobId);
      const status = data?.data?.status;
      if (status === "ready") {
        stopDownloadPoll(path);
        setDownloading(path, false);
        const base = import.meta.env.VITE_ADMIN_API_BASE || "/api/v1/admin";
        const tokenRes = await createAdminDiskDownloadToken(userId.value, {
          job_id: jobId
        });
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
        notify.error(data?.data?.message || "打包失败");
      }
    } catch (err: any) {
      stopDownloadPoll(path);
      setDownloading(path, false);
      notify.error(err?.response?.data?.msg || err?.message || "打包失败");
    }
  };
  poll();
  const timer = window.setInterval(poll, 1000);
  downloadPollers.value = { ...downloadPollers.value, [path]: timer };
};

const download = async (item: any) => {
  if (!userId.value) return;
  closeContextMenu();
  const base = import.meta.env.VITE_ADMIN_API_BASE || "/api/v1/admin";
  if (item.is_dir) {
    if (downloadingPaths.value.has(item.path)) return;
    setDownloading(item.path, true);
    try {
      const { data } = await prepareAdminDiskDownload(userId.value, item.path);
      const jobId = data?.data?.job_id;
      if (!jobId) {
        throw new Error("打包任务创建失败");
      }
      startDownloadPoll(item.path, jobId);
    } catch (err: any) {
      setDownloading(item.path, false);
      notify.error(err?.response?.data?.msg || err?.message || "打包失败");
    }
    return;
  }
  try {
    const tokenRes = await createAdminDiskDownloadToken(userId.value, {
      path: item.path
    });
    const token = tokenRes?.data?.data?.token;
    if (!token) {
      notify.error("下载令牌生成失败");
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
    notify.error(err?.response?.data?.msg || err?.message || "下载失败");
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

const canPreview = (item: any) =>
  canDownload.value && !item.is_dir && getPreviewType(item.name) !== "other";

const buildPreviewItems = (type: "image" | "video") =>
  entries.value.filter(
    (entry) => !entry.is_dir && getPreviewType(entry.name) === type
  );

const loadPreviewAt = async (items: any[], index: number) => {
  if (!userId.value) return;
  const target = items[index];
  if (!target) return;
  const base = import.meta.env.VITE_ADMIN_API_BASE || "/api/v1/admin";
  const tokenRes = await createAdminDiskDownloadToken(userId.value, {
    path: target.path
  });
  const token = tokenRes?.data?.data?.token;
  if (!token) {
    notify.error("预览令牌生成失败");
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
  if (!userId.value) return;
  closeContextMenu();
  try {
    const type = getPreviewType(item.name);
    if (type === "other") return;
    const items = buildPreviewItems(type);
    const index = items.findIndex((entry) => entry.path === item.path);
    await loadPreviewAt(items, Math.max(index, 0));
  } catch (err: any) {
    notify.error(err?.response?.data?.msg || err?.message || "预览失败");
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

const openDetails = (item: any) => {
  detailItem.value = item;
  showDetails.value = true;
  closeContextMenu();
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

const openContextMenu = (event: MouseEvent, item: any | null) => {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    item
  };
};

const closeContextMenu = () => {
  contextMenu.value.visible = false;
};

const toggleUploadMenu = () => {
  showUploadMenu.value = !showUploadMenu.value;
};

const handleRootClick = () => {
  closeContextMenu();
  showUploadMenu.value = false;
};

const closeConfirm = () => {
  confirmState.value.visible = false;
};

const triggerUpload = () => {
  closeContextMenu();
  uploadInput.value?.click();
};

const openNewFolder = () => {
  showFolderInput.value = true;
  closeContextMenu();
};

watch(showFolderInput, async (visible) => {
  if (!visible) return;
  await nextTick();
  newFolderInput.value?.focus();
});

const handleDrop = async (event: DragEvent) => {
  if (!event.dataTransfer || !userId.value) return;
  if (event.dataTransfer.files?.length && canUpload.value) {
    const files = Array.from(event.dataTransfer.files);
    await uploadFiles(files, currentPath.value);
    load();
    return;
  }
  const sourcePath = event.dataTransfer.getData("text/plain");
  if (sourcePath && canRename.value) {
    const name = sourcePath.split("/").pop() || sourcePath;
    const targetBase = currentPath.value;
    const dstPath = targetBase ? `${targetBase}/${name}` : name;
    if (dstPath === sourcePath) return;
    await renameAdminDisk(userId.value, sourcePath, dstPath, true);
    load();
  }
};

const handleDragStart = (item: any, event: DragEvent) => {
  if (!event.dataTransfer) return;
  dragSourcePath.value = item.path;
  event.dataTransfer.setData("text/plain", item.path);
  event.dataTransfer.effectAllowed = "move";
};

const handleMoveDrop = async (target: any, event: DragEvent) => {
  if (!userId.value || !target?.is_dir || !canRename.value) return;
  if (event?.dataTransfer?.files?.length && canUpload.value) {
    const files = Array.from(event.dataTransfer.files);
    await uploadFiles(files, target.path);
    load();
    return;
  }
  const sourcePath = dragSourcePath.value;
  if (!sourcePath) return;
  const sourceItem = findEntryByPath(sourcePath);
  const name = sourcePath.split("/").pop() || sourcePath;
  const dstPath = target.path ? `${target.path}/${name}` : name;
  if (dstPath === sourcePath) return;
  if (
    sourceItem?.is_dir &&
    (target.path === sourcePath || target.path.startsWith(`${sourcePath}/`))
  ) {
    error.value = "不能移动到自身或子目录";
    return;
  }
  await renameAdminDisk(userId.value, sourcePath, dstPath, true);
  load();
};

const findEntryByPath = (path: string) =>
  entries.value.find((entry) => entry.path === path);

const isSelected = (path: string) => selectedPaths.value.has(path);
const isDownloading = (path: string) => downloadingPaths.value.has(path);

const toggleSelect = (path: string, event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.checked) {
    selectedPaths.value.add(path);
  } else {
    selectedPaths.value.delete(path);
  }
};

const toggleSelectAll = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const next = new Set<string>();
  if (target.checked) {
    filteredEntries.value.forEach((entry) => next.add(entry.path));
  }
  selectedPaths.value = next;
};

const batchDelete = () => {
  if (!userId.value) return;
  const items = entries.value.filter((entry) =>
    selectedPaths.value.has(entry.path)
  );
  if (!items.length) return;
  confirmAction(
    "确认删除",
    `确定删除 ${items.length} 个项目吗？`,
    async () => {
      for (const item of items) {
        await deleteAdminDisk(userId.value, item.path, item.is_dir);
      }
      selectedPaths.value = new Set();
      load();
    },
    "批量删除成功"
  );
};

const confirmAction = (
  title: string,
  message: string,
  action: () => Promise<void>,
  successMessage?: string
) => {
  confirmState.value = {
    visible: true,
    title,
    message,
    onConfirm: async () => {
      try {
        await action();
        if (successMessage) {
          notify.success(successMessage);
        }
      } catch (err: any) {
        error.value = err?.response?.data?.msg || err?.message || "操作失败";
        notify.error(error.value);
      } finally {
        closeConfirm();
      }
    }
  };
};

watch(userId, () => {
  currentPath.value = "";
  treeRoots.value = [];
  moveTarget.value = "";
  load();
});

onMounted(() => {
  const saved = getAppStorage().disk?.admin;
  if (saved?.userId) userId.value = saved.userId;
  if (typeof saved?.path === "string") currentPath.value = saved.path;
  load();
});

watch([userId, currentPath], () => {
  setAppStorage({ disk: { admin: { userId: userId.value, path: currentPath.value } } });
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
  gap: 20px;
  flex-wrap: wrap;
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

@media (max-width: 768px) {
  .toolbar {
    flex-wrap: wrap;
  }

  .toolbar-group {
    margin-left: 0;
  }
}

.user-select {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.file-input {
  display: none;
}

.disk-table {
  --disk-table-bg: #ffffff;
  --disk-table-row-hover: var(--surface-alt);
}

.select-col {
  width: 36px;
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

.tree-root {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--stroke);
  margin-bottom: 12px;
  cursor: pointer;
  font-size: 13px;
}

.tree-list {
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--stroke);
  border-radius: var(--radius-sm);
  padding: 8px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}

.tree-toggle {
  width: 28px;
  border: none;
  background: transparent;
  cursor: pointer;
}

.tree-label {
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font-size: 13px;
}

.tree-selected {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  border-bottom: 1px solid var(--stroke);
  padding: 8px 0;
}

.context-menu {
  position: fixed;
  z-index: 40;
  background: var(--surface);
  border: 1px solid var(--stroke);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 6px;
  min-width: 160px;
}

.context-item {
  width: 100%;
  border: none;
  background: transparent;
  padding: 8px 10px;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  border-radius: 8px;
}

.context-item:hover {
  background: var(--surface-alt);
}

</style>
