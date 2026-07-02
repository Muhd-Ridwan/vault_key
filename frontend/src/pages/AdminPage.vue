<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header
      class="border-b border-border px-6 py-4 flex items-center justify-between"
    >
      <div class="flex items-center gap-3">
        <div class="text-gold font-mono text-xl tracking-widest">VAULT KEY</div>
        <span
          class="text-xs border border-gold/40 text-gold rounded px-2 py-0.5"
          >ADMIN</span
        >
      </div>
      <UserMenu :email="userEmail" :role="userRole" />
    </header>

    <!-- Tabs -->
    <div class="border-b border-border px-6 flex gap-6">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        class="py-3 text-sm border-b-2 transition-colors"
        :class="
          activeTab === tab.id
            ? 'border-gold text-gold'
            : 'border-transparent text-text-muted hover:text-text-primary'
        "
      >
        {{ tab.label }}
      </button>
    </div>
    <!-- Content -->
    <main class="flex-1 px-6 py-8 max-w-5xl mx-auto w-full">
      <!-- ACCESS REQUESTS -->
      <div v-if="activeTab === 'requests'">
        <div class="flex gap-3 mb-6">
          <select
            v-model="reqStatusFilter"
            @change="loadRequests(1)"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-gold"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
        <div v-if="reqLoading" class="text-text-muted text-sm">Loading...</div>
        <div v-else-if="requests.length === 0" class="text-text-muted text-sm">
          No requests found
        </div>
        <div v-else class="flex flex-col gap-3">
          <div
            v-for="r in requests"
            :key="r.id"
            class="bg-steel-panel border border-border rounded-xl px-5 py-4 flex flex-col gap-2"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex flex-col gap-1">
                <div class="flex items-center gap-2">
                  <span class="text-text-primary text-sm font-medium">{{
                    r.name
                  }}</span>
                  <span
                    class="text-xs font-mono border rounded px-2 py-0.5"
                    :class="{
                      'border-gold/40 text-gold': r.status === 'pending',
                      'border-success/40 text-success': r.status === 'approved',
                      'border-danger/40 text-danger': r.status === 'rejected',
                    }"
                  >
                    {{ r.status }}
                  </span>
                </div>
                <span class="text-text-muted text-xs">
                  {{ r.email }} · {{ r.phone }}
                </span>
                <span class="text-text-muted text-xs">
                  {{ r.reason }}
                </span>
                <span class="text-text-muted text-xs">
                  {{ formatDate(r.requested_at) }}
                </span>
              </div>
              <div v-if="r.status === 'pending'" class="flex gap-2 shrink-0">
                <button
                  @click="approveRequest(r.id)"
                  class="text-xs bg-gold text-vault-black font-medium px-3 py-1.5 rounded-lg hover:brightness-110 transition"
                >
                  Approve
                </button>
                <button
                  @click="rejectRequest(r.id)"
                  class="text-xs border border-danger text-danger px-3 py-1.5 rounded-lg hover:bg-danger/10 transition"
                >
                  Reject
                </button>
              </div>
            </div>
          </div>
          <div
            v-if="reqPages > 1"
            class="flex items-center justify-center gap-2 mt-6"
          >
            <button
              v-for="p in reqPages"
              :key="p"
              @click="loadRequests(p)"
              class="w-8 h-8 rounded text-sm transition-colors"
              :class="
                p === reqPage
                  ? 'bg-gold text-vault-black font-medium'
                  : 'text-text-muted hover:text-text-primary'
              "
            >
              {{ p }}
            </button>
          </div>
        </div>
      </div>
      <!-- USERS -->
      <div v-if="activeTab === 'users'">
        <div class="flex gap-3 mb-6">
          <select
            v-model="userStatusFilter"
            @change="loadUsers(1)"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-gold"
          >
            <option value="">All</option>
            <option value="approved">Approved</option>
            <option value="revoked">Revoked</option>
          </select>
        </div>
        <div v-if="usersLoading" class="text-text-muted text-sm">
          Loading...
        </div>
        <div v-else-if="users.length === 0" class="text-text-muted text-sm">
          No users found.
        </div>
        <div v-else class="flex flex-col gap-3">
          <div
            v-for="u in users"
            :key="u.id"
            class="bg-steel-panel border border-border rounded-xl px-5 py-4 flex items-center justify-between gap-4"
          >
            <div class="flex flex-col gap-1">
              <div class="flex items-center gap-2">
                <span class="text-text-primary text-sm font-medium">
                  {{ u.name }}
                </span>
                <span
                  class="text-xs border rounded px-2 py-0.5 font-mono"
                  :class="
                    u.role === 'superadmin'
                      ? 'text-gold border-gold/40'
                      : 'text-text-muted border-border'
                  "
                >
                  {{ u.role }}
                </span>
                <span
                  class="text-xs border rounded px-2 py-0.5"
                  :class="
                    u.status === 'approved'
                      ? 'text-success border-success/40'
                      : 'text-danger border-danger/40'
                  "
                >
                  {{ u.status }}
                </span>
              </div>
              <span class="text-text-muted text-xs">{{ u.email }}</span>
              <span class="text-text-muted text-xs"
                >Joined {{ formatDate(u.created_at) }}</span
              >
            </div>
            <div v-if="u.role !== 'superadmin'" class="flex gap-2 shrink-0">
              <button
                v-if="u.status === 'approved'"
                @click="revokeUser(u.id)"
                class="text-xs border border-danger text-danger px-3 py-1.5 rounded-lg hover:bg-danger/10 transition"
              >
                Revoke
              </button>
              <button
                v-if="u.status === 'revoked'"
                @click="approveUser(u.id)"
                class="text-xs bg-gold text-vault-black font-medium px-3 py-1.5 rounded-lg hover:brightness-110 transition"
              >
                Approve
              </button>
              <button
                @click="resetTotp(u.id)"
                class="text-xs border border-border text-text-muted px-3 py-1.5 rounded-lg hover:border-gold hover:text-gold transition"
              >
                Reset TOTP
              </button>
            </div>
          </div>
          <div
            v-if="userPages > 1"
            class="flex items-center justify-center gap-2 mt-6"
          >
            <button
              v-for="p in userPages"
              :key="p"
              @click="loadUsers(p)"
              class="w-8 h-8 rounded text-sm transition-colors"
              :class="
                p === userPage
                  ? 'bg-gold text-vault-black font-medium'
                  : 'text-text-muted hover:text-text-primary'
              "
            >
              {{ p }}
            </button>
          </div>
        </div>
      </div>
      <!-- AUDIT LOGs -->
      <div v-if="activeTab === 'audit'">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-6">
          <input
            v-model="auditAction"
            type="text"
            placeholder="Filter by action..."
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 w-full placeholder:text-text-muted focus:outline-none focus:border-gold"
          />
          <input
            v-model="auditDateFrom"
            type="date"
            class="bg-steel-panel border border-border text-text-muted text-sm rounded-lg px-3 py-2 w-full focus:outline-none focus:border-gold"
          />
          <input
            v-model="auditDateTo"
            type="date"
            class="bg-steel-panel border border-border text-text-muted text-sm rounded-lg px-3 py-2 w-full focus:outline-none focus:border-gold"
          />
          <div class="flex gap-2 sm:col-span-2">
            <button
              @click="loadAudit(1)"
              class="bg-steel-elevated border border-border text-text-primary text-sm px-4 py-2 rounded-lg hover:border-gold transition-colors"
            >
              Apply
            </button>
            <button
              @click="resetAuditFilters"
              class="text-text-muted text-sm px-4 py-2 hover:text-text-primary transition-colors"
            >
              Reset
            </button>
          </div>
        </div>

        <div v-if="auditLoading" class="text-text-muted text-sm">
          Loading...
        </div>
        <div v-else-if="auditLogs.length === 0" class="text-text-muted text-sm">
          No logs found.
        </div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="log in auditLogs"
            :key="log.id"
            class="bg-steel-panel border border-border rounded-xl px-5 py-3 flex flex-col gap-1"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <span
                  class="text-xs font-mono border border-border rounded px-2 py-0.5 text-text-muted shrink-0"
                >
                  {{ log.action }}
                </span>
                <span class="text-text-primary text-sm truncate">{{
                  log.actor_email
                }}</span>
              </div>
              <span class="text-text-muted text-xs shrink-0">{{
                formatDate(log.timestamp)
              }}</span>
            </div>
            <div class="text-text-muted text-xs">
              <span v-if="log.target_label">{{ log.target_label }}</span>
              <span v-if="log.detail"> — {{ log.detail }}</span>
              <span v-if="log.ip_address"> · {{ log.ip_address }}</span>
            </div>
          </div>
          <div
            v-if="auditPages > 1"
            class="flex items-center justify-center gap-2 mt-6"
          >
            <button
              v-for="p in auditPages"
              :key="p"
              @click="loadAudit(p)"
              class="w-8 h-8 rounded text-sm transition-colors"
              :class="
                p === auditPage
                  ? 'bg-gold text-vault-black font-medium'
                  : 'text-text-muted hover:text-text-primary'
              "
            >
              {{ p }}
            </button>
          </div>
        </div>
      </div>
      <!-- SETTINGs -->
      <div v-if="activeTab === 'settings'">
        <div
          class="bg-steel-panel border border-border rounded-xl px-5 py-4 flex items-center justify-between gap-4 max-w-md"
        >
          <div class="flex flex-col gap-1">
            <span class="text-text-primary text-sm font-medium"
              >Vault Visibility</span
            >
            <span class="text-text-muted text-xs">
              {{
                visibility === "shared"
                  ? "All approved users see all entries."
                  : "Users only see their own entries."
              }}
            </span>
          </div>
          <button
            @click="toggleVisibility"
            class="text-xs font-medium px-4 py-2 rounded-lg border transition shrink-0"
            :class="
              visibility === 'shared'
                ? 'border-gold text-gold hover:bg-gold/10'
                : 'bg-gold text-vault-black border-gold hover:brightness-110'
            "
          >
            {{
              visibility === "shared" ? "Switch to Private" : "Switch to Shared"
            }}
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import api from "../services/api";
import { useToastStore } from "../stores/toast";
import UserMenu from "../components/UserMenu.vue";
import { parseJwt } from "../utils/jwt.js";

