import axios from "axios";
import { useAdminAuthStore } from "../stores/adminAuth";

const adminApi = axios.create({
  baseURL: import.meta.env.VITE_ADMIN_API_BASE || "/api/v1/admin",
  timeout: 120000
});

adminApi.interceptors.request.use((config) => {
  const auth = useAdminAuthStore();
  if (auth.token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const auth = useAdminAuthStore();
    if (error?.response?.status === 401) {
      auth.logout();
    }
    return Promise.reject(error);
  }
);

export default adminApi;
