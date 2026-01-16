import { defineStore } from "pinia";
import {
  adminFetchMe,
  adminFetchMenus,
  adminFetchPerms,
  adminLogin,
  adminLogout
} from "../api/admin";
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

export const useAdminAuthStore = defineStore("adminAuth", {
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
    menus: [] as MenuNode[],
    permissions: [] as string[]
  }),
  getters: {
    isAuthed: (state) => Boolean(state.token),
    hasPerm: (state) => (perm: string) => {
      if (state.user?.is_superuser) {
        return true;
      }
      const perms = new Set(state.permissions);
      return perms.has("*:*:*") || perms.has(perm);
    }
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await adminLogin(username, password);
      const token = data?.data?.access_token || data?.access_token;
      if (!token) {
        throw new Error("登录失败");
      }
      this.token = token;
      setAppStorage({ token });
      await Promise.all([this.loadUser(), this.loadMenus(), this.loadPerms()]);
    },
    async loadUser() {
      const { data } = await adminFetchMe();
      this.user = data?.data || null;
    },
    async loadMenus() {
      const { data } = await adminFetchMenus();
      this.menus = data?.data || [];
    },
    async loadPerms() {
      const { data } = await adminFetchPerms();
      this.permissions = data?.data || [];
    },
    async logout() {
      try {
        await adminLogout();
      } catch (error) {
        // Ignore logout errors.
      }
      this.token = "";
      this.user = null;
      this.menus = [];
      this.permissions = [];
      clearAppStorageToken();
    }
  }
});
