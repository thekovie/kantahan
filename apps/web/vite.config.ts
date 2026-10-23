import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["brand/favicon.svg", "brand/apple-touch-icon.png", "theme-init.js"],
      manifest: {
        name: "Kantahan",
        short_name: "Kantahan",
        description: "Offline karaoke songbook: find any song number by title, artist or number.",
        theme_color: "#C4006D",
        background_color: "#1B1038",
        display: "standalone",
        orientation: "portrait",
        start_url: "/",
        scope: "/",
        lang: "en-PH",
        categories: ["music", "entertainment"],
        icons: [
          { src: "/brand/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/brand/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,woff2,webmanifest}"],
        globIgnores: ["**/brand/og.png", "**/catalog*/**"],
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/catalog/],
        runtimeCaching: [
          {
            // Catalog files change rarely and must work offline: serve the cached copy at once and
            // refresh it in the background.
            urlPattern: ({ url }) => url.pathname.startsWith("/catalog"),
            handler: "StaleWhileRevalidate",
            options: { cacheName: "kantahan-catalog", cacheableResponse: { statuses: [200] } },
          },
        ],
      },
    }),
  ],
  build: { target: "es2022" },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/main.tsx", "src/vite-env.d.ts"],
      reporter: ["text", "html"],
      thresholds: { lines: 80, statements: 80, functions: 80, branches: 70 },
    },
  },
});
