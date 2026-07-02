<template>
  <div class="min-h-screen flex items-center justify-center">
    <div
      class="bg-steel-panel border border-border rounded-xl p-10 w-full max-w-sm flex flex-col items-center gap-6"
    >
      <div class="flex flex-col items-center gap-2">
        <div class="text-gold text-4xl font-mono font-medium tracking-widest">
          VAULT
        </div>
        <div class="text-text-muted text-sm">Secure Credential Storage</div>
      </div>

      <div class="w-full h-px bg-border"></div>
      <div id="google-signin-btn" class="w-full flex justify-center"></div>
      <RouterLink
        to="/request-access"
        class="text-text-muted text-xs hover:text-gold transition-colors"
        >Don't have access? Request here</RouterLink
      >
      <p
        v-if="errorMessage && !needsAccessRequest"
        class="text-danger text-sm text-center"
      >
        {{ errorMessage }}
      </p>
      <div
        v-if="needsAccessRequest"
        class="flex flex-col items-center gap-2 text-center"
      >
        <p class="text-danger text-sm">You do not have access to this vault</p>
        <RouterLink
          to="/request-access"
          class="text-gold text-sm hover:underline"
        >
          Request access
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Router } from "lucide-vue-next";
import { ref, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";

const router = useRouter();
const errorMessage = ref("");
const needsAccessRequest = ref(false);

onMounted(() => {
  window.google.accounts.id.initialize({
    client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
    callback: handleCredentialResponse,
  });

  window.google.accounts.id.renderButton(
    document.getElementById("google-signin-btn"),
    { theme: "filled_black", size: "large", width: 200 },
  );
});

async function handleCredentialResponse(response) {
  try {
    const res = await fetch(
      `${import.meta.env.VITE_API_BASE_URL}/auth/google`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: response.credential }),
      },
    );

    const data = await res.json();

    if (!res.ok) {
      if (
        data.detail === "You do not have access. Please request access first."
      ) {
        needsAccessRequest.value = true;
      } else {
        errorMessage.value = data.detail || "Login failed.";
      }
      return;
    }

    localStorage.setItem("token", data.access_token);
    router.push("/vault");
  } catch {
    errorMessage.value = "Could not reach the server. Try again.";
  }
}
</script>
