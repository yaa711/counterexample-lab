import { defineConfig } from "@playwright/test";

const port = Number(process.env.LAB_TEST_PORT || 8765);

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    headless: true,
    channel: process.env.LAB_BROWSER_CHANNEL || undefined,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `python3 -m backend.server --port ${port}`,
    cwd: "..",
    url: `http://127.0.0.1:${port}/api/tasks`,
    reuseExistingServer: false,
    timeout: 15000,
  },
});
