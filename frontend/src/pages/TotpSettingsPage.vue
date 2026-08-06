<template>
  <div class="min-h-screen bg-steel-base p-4 md:p-8">
    <div class="max-w-2xl mx-auto flex flex-col gap-6">
      <div class="flex items-center justify-between">
        <h1 class="text-text-primary text-lg font-medium">
          Two-Factor Devices
        </h1>
        <RouterLink
          to="/vault"
          class="flex items-center gap-1 text-text-muted text-sm hover:text-text-primary transition-colors"
        >
          <ArrowLeft :size="16" />
          Back To Vault
        </RouterLink>
      </div>

      <div v-if="loading" class="text-text-muted text-sm">
        Loading devices...
      </div>

      <div v-else class="flex flex-col gap-3">
        <div
          v-for="device in devices"
          :key="device.id"
          class="bg-steel-elevated border border-border rounded-xl p-4 flex items-center justify-between gap-3"
        >
          <div class="flex flex-col gap-1 min-w-0">
            <p class="text-text-primary text-sm font-medium truncate">
              {{ device.label }}
            </p>
            <p class="text-text-muted text-xs">
              {{ device.confirmed ? "Active" : "Pending confirmation" }}
              · Added {{ formatDate(device.created_at) }}
              <template v-if="device.last_used_at">
                · Last used {{ formatDate(device.last_used_at) }}
              </template>
            </p>
          </div>
          <button
            @click="pendingDelete = device"
            class="text-danger text-sm px-3 py-1.5 rounded-lg border border-border hover:bg-danger hover:text-white hover:border-danger transition-colors"
          >
            Remove
          </button>
        </div>

        <p v-if="devices.length === 0" class="text-text-muted text-sm">
          No devices registered.
        </p>
      </div>

      <button
        @click="showEnrollModal = true"
        class="self-start bg-gold text-vault-black text-sm font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity"
      >
        Add Device
      </button>
    </div>

    <TotpEnrollModal v-if="showEnrollModal" @done="onEnrolled" />

    <div
      v-if="pendingDelete"
      class="fixed inset-0 z-40 flex items-center justify-center bg-black/60"
    >
      <div
        class="bg-steel-panel border border-border rounded-xl p-6 w-80 flex flex-col gap-4"
      >
        <p class="text-text-primary text-sm">
          Remove
          <span class="font-mono text-gold">{{ pendingDelete.label }}</span>
          ? You won't be able to unlock with it anymore.
        </p>
        <div class="flex gap-3 justify-end">
          <button
            @click="pendingDelete = null"
            class="text-text-muted text-sm hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            @click="removeDevice"
            class="bg-danger text-white text-sm px-4 py-2 rounded-lg hover:opacity-90"
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { RouterLink } from "vue-router";
import api from "../services/api";
import { useToastStore } from "../stores/toast";
import TotpEnrollModal from "../components/TotpEnrollModal.vue";
import { ArrowLeft } from "lucide-vue-next";

const toast = useToastStore();
const devices = ref([]);
const loading = ref(true);
const showEnrollModal = ref(false);
const pendingDelete = ref(null);

async function loadDevices() {
  loading.value = true;
  try {
    const res = await api.get("/auth/totp/devices");
    devices.value = res.data;
  } catch {
    toast.show("Failed to load devices.", "error");
  } finally {
    loading.value = false;
  }
}

async function removeDevice() {
  if (!pendingDelete.value) return;
  try {
    await api.delete(`/auth/totp/devices/${pendingDelete.value.id}`);
    toast.show("Device removed.", "success");
    pendingDelete.value = null;
    loadDevices();
  } catch (err) {
    toast.show(
      err.response?.data?.detail || "Failed to remove device.",
      "error",
    );
  }
}

function onEnrolled() {
  showEnrollModal.value = false;
  loadDevices();
}

function formatDate(value) {
  return new Date(value).toLocaleDateString();
}

onMounted(loadDevices);
</script>
