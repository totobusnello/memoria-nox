/**
 * telemetry.js — F10 Phase C Phase 1 dashboard client
 *
 * Vanilla JS. No external dependencies.
 * Polls /api/observability/telemetry every 60s.
 * Renders:
 *   - Summary cards (aggregate metrics)
 *   - Latency bar chart (p50/p95/p99 per bucket)
 *   - Request count bar chart (per bucket)
 *   - Path breakdown table (by_path_used aggregate)
 *
 * Spec: specs/2026-05-01-F10-observability-dashboard.md §P2
 */

// ── Constants ──────────────────────────────────────────────────────────────────

const API_BASE = "/api/observability/telemetry";
const POLL_MS = 60_000; // 60s — telemetry changes less frequently than health

// Canvas colours matching CSS vars (inline since we can't read CSS vars on canvas)
const COLORS = {
  p50: "#58a6ff",
  p95: "#d29922",
  p99: "#f85149",
  count: "#388bfd44",
  countBorder: "#388bfd",
  text: "#8b949e",
  grid: "#21262d",
  axis: "#30363d",
};

// ── State ──────────────────────────────────────────────────────────────────────

let currentWindow = "24h";
let pollTimer = null;

// ── DOM refs ───────────────────────────────────────────────────────────────────

const statusDot = document.getElementById("status-dot");
const statusLabel = document.getElementById("status-label");
const windowSelect = document.getElementById("window-select");
const refreshBtn = document.getElementById("refresh-btn");
const footerTs = document.getElementById("footer-ts");

const latencyCanvas = document.getElementById("latency-chart");
const countCanvas = document.getElementById("count-chart");
const latencyCtx = latencyCanvas.getContext("2d");
const countCtx = countCanvas.getContext("2d");

// Card refs
const aggCount = document.getElementById("agg-count");
const aggAvg = document.getElementById("agg-avg");
const aggP50 = document.getElementById("agg-p50");
const aggP95 = document.getElementById("agg-p95");
const aggP99 = document.getElementById("agg-p99");
const aggSemantic = document.getElementById("agg-semantic");
const aggPaths = document.getElementById("agg-paths");

const pathTableBody = document.querySelector("#path-table tbody");

// ── Fetch + render ─────────────────────────────────────────────────────────────

async function fetchAndRender() {
  setStatus("polling…", "unknown");
  try {
    const url = `${API_BASE}?window=${encodeURIComponent(currentWindow)}&bucket=1h`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    render(data);
    setStatus("live", "ok");
  } catch (e) {
    setStatus(`error: ${e.message}`, "err");
  }
}

function render(data) {
  renderCards(data.aggregate);
  renderLatencyChart(data.buckets);
  renderCountChart(data.buckets);
  renderPathTable(data.buckets, data.aggregate);
  footerTs.textContent = `generated at ${new Date(data.generated_at_ms).toISOString()} · window=${data.window.hours}h`;
}

// ── Cards ──────────────────────────────────────────────────────────────────────

function renderCards(agg) {
  aggCount.textContent = agg.count.toLocaleString();
  aggAvg.textContent = agg.avg_latency_ms !== null ? `${agg.avg_latency_ms} ms` : "—";
  aggP50.textContent = agg.p50_ms !== null ? `${agg.p50_ms} ms` : "—";
  aggP95.textContent = agg.p95_ms !== null ? `${agg.p95_ms} ms` : "—";
  aggP99.textContent = agg.p99_ms !== null ? `${agg.p99_ms} ms` : "—";
  aggSemantic.textContent = agg.semantic_ratio !== null
    ? `${Math.round(agg.semantic_ratio * 100)}%`
    : "—";
  aggPaths.textContent = `${agg.by_path.search} / ${agg.by_path.answer}`;
}

// ── Latency chart ──────────────────────────────────────────────────────────────

function renderLatencyChart(buckets) {
  const ctx = latencyCtx;
  const W = latencyCanvas.width;
  const H = latencyCanvas.height;
  const PAD = { top: 16, right: 20, bottom: 40, left: 60 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  ctx.clearRect(0, 0, W, H);

  if (!buckets || buckets.length === 0) {
    drawEmpty(ctx, W, H, "No data");
    return;
  }

  const maxLatency = Math.max(
    ...buckets.map(b => b.p99_ms ?? 0),
    100, // floor
  );
  const yMax = Math.ceil(maxLatency * 1.15 / 100) * 100; // round up to nice value

  const barWidth = plotW / buckets.length;

  // Grid lines (5 horizontal)
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  ctx.fillStyle = COLORS.text;
  ctx.font = "10px monospace";
  ctx.textAlign = "right";
  for (let i = 0; i <= 4; i++) {
    const val = (yMax / 4) * i;
    const y = PAD.top + plotH - (val / yMax) * plotH;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(PAD.left + plotW, y);
    ctx.stroke();
    ctx.fillText(Math.round(val) + "ms", PAD.left - 6, y + 4);
  }

  // Bars: p99 (background), p95 (midground), p50 (foreground)
  buckets.forEach((b, i) => {
    const x = PAD.left + i * barWidth;
    const bw = Math.max(barWidth - 3, 1);

    function barH(val) {
      if (val === null) return 0;
      return Math.max(1, (val / yMax) * plotH);
    }

    // p99 bar
    if (b.p99_ms !== null) {
      const h = barH(b.p99_ms);
      ctx.fillStyle = COLORS.p99 + "55";
      ctx.fillRect(x + 1, PAD.top + plotH - h, bw, h);
    }

    // p95 bar
    if (b.p95_ms !== null) {
      const h = barH(b.p95_ms);
      ctx.fillStyle = COLORS.p95 + "88";
      ctx.fillRect(x + 2, PAD.top + plotH - h, bw - 2, h);
    }

    // p50 bar
    if (b.p50_ms !== null) {
      const h = barH(b.p50_ms);
      ctx.fillStyle = COLORS.p50;
      ctx.fillRect(x + 3, PAD.top + plotH - h, Math.max(bw - 4, 1), h);
    }

    // X label (hour, every Nth to avoid crowding)
    const step = Math.ceil(buckets.length / 12);
    if (i % step === 0) {
      ctx.fillStyle = COLORS.text;
      ctx.font = "9px monospace";
      ctx.textAlign = "center";
      const label = bucketHourLabel(b.label);
      ctx.fillText(label, x + barWidth / 2, PAD.top + plotH + 14);
    }
  });

  // Axis
  ctx.strokeStyle = COLORS.axis;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD.left, PAD.top);
  ctx.lineTo(PAD.left, PAD.top + plotH);
  ctx.lineTo(PAD.left + plotW, PAD.top + plotH);
  ctx.stroke();
}

