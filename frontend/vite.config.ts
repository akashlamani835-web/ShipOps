import { defineConfig, loadEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  const proxy: ProxyOptions = {
    target: env.SHIPOPS_API_TARGET || "http://127.0.0.1:8000",
    changeOrigin: true,
    ...(env.SHIPOPS_API_TOKEN
      ? {
          headers: {
            Authorization: `Bearer ${env.SHIPOPS_API_TOKEN}`,
          },
        }
      : {}),
  };

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": proxy,
        "/connectivity": proxy,
        "/health": proxy,
        "/live": proxy,
        "/ready": proxy,
      },
    },
  };
});