import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for nox-mem P5 viewer visual regression.
 *
 * Browsers: Chromium (primary) + Firefox + WebKit (secondary).
 * Viewports: desktop 1920×1080, laptop 1366×768, mobile 375×667.
 * Diff threshold: 0.1% pixels (configurable via NOX_VR_THRESHOLD env).
 */

const threshold = Number(process.env.NOX_VR_THRESHOLD ?? "0.001"); // 0.1%

export default defineConfig({
  testDir: "./src",
  testMatch: "**/*.spec.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
    ...(process.env.CI
      ? [["github"] as ["github"]]
      : []),
  ],

  // Global snapshot opts — override per test via expect().toMatchSnapshot({...})
  expect: {
    toMatchSnapshot: {
      maxDiffPixelRatio: threshold,
    },
    toHaveScreenshot: {
      maxDiffPixelRatio: threshold,
    },
  },

  use: {
    // Base URL for the mock SSE server (set by test fixture)
    baseURL: process.env.NOX_VR_BASE_URL ?? "http://127.0.0.1:18903",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
    // Deterministic: no animations, no transitions during screenshots
    // (we inject CSS in tests that need stable rendering)
  },

  snapshotDir: "./snapshots",
  // Snapshots are named: <test-file>/<test-name>-<browser>-<viewport>.png
  snapshotPathTemplate:
    "{snapshotDir}/{testFilePath}/{arg}-{projectName}-{platform}{ext}",

  projects: [
    // ── Desktop chromium (primary) ─────────────────────────────
    {
      name: "chromium-desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        colorScheme: "light",
      },
    },
    {
      name: "chromium-desktop-dark",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        colorScheme: "dark",
      },
    },
    // ── Laptop chromium ───────────────────────────────────────
    {
      name: "chromium-laptop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1366, height: 768 },
        colorScheme: "light",
      },
    },
    // ── Mobile chromium ───────────────────────────────────────
    {
      name: "chromium-mobile",
      use: {
        ...devices["Pixel 5"],
        viewport: { width: 375, height: 667 },
        colorScheme: "light",
      },
    },
    // ── Firefox (secondary) ───────────────────────────────────
    {
      name: "firefox-desktop",
      use: {
        ...devices["Desktop Firefox"],
        viewport: { width: 1920, height: 1080 },
        colorScheme: "light",
      },
    },
    // ── WebKit / Safari (secondary) ───────────────────────────
    {
      name: "webkit-desktop",
      use: {
        ...devices["Desktop Safari"],
        viewport: { width: 1920, height: 1080 },
        colorScheme: "light",
      },
    },
  ],

  webServer: {
    command:
      "npx ts-node --project tsconfig.json src/mock-sse-server.ts",
    port: 18903,
    timeout: 15_000,
    reuseExistingServer: !process.env.CI,
  },
});