const toast = useToastStore();
const token = localStorage.getItem("token");
const payload = token ? parseJwt(token) : null;
const userEmail = payload?.email ?? "";
const userRole = payload?.role ?? "";

const tabs = [
  { id: "requests", label: "Access Requests" },
  { id: "users", label: "Users" },
  { id: "audit", label: "Audit Log" },
  { id: "settings", label: "Settings" },
];
const activeTab = ref("requests");

// ACCESS REQUESTS
const requests = ref([]);
const reqLoading = ref(false);
const reqPage = ref(1);
const reqPages = ref(1);
const reqStatusFilter = ref("pending");

async function loadRequests(page = 1) {
  reqLoading.value = true;
  try {
    const params = { page, limit: 50 };
    if (reqStatusFilter.value) params.status = reqStatusFilter.value;
    const res = await api.get("/admin/access-requests", { params });
    requests.value = res.data.items;
    reqPage.value = res.data.page;
    reqPages.value = res.data.pages;
  } catch {
    toast.show("Failed to load access requests.", "error");
  } finally {
    reqLoading.value = false;
  }
}

async function approveRequest(id) {
  try {
    const res = await api.post(`/admin/access-requests/${id}/approve`);
    toast.show(res.data.message, "success");
    loadRequests(reqPage.value);
  } catch (err) {
    toast.show(err.response?.data?.detail || "Failed to approve.", "error");
  }
}