// ── Count chart ────────────────────────────────────────────────────────────────

function renderCountChart(buckets) {
  const ctx = countCtx;
  const W = countCanvas.width;
  const H = countCanvas.height;
  const PAD = { top: 12, right: 20, bottom: 32, left: 60 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  ctx.clearRect(0, 0, W, H);

  if (!buckets || buckets.length === 0) {
    drawEmpty(ctx, W, H, "No data");
    return;
  }

  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const yMax = Math.ceil(maxCount * 1.15);

  const barWidth = plotW / buckets.length;

  // Grid
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  ctx.fillStyle = COLORS.text;
  ctx.font = "10px monospace";
  ctx.textAlign = "right";
  for (let i = 0; i <= 3; i++) {
    const val = (yMax / 3) * i;
    const y = PAD.top + plotH - (val / yMax) * plotH;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(PAD.left + plotW, y);
    ctx.stroke();
    ctx.fillText(Math.round(val), PAD.left - 6, y + 4);
  }

  // Bars
  buckets.forEach((b, i) => {
    const x = PAD.left + i * barWidth;
    const bw = Math.max(barWidth - 2, 1);
    const h = b.count > 0 ? Math.max(1, (b.count / yMax) * plotH) : 0;

    if (h > 0) {
      ctx.fillStyle = COLORS.count;
      ctx.strokeStyle = COLORS.countBorder;
      ctx.lineWidth = 1;
      ctx.fillRect(x + 1, PAD.top + plotH - h, bw, h);
      ctx.strokeRect(x + 1, PAD.top + plotH - h, bw, h);
    }

    // X labels
    const step = Math.ceil(buckets.length / 12);
    if (i % step === 0) {
      ctx.fillStyle = COLORS.text;
      ctx.font = "9px monospace";
      ctx.textAlign = "center";
      const label = bucketHourLabel(b.label);
      ctx.fillText(label, x + barWidth / 2, PAD.top + plotH + 13);
    }
  });

  // Axis
  ctx.strokeStyle = COLORS.axis;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD.left, PAD.top);
  ctx.lineTo(PAD.left, PAD.top + plotH);
  ctx.lineTo(PAD.left + plotW, PAD.top + plotH);
  ctx.stroke();
}

// ── Path breakdown table ───────────────────────────────────────────────────────

function renderPathTable(buckets, agg) {
  // Aggregate by_path_used across all buckets
  const totals = {};
  let totalCount = 0;
  for (const b of buckets) {
    for (const [path, cnt] of Object.entries(b.by_path_used || {})) {
      totals[path] = (totals[path] || 0) + cnt;
      totalCount += cnt;
    }
  }

  // Sort by count descending
  const entries = Object.entries(totals).sort(([, a], [, b]) => b - a);

  pathTableBody.innerHTML = "";

  if (entries.length === 0) {
    const row = pathTableBody.insertRow();
    row.className = "empty-row";
    const cell = row.insertCell();
    cell.colSpan = 3;
    cell.textContent = "No data in selected window";
    return;
  }

  for (const [path, count] of entries) {
    const row = pathTableBody.insertRow();
    const pct = totalCount > 0 ? ((count / totalCount) * 100).toFixed(1) : "0.0";
    row.insertCell().textContent = path;
    row.insertCell().textContent = count.toLocaleString();
    row.insertCell().textContent = `${pct}%`;
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function drawEmpty(ctx, W, H, msg) {
  ctx.fillStyle = COLORS.text;
  ctx.font = "12px monospace";
  ctx.textAlign = "center";
  ctx.fillText(msg, W / 2, H / 2);
}

/** Extract "HH:00" from "YYYY-MM-DDTHH:00Z" label */
function bucketHourLabel(label) {
  if (!label) return "?";
  const match = /T(\d{2}):00/.exec(label);
  return match ? `${match[1]}h` : label.slice(-6);
}

function setStatus(msg, level) {
  statusLabel.textContent = msg;
  statusDot.className = `dot dot-${level}`;
}

// ── Event handlers ─────────────────────────────────────────────────────────────

windowSelect.addEventListener("change", () => {
  currentWindow = windowSelect.value;
  stopPoll();
  fetchAndRender();
  startPoll();
});

refreshBtn.addEventListener("click", () => {
  stopPoll();
  fetchAndRender();
  startPoll();
});

// ── Poll management ────────────────────────────────────────────────────────────

function startPoll() {
  pollTimer = setInterval(fetchAndRender, POLL_MS);
}

function stopPoll() {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ── Boot ───────────────────────────────────────────────────────────────────────

fetchAndRender();
startPoll();
