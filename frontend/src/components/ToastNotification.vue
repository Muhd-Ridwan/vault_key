<script setup>
import { CheckCircle, XCircle } from "lucide-vue-next";
import { useToastStore } from "../stores/toast.js";

const toast = useToastStore();
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>

<template>
  <Transition name="toast">
    <div
      v-if="toast.visible"
      @click="toast.hide()"
      class="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border text-sm cursor-pointer shadow-lg"
      :class="
        toast.type === 'success'
          ? 'bg-steel-elevated border-success text-success'
          : 'bg-steel-elevated border-danger text-danger'
      "
    >
      <CheckCircle v-if="toast.type === 'success'" :size="16" />
      <XCircle v-else :size="16" />
      {{ toast.message }}
    </div>
  </Transition>
</template>
