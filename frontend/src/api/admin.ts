import adminApi from "./adminClient";
import adminAuthApi from "./adminAuthClient";

export const adminLogin = (username: string, password: string) => {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);
  return adminAuthApi.post("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" }
  });
};

export const adminFetchMe = () => adminAuthApi.get("/auth/me");
export const adminFetchMenus = () => adminAuthApi.get("/auth/routers");
export const adminFetchPerms = () => adminAuthApi.get("/auth/permissions");
export const adminLogout = () => adminAuthApi.get("/auth/logout");

export const fetchUsers = (page = 1, size = 20) =>
  adminApi.get("/system/user/list", { params: { page, size } });
export const createUser = (payload: Record<string, unknown>) =>
  adminApi.post("/system/user", payload);
export const updateUser = (payload: Record<string, unknown>) =>
  adminApi.put("/system/user", payload);
export const deleteUser = (id: number) => adminApi.delete(`/system/user/${id}`);

export const fetchRoles = (page = 1, size = 20) =>
  adminApi.get("/system/role/list", { params: { page, size } });
export const createRole = (payload: Record<string, unknown>) =>
  adminApi.post("/system/role", payload);
export const updateRole = (payload: Record<string, unknown>) =>
  adminApi.put("/system/role", payload);
export const deleteRole = (id: number) => adminApi.delete(`/system/role/${id}`);

export const fetchMenusList = (page = 1, size = 200) =>
  adminApi.get("/system/menu/list", { params: { page, size } });
export const createMenu = (payload: Record<string, unknown>) =>
  adminApi.post("/system/menu", payload);
export const updateMenu = (payload: Record<string, unknown>) =>
  adminApi.put("/system/menu", payload);
export const deleteMenu = (id: number) => adminApi.delete(`/system/menu/${id}`);

export const listAdminDisk = (userId: number, path = "") =>
  adminApi.get("/disk/list", { params: { user_id: userId, path } });
export const mkdirAdminDisk = (userId: number, path: string) =>
  adminApi.post("/disk/mkdir", { path }, { params: { user_id: userId } });
export const deleteAdminDisk = (userId: number, path: string, recursive = false) =>
  adminApi.delete("/disk", { params: { user_id: userId, path, recursive } });
export const renameAdminDisk = (
  userId: number,
  src: string,
  dst: string,
  overwrite = false
) => adminApi.post("/disk/rename", { src, dst, overwrite }, { params: { user_id: userId } });
export const uploadAdminDisk = (
  userId: number,
  files: File[],
  path = "",
  overwrite = false,
  onUploadProgress?: (event: ProgressEvent) => void
) => {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  form.append("path", path);
  form.append("overwrite", String(overwrite));
  form.append("user_id", String(userId));
  return adminApi.post("/disk/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress
  });
};
export const initAdminDiskUpload = (
  userId: number,
  payload: {
    path: string;
    filename: string;
    size: number;
    total_chunks: number;
    overwrite?: boolean;
  }
) => adminApi.post("/disk/upload/init", payload, { params: { user_id: userId } });
export const uploadAdminDiskChunk = (
  uploadId: string,
  index: number,
  chunk: Blob,
  userId: number,
  onUploadProgress?: (event: ProgressEvent) => void
) => {
  const form = new FormData();
  form.append("upload_id", uploadId);
  form.append("index", String(index));
  form.append("chunk", chunk);
  form.append("user_id", String(userId));
  return adminApi.post("/disk/upload/chunk", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress
  });
};
export const completeAdminDiskUpload = (userId: number, uploadId: string) =>
  adminApi.post("/disk/upload/complete", { upload_id: uploadId }, { params: { user_id: userId } });
export const prepareAdminDiskDownload = (userId: number, path: string) =>
  adminApi.post("/disk/download/prepare", { path }, { params: { user_id: userId } });
export const getAdminDiskDownloadStatus = (userId: number, jobId: string) =>
  adminApi.get("/disk/download/status", {
    params: { user_id: userId, job_id: jobId }
  });
export const createAdminDiskDownloadToken = (
  userId: number,
  payload: { path?: string; job_id?: string }
) => adminApi.post("/disk/download/token", payload, { params: { user_id: userId } });
