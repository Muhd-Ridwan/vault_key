import axios from "axios";
import { useTotpStore } from "../stores/totp.js";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let totpStore = null;
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const requireTotp = error.response?.headers.get?.("x-require-totp");
    if (error.response?.status === 403 && requireTotp) {
      if (!totpStore) totpStore = useTotpStore();
      await totpStore.prompt();
      return api.request(error.config);
    }
    return Promise.reject(error);
  },
);
export default api;
