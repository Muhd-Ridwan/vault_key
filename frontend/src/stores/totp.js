import { defineStore } from "pinia";
import { ref } from "vue";

export const useTotpStore = defineStore("totp", () => {
  const visible = ref(false);
  const unlockExpiresAt = ref(null);
  let resolveFn = null;

  function prompt() {
    visible.value = true;
    return new Promise((resolve) => {
      resolveFn = resolve;
    });
  }

  function unlock(expiresAt) {
    visible.value = false;
    unlockExpiresAt.value = expiresAt;
    if (resolveFn) resolveFn();
  }

  return { visible, unlockExpiresAt, prompt, unlock };
});
