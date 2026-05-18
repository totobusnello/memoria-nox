/**
 * viewer.spec.ts — Visual regression tests for nox-mem P5 viewer.
 *
 * 11 test scenarios covering all key UI states.
 * Uses mock-sse-server.ts (started by playwright webServer config).
 *
 * Run:  npx playwright test
 * Update baselines: npx playwright test --update-snapshots
 */

import { test, expect, Page, BrowserContext } from "@playwright/test";

// ── Helpers ────────────────────────────────────────────────────────────────

const BASE = "http://127.0.0.1:18903";
const VIEWER_URL = `${BASE}/viewer/`;
const INJECT_URL = `${BASE}/api/test/inject`;
const RESET_URL = `${BASE}/api/test/reset`;

/** Reset mock server state before each test for isolation. */
async function resetServer(): Promise<void> {
  const resp = await fetch(RESET_URL, { method: "POST" });
  if (!resp.ok) throw new Error(`Reset failed: ${resp.status}`);
}

/** Inject one or multiple ViewerEvents. */
async function injectEvents(
  events: ViewerEvent | ViewerEvent[]
): Promise<void> {
  const resp = await fetch(INJECT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(events),
  });
  if (!resp.ok) throw new Error(`Inject failed: ${resp.status}`);
}

interface ViewerEvent {
  ts: string;
  type: "ingest" | "search" | "kg" | "crystallize" | "op_audit";
  source: string;
  summary: string;
  details?: Record<string, unknown>;
}

function makeEvent(
  type: ViewerEvent["type"],
  index = 0
): ViewerEvent {
  return {
    ts: `2026-05-18T10:0${index}:00.000Z`,
    type,
    source: `${type}-source`,
    summary: `${type} event #${index + 1}`,
    details: { index, mock: true },
  };
}

/**
 * Disable CSS transitions and animations to get stable screenshots.
 * Must be called after page load.
 */
