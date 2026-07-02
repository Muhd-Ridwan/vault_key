import { createRouter, createWebHistory } from "vue-router";
import LoginPage from "../pages/LoginPage.vue";
import VaultPage from "../pages/VaultPage.vue";
import RequestAccessPage from "../pages/RequestAccessPage.vue";
import AdminPage from "../pages/AdminPage.vue";
import { parseJwt } from "../utils/jwt.js";

const routes = [
  {
    path: "/",
    redirect: "/login",
  },
  {
    path: "/login",
    component: LoginPage,
  },
  {
    path: "/request-access",
    component: RequestAccessPage,
  },
  {
    path: "/admin",
    component: AdminPage,
    meta: { requiresAuth: true, requiresSuperadmin: true },
  },
  {
    path: "/vault",
    component: VaultPage,
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

function getRole() {
  const token = localStorage.getItem("token");
  if (!token) return null;
  try {
    return parseJwt(token)?.role;
  } catch {
    return null;
  }
}

router.beforeEach((to) => {
  const token = localStorage.getItem("token");
  if (to.meta.requiresAuth && !token) {
    return { path: "/login" };
  }
  if (to.meta.requiresSuperadmin && getRole() !== "superadmin") {
    return { path: "/vault" };
  }
});

export default router;
