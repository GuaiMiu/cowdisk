import { defineStore } from "pinia";
import { fetchMe, fetchMenus, login, logout } from "../api";
import { clearAppStorageToken, getAppStorage, setAppStorage } from "../utils/storage";

interface MenuNode {
  id?: number;
  name?: string;
  router_path?: string;
  type?: number;
  children?: MenuNode[];
}

interface UserInfo {
  username?: string;
  mail?: string;
  is_superuser?: boolean;
  roles?: Array<{ name?: string }>;
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: (() => {
      const storage = getAppStorage();
      if (storage.token) return storage.token;
      const legacy = localStorage.getItem("cow_admin_token");
      if (legacy) {
        setAppStorage({ token: legacy });
        localStorage.removeItem("cow_admin_token");
        return legacy;
      }
      return "";
    })(),
    user: null as UserInfo | null,
    menus: [] as MenuNode[]
  }),
  getters: {
    isAuthed: (state) => Boolean(state.token)
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await login(username, password);
      const token = data?.data?.access_token || data?.access_token;
      if (!token) {
        throw new Error("登录失败");
      }
      this.token = token;
      setAppStorage({ token });
      await Promise.all([this.loadUser(), this.loadMenus()]);
    },
    async loadUser() {
      const { data } = await fetchMe();
      this.user = data?.data || null;
    },
    async loadMenus() {
      const { data } = await fetchMenus();
      this.menus = data?.data || [];
    },
    async logout() {
      try {
        await logout();
      } catch (error) {
        // Ignore logout errors.
      }
      this.token = "";
      this.user = null;
      this.menus = [];
      clearAppStorageToken();
    }
  }
});
