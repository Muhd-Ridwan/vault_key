<template>
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-black/60">
    <div
      class="bg-steel-elevated border border-border rounded-xl p-6 w-full max-w-md flex flex-col gap-5"
    >
      <div>
        <h2 class="text-text-primary font-medium mb-1">
          Set Up Two-Factor Authentication
        </h2>
        <p class="text-text-muted text-xs">
          Scan the QR code with your authenticator app (Google Authenticator,
          Authy, etc.), then enter the 6-digit code to confirm.
        </p>
      </div>
      <div v-if="loading" class="text-text-muted text-sm text-center py-4">
        Generating QR code...
      </div>
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
import { ref, onMounted } from "vue";
import api from "../services/api";
import { useToastStore } from "../stores/toast";
import { useTotpStore } from "../stores/totp";

const emit = defineEmits(["done"]);
const toast = useToastStore();
const loading = ref(true);
const qrCode = ref("");
const code = ref("");
const submitting = ref(false);
const manualKey = ref("");
const totpStore = useTotpStore();

onMounted(async () => {
  try {
    const res = await api.post("/auth/totp/enroll");
    qrCode.value = res.data.qr_code;
    manualKey.value = res.data.secret;
  } catch (err) {
    if (err.response?.status === 409) {
      toast.show("Already enrolled. You can use the vault.", "success");
      emit("done");
      return;
    }
    toast.show(
      err.response?.data?.detail || "Failed to start enrollment.",
      "error",
    );
  } finally {
    loading.value = false;
  }
});

async function verify() {
  if (code.value.length !== 6) return;
  submitting.value = true;
  try {
    const res = await api.post("/auth/totp/verify", { code: code.value });
    totpStore.unlock(res.data.expires_at);
    toast.show("Two-factor authentication activated.", "success");
    emit("done");
  } catch (err) {
    if (err.response?.status === 409) {
      toast.show("Already enrolled. You can now use the vault.", "success");
      emit("done");
      return;
    }
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
