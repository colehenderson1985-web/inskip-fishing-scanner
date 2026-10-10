import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served from https://<user>.github.io/inskip-fishing-scanner/
export default defineConfig({
  plugins: [react()],
  base: process.env.SITE_BASE ?? "/inskip-fishing-scanner/",
  build: { outDir: "dist", sourcemap: false },
});
