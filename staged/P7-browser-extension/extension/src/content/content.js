/**
 * content.js — Content script for memoria-nox.
 *
 * Runs ONLY on URLs matched by `content_scripts.matches` in manifest.json.
 * In v0.1, manifest restricts to `http://127.0.0.1/*` + `https://127.0.0.1/*`
 * to keep the script silent on the open web. The real allowlist is enforced
 * by the service worker — content menu items only act if the tab's hostname
 * is in `settings.allowlist`.
 *
 * Responsibilities (spec §2):
 *   - Listen for "TOAST" messages from background to show in-page toast.
 *   - Capture text selection and forward to background on demand.
 *
 * NOTE: The actual context menu lives in the background script (chrome.contextMenus).
 * Content script doesn't render the menu — it only renders the toast and reads
 * the selection.
 *
 * No external runtime deps. Plain DOM, no framework.
 */

(function () {
  "use strict";

  // ──────────────────────────────────────────────────────────────────────
  // Toast UI
  // ──────────────────────────────────────────────────────────────────────

  const TOAST_ID = "memoria-nox-toast";

  function showToast(message, durationMs = 2000) {
    let toast = document.getElementById(TOAST_ID);
    if (!toast) {
      toast = document.createElement("div");
      toast.id = TOAST_ID;
      Object.assign(toast.style, {
        position: "fixed",
        bottom: "16px",
        right: "16px",
        background: "#1F2937",
        color: "#10B981",
        padding: "10px 14px",
        borderRadius: "6px",
        fontFamily: "-apple-system, system-ui, sans-serif",
        fontSize: "13px",
        zIndex: "2147483647",
        boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
        pointerEvents: "none",
        opacity: "0",
        transition: "opacity 150ms ease-in-out",
        maxWidth: "320px",
      });
      document.documentElement.appendChild(toast);
    }
    toast.textContent = `✓ ${message}`;
    requestAnimationFrame(() => {
      toast.style.opacity = "1";
    });
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(() => {
      toast.style.opacity = "0";
    }, durationMs);
  }

  // ──────────────────────────────────────────────────────────────────────
  // Message listener
  // ──────────────────────────────────────────────────────────────────────

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type === "TOAST") {
      showToast(msg.message || "Saved");
      sendResponse({ ok: true });
      return false;
    }
    if (msg?.type === "GET_SELECTION") {
      const text = String(window.getSelection?.() || "");
      sendResponse({ text, title: document.title, url: location.href });
      return false;
    }
    return false;
  });
})();
