<template>
  <div
    class="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4"
  >
    <div
      class="bg-steel-elevated border border-border rounded-xl p-6 w-full max-w-md flex flex-col gap-5"
    >
      <div>
        <h2 class="text-text-primary font-medium mb-1">
          Set Up Two-Factor Authentication
        </h2>
        <p class="text-text-muted text-xs">
          {{
            step === "label"
              ? "Give this device a name so you can recognize it later."
              : "Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.), then enter the 6-digit code to confirm."
          }}
        </p>
      </div>

      <template v-if="step === 'label'">
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">
            Device Name <span class="text-danger">*</span>
          </label>
          <input
            v-model="label"
            type="text"
            maxlength="50"
            placeholder="e.g. User's Phone"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 placeholder:text-text-muted focus:outline-none focus:border-gold"
            @keyup.enter="startEnroll"
          />
        </div>
        <button
          @click="startEnroll"
          :disabled="starting || !label.trim()"
          class="bg-gold text-vault-black text-sm font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {{ starting ? "Starting..." : "Continue" }}
        </button>
      </template>

      <template v-else>
        <div class="flex justify-center">
          <img
            :src="`data:image/png;base64,${qrCode}`"
            alt="TOTP QR CODE"
            class="w-44 h-44 rounded-lg"
          />
        </div>
        <div class="flex flex-col gap-1">
          <p class="text-text-muted text-xs">
            Can't scan ? Enter this key manually:
          </p>
          <code
            class="text-gold text-xs font-mono bg-steel-panel border border-border rounded px-3 py-2 break-all"
          >
            {{ manualKey }}
          </code>
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">
            6-Digit Code <span class="text-danger">*</span>
          </label>
          <input
            v-model="code"
            type="text"
            inputmode="numeric"
            maxlength="6"
            placeholder="000000"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 font-mono tracking-widest placeholder:text-text-muted focus:outline-none focus:border-gold"
            @keyup.enter="verify"
          />
        </div>
        <button
          @click="verify"
          :disabled="submitting || code.length !== 6"
          class="bg-gold text-vault-black text-sm font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {{ submitting ? "Verifying..." : "Confirm & Activate" }}
        </button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import api from "../services/api";
import { useToastStore } from "../stores/toast";
import { useTotpStore } from "../stores/totp";

const emit = defineEmits(["done"]);
const toast = useToastStore();
const step = ref("label");
const label = ref("");
const starting = ref(false);
const qrCode = ref("");
const manualKey = ref("");
const deviceId = ref("");
const code = ref("");
const submitting = ref(false);
const totpStore = useTotpStore();

async function startEnroll() {
  if (!label.value.trim()) return;
  starting.value = true;
  try {
    const res = await api.post("/auth/totp/enroll", {
      label: label.value.trim(),
    });
    qrCode.value = res.data.qr_code;
    manualKey.value = res.data.secret;
    deviceId.value = res.data.device_id;
    step.value = "qr";
  } catch (err) {
    toast.show(
      err.response?.data?.detail || "Failed to start enrollment.",
      "error",
    );
  } finally {
    starting.value = false;
  }
}

async function verify() {
  if (code.value.length !== 6) return;
  submitting.value = true;
  try {
    const res = await api.post("/auth/totp/verify", {
      device_id: deviceId.value,
      code: code.value,
    });
    totpStore.unlock(res.data.expires_at);
    toast.show("Two-factor authentication activated.", "success");
    emit("done");
  } catch (err) {
    toast.show(
      err.response?.data?.detail || "Invalid code. Try again.",
      "error",
    );
    code.value = "";
  } finally {
    submitting.value = false;
  }
}
</script>
