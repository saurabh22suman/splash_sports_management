import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: [["list"]],
  use: {
    trace: "on-first-retry",
  },
  projects: [
    { name: "admin", use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:5173" } },
    { name: "customer", use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:5174" } },
  ],
  webServer: [
    {
      command: "make -C apps/backend dev",
      url: "http://127.0.0.1:8765/healthz",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "pnpm --filter admin-pwa dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "pnpm --filter customer-pwa dev",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
