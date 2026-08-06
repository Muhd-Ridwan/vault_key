import { defineStore } from "pinia";
import { ref } from "vue";

export const useTotpStore = defineStore("totp", () => {
  const visible = ref(false);
  const unlockExpiresAt = ref(null);
  let resolveFn = null;
  let rejectFn = null;

  function prompt() {
    visible.value = true;
    return new Promise((resolve, reject) => {
      resolveFn = resolve;
      rejectFn = reject;
    });
  }

  function unlock(expiresAt) {
    visible.value = false;
    unlockExpiresAt.value = expiresAt;
    resolveFn?.();
    resolveFn = rejectFn = null;
  }

  function cancel() {
    visible.value = false;
    rejectFn?.(new Error("totp_cancelled"));
    resolveFn = rejectFn = null;
  }

  return { visible, unlockExpiresAt, prompt, unlock, cancel };
});
