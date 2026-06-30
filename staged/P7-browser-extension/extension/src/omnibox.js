/**
 * omnibox.js — Stand-alone module that mirrors the omnibox handler in
 * background.js. Imported there directly (no global registration needed).
 *
 * Kept as a separate file per spec T6 so future iterations can split it
 * out (e.g. dedicated omnibox-only build target). For v0.1 it just exposes
 * the helpers used by background.js.
 */

/**
 * Format a search result row into a chrome.omnibox.SuggestResult.
 *
 * @param {{id?: string|number, title?: string, snippet?: string, text?: string, url?: string}} r
 * @param {number} idx
 * @returns {{content: string, description: string}}
 */
export function formatOmniboxSuggestion(r, idx) {
  const title = (r.title || r.snippet || r.text || "result")
    .replace(/\s+/g, " ")
    .slice(0, 100);
  const id = r.id ?? `result-${idx}`;
  const content = r.url || String(id);
  return {
    content,
    description: `${escapeXml(title)} — <dim>chunk #${escapeXml(String(id))}</dim>`,
  };
}

export function escapeXml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
