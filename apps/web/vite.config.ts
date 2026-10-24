import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { VitePWA } from "vite-plugin-pwa";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

/**
 * Production builds put one tiny boot script straight into the page, so it needs no request of its own:
 * it sets the theme before first paint and, on a first visit only (nothing saved yet), starts downloading
 * the catalog manifest while the app's scripts are still loading. Only the app's first-load path takes that
 * download (see loader.ts), so no later check can ever be answered by it. A strict Content-Security-Policy
 * still allows the script: the build writes its SHA-256 to csp-script-hash.txt for the web server's policy
 * (see deploy/web/Dockerfile).
 */
function inlineBootScript(): Plugin {
  const theme = readFileSync(join(process.cwd(), "public", "theme-init.js"), "utf8");
  const base = (process.env.VITE_CATALOG_BASE ?? "/catalog").replace(/\/$/, "");
  const early = `
// First visit only: start the catalog manifest download now. The app takes it once (loader.ts).
(function () {
  try {
    if (localStorage.getItem("kantahan.lastCheck")) return;
    var early = fetch(${JSON.stringify(`${base}/manifest.json`)}, { headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("manifest");
      return r.arrayBuffer();
    });
    early.catch(function () {});
    window.__kantahanManifest = early;
  } catch (e) {
    /* storage blocked or no fetch: the app loads the manifest itself */
  }
})();
`;
  const source = theme + early;
  const hash = `'sha256-${createHash("sha256").update(source).digest("base64")}'`;
  return {
    name: "inline-boot-script",
    apply: "build",
    transformIndexHtml: {
      order: "pre",
      handler: (html) => html.replace('<script src="/theme-init.js"></script>', `<script>${source}</script>`),
    },
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "csp-script-hash.txt", source: hash });
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    inlineBootScript(),
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
        // No runtime caching for /catalog: the manifest must always come from the network (a stale
        // copy could hide a pause or a rollback) and saved songs live in IndexedDB, where a catalog
        // update replaces them in one transaction and removed ones are deleted.
      },
    }),
  ],
  server: { proxy: { "/api": "http://localhost:8000" } }, // the contact service, when running locally
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
