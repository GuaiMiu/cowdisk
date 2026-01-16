import { createRouter, createWebHistory } from "vue-router";
import { useAdminAuthStore } from "../stores/adminAuth";
import { useUserAuthStore } from "../stores/userAuth";

const routes = [
  {
    path: "/admin/login",
    name: "admin-login",
    component: () => import("../views/auth/AdminLogin.vue")
  },
  {
    path: "/admin",
    component: () => import("../layouts/AdminLayout.vue"),
    meta: { requiresAdmin: true },
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("../views/Dashboard.vue")
      },
      {
        path: "user",
        name: "users",
        component: () => import("../views/users/UsersList.vue")
      },
      {
        path: "role",
        name: "roles",
        component: () => import("../views/roles/RolesList.vue")
      },
      {
        path: "menu",
        name: "menus",
        component: () => import("../views/menus/MenusList.vue")
      },
      {
        path: "disk",
        name: "admin-disk",
        component: () => import("../views/disk/AdminDiskBrowser.vue")
      }
    ]
  },
  {
    path: "/login",
    name: "user-login",
    component: () => import("../views/auth/UserLogin.vue")
  },
  {
    path: "/",
    component: () => import("../layouts/UserLayout.vue"),
    meta: { requiresUser: true },
    children: [
      {
        path: "",
        name: "user-disk",
        component: () => import("../views/disk/UserDiskBrowser.vue")
      },
      {
        path: "share",
        name: "user-share",
        component: () => import("../views/disk/UserShare.vue")
      },
      {
        path: "recycle",
        name: "user-recycle",
        component: () => import("../views/disk/UserRecycle.vue")
      }
    ]
  }
];

export const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to) => {
  const adminAuth = useAdminAuthStore();
  const userAuth = useUserAuthStore();

  if (to.path.startsWith("/admin")) {
    if (to.path === "/admin/login") {
      if (adminAuth.isAuthed) {
        return "/admin";
      }
      return true;
    }
    if (to.meta.requiresAdmin && !adminAuth.isAuthed) {
      return "/admin/login";
    }
    if (
      adminAuth.isAuthed &&
      (!adminAuth.user || !adminAuth.menus.length || !adminAuth.permissions.length)
    ) {
      await Promise.all([
        adminAuth.loadUser(),
        adminAuth.loadMenus(),
        adminAuth.loadPerms()
      ]);
    }
    return true;
  }

  if (to.path === "/login") {
    if (userAuth.isAuthed) {
      return "/";
    }
    return true;
  }
  if (to.meta.requiresUser && !userAuth.isAuthed) {
    return "/login";
  }
  if (
    userAuth.isAuthed &&
    (!userAuth.user || !userAuth.menus.length || !userAuth.permissions.length)
  ) {
    await Promise.all([
      userAuth.loadUser(),
      userAuth.loadMenus(),
      userAuth.loadPerms()
    ]);
  }
  return true;
});
