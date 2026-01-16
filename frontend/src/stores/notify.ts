import { defineStore } from "pinia";

export type NotifyType = "success" | "error" | "info" | "warn";

export interface NotifyItem {
  id: number;
  type: NotifyType;
  message: string;
}

export const useNotifyStore = defineStore("notify", {
  state: () => ({
    items: [] as NotifyItem[],
    nextId: 1
  }),
  actions: {
    add(message: string, type: NotifyType = "info", duration = 3000) {
      const id = this.nextId++;
      this.items.push({ id, type, message });
      if (duration > 0) {
        setTimeout(() => this.remove(id), duration);
      }
    },
    success(message: string, duration = 3000) {
      this.add(message, "success", duration);
    },
    error(message: string, duration = 3500) {
      this.add(message, "error", duration);
    },
    info(message: string, duration = 3000) {
      this.add(message, "info", duration);
    },
    warn(message: string, duration = 3200) {
      this.add(message, "warn", duration);
    },
    remove(id: number) {
      this.items = this.items.filter((item) => item.id !== id);
    },
    clear() {
      this.items = [];
    }
  }
});
