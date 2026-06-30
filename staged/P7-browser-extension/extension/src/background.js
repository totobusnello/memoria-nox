/**
 * background.js — MV3 service worker for memoria-nox extension.
 *
 * Responsibilities (spec §2):
 *   - Single point of contact with nox-mem HTTP API (127.0.0.1:18802 by default).
 *   - Message hub between popup / content / omnibox and the API.
 *   - Heartbeat (chrome.alarms) for connectivity status.
 *   - Offline queue (chrome.storage.local) — drains on reconnect.
 *   - Context menu (right-click "Save selection").
 *   - Omnibox handler (`nx <query>` → /api/search suggestions).
 *
 * IMPORTANT — MV3 lifecycle:
 *   Service worker is terminated after ~30s idle. NEVER keep state in
 *   module-level variables. Always read from chrome.storage.local on each
 *   call. Heartbeat status is cached in storage too.
 */

import { redactAll } from "./lib/privacy/index.js";

// ════════════════════════════════════════════════════════════════════════════
//   Constants
// ════════════════════════════════════════════════════════════════════════════

const DEFAULT_SETTINGS = Object.freeze({
  api_url: "http://127.0.0.1:18802",
  auth_token: "",
  allowlist: [],
  auto_capture: false,
  inline_answer: false,
  omnibox_prefix: "nx",
});

const QUEUE_MAX = 100;
const HEARTBEAT_ALARM = "nox-heartbeat";
const HEARTBEAT_INTERVAL_MIN = 0.5; // 30s — minimum allowed by chrome.alarms

const STORAGE_KEYS = Object.freeze({
  SETTINGS: "settings",
  PENDING: "pending_chunks",
  RECENT: "recent_saves",
  STATUS: "api_status", // { online: bool, lastCheck: ts, chunks: number }
});

// ════════════════════════════════════════════════════════════════════════════
//   Storage helpers
// ════════════════════════════════════════════════════════════════════════════

/**
 * @returns {Promise<typeof DEFAULT_SETTINGS>}
 */
async function getSettings() {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
  return { ...DEFAULT_SETTINGS, ...(stored[STORAGE_KEYS.SETTINGS] || {}) };
}

async function getPending() {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.PENDING);
  return Array.isArray(stored[STORAGE_KEYS.PENDING])
    ? stored[STORAGE_KEYS.PENDING]
    : [];
}

async function setPending(arr) {
  // Cap at QUEUE_MAX (FIFO drop oldest).
  const trimmed = arr.length > QUEUE_MAX ? arr.slice(-QUEUE_MAX) : arr;
  await chrome.storage.local.set({ [STORAGE_KEYS.PENDING]: trimmed });
}

async function getRecent() {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.RECENT);
  return Array.isArray(stored[STORAGE_KEYS.RECENT])
    ? stored[STORAGE_KEYS.RECENT]
    : [];
}

async function pushRecent(entry) {
  const list = await getRecent();
  list.unshift(entry); // newest first
  await chrome.storage.local.set({
    [STORAGE_KEYS.RECENT]: list.slice(0, 5),
  });
}

async function setStatus(status) {
  await chrome.storage.local.set({ [STORAGE_KEYS.STATUS]: status });
}

async function getStatus() {
  const s = await chrome.storage.local.get(STORAGE_KEYS.STATUS);
  return s[STORAGE_KEYS.STATUS] || { online: false, lastCheck: 0, chunks: 0 };
}

// ════════════════════════════════════════════════════════════════════════════
//   HTTP helpers
// ════════════════════════════════════════════════════════════════════════════

/**
 * Build fetch options with Bearer auth if configured.
 */
async function buildRequestInit(method, body) {
  const settings = await getSettings();
  const headers = { "Content-Type": "application/json" };
  if (settings.auth_token) {
    headers["Authorization"] = `Bearer ${settings.auth_token}`;
  }
  /** @type {RequestInit} */
  const init = { method, headers, mode: "cors", credentials: "omit" };
  if (body !== undefined) init.body = JSON.stringify(body);
  return init;
}

/**
 * POST /api/ingest with redacted body.
 * Returns { ok, chunk_id?, error? }.
 */
async function apiIngest(chunk) {
  const settings = await getSettings();
  try {
    const init = await buildRequestInit("POST", chunk);
    const res = await fetch(`${settings.api_url}/api/ingest`, init);
    if (!res.ok) {
      return { ok: false, error: `HTTP ${res.status}` };
    }
    const data = await res.json().catch(() => ({}));
    return { ok: true, chunk_id: data.chunk_id ?? null };
  } catch (err) {
    return { ok: false, error: String(err.message || err) };
  }
}

/**
 * GET /api/search?q=<query>&limit=<n>
 */
async function apiSearch(query, limit = 5) {
  const settings = await getSettings();
  try {
    const init = await buildRequestInit("GET");
    const url = `${settings.api_url}/api/search?q=${encodeURIComponent(query)}&limit=${limit}`;
    const res = await fetch(url, init);
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = await res.json().catch(() => ({}));
    return { ok: true, results: Array.isArray(data.results) ? data.results : [] };
  } catch (err) {
    return { ok: false, error: String(err.message || err) };
  }
}

