import userApi from "./userClient";
import userAuthApi from "./userAuthClient";

export const userLogin = (username: string, password: string) => {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);
  return userAuthApi.post("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" }
  });
};

export const userFetchMe = () => userAuthApi.get("/auth/me");
export const userFetchMenus = () => userAuthApi.get("/auth/routers");
export const userFetchPerms = () => userAuthApi.get("/auth/permissions");
export const userLogout = () => userAuthApi.get("/auth/logout");

export const listDisk = (path = "") => userApi.get("/disk/list", { params: { path } });
export const mkdirDisk = (path: string) => userApi.post("/disk/mkdir", { path });
export const deleteDisk = (path: string, recursive = false) =>
  userApi.delete("/disk", { params: { path, recursive } });
export const renameDisk = (src: string, dst: string, overwrite = false) =>
  userApi.post("/disk/rename", { src, dst, overwrite });
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
  return userApi.post("/disk/upload", form, {
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
}) => userApi.post("/disk/upload/init", payload);
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
  return userApi.post("/disk/upload/chunk", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress
  });
};
export const completeDiskUpload = (uploadId: string) =>
  userApi.post("/disk/upload/complete", { upload_id: uploadId });
export const prepareDiskDownload = (path: string) =>
  userApi.post("/disk/download/prepare", { path });
export const getDiskDownloadStatus = (jobId: string) =>
  userApi.get("/disk/download/status", { params: { job_id: jobId } });
export const createDiskDownloadToken = (payload: { path?: string; job_id?: string }) =>
  userApi.post("/disk/download/token", payload);

export const listDiskTrash = () => userApi.get("/disk/trash");
export const restoreDiskTrash = (id: string) =>
  userApi.post("/disk/trash/restore", { id });
export const deleteDiskTrash = (id: string) =>
  userApi.delete("/disk/trash", { data: { id } });
export const clearDiskTrash = () => userApi.delete("/disk/trash/clear");

export const createDiskShare = (payload: { path: string; expires_hours?: number }) =>
  userApi.post("/disk/share", payload);
export const listDiskShare = () => userApi.get("/disk/share");
export const revokeDiskShare = (id: string) => userApi.delete(`/disk/share/${id}`);