async function rejectRequest(id) {
  try {
    const res = await api.post(`/admin/access-requests/${id}/reject`);
    toast.show(res.data.message, "success");
    loadRequests(reqPage.value);
  } catch (err) {
    toast.show(err.response?.data?.detail || "Failed to reject.", "error");
  }
}

// USERS
const users = ref([]);
const usersLoading = ref(false);
const userPage = ref(1);
const userPages = ref(1);
const userStatusFilter = ref("");

async function loadUsers(page = 1) {
  usersLoading.value = true;
  try {
    const params = { page, limit: 50 };
    if (userStatusFilter.value) params.status = userStatusFilter.value;
    const res = await api.get("/admin/users", { params });
    users.value = res.data.items;
    userPage.value = res.data.page;
    userPages.value = res.data.pages;
  } catch {
    toast.show("Failed to load users.", "error");
  } finally {
    usersLoading.value = false;
  }
}

async function revokeUser(id) {
  try {
    const res = await api.post(`/admin/users/${id}/revoke`);
    toast.show(res.data.message, "success");
    loadUsers(userPage.value);
  } catch (err) {
    toast.show(err.response?.data?.detail || "Failed to revoke.", "error");
  }
}

async function approveUser(id) {
  try {
    const res = await api.post(`/admin/users/${id}/approve`);
    toast.show(res.data.message, "success");
    loadUsers(userPage.value);
  } catch (err) {
    toast.show(err.response?.data?.detail || "Failed to approve.", "error");
  }
}

async function resetTotp(id) {
  try {
    const res = await api.delete(`/auth/totp/reset/${id}`);
    toast.show(res.data.message, "success");
  } catch (err) {
    toast.show(err.response?.data?.detail || "Failed to reset TOTP.", "error");
  }
}

// AUDIT LOG
const auditLogs = ref([]);
const auditLoading = ref(false);
const auditPage = ref(1);
const auditPages = ref(1);
const auditAction = ref("");
const auditDateFrom = ref("");
const auditDateTo = ref("");

async function loadAudit(page = 1) {
  auditLoading.value = true;
  try {
    const params = { page, limit: 20 };
    if (auditAction.value) params.action = auditAction.value;
    if (auditDateFrom.value) params.date_from = auditDateFrom.value;
    if (auditDateTo.value) params.date_to = auditDateTo.value;
    const res = await api.get("/admin/audit", { params });
    auditLogs.value = res.data.items;
    auditPage.value = res.data.page;
    auditPages.value = res.data.pages;
  } catch {
    toast.show("Failed to load audit log.", "error");
  } finally {
    auditLoading.value = false;
  }
}

function resetAuditFilters() {
  auditAction.value = "";
  auditDateFrom.value = "";
  auditDateTo.value = "";
  loadAudit(1);
}

// SETTINGS
const visibility = ref("shared");

async function loadSettings() {
  try {
    const res = await api.get("/admin/settings");
    visibility.value = res.data.vault_visibility;
  } catch {
    toast.show("Failed to load settings.", "error");
  }
}

async function toggleVisibility() {
  const next = visibility.value === "shared" ? "private" : "shared";
  try {
    const res = await api.put("/admin/settings/visibility", {
      visibility: next,
    });
    visibility.value = res.data.vault_visibility;
    toast.show(`Vault visibility set to ${visibility.value}.`, "success");
  } catch (err) {
    toast.show(err.response?.data?.detail || "Failed to update.", "error");
  }
}

// HELPERS
function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-MY", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

onMounted(() => {
  loadRequests();
  loadUsers();
  loadAudit();
  loadSettings();
});
</script>
