<template>
  <RouterView />
  <ToastNotification />
  <TotpUnlockModal v-if="totpStore.visible" />
</template>

<script setup>
import ToastNotification from "./components/ToastNotification.vue";
import TotpUnlockModal from "./components/TotpUnlockModal.vue";
import { useTotpStore } from "./stores/totp.js";

const totpStore = useTotpStore();
</script>
