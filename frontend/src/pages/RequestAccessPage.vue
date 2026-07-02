<template>
  <div class="min-h-screen flex items-center justify-center px-4">
    <div
      class="bg-steel-panel border border-border rounded-xl p-10 w-full max-w-md flex flex-col gap-6"
    >
      <div class="flex flex-col items-center gap-2">
        <div class="text-gold text-4xl font-mono font-medium tracking-widest">
          VAULT
        </div>
        <div class="text-text-muted text-sm">Request Access</div>
      </div>
      <div class="w-full h-px bg-border"></div>
      <div
        v-if="submitted"
        class="flex flex-col items-center gap-4 text-center"
      >
        <p class="text-text-primary text-sm">
          Your request has been submitted. You will be notified by email once
          approved
        </p>
        <RouterLink to="/login" class="text-gold text-sm hover:underline">
          Back to login
        </RouterLink>
      </div>
      <form v-else @submit.prevent="submit" class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs uppercase tracking-wider">
            Full Name
          </label>
          <input
            v-model="form.name"
            type="text"
            required
            placeholder="Your name"
            class="bg-steel-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm outline-none focus:border-gold"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs uppercase tracking-wider">
            Gmail Address
          </label>
          <input
            v-model="form.email"
            type="email"
            required
            placeholder="you@gmail.com"
            class="bg-steel-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm outline-none focus:border-gold"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs uppercase tracking-wider">
            Phone Number
          </label>
          <input
            v-model="form.phone"
            type="tel"
            required
            placeholder="+60123456789"
            class="bg-steel-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm outline-none focus:border-gold"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-text-muted text-xs uppercase tracking-wider">
            Reason for Access
          </label>
          <textarea
            v-model="form.reason"
            required
            rows="3"
            placeholder="Why do you need access?"
            class="bg-steel-base border border-border rounded-lg px-3 py-2 text-text-primary text-sm outline-none focus:border-gold resize-none"
          ></textarea>
        </div>
        <p v-if="errorMessage" class="text-danger text-sm text-center">
          {{ errorMessage }}
        </p>
        <button
          type="submit"
          :disabled="loading"
          class="bg-gold text-steel-base font-semibold rounded-lg py-2 text-sm hover:brightness-110 disabled:opacity-50 transition"
        >
          {{ loading ? "Submitting..." : "Submit Request" }}
        </button>
        <RouterLink
          to="/login"
          class="text-text-muted text-xs text-center hover:text-gold transition"
        >
          Back to login
        </RouterLink>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";

const form = ref({ name: "", email: "", phone: "", reason: "" });
const loading = ref(false);
const submitted = ref(false);
const errorMessage = ref("");

async function submit() {
  loading.value = true;
  errorMessage.value = "";
  try {
    const res = await fetch(
      `${import.meta.env.VITE_API_BASE_URL}/auth/request-access`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form.value),
      },
    );
    const data = await res.json();
    if (!res.ok) {
      errorMessage.value = data.detail || "Submission failed.";
      return;
    }
    submitted.value = true;
  } catch {
    errorMessage.value = "Could not reach the server. Try again.";
  } finally {
    loading.value = false;
  }
}
</script>