/**
 * GET /api/health — used by heartbeat.
 */
async function apiHealth() {
  const settings = await getSettings();
  try {
    const init = await buildRequestInit("GET");
    const res = await fetch(`${settings.api_url}/api/health`, init);
    if (!res.ok) return { ok: false };
    const data = await res.json().catch(() => ({}));
    return { ok: true, data };
  } catch {
    return { ok: false };
  }
}

// ════════════════════════════════════════════════════════════════════════════
//   Save chunk (with offline queue fallback)
// ════════════════════════════════════════════════════════════════════════════

/**
 * Apply A1+A1.1 redaction and POST to /api/ingest. On failure, enqueue
 * for later retry.
 *
 * @param {{ text: string, source_url?: string, source_title?: string }} payload
 * @returns {Promise<{ok: boolean, chunk_id?: number|null, queued?: boolean, redactions?: string[]}>}
 */
async function saveChunk(payload) {
  const { text, source_url, source_title } = payload;
  const redacted = redactAll(text || "");

  const chunk = {
    text: redacted.text,
    source_url: source_url || null,
    source_title: source_title || null,
    provenance: "browser_extension",
    captured_at: new Date().toISOString(),
    redaction: {
      count: redacted.redactionCount,
      kinds: redacted.kinds,
    },
  };

  const result = await apiIngest(chunk);
  if (result.ok) {
    await pushRecent({
      title: source_title || chunk.text.slice(0, 60),
      url: source_url || "",
      chunk_id: result.chunk_id,
      ts: chunk.captured_at,
    });
    return {
      ok: true,
      chunk_id: result.chunk_id ?? null,
      queued: false,
      redactions: redacted.kinds,
    };
  }

  // Failed — queue for retry.
  const queue = await getPending();
  queue.push(chunk);
  await setPending(queue);
  return { ok: false, queued: true, redactions: redacted.kinds };
}

/**
 * Drain offline queue. Called from heartbeat when API comes back online.
 */
async function drainQueue() {
  const queue = await getPending();
  if (queue.length === 0) return;
  const remaining = [];
  for (const chunk of queue) {
    const result = await apiIngest(chunk);
    if (!result.ok) {
      remaining.push(chunk);
      // Stop on first failure — API likely just went down again.
      break;
    }
  }
  if (remaining.length < queue.length) {
    // Keep remaining + anything left we didn't try yet.
    const idx = queue.length - remaining.length;
    const untried = queue.slice(idx);
    await setPending([...remaining, ...untried]);
  }
}

// ════════════════════════════════════════════════════════════════════════════
//   Heartbeat (chrome.alarms)
// ════════════════════════════════════════════════════════════════════════════

async function runHeartbeat() {
  const result = await apiHealth();
  const previous = await getStatus();
  const status = {
    online: result.ok,
    lastCheck: Date.now(),
    chunks: result.data?.totalChunks || result.data?.chunks || 0,
  };
  await setStatus(status);

  // Just came back online — drain queue.
  if (result.ok && !previous.online) {
    await drainQueue();
  }
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === HEARTBEAT_ALARM) {
    runHeartbeat().catch(() => {
      /* swallow — alarm will fire again */
    });
  }
});

async function ensureHeartbeatAlarm() {
  const existing = await chrome.alarms.get(HEARTBEAT_ALARM);
  if (!existing) {
    chrome.alarms.create(HEARTBEAT_ALARM, {
      periodInMinutes: HEARTBEAT_INTERVAL_MIN,
    });
  }
}

// ════════════════════════════════════════════════════════════════════════════
//   Context menu (right-click "Save selection")
// ════════════════════════════════════════════════════════════════════════════

const CTX_SAVE_SELECTION = "nox-save-selection";

async function setupContextMenus() {
  try {
    await chrome.contextMenus.removeAll();
  } catch {
    /* no-op */
  }
  // Allowlist is enforced at click-time, not here. The menu shows on all
  // pages; we silently drop if the active tab isn't in allowlist.
  chrome.contextMenus.create({
    id: CTX_SAVE_SELECTION,
    title: "Save selection to nox-mem",
    contexts: ["selection"],
  });
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== CTX_SAVE_SELECTION) return;
  if (!info.selectionText) return;
  if (!tab?.url) return;

  // Allowlist check.
  const settings = await getSettings();
  if (!isAllowed(tab.url, settings.allowlist)) {
    // Silently drop — content script not even injected.
    return;
  }

  await saveChunk({
    text: info.selectionText,
    source_url: tab.url,
    source_title: tab.title || "",
  });

  // Notify content script to show toast.
  try {
    await chrome.tabs.sendMessage(tab.id, { type: "TOAST", message: "Saved to nox-mem" });
  } catch {
    /* content script may not be injected — silent */
  }
});

