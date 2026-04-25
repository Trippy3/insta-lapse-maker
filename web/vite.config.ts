import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 開発時は /api を uvicorn (127.0.0.1:8765) へプロキシし、
// ビルド後は FastAPI が dist/ を StaticFiles として配信する。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
