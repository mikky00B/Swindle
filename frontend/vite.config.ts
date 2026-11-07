import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy API calls so the dev app talks to the backend same-origin,
    // mirroring the production nginx /api reverse proxy. This keeps the
    // auth session cookie first-party no matter which host the page uses.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
