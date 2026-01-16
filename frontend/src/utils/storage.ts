type DiskStorage = {
  userPath?: string;
  legacyPath?: string;
  admin?: {
    userId?: number;
    path?: string;
  };
};

export type AppStorage = {
  token?: string;
  disk?: DiskStorage;
  menuExpanded?: number[];
};

const STORAGE_KEY = "cow_storage";

export const getAppStorage = (): AppStorage => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AppStorage) : {};
  } catch {
    return {};
  }
};

export const setAppStorage = (patch: AppStorage): AppStorage => {
  const current = getAppStorage();
  const next: AppStorage = {
    ...current,
    ...patch,
    disk: {
      ...current.disk,
      ...patch.disk,
      admin: {
        ...current.disk?.admin,
        ...patch.disk?.admin
      }
    }
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
};

export const clearAppStorageToken = () => {
  const current = getAppStorage();
  if ("token" in current) {
    const next = { ...current };
    delete next.token;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }
};