async function freezeAnimations(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `,
  });
}

/** Navigate to viewer and wait for DOM ready (disconnected state, no SSE). */
async function openViewer(page: Page): Promise<void> {
  await page.goto(VIEWER_URL);
  // Wait for the event-log to be present in DOM
  await page.waitForSelector("#event-log", { state: "attached" });
  await freezeAnimations(page);
}

/** Wait for N events to appear in the event-log. */
async function waitForEvents(page: Page, count: number): Promise<void> {
  await page.waitForFunction(
    (n) => document.querySelectorAll("#event-log li").length >= n,
    count,
    { timeout: 5000 }
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────

test.describe("P5 viewer visual regression", () => {
  test.beforeEach(async () => {
    await resetServer();
  });

  // T1 — Empty state
  test("T1 empty state shows waiting message", async ({ page }) => {
    await openViewer(page);
    // No events injected — event-log should be empty
    const items = await page.locator("#event-log li").count();
    expect(items).toBe(0);
    await expect(page).toHaveScreenshot("T1-empty-state.png", {
      fullPage: false,
    });
  });

  // T2 — Single event rendered as event card
  test("T2 single ingest event shown as event card", async ({ page }) => {
    await openViewer(page);
    await injectEvents(makeEvent("ingest", 0));
    await waitForEvents(page, 1);
    await freezeAnimations(page);

    const li = page.locator("#event-log li").first();
    await expect(li).toBeVisible();
    await expect(li.locator(".badge")).toHaveText("ingest");
    await expect(li.locator(".summary")).toHaveText("ingest event #1");

    await expect(page).toHaveScreenshot("T2-single-event.png");
  });

  // T3 — Multiple events with different types
  test("T3 five events with different types all visible", async ({ page }) => {
    await openViewer(page);

    const events: ViewerEvent[] = [
      makeEvent("ingest", 0),
      makeEvent("search", 1),
      makeEvent("kg", 2),
      makeEvent("crystallize", 3),
      makeEvent("op_audit", 4),
    ];
    await injectEvents(events);
    await waitForEvents(page, 5);
    await freezeAnimations(page);

    // Assert all 5 events visible
    await expect(page.locator("#event-log li")).toHaveCount(5);

    // Assert badge color classes are present
    for (const ev of events) {
      const badge = page.locator(`#event-log li[data-type="${ev.type}"] .badge`);
      await expect(badge.first()).toBeVisible();
    }

    await expect(page).toHaveScreenshot("T3-five-events.png");
  });

  // T4 — Event detail expanded on click
  test("T4 click event expands JSON detail", async ({ page }) => {
    await openViewer(page);
    await injectEvents(makeEvent("search", 0));
    await waitForEvents(page, 1);
    await freezeAnimations(page);

    const li = page.locator("#event-log li").first();
    await li.click();

    // Wait for pre element containing JSON
    const pre = li.locator("pre");
    await expect(pre).toBeVisible();
    const text = await pre.textContent();
    expect(text).toContain('"type": "search"');
    expect(text).toContain('"mock": true');

    await expect(page).toHaveScreenshot("T4-event-detail-expanded.png");
  });

  // T5 — Filter checkboxes hide/show events
  test("T5 uncheck ingest filter hides ingest events", async ({ page }) => {
    await openViewer(page);

    await injectEvents([makeEvent("ingest", 0), makeEvent("search", 1)]);
    await waitForEvents(page, 2);
    await freezeAnimations(page);

    // Uncheck ingest
    const ingestCheckbox = page.locator(
      '#filters input[type="checkbox"][value="ingest"]'
    );
    await ingestCheckbox.uncheck();

    // ingest li should be hidden
    const ingestLi = page.locator('#event-log li[data-type="ingest"]');
    await expect(ingestLi).toBeHidden();

    // search li should still be visible
    const searchLi = page.locator('#event-log li[data-type="search"]');
    await expect(searchLi).toBeVisible();

    await expect(page).toHaveScreenshot("T5-filter-ingest-hidden.png");
  });

  // T6 — Dark mode (prefers-color-scheme: dark)
  test("T6 dark mode applies dark theme", async ({ browser }) => {
    const ctx: BrowserContext = await browser.newContext({
      colorScheme: "dark",
    });
    const page = await ctx.newPage();
    await resetServer();
    await page.goto(VIEWER_URL);
    await page.waitForSelector("#event-log", { state: "attached" });
    await freezeAnimations(page);

    // Background should be dark
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    // In dark mode: --bg: #0d1117
    expect(bgColor).not.toBe("rgb(250, 250, 250)"); // not light #fafafa

    await expect(page).toHaveScreenshot("T6-dark-mode.png");
    await ctx.close();
  });

  // T7 — Light mode (prefers-color-scheme: light)
  test("T7 light mode applies light theme", async ({ browser }) => {
    const ctx: BrowserContext = await browser.newContext({
      colorScheme: "light",
    });
    const page = await ctx.newPage();
    await resetServer();
    await page.goto(VIEWER_URL);
    await page.waitForSelector("#event-log", { state: "attached" });
    await freezeAnimations(page);

    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    // In light mode: --bg: #fafafa → rgb(250, 250, 250)
    expect(bgColor).toBe("rgb(250, 250, 250)");

    await expect(page).toHaveScreenshot("T7-light-mode.png");
    await ctx.close();
  });

  // T8 — High event volume: 100 events injected, oldest scrolls off
  test("T8 100 events injected: MAX_VISIBLE=100 enforced in DOM", async ({
    page,
  }) => {
    await openViewer(page);

    // Inject 110 events — only last 100 should remain in DOM
    const events: ViewerEvent[] = Array.from({ length: 110 }, (_, i) =>
      makeEvent(["ingest", "search", "kg", "crystallize", "op_audit"][i % 5] as ViewerEvent["type"], i)
    );

    // Inject in batches to avoid race conditions
    await injectEvents(events.slice(0, 55));
    await injectEvents(events.slice(55));

    // Wait for DOM to stabilize at MAX_VISIBLE
    await page.waitForFunction(
      () => {
        const lis = document.querySelectorAll("#event-log li");
        return lis.length <= 100;
      },
      { timeout: 8000 }
    );

    const count = await page.locator("#event-log li").count();
    expect(count).toBeLessThanOrEqual(100);
    // Should show the last 100 events
    expect(count).toBeGreaterThanOrEqual(95); // allow for timing

    await freezeAnimations(page);
    await expect(page).toHaveScreenshot("T8-high-volume-100-events.png");
  });

  // T9 — SSE disconnect shows reconnecting state
  test("T9 SSE disconnect shows reconnecting banner", async ({ page }) => {
    await openViewer(page);
    // Inject one event so connection was established
    await injectEvents(makeEvent("ingest", 0));
    await waitForEvents(page, 1);

    // Force disconnect all SSE clients
    await fetch(`${BASE}/api/test/disconnect`, { method: "POST" });

    // Wait for the reconnecting label to appear
    // The EventSource reconnects automatically; connection-dot should go "off"
    await page.waitForFunction(
      () => {
        const label = document.getElementById("connection-label");
        return label?.textContent?.includes("reconnect");
      },
      { timeout: 10000 }
    );

    await freezeAnimations(page);
    await expect(page).toHaveScreenshot("T9-sse-disconnect-reconnecting.png");
  });

  // T10 — Stats bar: events/sec + total today
  test("T10 stats bar shows correct total today count", async ({ page }) => {
    await openViewer(page);

    const events = [
      makeEvent("ingest", 0),
      makeEvent("search", 1),
      makeEvent("kg", 2),
    ];
    await injectEvents(events);
    await waitForEvents(page, 3);

    // stat-today should show 3
    await page.waitForFunction(
      () => document.getElementById("stat-today")?.textContent === "3",
      { timeout: 5000 }
    );
    const totalText = await page.locator("#stat-today").textContent();
    expect(totalText).toBe("3");

    await freezeAnimations(page);
    await expect(page).toHaveScreenshot("T10-stats-bar.png");
  });

  // T11 — Stats per type: breakdown by event type accurate
  test("T11 stats per type accurate for each event type", async ({ page }) => {
    await openViewer(page);

    const events: ViewerEvent[] = [
      makeEvent("ingest", 0),
      makeEvent("ingest", 1),
      makeEvent("search", 2),
      makeEvent("kg", 3),
      makeEvent("op_audit", 4),
    ];
    await injectEvents(events);
    await waitForEvents(page, 5);

    // Wait for stats to update
    await page.waitForFunction(
      () => document.getElementById("stat-ingest")?.textContent === "2",
      { timeout: 5000 }
    );

    const ingestCount = await page.locator("#stat-ingest").textContent();
    const searchCount = await page.locator("#stat-search").textContent();
    const kgCount = await page.locator("#stat-kg").textContent();
    const opAuditCount = await page.locator("#stat-op_audit").textContent();

    expect(ingestCount).toBe("2");
    expect(searchCount).toBe("1");
    expect(kgCount).toBe("1");
    expect(opAuditCount).toBe("1");

    await freezeAnimations(page);
    await expect(page).toHaveScreenshot("T11-stats-per-type.png");
  });
});

