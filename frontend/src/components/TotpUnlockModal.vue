<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
    @click.self="totpStore.cancel()"
  >
    <div
      class="bg-steel-elevated border border-border rounded-xl p-6 w-full max-w-sm flex flex-col gap-4"
    >
      <div class="flex flex-col gap-1">
        <h2 class="text-text-primary font-medium">Verification Required</h2>
        <p class="text-text-muted text-sm">
          Your session needs re-verification. Enter your 6-digit authenticator
          code to continue.
        </p>
      </div>
      <input
        v-model="code"
        type="text"
        inputmode="numeric"
        maxlength="6"
        placeholder="000000"
        class="bg-steel-panel border border-border text-text-primary text-center text-xl font-mono tracking-widest rounded-lg px-3 py-3 focus:outline-none focus:border-gold"
        @keyup.enter="submit"
      />
      <p v-if="errorMessage" class="text-danger text-sm text-center">
        {{ errorMessage }}
      </p>
      <div class="flex gap-2">
        <button
          type="button"
          @click="totpStore.cancel()"
          class="flex-1 bg-steel-panel border border-border text-text-secondary text-sm font-medium px-4 py-2 rounded-lg cursor-pointer hover:bg-danger hover:text-white hover:border-danger transition-colors"
        >
          Cancel
        </button>
        <button
          @click="submit"
          :disabled="submitting || code.length !== 6"
          class="flex-1 bg-gold text-vault-black text-sm font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {{ submitting ? "Verifying..." : "Verify" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useTotpStore } from "../stores/totp.js";
import { useToastStore } from "../stores/toast.js";
import api from "../services/api.js";

const totpStore = useTotpStore();
const code = ref("");
const errorMessage = ref("");
const submitting = ref(false);

async function submit() {
  if (code.value.length !== 6) return;
  submitting.value = true;
  errorMessage.value = "";
  try {
    const res = await api.post("/auth/totp/unlock", { code: code.value });
    totpStore.unlock(res.data.expires_at);
  } catch {
    errorMessage.value = "Invalid code. Try again.";
  } finally {
    submitting.value = false;
  }
}
</script>
