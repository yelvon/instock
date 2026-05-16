import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  plugins: [vue()],
  base: "/instock/app/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "../vue-dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/ag-grid")) return "ag-grid";
          if (id.includes("node_modules/echarts")) return "echarts";
          if (id.includes("node_modules/lightweight-charts")) return "lw-charts";
          if (id.includes("node_modules/element-plus")) return "element-plus";
          if (id.includes("node_modules/@tanstack")) return "tanstack-query";
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/instock/api": {
        target: "http://127.0.0.1:9988",
        changeOrigin: true,
      },
      "/instock/api_data": {
        target: "http://127.0.0.1:9988",
        changeOrigin: true,
      },
      "/instock/control": {
        target: "http://127.0.0.1:9988",
        changeOrigin: true,
      },
    },
  },
});
