<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header
      class="border-b border-border px-4 sm:px-6 py-3 flex items-center justify-between gap-2"
    >
      <div
        class="text-gold font-mono text-xl sm:text-xl tracking-widest shrink-0 whitespace-nowrap"
      >
        VAULT KEY
      </div>
      <UserMenu :email="userEmail" :role="userRole" />
    </header>

    <!-- MAIN CONTENT -->
    <main class="flex-1 px-6 py-8 max-w-4xl mx-auto w-full">
      <!-- PAGE TITLE -->
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-text-primary text-lg font-medium">Credentials</h1>
        <button
          @click="showAddModal = true"
          class="flex items-center gap-2 bg-gold text-vault-black text-sm font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
        >
          <Plus :size="16" />
          Add Entry
        </button>
      </div>
      <!-- Filters -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-6">
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">Search by Title</label>
          <div class="relative">
            <input
              v-model="filters.title"
              type="text"
              placeholder="e.g. SSH"
              class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 w-full placeholder:text-text-muted focus:outline-none focus:border-gold"
            />
          </div>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">
            Search by Creator Name
          </label>
          <div class="relative">
            <input
              v-model="filters.name"
              type="text"
              placeholder="e.g. Ridwan"
              class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 w-full placeholder:text-text-muted focus:outline-none focus:border-gold"
            />
          </div>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">From Date</label>
          <div class="relative">
            <input
              v-model="filters.dateFrom"
              type="date"
              placeholder="mm/dd/yyyy"
              class="relative bg-steel-panel border border-border text-text-muted text-sm placeholder:text-text-muted rounded-lg pl-3 py-2 pr-9 w-full focus:outline-none focus:border-gold"
            />
            <Calendar
              :size="16"
              class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted"
            />
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">To Date</label>
          <div class="relative">
            <input
              v-model="filters.dateTo"
              type="date"
              placeholder="mm/dd/yyyy"
              class="relative bg-steel-panel border border-border text-text-muted text-sm placeholder:text-text-muted rounded-lg pl-3 pr-9 py-2 w-full focus:outline-none focus:border-gold"
            />
            <Calendar
              :size="16"
              class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted"
            />
          </div>
        </div>

        <div class="flex gap-2 sm:col-span-2">
          <button
            @click="applyFilters"
            class="bg-steel-elevated border border-border text-text-primary text-sm px-4 py-2 rounded-lg hover:border-gold transition-colors"
          >
            Apply
          </button>
          <button
            @click="resetFilters"
            class="text-text-muted text-sm px-4 py-2 hover:text-text-primary transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      <!-- Entry List -->
      <div v-if="loading" class="text-text-muted text-sm">Loading...</div>
      <div v-else-if="entries.length === 0" class="text-text-muted text-sm">
        No entries found.
      </div>
      <div v-else class="flex flex-col gap-3">
        <div
          v-for="entry in entries"
          :key="entry.id"
          class="bg-steel-panel border border-border rounded-xl overflow-hidden"
        >
          <!-- Collapsed Row -->
          <div
            @click="toggleEntry(entry.id)"
            class="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-steel-elevated transition-colors"
          >
            <div class="flex items-center gap-3">
              <span
                class="text-text-muted text-xs border border-border rounded px-2 py-0.5 font-mono"
              >
                {{ entry.entry_type }}
              </span>
              <span class="text-text-primary font-mono text-sm">
                {{ entry.title }}
              </span>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-text-muted text-xs">{{
                entry.created_by_name
              }}</span>
              <ChevronDown
                :size="16"
                class="text-text-muted transition-transform duration-200"
                :class="{ 'rotate-180': expandedEntries.includes(entry.id) }"
              />
            </div>
          </div>

          <!-- Expanded Content -->
          <div
            v-if="expandedEntries.includes(entry.id)"
            class="border-t border-border px-5 py-4 flex flex-col gap-3"
          >
            <div v-if="entry.username" class="flex items-center gap-2">
              <span class="text-text-muted text-xs w-20">Username</span>
              <span class="text-text-primary text-sm font-mono">{{
                entry.username
              }}</span>
              <button
                @click="copyToClipboard(entry.username)"
                class="text-text-muted hover:text-gold transition-colors"
              >
                <Copy :size="15" />
              </button>
            </div>
            <div v-if="entry.url" class="flex items-center gap-2">
              <span class="text-text-muted text-xs w-20">URL</span>
              <a
                :href="entry.url"
                target="_blank"
                class="text-gold text-sm hover:underline"
                >{{ entry.url }}</a
              >
            </div>
            <div v-if="entry.description" class="flex items-center gap-2">
              <span class="text-text-muted text-xs w-20">Description</span>
              <span class="text-text-primary text-sm">{{
                entry.description
              }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-text-muted text-xs w-20 shrink-0">Secret</span>
              <div class="flex-1 min-w-0 overflow-x-auto">
                <span
                  class="text-text-primary text-sm font-mono whitespace-nowrap"
                  >{{ revealedSecrets[entry.id] ?? "••••••••" }}</span
                >
              </div>

              <button
                @click="revealSecret(entry.id)"
                class="ml-2 text-text-muted hover:text-gold transition-colors"
              >
                <Eye :size="15" />
              </button>
              <button
                v-if="revealedSecrets[entry.id]"
                @click="copyToClipboard(revealedSecrets[entry.id])"
                class="text-text-muted hover:text-gold transition-colors"
              >
                <Copy :size="15" />
              </button>
            </div>
            <div
              class="flex items-center gap-3 pt-2 border-t border-border mt-1"
            >
              <button
                @click.stop="openEditModal(entry)"
                class="text-text-muted text-xs hover:text-gold transition-colors flex items-center gap-1"
              >
                <Pencil :size="13" /> Edit
              </button>
              <button
                @click.stop="confirmDelete(entry)"
                class="text-text-muted text-xs hover:text-danger transition-colors flex items-center gap-1"
              >
                <Trash2 :size="13" /> Delete
              </button>
            </div>
          </div>
        </div>
        <!-- Pagination -->
        <div
          v-if="totalPages > 1"
          class="flex items-center justify-center gap-2 mt-8"
        >
          <button
            v-for="page in totalPages"
            :key="page"
            @click="goToPage(page)"
            class="w-8 h-8 rounded text-sm transition-colors"
            :class="
              page === currentPage
                ? 'bg-gold text-vault-black font-medium'
                : 'text-text-muted hover:text-text-primary'
            "
          >
            {{ page }}
          </button>
        </div>
      </div>
    </main>

    <AddEntryModal
      v-if="showAddModal"
      @close="showAddModal = false"
      @saved="onEntrySaved"
    />
    <div
      v-if="showDeleteConfirm"
      class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      @click.self="showDeleteConfirm = false"
    >
      <div
        class="bg-steel-panel border border-border rounded-xl p-6 w-80 flex flex-col gap-4"
      >
        <p class="text-text-primary text-sm">
          Delete
          <span class="font-mono text-gold">{{
            pendingDeleteEntry?.title
          }}</span>
          ? This cannot be undone.
        </p>
        <div class="flex gap-3 justify-end">
          <button
            @click="showDeleteConfirm = false"
            class="text-text-muted text-sm hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            @click="deleteEntry"
            class="bg-danger text-white text-sm px-4 py-2 rounded-lg hover:opacity-90"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
    <EditEntryModal
      v-if="showEditModal"
      :entry="editingEntry"
      @close="
        showEditModal = false;
        editingEntry = null;
      "
      @saved="onEntryUpdated"
    />
    <TotpEnrollModal v-if="showEnrollModal" @done="showEnrollModal = false" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import {
  Plus,
  Eye,
  ChevronDown,
  Copy,
  Pencil,
  Trash2,
  Calendar,
} from "lucide-vue-next";
import api from "../services/api.js";
import { useToastStore } from "../stores/toast.js";
import AddEntryModal from "../components/AddEntryModal.vue";
import EditEntryModal from "../components/EditEntryModal.vue";
import TotpEnrollModal from "../components/TotpEnrollModal.vue";
import UserMenu from "../components/UserMenu.vue";
import { parseJwt } from "../utils/jwt.js";
import { useTotpStore } from "../stores/totp.js";

const router = useRouter();

const entries = ref([]);
const loading = ref(true);
const expandedEntries = ref([]);
const revealedSecrets = ref({});
const currentPage = ref(1);
const totalPages = ref(1);
const filters = ref({ name: "", title: "", dateFrom: "", dateTo: "" });
const showAddModal = ref(false);
const showEditModal = ref(false);
const editingEntry = ref(null);
const pendingDeleteEntry = ref(null);
const showDeleteConfirm = ref(false);
const showEnrollModal = ref(false);
const toast = useToastStore();
const token = localStorage.getItem("token");
const payload = token ? parseJwt(token) : null;
const userEmail = payload?.email ?? "";
const userRole = payload?.role ?? "";
const totpStore = useTotpStore();

let expiryTimer = null;

onMounted(async () => {
  loadEntries();
  try {
    const res = await api.get("/auth/totp/status");
    if (!res.data.enrolled) showEnrollModal.value = true;
  } catch {
    // VAULT STILL LOADS
  }
  expiryTimer = setInterval(() => {
    if (
      totpStore.unlockExpiresAt &&
      new Date() > new Date(totpStore.unlockExpiresAt)
    ) {
      revealedSecrets.value = {};
    }
  }, 60000);
});

async function loadEntries(page = 1) {
  loading.value = true;
  try {
    const params = {
      page,
      limit: 20,
      ...(filters.value.name && { created_by_name: filters.value.name }),
      ...(filters.value.title && { title: filters.value.title }),
      ...(filters.value.dateFrom && { date_from: filters.value.dateFrom }),
      ...(filters.value.dateTo && { date_to: filters.value.dateTo }),
    };
    const res = await api.get("/vault/entries", { params });
    entries.value = res.data.items;
    currentPage.value = res.data.page;
    totalPages.value = res.data.pages;
  } catch (err) {
    if (err.response?.status === 401) router.push("/login");
    else toast.show("Failed to load entries.", "error");
  } finally {
    loading.value = false;
  }
}

function openEditModal(entry) {
  editingEntry.value = entry;
  showEditModal.value = true;
}

function confirmDelete(entry) {
  pendingDeleteEntry.value = entry;
  showDeleteConfirm.value = true;
}

async function deleteEntry() {
  if (!pendingDeleteEntry.value) return;
  try {
    await api.delete(`/vault/entries/${pendingDeleteEntry.value.id}`);
    toast.show("Entry deleted.", "success");
    showDeleteConfirm.value = false;
    pendingDeleteEntry.value = null;
    loadEntries(currentPage.value);
  } catch {
    toast.show("Failed to delete entry.", "error");
  }
}

function onEntryUpdated() {
  showEditModal.value = false;
  editingEntry.value = null;
  loadEntries(currentPage.value);
}

function toggleEntry(id) {
  const idx = expandedEntries.value.indexOf(id);
  if (idx === -1) {
    expandedEntries.value.push(id);
  } else {
    expandedEntries.value.splice(idx, 1);
  }
}

async function revealSecret(id) {
  if (revealedSecrets.value[id]) {
    delete revealedSecrets.value[id];
    return;
  }
  try {
    const res = await api.get(`/vault/entries/${id}/secret`);
    revealedSecrets.value[id] = res.data.secret;
  } catch (err) {
    if (err.response?.status === 401) router.push("/login");
    else toast.show("Failed to reveal secret.", "error");
  }
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast.show("Copied to clipboard.", "success");
  } catch {
    toast.show("Failed to copy to clipboard.", "error");
  }
}

function applyFilters() {
  loadEntries(1);
}

function resetFilters() {
  filters.value = { name: "", title: "", dateFrom: "", dateTo: "" };
  loadEntries(1);
}

function goToPage(page) {
  loadEntries(page);
}

function onEntrySaved() {
  showAddModal.value = false;
  loadEntries(currentPage.value);
}

onMounted(async () => {
  loadEntries();
  try {
    const res = await api.get("/auth/totp/status");
    if (!res.data.enrolled) showEnrollModal.value = true;
  } catch {
    // Silent skip. Vault still loads
  }
});
</script>

<style scoped>
input[type="date"]::-webkit-calendar-picker-indicator {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}
</style>
