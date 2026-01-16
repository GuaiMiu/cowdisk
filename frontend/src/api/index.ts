import api from "./client";

export const login = (username: string, password: string) => {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);
  return api.post("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" }
  });
};

export const fetchMe = () => api.get("/auth/me");
export const fetchMenus = () => api.get("/auth/routers");
export const logout = () => api.get("/auth/logout");

export const fetchUsers = (page = 1, size = 20) =>
  api.get("/system/user/list", { params: { page, size } });
export const createUser = (payload: Record<string, unknown>) =>
  api.post("/system/user", payload);
export const updateUser = (payload: Record<string, unknown>) =>
  api.put("/system/user", payload);
export const deleteUser = (id: number) => api.delete(`/system/user/${id}`);

export const fetchRoles = (page = 1, size = 20) =>
  api.get("/system/role/list", { params: { page, size } });
export const createRole = (payload: Record<string, unknown>) =>
  api.post("/system/role", payload);
export const updateRole = (payload: Record<string, unknown>) =>
  api.put("/system/role", payload);
export const deleteRole = (id: number) => api.delete(`/system/role/${id}`);

export const fetchMenusList = (page = 1, size = 200) =>
  api.get("/system/menu/list", { params: { page, size } });
export const createMenu = (payload: Record<string, unknown>) =>
  api.post("/system/menu", payload);
export const updateMenu = (payload: Record<string, unknown>) =>
  api.put("/system/menu", payload);
export const deleteMenu = (id: number) => api.delete(`/system/menu/${id}`);

export const listDisk = (path = "") =>
  api.get("/disk/list", { params: { path } });
export const mkdirDisk = (path: string) => api.post("/disk/mkdir", { path });
export const deleteDisk = (path: string, recursive = false) =>
  api.delete("/disk", { params: { path, recursive } });
export const renameDisk = (src: string, dst: string, overwrite = false) =>
  api.post("/disk/rename", { src, dst, overwrite });
export const uploadDisk = (
  files: File[],
  path = "",
  overwrite = false,
  onUploadProgress?: (event: ProgressEvent) => void
) => {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  form.append("path", path);
  form.append("overwrite", String(overwrite));
  return api.post("/disk/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress
  });
};
export const initDiskUpload = (payload: {
  path: string;
  filename: string;
  size: number;
  total_chunks: number;
  overwrite?: boolean;
}) => api.post("/disk/upload/init", payload);
export const uploadDiskChunk = (
  uploadId: string,
  index: number,
  chunk: Blob,
  onUploadProgress?: (event: ProgressEvent) => void
) => {
  const form = new FormData();
  form.append("upload_id", uploadId);
  form.append("index", String(index));
  form.append("chunk", chunk);
  return api.post("/disk/upload/chunk", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress
  });
};
export const completeDiskUpload = (uploadId: string) =>
  api.post("/disk/upload/complete", { upload_id: uploadId });
export const prepareDiskDownload = (path: string) =>
  api.post("/disk/download/prepare", { path });
export const getDiskDownloadStatus = (jobId: string) =>
  api.get("/disk/download/status", { params: { job_id: jobId } });
export const createDiskDownloadToken = (payload: { path?: string; job_id?: string }) =>
  api.post("/disk/download/token", payload);
