import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "Splashh",
        short_name: "Splashh",
        description: "Manage your sports club",
        theme_color: "#0EA5E9",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
        shortcuts: [
          { name: "My bookings", url: "/book/bookings", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
          { name: "Browse facilities", url: "/book", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^\/v1\//,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              networkTimeoutSeconds: 10,
              expiration: { maxEntries: 100, maxAgeSeconds: 86400 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|webp|avif|gif)$/,
            handler: "CacheFirst",
            options: { cacheName: "image-cache", expiration: { maxEntries: 200, maxAgeSeconds: 2592000 } },
          },
        ],
      },
    }),
  ],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/v1": { target: "http://127.0.0.1:8765", changeOrigin: false } },
  },
  test: { environment: "happy-dom", globals: true, setupFiles: ["./test-setup.ts"] },
});
