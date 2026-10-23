import { defineConfig, devices } from "@playwright/test";

// Runs against the production build, because the service worker only exists there.
// Uses the installed Chrome so no browser download is needed.
export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  reporter: "list",
  use: { baseURL: "http://localhost:4173", trace: "retain-on-failure" },
  webServer: {
    command: "npm run build && npm run preview",
    url: "http://localhost:4173",
    reuseExistingServer: true,
    timeout: 180_000,
  },
  projects: [
    { name: "mobile", use: { ...devices["Pixel 7"], channel: "chrome" } },
    { name: "desktop", use: { viewport: { width: 1440, height: 900 }, channel: "chrome" } },
  ],
});
