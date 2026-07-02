import { defineStore } from "pinia";
import { ref } from "vue";

export const useToastStore = defineStore("toast", () => {
  const message = ref("");
  const type = ref("success");
  const visible = ref(false);
  let timer = null;

  function show(msg, toastType = "success") {
    if (timer) clearTimeout(timer);
    message.value = msg;
    type.value = toastType;
    visible.value = true;
    timer = setTimeout(() => {
      visible.value = false;
    }, 3000);
  }
  function hide() {
    visible.value = false;
  }

  return { message, type, visible, show, hide };
});
