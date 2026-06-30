/* F10 Phase B · evals.js — eval dashboard, vanilla JS + Chart.js */

(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  // Deterministic palette — 12 perceptually-distinct hues (Okabe-Ito-ish + extras).
  const PALETTE = [
    "#4ea1ff", "#4cc38a", "#e2b341", "#ef4d4d",
    "#9c6ade", "#ff8c42", "#26c1c3", "#d65db1",
    "#a3d977", "#6f78d4", "#c97064", "#7a8395",
  ];

  let cachedRows = [];
  let chartNdcg = null;
  let chartMrr = null;

  // ── Helpers ────────────────────────────────────────────────────────────────

  function fmtFloat(n, digits) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toFixed(digits ?? 4);
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

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function colorFor(idx) {
    return PALETTE[idx % PALETTE.length];
  }

  async function getJson(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status} on ${url}`);
    return await r.json();
  }

  // ── Data preparation ───────────────────────────────────────────────────────

  /**
   * Group rows by config_id into series suitable for Chart.js:
   *   [{ label, data: [{ x: ranAtMs, y: ndcg }, ...] }, ...]
   * `metric` selects the field name on the row.
   */
  function buildSeries(rows, metric) {
    const byConfig = new Map();
    for (const r of rows) {
      const y = r[metric];
      if (y == null) continue;
      if (!byConfig.has(r.config_id)) byConfig.set(r.config_id, []);
      byConfig.get(r.config_id).push({ x: r.ran_at_ms, y, run_id: r.run_id, annotations: r.annotations });
    }
    const labels = Array.from(byConfig.keys()).sort();
    return labels.map((label, i) => ({
      label,
      data: byConfig.get(label).sort((a, b) => a.x - b.x),
      borderColor: colorFor(i),
      backgroundColor: colorFor(i),
      pointRadius: 4,
      pointHoverRadius: 6,
      borderWidth: 2,
      tension: 0,
      spanGaps: true,
    }));
  }

  /**
   * Returns Chart.js plugin that paints vertical dashed lines + labels at
   * annotation dates. Lines are drawn for every unique annotation that maps
   * to a UTC day present in the data's X-axis range.
   */
  function annotationPlugin(annotations) {
    return {
      id: "gate-annotations",
      afterDraw(chart) {
        if (!annotations.length) return;
        const { ctx, chartArea: ca, scales: { x } } = chart;
        ctx.save();
        ctx.strokeStyle = "#7a8395";
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.font = "10px ui-monospace, SF Mono, Menlo, Consolas, monospace";
        ctx.fillStyle = "#7a8395";

        // Stack labels vertically when several gates fall on close dates
        const placed = [];
        for (const a of annotations) {
          const ms = Date.parse(a.date + "T12:00:00Z"); // mid-day for nicer placement
          if (!Number.isFinite(ms)) continue;
          const px = x.getPixelForValue(ms);
          if (px < ca.left || px > ca.right) continue;
          ctx.beginPath();
          ctx.moveTo(px, ca.top);
          ctx.lineTo(px, ca.bottom);
          ctx.stroke();
          // Label — find a row index where no previous label overlaps within 80px
          let row = 0;
          while (placed.some((p) => p.row === row && Math.abs(p.px - px) < 90)) row++;
          placed.push({ row, px });
          const yLabel = ca.top + 12 + row * 12;
          ctx.fillText(a.label, px + 3, yLabel);
        }
        ctx.restore();
      },
    };
  }

  /**
   * Loads the annotations JSON sidecar.
   */
  async function loadAnnotations() {
    try {
      return await getJson("/observability/gate-annotations.json");
    } catch (err) {
      console.warn("[evals] annotations load failed", err);
      return [];
    }
  }

  // ── Rendering ──────────────────────────────────────────────────────────────

  function renderTable(rows) {
    const tbody = $("evals-tbody");
    $("inv-count").textContent = `· ${rows.length} rows`;
    $("row-count").textContent = `${rows.length} rows`;
    if (!rows.length) {
      tbody.innerHTML = '<tr class="empty"><td colspan="8">no rows for this filter</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((r) => {
      const ts = new Date(r.ran_at_ms).toISOString().replace("T", " ").substring(0, 19);
      const bucket = r.run_id.split("::")[0];
      const gates = (r.annotations || []).map((g) => `<span class="gate-pill">${escapeHtml(g)}</span>`).join("");
      return (
        `<tr>` +
          `<td title="${escapeHtml(r.ran_at)}">${escapeHtml(ts)}</td>` +
          `<td>${escapeHtml(bucket)}</td>` +
          `<td>${escapeHtml(r.config_id)}</td>` +
          `<td>${escapeHtml(r.db_source)}</td>` +
          `<td class="num">${fmtFloat(r.ndcg_at_10)}</td>` +
          `<td class="num">${fmtFloat(r.mrr)}</td>` +
          `<td class="num">${fmtFloat(r.recall_at_10)}</td>` +
          `<td>${gates}</td>` +
        `</tr>`
      );
    }).join("");
  }

  function destroyCharts() {
    if (chartNdcg) { chartNdcg.destroy(); chartNdcg = null; }
    if (chartMrr)  { chartMrr.destroy();  chartMrr  = null; }
  }

  function buildChart(canvasId, rows, metric, title, annotations) {
    const ctx = $(canvasId).getContext("2d");
    const datasets = buildSeries(rows, metric);
    const tickColor = "#7a8395";
    const gridColor = "rgba(122, 131, 149, 0.15)";
    return new Chart(ctx, {
      type: "line",
      data: { datasets },
      plugins: [annotationPlugin(annotations)],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        parsing: false,
        interaction: { mode: "nearest", intersect: false },
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#d7dce5", boxWidth: 10, boxHeight: 10, font: { size: 10 } },
          },
          tooltip: {
            callbacks: {
              title: (items) => {
                if (!items.length) return "";
                const t = items[0].parsed.x;
                return new Date(t).toISOString().replace("T", " ").substring(0, 19) + " UTC";
              },
              label: (ctx) => {
                const v = ctx.parsed.y;
                const r = ctx.raw;
                const gates = r.annotations && r.annotations.length
                  ? ` [${r.annotations.join(", ")}]`
                  : "";
                return `${ctx.dataset.label}: ${v.toFixed(4)}${gates}`;
              },
            },
          },
          title: { display: false, text: title },
        },
        scales: {
          x: {
            type: "time",
            time: { unit: "hour", tooltipFormat: "yyyy-MM-dd HH:mm" },
            ticks: { color: tickColor, font: { size: 10 } },
            grid: { color: gridColor },
          },
          y: {
            min: 0,
            max: 1,
            ticks: { color: tickColor, font: { size: 10 } },
            grid: { color: gridColor },
            title: { display: true, text: metric === "ndcg_at_10" ? "nDCG@10" : "MRR", color: tickColor, font: { size: 11 } },
          },
        },
      },
    });
  }

  /**
   * Chart.js 4 requires a date adapter (chartjs-adapter-date-fns or similar)
   * for `type: "time"` scales. To stay zero-extra-deps we register a minimal
   * adapter that delegates to native Date. Acceptable for ISO/ms-based axes.
   */
  function registerMinimalDateAdapter() {
    if (!window.Chart || !window.Chart._adapters || !window.Chart._adapters._date) return;
    window.Chart._adapters._date.override({
      _id: "minimal-date",
      formats: () => ({
        datetime: "yyyy-MM-dd HH:mm:ss",
        millisecond: "HH:mm:ss.SSS",
        second: "HH:mm:ss",
        minute: "HH:mm",
        hour: "yyyy-MM-dd HH:mm",
        day: "yyyy-MM-dd",
        week: "yyyy-MM-dd",
        month: "yyyy-MM",
        quarter: "yyyy-[q]Q",
        year: "yyyy",
      }),
      parse: (v) => {
        if (v == null) return null;
        if (typeof v === "number") return v;
        if (v instanceof Date) return v.getTime();
        const t = Date.parse(v);
        return Number.isNaN(t) ? null : t;
      },
      format: (ts) => new Date(ts).toISOString(),
      add: (ts, amount, unit) => {
        const d = new Date(ts);
        switch (unit) {
          case "millisecond": d.setUTCMilliseconds(d.getUTCMilliseconds() + amount); break;
          case "second":      d.setUTCSeconds(d.getUTCSeconds() + amount); break;
          case "minute":      d.setUTCMinutes(d.getUTCMinutes() + amount); break;
          case "hour":        d.setUTCHours(d.getUTCHours() + amount); break;
          case "day":         d.setUTCDate(d.getUTCDate() + amount); break;
          case "week":        d.setUTCDate(d.getUTCDate() + 7 * amount); break;
          case "month":       d.setUTCMonth(d.getUTCMonth() + amount); break;
          case "quarter":     d.setUTCMonth(d.getUTCMonth() + 3 * amount); break;
          case "year":        d.setUTCFullYear(d.getUTCFullYear() + amount); break;
        }
        return d.getTime();
      },
      diff: (max, min, unit) => {
        const ms = max - min;
        switch (unit) {
          case "millisecond": return ms;
          case "second":      return ms / 1000;
          case "minute":      return ms / 60000;
          case "hour":        return ms / 3600000;
          case "day":         return ms / 86400000;
          case "week":        return ms / (7 * 86400000);
          case "month":       return ms / (30 * 86400000);
          case "quarter":     return ms / (91 * 86400000);
          case "year":        return ms / (365 * 86400000);
        }
        return ms;
      },
      startOf: (ts, unit) => {
        const d = new Date(ts);
        switch (unit) {
          case "second":      d.setUTCMilliseconds(0); break;
          case "minute":      d.setUTCSeconds(0, 0); break;
          case "hour":        d.setUTCMinutes(0, 0, 0); break;
          case "day":         d.setUTCHours(0, 0, 0, 0); break;
          case "week":        d.setUTCDate(d.getUTCDate() - d.getUTCDay()); d.setUTCHours(0, 0, 0, 0); break;
          case "month":       d.setUTCDate(1); d.setUTCHours(0, 0, 0, 0); break;
          case "year":        d.setUTCMonth(0, 1); d.setUTCHours(0, 0, 0, 0); break;
        }
        return d.getTime();
      },
      endOf: (ts, unit) => ts,
    });
  }

  function populateDbFilter(rows) {
    const sel = $("db-filter");
    const present = new Set(rows.map((r) => r.db_source));
    // Always include the ones the team explicitly tracks
    ["entity-eval.db", "entity-eval-v2.db", "g5.db", "g9.db"].forEach((d) => present.add(d));
    const sorted = Array.from(present).sort();
    // Preserve current selection if possible
    const current = sel.value || "all";
    sel.innerHTML = '<option value="all">all</option>' + sorted.map((d) =>
      `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`
    ).join("");
    sel.value = sorted.includes(current) || current === "all" ? current : "all";
  }

  function applyFilter() {
    const selected = $("db-filter").value;
    const rows = selected === "all"
      ? cachedRows
      : cachedRows.filter((r) => r.db_source === selected);
    renderTable(rows);
    rebuildCharts(rows);
  }

  let cachedAnnotations = [];

  function rebuildCharts(rows) {
    destroyCharts();
    chartNdcg = buildChart("chart-ndcg", rows, "ndcg_at_10", "nDCG@10", cachedAnnotations);
    chartMrr  = buildChart("chart-mrr",  rows, "mrr",        "MRR",     cachedAnnotations);
  }

  // ── Boot ───────────────────────────────────────────────────────────────────

  async function refresh() {
    $("last-refresh").textContent = "loading…";
    try {
      const [rows, anns] = await Promise.all([
        getJson("/api/observability/evals?limit=500"),
        loadAnnotations(),
      ]);
      cachedRows = Array.isArray(rows) ? rows : [];
      cachedAnnotations = Array.isArray(anns) ? anns : [];
      populateDbFilter(cachedRows);
      applyFilter();
      $("last-refresh").textContent = "refreshed " + fmtAge(0);
    } catch (err) {
      $("last-refresh").textContent = "error: " + String(err.message || err);
      console.error("[evals] refresh failed", err);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!window.Chart) {
      $("last-refresh").textContent = "Chart.js failed to load (CDN blocked?)";
      return;
    }
    registerMinimalDateAdapter();
    $("refresh-btn").addEventListener("click", () => refresh());
    $("db-filter").addEventListener("change", () => applyFilter());
    refresh();
  });
})();
