import axios from "axios";
import { useUserAuthStore } from "../stores/userAuth";

const userApi = axios.create({
  baseURL: import.meta.env.VITE_USER_API_BASE || "/api/v1/user",
  timeout: 120000
});

userApi.interceptors.request.use((config) => {
  const auth = useUserAuthStore();
  if (auth.token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

userApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const auth = useUserAuthStore();
    if (error?.response?.status === 401) {
      auth.logout();
    }
    return Promise.reject(error);
  }
);

export default userApi;
