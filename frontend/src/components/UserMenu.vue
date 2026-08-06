<template>
  <div class="relative">
    <button
      @click="open = !open"
      class="w-8 h-8 rounded-full bg-steel-panel border border-border flex items-center justify-center text-gold font-mono text-sm font-medium hover:border-gold transition-colors"
    >
      {{ initial }}
    </button>

    <div v-if="open" class="fixed inset-0 z-10" @click="open = false" />

    <div
      v-if="open"
      class="absolute right-0 top-full mt-2 w-52 bg-steel-elevated border border-border rounded-xl z-20 overflow-hidden"
    >
      <div class="px-4 py-3 border-b border-border">
        <p class="text-text-muted text-xs truncate">{{ email }}</p>
      </div>
      <div class="py-1">
        <RouterLink
          v-if="role === 'superadmin' && route.path !== '/admin'"
          to="/admin"
          @click="open = false"
          class="flex items-center px-4 py-2.5 text-sm text-text-muted hover:text-text-primary hover:bg-steel-panel transition-colors"
        >
          Admin panel
        </RouterLink>
        <RouterLink
          v-if="route.path === '/admin'"
          to="/vault"
          @click="open = false"
          class="flex items-center px-4 py-2.5 text-sm text-text-muted hover:text-text-primary hover:bg-steel-panel transition-colors"
        >
          Vault
        </RouterLink>
        <RouterLink
          v-if="route.path !== '/settings/totp'"
          to="/settings/totp"
          @click="open = false"
          class="flex items-center px-4 py-2.5 text-sm text-text-muted hover:text-text-primary hover:bg-steel-panel transition-colors"
        >
          MFA devices
        </RouterLink>
        <button
          @click="logout"
          class="w-full text-left flex items-center px-4 py-2.5 text-sm text-text-muted hover:text-danger hover:bg-steel-panel transition-colors"
        >
          Sign out
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter, useRoute, RouterLink } from "vue-router";

const props = defineProps({
  email: String,
  role: String,
});

const router = useRouter();
const route = useRoute();
const open = ref(false);

const initial = computed(() => props.email?.[0]?.toUpperCase() ?? "?");

function logout() {
  localStorage.removeItem("token");
  router.push("/login");
}
</script>
