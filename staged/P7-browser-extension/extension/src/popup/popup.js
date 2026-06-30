/**
 * popup.js — Quick capture + search + status UI.
 *
 * Communicates with background via chrome.runtime.sendMessage. No direct
 * fetches to nox-mem — the popup is a thin client, all I/O via SW.
 */

import { scanRedactions } from "../lib/privacy/index.js";

// ────────────────────────────────────────────────────────────────────────
// DOM
// ────────────────────────────────────────────────────────────────────────

const $ = (sel) => document.querySelector(sel);

const dotEl = $("#status-dot");
const statusTextEl = $("#status-text");
const chunksCountEl = $("#chunks-count");
const pendingBadgeEl = $("#pending-badge");

const quickTextEl = $("#quick-text");
const btnSaveEl = $("#btn-save");
const redactHintEl = $("#redact-hint");

const searchInputEl = $("#search-input");
const searchResultsEl = $("#search-results");

const recentListEl = $("#recent-list");

// ────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────

function send(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message });
          return;
        }
        resolve(response || { ok: false, error: "no_response" });
      });
    } catch (err) {
      resolve({ ok: false, error: String(err.message || err) });
    }
  });
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function fmtTimeAgo(iso) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ────────────────────────────────────────────────────────────────────────
// Status & recent (initial paint)
// ────────────────────────────────────────────────────────────────────────

async function refreshStatus() {
  const res = await send({ type: "GET_STATUS" });
  const online = !!res?.online;
  dotEl.classList.toggle("online", online);
  dotEl.classList.toggle("offline", !online);
  statusTextEl.textContent = online ? "nox-mem online" : "nox-mem offline";
  chunksCountEl.textContent = res?.chunks
    ? `${(res.chunks / 1000).toFixed(1)}k chunks`
    : "";
  const pending = res?.pending || 0;
  pendingBadgeEl.textContent = `Pending: ${pending}`;
  pendingBadgeEl.classList.toggle("has-pending", pending > 0);
}

async function refreshRecent() {
  const res = await send({ type: "GET_RECENT" });
  const recent = res?.recent || [];
  if (recent.length === 0) {
    recentListEl.innerHTML = `<li class="empty">No captures yet.</li>`;
    return;
  }
  recentListEl.innerHTML = recent
    .slice(0, 5)
    .map(
      (r) => `
        <li>
          ${escapeHtml((r.title || "(untitled)").slice(0, 80))}
          <span class="meta">${escapeHtml(fmtTimeAgo(r.ts))}${
            r.chunk_id ? ` · #${escapeHtml(String(r.chunk_id))}` : ""
          }</span>
        </li>
      `,
    )
    .join("");
}

// ────────────────────────────────────────────────────────────────────────
// Quick capture
// ────────────────────────────────────────────────────────────────────────

function updateRedactHint() {
  const text = quickTextEl.value || "";
  if (!text.trim()) {
    redactHintEl.textContent = "";
    return;
  }
  const scan = scanRedactions(text);
  if (scan.totalMatches > 0) {
    redactHintEl.textContent = `Will redact ${scan.totalMatches} item${
      scan.totalMatches > 1 ? "s" : ""
    } (${scan.kinds.join(", ")})`;
  } else {
    redactHintEl.textContent = "No PII detected";
  }
}

quickTextEl.addEventListener("input", debounce(updateRedactHint, 200));

btnSaveEl.addEventListener("click", async () => {
  const text = quickTextEl.value.trim();
  if (!text) return;
  btnSaveEl.disabled = true;
  btnSaveEl.textContent = "Saving…";
  try {
    const res = await send({
      type: "SAVE_CHUNK",
      payload: {
        text,
        source_url: "",
        source_title: "popup_capture",
      },
    });
    if (res?.ok) {
      btnSaveEl.textContent = "Saved ✓";
      quickTextEl.value = "";
      redactHintEl.textContent = "";
      await Promise.all([refreshStatus(), refreshRecent()]);
    } else if (res?.queued) {
      btnSaveEl.textContent = "Queued (offline)";
      quickTextEl.value = "";
    } else {
      btnSaveEl.textContent = "Failed";
    }
  } finally {
    setTimeout(() => {
      btnSaveEl.disabled = false;
      btnSaveEl.textContent = "Save";
    }, 1200);
  }
});

// ────────────────────────────────────────────────────────────────────────
// Search
// ────────────────────────────────────────────────────────────────────────

const runSearch = debounce(async () => {
  const q = searchInputEl.value.trim();
  if (q.length < 2) {
    searchResultsEl.innerHTML = "";
    return;
  }
  const res = await send({ type: "SEARCH", query: q, limit: 5 });
  if (!res?.ok) {
    searchResultsEl.innerHTML = `<li class="empty">${escapeHtml(
      res?.error || "Search failed",
    )}</li>`;
    return;
  }
  const items = res.results || [];
  if (items.length === 0) {
    searchResultsEl.innerHTML = `<li class="empty">No results.</li>`;
    return;
  }
  searchResultsEl.innerHTML = items
    .slice(0, 5)
    .map((r) => {
      const title =
        r.title ||
        r.snippet ||
        (r.text ? r.text.slice(0, 80) : "(untitled)");
      const meta = [r.id ? `#${r.id}` : null, r.score ? `score ${r.score.toFixed(2)}` : null]
        .filter(Boolean)
        .join(" · ");
      return `<li>
        ${escapeHtml(title)}
        <span class="meta">${escapeHtml(meta)}</span>
      </li>`;
    })
    .join("");
}, 250);

searchInputEl.addEventListener("input", runSearch);

// ────────────────────────────────────────────────────────────────────────
// Settings link
// ────────────────────────────────────────────────────────────────────────

function openOptions(ev) {
  ev?.preventDefault?.();
  if (chrome.runtime.openOptionsPage) {
    chrome.runtime.openOptionsPage();
  } else {
    window.open(chrome.runtime.getURL("src/options/options.html"));
  }
}

$("#settings-link").addEventListener("click", openOptions);
$("#open-options").addEventListener("click", openOptions);

// ────────────────────────────────────────────────────────────────────────
// Boot
// ────────────────────────────────────────────────────────────────────────

(async function init() {
  await Promise.all([refreshStatus(), refreshRecent()]);
  // Poll status every 5s while popup is open.
  const interval = setInterval(refreshStatus, 5000);
  window.addEventListener("beforeunload", () => clearInterval(interval));
})();
