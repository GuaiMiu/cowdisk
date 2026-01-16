import axios from "axios";
import { useAdminAuthStore } from "../stores/adminAuth";

const adminAuthApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "/api/v1",
  timeout: 120000
});

adminAuthApi.interceptors.request.use((config) => {
  const auth = useAdminAuthStore();
  if (auth.token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

adminAuthApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const auth = useAdminAuthStore();
    if (error?.response?.status === 401) {
      auth.logout();
    }
    return Promise.reject(error);
  }
);

export default adminAuthApi;
