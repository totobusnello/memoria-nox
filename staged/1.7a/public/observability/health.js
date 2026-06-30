/* F10 Phase A · health.js — polling + render, no framework */

(() => {
  "use strict";

  const POLL_INTERVAL_MS = 30_000;
  const $ = (id) => document.getElementById(id);

  // ── Helpers ────────────────────────────────────────────────────────────────

  function fmtInt(n) {
    if (n == null || Number.isNaN(n)) return "—";
    return n.toLocaleString("en-US");
  }

  function fmtBytes(mb) {
    if (mb == null) return "—";
    if (mb >= 1024) return (mb / 1024).toFixed(2) + " GB";
    return mb.toFixed(1) + " MB";
  }

  function fmtDelta(n, suffix) {
    if (n == null) return "";
    if (n === 0) return "(no change)";
    const sign = n > 0 ? "+" : "";
    return `(${sign}${n}${suffix || ""} vs 24h ago)`;
  }

  function deltaClass(n) {
    if (n == null || n === 0) return "delta";
    return n > 0 ? "delta pos" : "delta neg";
  }

  function fmtAge(ms) {
    if (ms == null) return "—";
    const m = Math.floor(ms / 60000);
    if (m < 1) return "just now";
    if (m < 60) return `${m}min ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  }

  function fmtTimestamp(ms) {
    if (ms == null) return "—";
    const d = new Date(ms);
    return d.toISOString().replace("T", " ").substring(0, 19) + " UTC";
  }

  function fmtDuration(ms) {
    if (ms == null) return "—";
    if (ms < 1000) return ms + "ms";
    if (ms < 60_000) return (ms / 1000).toFixed(1) + "s";
    return Math.floor(ms / 60_000) + "m " + Math.floor((ms % 60_000) / 1000) + "s";
  }

  function setDot(el, level) {
    el.className = "dot";
    if (level === "green") el.classList.add("dot-green");
    else if (level === "yellow") el.classList.add("dot-yellow");
    else if (level === "red") el.classList.add("dot-red");
  }

  function setLiveDot(level) {
    const el = $("live-indicator");
    el.className = "dot";
    if (level === "ok") el.classList.add("dot-green");
    else if (level === "warn") el.classList.add("dot-yellow");
    else if (level === "err") el.classList.add("dot-red");
  }

  // ── Fetch + render ─────────────────────────────────────────────────────────

  async function getJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status} on ${url}`);
    return await r.json();
  }

  function renderHealth(data) {
    const c = data.current;
    $("chunks-total").textContent = fmtInt(c.chunks_total);
    const dc = data.delta_24h;

    $("chunks-delta").textContent = fmtDelta(dc.chunks);
    $("chunks-delta").className = deltaClass(dc.chunks);

    const vc = c.vector_coverage;
    const pct = vc.total === 0 ? 0 : (vc.embedded / vc.total) * 100;
    $("vec-ratio").textContent = pct.toFixed(2) + "%";
    $("vec-detail").textContent = ` (${fmtInt(vc.embedded)} / ${fmtInt(vc.total)}, ${fmtInt(vc.orphans)} orphans)`;
    setDot($("vec-indicator"), data.indicators.vector);

    $("salience-mode").textContent = c.salience_mode;

    $("db-size").textContent = fmtBytes(c.db_size_mb);
    $("db-size-delta").textContent = fmtDelta(dc.db_size_mb, " MB");
    $("db-size-delta").className = deltaClass(dc.db_size_mb);

    $("kg-entities").textContent = fmtInt(c.kg_entities);
    $("kg-entities-delta").textContent = fmtDelta(dc.kg_entities);
    $("kg-entities-delta").className = deltaClass(dc.kg_entities);

    $("kg-relations").textContent = fmtInt(c.kg_relations);
    $("kg-relations-delta").textContent = fmtDelta(dc.kg_relations);
    $("kg-relations-delta").className = deltaClass(dc.kg_relations);

    setDot($("canary-indicator"), data.indicators.canary);
    setDot($("ops-indicator"), data.indicators.recentOps);
  }

  function renderOps(rows) {
    const tbody = $("ops-tbody");
    if (!rows.length) {
      tbody.innerHTML = '<tr class="empty"><td colspan="5">no failed or crashed ops in last 24h</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((r) => {
      const statusCls = `status-${(r.status || "").toLowerCase()}`;
      return (
        `<tr>` +
          `<td>${escapeHtml(r.op_name)}</td>` +
          `<td class="${statusCls}">${escapeHtml(r.status)}</td>` +
          `<td>${escapeHtml(r.db_source)}</td>` +
          `<td title="${fmtTimestamp(r.started_at_ms)}">${fmtAge(Date.now() - r.started_at_ms)}</td>` +
          `<td>${fmtDuration(r.duration_ms)}</td>` +
        `</tr>`
      );
    }).join("");
  }

  function renderCanary(lines) {
    const ul = $("canary-list");
    if (!lines.length) {
      ul.innerHTML = '<li class="muted">no canary log entries (check VPS /var/log/nox-schema-invariants.log)</li>';
      return;
    }
    ul.innerHTML = lines.map((l) => {
      const cls = l.ok ? "ok" : "fail";
      return `<li class="${cls}">${escapeHtml(l.raw)}</li>`;
    }).join("");
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // ── Polling loop ───────────────────────────────────────────────────────────

  let pollTimer = null;
  let inflight = false;

  async function pollOnce() {
    if (inflight) return;
    inflight = true;
    setLiveDot("warn");
    try {
      const [health, ops, canary] = await Promise.all([
        getJson("/api/observability/health"),
        getJson("/api/observability/recent-ops?n=10"),
        getJson("/api/observability/canary-tail?n=3"),
      ]);
      renderHealth(health);
      renderOps(ops);
      renderCanary(canary);
      $("last-refresh").textContent = "refreshed " + fmtAge(0);
      setLiveDot("ok");
    } catch (err) {
      $("last-refresh").textContent = "error: " + String(err.message || err);
      setLiveDot("err");
    } finally {
      inflight = false;
    }
  }

  function startPolling() {
    pollOnce();
    pollTimer = setInterval(pollOnce, POLL_INTERVAL_MS);
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("poll-rate").textContent = POLL_INTERVAL_MS / 1000 + "s";
    $("refresh-btn").addEventListener("click", () => pollOnce());
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") pollOnce();
    });
    startPolling();
  });
})();
