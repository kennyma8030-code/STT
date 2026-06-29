import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    strictPort: true, // fail loudly instead of silently moving ports (CORS depends on 5173)
    open: true, // auto-open the browser on `npm run dev`
  },
});
