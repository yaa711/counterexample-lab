import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8765",
    headless: true,
    channel: process.env.LAB_BROWSER_CHANNEL || undefined,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "python3 -m backend.server",
    cwd: "..",
    url: "http://127.0.0.1:8765/api/tasks",
    reuseExistingServer: !process.env.CI,
    timeout: 15000,
  },
});
