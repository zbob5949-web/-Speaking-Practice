import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/admin-ui/",
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5174, proxy: { "/api": "http://127.0.0.1:8000" } },
  build: {
    outDir: "../admin-dist",
    emptyOutDir: true,
    assetsDir: "assets",
  },
});
