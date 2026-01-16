import { defineStore } from "pinia";
import {
  userFetchMe,
  userFetchMenus,
  userFetchPerms,
  userLogin,
  userLogout
} from "../api/user";
import { clearAppStorageToken, getAppStorage, setAppStorage } from "../utils/storage";

interface UserInfo {
  username?: string;
  mail?: string;
  is_superuser?: boolean;
  total_space?: number;
  used_space?: number;
  roles?: Array<{ id?: number; name?: string }>;
}

export const useUserAuthStore = defineStore("userAuth", {
  state: () => ({
    token: (() => {
      const storage = getAppStorage();
      if (storage.token) return storage.token;
      const legacy = localStorage.getItem("cow_user_token");
      if (legacy) {
        setAppStorage({ token: legacy });
        localStorage.removeItem("cow_user_token");
        return legacy;
      }
      return "";
    })(),
    user: null as UserInfo | null,
    menus: [] as any[],
    permissions: [] as string[]
  }),
  getters: {
    isAuthed: (state) => Boolean(state.token),
    hasPerm: (state) => (perm: string) => {
      const perms = new Set(state.permissions);
      return perms.has("*:*:*") || perms.has(perm);
    }
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await userLogin(username, password);
      const token = data?.data?.access_token || data?.access_token;
      if (!token) {
        throw new Error("登录失败");
      }
      this.token = token;
      setAppStorage({ token });
      await Promise.all([this.loadUser(), this.loadMenus(), this.loadPerms()]);
    },
    async loadUser() {
      const { data } = await userFetchMe();
      this.user = data?.data || null;
    },
    async loadMenus() {
      const { data } = await userFetchMenus();
      this.menus = data?.data || [];
    },
    async loadPerms() {
      const { data } = await userFetchPerms();
      this.permissions = data?.data || [];
    },
    async logout() {
      try {
        await userLogout();
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