// ════════════════════════════════════════════════════════════════════════════
//   Omnibox handler
// ════════════════════════════════════════════════════════════════════════════

chrome.omnibox.onInputChanged?.addListener(async (text, suggest) => {
  if (!text || text.length < 2) {
    suggest([]);
    return;
  }
  const result = await apiSearch(text, 5);
  if (!result.ok) {
    suggest([
      {
        content: text,
        description: `nox-mem offline — search "${escapeXml(text)}" when online`,
      },
    ]);
    return;
  }
  const suggestions = (result.results || []).slice(0, 5).map((r, i) => ({
    content: r.url || r.id || `result-${i}`,
    description: `${escapeXml(r.title || r.snippet || r.text || "result").slice(0, 100)} — <dim>chunk #${r.id || "?"}</dim>`,
  }));
  if (suggestions.length === 0) {
    suggestions.push({
      content: text,
      description: `No matches for "${escapeXml(text)}"`,
    });
  }
  suggest(suggestions);
});

chrome.omnibox.onInputEntered?.addListener(async (content, _disposition) => {
  // If content is a URL, open it. Otherwise open popup-like search results
  // page (in v0.1, just open the API search URL).
  if (/^https?:\/\//.test(content)) {
    await chrome.tabs.create({ url: content });
    return;
  }
  const settings = await getSettings();
  const url = `${settings.api_url}/api/search?q=${encodeURIComponent(content)}`;
  await chrome.tabs.create({ url });
});

// ════════════════════════════════════════════════════════════════════════════
//   Message hub (from popup / content / options)
// ════════════════════════════════════════════════════════════════════════════

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // All handlers are async — wrap and return true to keep channel alive.
  (async () => {
    try {
      switch (msg?.type) {
        case "SAVE_CHUNK": {
          // Re-check allowlist if sender is content-script.
          const settings = await getSettings();
          if (sender.tab?.url && !isAllowed(sender.tab.url, settings.allowlist)) {
            sendResponse({ ok: false, error: "domain_not_in_allowlist" });
            return;
          }
          const res = await saveChunk(msg.payload || {});
          sendResponse(res);
          return;
        }
        case "SEARCH": {
          const res = await apiSearch(msg.query, msg.limit || 5);
          sendResponse(res);
          return;
        }
        case "GET_STATUS": {
          const status = await getStatus();
          const pending = await getPending();
          sendResponse({ ...status, pending: pending.length });
          return;
        }
        case "GET_RECENT": {
          sendResponse({ recent: await getRecent() });
          return;
        }
        case "GET_SETTINGS": {
          sendResponse({ settings: await getSettings() });
          return;
        }
        case "SET_SETTINGS": {
          await chrome.storage.local.set({
            [STORAGE_KEYS.SETTINGS]: { ...DEFAULT_SETTINGS, ...msg.settings },
          });
          // Trigger immediate heartbeat with new settings.
          runHeartbeat().catch(() => {});
          sendResponse({ ok: true });
          return;
        }
        case "PING_API": {
          const res = await apiHealth();
          sendResponse(res);
          return;
        }
        case "CLEAR_QUEUE": {
          await setPending([]);
          sendResponse({ ok: true });
          return;
        }
        default:
          sendResponse({ ok: false, error: "unknown_message_type" });
      }
    } catch (err) {
      sendResponse({ ok: false, error: String(err.message || err) });
    }
  })();
  return true; // keep sendResponse channel open
});

// ════════════════════════════════════════════════════════════════════════════
//   Lifecycle hooks
// ════════════════════════════════════════════════════════════════════════════

chrome.runtime.onInstalled.addListener(async () => {
  // Seed defaults on first install if missing.
  const current = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
  if (!current[STORAGE_KEYS.SETTINGS]) {
    await chrome.storage.local.set({ [STORAGE_KEYS.SETTINGS]: DEFAULT_SETTINGS });
  }
  await setupContextMenus();
  await ensureHeartbeatAlarm();
  runHeartbeat().catch(() => {});
});

chrome.runtime.onStartup?.addListener(async () => {
  await setupContextMenus();
  await ensureHeartbeatAlarm();
  runHeartbeat().catch(() => {});
});

// ════════════════════════════════════════════════════════════════════════════
//   Utilities (exported for tests via dynamic import in __tests__)
// ════════════════════════════════════════════════════════════════════════════

/**
 * Check if a URL's hostname is in the allowlist.
 * Allowlist entries support exact hostname match. Wildcards are NOT supported
 * in v0.1 (avoid greedy mistakes; user adds each domain explicitly).
 *
 * @param {string} url
 * @param {string[]} allowlist
 * @returns {boolean}
 */
export function isAllowed(url, allowlist) {
  if (!Array.isArray(allowlist) || allowlist.length === 0) return false;
  try {
    const u = new URL(url);
    return allowlist.includes(u.hostname);
  } catch {
    return false;
  }
}

/**
 * Minimal XML escape for omnibox suggestions (which support inline markup).
 */
export function escapeXml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