// ── SSE mock server control tests (T3 group, 8 tests) ─────────────────────

test.describe("mock-sse-server control", () => {
  test.beforeEach(async () => {
    await resetServer();
  });

  test("C1 GET /api/test/status returns zero clients after reset", async () => {
    const resp = await fetch(`${BASE}/api/test/status`);
    const data = await resp.json();
    expect(data.clients).toBe(0);
    expect(data.totalInjected).toBe(0);
  });

  test("C2 POST /api/test/inject single event increments totalInjected", async () => {
    await injectEvents(makeEvent("ingest", 0));
    const resp = await fetch(`${BASE}/api/test/status`);
    const data = await resp.json();
    expect(data.totalInjected).toBe(1);
  });

  test("C3 POST /api/test/inject array increments by array length", async () => {
    await injectEvents([makeEvent("ingest", 0), makeEvent("search", 1)]);
    const resp = await fetch(`${BASE}/api/test/status`);
    const data = await resp.json();
    expect(data.totalInjected).toBe(2);
  });

  test("C4 ringBuffer stores last injected events", async () => {
    await injectEvents([
      makeEvent("ingest", 0),
      makeEvent("search", 1),
      makeEvent("kg", 2),
    ]);
    const resp = await fetch(`${BASE}/api/test/status`);
    const data = await resp.json();
    expect(data.ringBuffer.length).toBe(3);
    expect(data.ringBuffer[2].type).toBe("kg");
  });

  test("C5 POST /api/test/reset clears all state", async () => {
    await injectEvents([makeEvent("ingest", 0), makeEvent("search", 1)]);
    await fetch(RESET_URL, { method: "POST" });
    const resp = await fetch(`${BASE}/api/test/status`);
    const data = await resp.json();
    expect(data.totalInjected).toBe(0);
    expect(data.ringBuffer.length).toBe(0);
  });

  test("C6 GET /viewer/ returns HTML with nox-mem viewer title", async () => {
    const resp = await fetch(`${BASE}/viewer/`);
    expect(resp.status).toBe(200);
    const html = await resp.text();
    expect(html).toContain("nox-mem viewer");
  });

  test("C7 GET /viewer/app.js returns JS content", async () => {
    const resp = await fetch(`${BASE}/viewer/app.js`);
    expect(resp.status).toBe(200);
    const js = await resp.text();
    expect(js).toContain("MAX_VISIBLE");
  });

  test("C8 GET /viewer/style.css returns CSS with accent color", async () => {
    const resp = await fetch(`${BASE}/viewer/style.css`);
    expect(resp.status).toBe(200);
    const css = await resp.text();
    expect(css).toContain("#00c896");
  });
});
