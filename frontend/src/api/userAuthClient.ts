import axios from "axios";
import { useUserAuthStore } from "../stores/userAuth";

const userAuthApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "/api/v1",
  timeout: 120000
});

userAuthApi.interceptors.request.use((config) => {
  const auth = useUserAuthStore();
  if (auth.token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

userAuthApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const auth = useUserAuthStore();
    if (error?.response?.status === 401) {
      auth.logout();
    }
    return Promise.reject(error);
  }
);

export default userAuthApi;
