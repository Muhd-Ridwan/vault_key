<template>
  <div
    class="fixed inset-0 z-40 flex items-center justify-center bg-black/60"
    @click.self="$emit('close')"
  >
    <div
      class="bg-steel-elevated border border-border rounded-xl p-6 w-full max-w-md flex flex-col gap-4"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h2 class="text-text-primary font-medium">Edit Entry</h2>
          <span
            class="text-text-muted text-xs border border-border rounded px-2 py-0.5 font-mono"
            >{{ entry.entry_type }}</span
          >
        </div>
        <button
          @click="$emit('close')"
          class="text-text-muted hover:text-text-primary"
        >
          <X :size="18" />
        </button>
      </div>
      <div class="flex flex-col gap-3">
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs"
            >Title <span class="text-danger">*</span></label
          >
          <input
            v-model="form.title"
            type="text"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 placeholder:text-text-muted focus:outline-none focus:border-gold"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">Username</label>
          <input
            v-model="form.username"
            type="text"
            placeholder="Optional"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 placeholder:text-text-muted focus:outline-none focus:border-gold"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">URL</label>
          <input
            v-model="form.url"
            type="text"
            placeholder="Optional"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 placeholder:text-text-muted focus:outline-none focus:border-gold"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs">Description</label>
          <input
            v-model="form.description"
            type="text"
            placeholder="Optional"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 placeholder:text-text-muted focus:outline-none focus:border-gold"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs"
            >New Secret<span class="text-text-muted font-normal"
              >(leave blank to keep current)</span
            ></label
          >
          <div class="relative">
            <input
              v-model="form.secret"
              :type="showSecret ? 'text' : 'password'"
              placeholder="Leave blank to keep existing"
              class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 placeholder:text-text-muted focus:outline-none focus:border-gold font-mono w-full pr-10"
            />
            <button
              type="button"
              @click="showSecret = !showSecret"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-gold transition-colors"
            >
              <Eye v-if="!showSecret" :size="15" />
              <EyeOff v-else :size="15" />
            </button>
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs"
            >Notes<span class="text-text-muted font-normal"
              >(leave blank to keep current)</span
            ></label
          >
          <textarea
            v-model="form.notes"
            placeholder="Leave blank to keep existing"
            rows="3"
            class="bg-steel-panel border border-border text-text-primary text-sm rounded-lg px-3 py-2 placeholder:text-text-muted focus:outline-none focus:border-gold resize-none"
          ></textarea>
        </div>
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button
          @click="$emit('close')"
          class="text-text-muted text-sm px-4 py-2 hover:text-text-primary transition-colors"
        >
          Cancel
        </button>
        <button
          @click="submit"
          :disabled="submitting"
          class="bg-gold text-vault-black text-sm font-medium px-4 py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {{ submitting ? "Saving..." : "Save Changes" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Eye, EyeOff, X } from "lucide-vue-next";
import api from "../services/api";
import { useToastStore } from "../stores/toast";

const props = defineProps(["entry"]);
const emit = defineEmits(["close", "saved"]);
const toast = useToastStore();
const showSecret = ref(false);
const submitting = ref(false);

const form = ref({
  title: props.entry.title || "",
  username: props.entry.username || "",
  url: props.entry.url || "",
  description: props.entry.description || "",
  secret: "",
  notes: "",
});

async function submit() {
  if (!form.value.title.trim()) {
    toast.show("Title is required.", "error");
    return;
  }
  submitting.value = true;
  try {
    await api.put(`/vault/entries/${props.entry.id}`, {
      title: form.value.title.trim(),
      username: form.value.username.trim() || null,
      url: form.value.url.trim() || null,
      description: form.value.description.trim() || null,
      secret: form.value.secret.trim() || null,
      notes: form.value.notes.trim() || null,
    });
    toast.show("Entry updated.", "success");
    emit("saved");
  } catch (err) {
    const msg = err.response?.data?.detail || "Failed to update entry.";
    toast.show(msg, "error");
  } finally {
    submitting.value = false;
  }
}
</script>
