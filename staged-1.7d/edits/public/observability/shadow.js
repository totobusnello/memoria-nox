/**
 * shadow.js — F10 Phase D shadow tracker dashboard client
 *
 * Vanilla JS. No external deps.
 * Polls /api/observability/shadow every 60s.
 * Renders:
 *   - Summary cards (features count, comparisons, wins, regressions, neutral)
 *   - Per-feature bar chart (mean delta % with win/regression colouring)
 *   - Per-feature stats table (count, win, regression, neutral, mean Δ%, std-dev)
 *   - Drill-down (when ?feature selected): latest 10 comparisons
 *
 * Spec: docs/ROADMAP.md F10 Phase D
 */

// ── Constants ─────────────────────────────────────────────────────────────────

const API_BASE = "/api/observability/shadow";
const POLL_MS = 60_000;

const COLORS = {
  win: "#3fb950",
  reg: "#f85149",
  zero: "#8b949e",
  text: "#8b949e",
  grid: "#21262d",
  axis: "#30363d",
};

// ── State ─────────────────────────────────────────────────────────────────────

let currentFeature = ""; // empty = all
let currentWindow = "24h";
let pollTimer = null;
let knownFeatures = new Set();

// ── DOM refs ──────────────────────────────────────────────────────────────────

const statusDot = document.getElementById("status-dot");
const statusLabel = document.getElementById("status-label");
const featureSelect = document.getElementById("feature-select");
const windowSelect = document.getElementById("window-select");
const refreshBtn = document.getElementById("refresh-btn");
const footerTs = document.getElementById("footer-ts");

const deltaCanvas = document.getElementById("delta-chart");
const deltaCtx = deltaCanvas.getContext("2d");

const aggFeatures = document.getElementById("agg-features");
const aggCount = document.getElementById("agg-count");
const aggWins = document.getElementById("agg-wins");
const aggRegressions = document.getElementById("agg-regressions");
const aggNeutral = document.getElementById("agg-neutral");

const featuresTableBody = document.querySelector("#features-table tbody");
const drilldownPanel = document.getElementById("drilldown-panel");
const drilldownTableBody = document.querySelector("#drilldown-table tbody");

// ── Fetch + render ────────────────────────────────────────────────────────────

async function fetchAndRender() {
  setStatus("polling…", "unknown");
  try {
    const qs = new URLSearchParams({ window: currentWindow });
    if (currentFeature) qs.set("feature", currentFeature);
    const resp = await fetch(`${API_BASE}?${qs.toString()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    render(data);
    setStatus("live", "ok");
  } catch (e) {
    setStatus(`error: ${e.message}`, "err");
  }
}

function render(data) {
  // Discover features from response so the dropdown stays fresh
  updateFeatureDropdown(data.features);

  renderCards(data.features);
  renderDeltaChart(data.features);
  renderFeaturesTable(data.features);
  renderDrilldown(data.latest_runs, currentFeature);

  footerTs.textContent = `generated at ${new Date(data.generated_at_ms).toISOString()} · window=${data.window.hours}h · feature=${currentFeature || "all"}`;
}

// ── Feature dropdown ──────────────────────────────────────────────────────────

function updateFeatureDropdown(features) {
  let dirty = false;
  for (const f of features) {
    if (!knownFeatures.has(f.feature)) {
      knownFeatures.add(f.feature);
      dirty = true;
    }
  }
  if (!dirty) return;

  // Rebuild the dropdown, preserving the current selection.
  const sel = featureSelect.value;
  featureSelect.innerHTML = "";
  const allOpt = document.createElement("option");
  allOpt.value = "";
  allOpt.textContent = "— all features —";
  featureSelect.appendChild(allOpt);
  for (const name of Array.from(knownFeatures).sort()) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    featureSelect.appendChild(opt);
  }
  featureSelect.value = sel;
}

// ── Cards ─────────────────────────────────────────────────────────────────────

function renderCards(features) {
  let count = 0;
  let wins = 0;
  let regressions = 0;
  let neutral = 0;
  for (const f of features) {
    count += f.count;
    wins += f.win_count;
    regressions += f.regression_count;
    neutral += f.neutral_count;
  }
  aggFeatures.textContent = features.length.toLocaleString();
  aggCount.textContent = count.toLocaleString();
  aggWins.textContent = wins.toLocaleString();
  aggRegressions.textContent = regressions.toLocaleString();
  aggNeutral.textContent = neutral.toLocaleString();
}

// ── Delta chart ───────────────────────────────────────────────────────────────

function renderDeltaChart(features) {
  const ctx = deltaCtx;
  const W = deltaCanvas.width;
  const H = deltaCanvas.height;
  const PAD = { top: 16, right: 24, bottom: 60, left: 70 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  ctx.clearRect(0, 0, W, H);

  // Filter to features that have any measured delta (mean !== null)
  const measured = features.filter((f) => f.mean_delta_pct !== null);
  if (measured.length === 0) {
    drawEmpty(ctx, W, H, "No measured deltas in window");
    return;
  }

  // y-range: symmetric around 0, padded by 15%
  const maxAbs = Math.max(...measured.map((f) => Math.abs(f.mean_delta_pct ?? 0)), 5);
  const yMax = Math.ceil((maxAbs * 1.15) / 5) * 5;
  const yMin = -yMax;

  const barWidth = plotW / measured.length;

  // Grid + axis labels
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  ctx.fillStyle = COLORS.text;
  ctx.font = "10px monospace";
  ctx.textAlign = "right";
  const ticks = 5;
  for (let i = 0; i <= ticks; i++) {
    const val = yMin + ((yMax - yMin) / ticks) * i;
    const y = PAD.top + plotH - ((val - yMin) / (yMax - yMin)) * plotH;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(PAD.left + plotW, y);
    ctx.stroke();
    ctx.fillText(`${val.toFixed(1)}%`, PAD.left - 6, y + 4);
  }

  // Zero line emphasised
  const yZero = PAD.top + plotH - ((0 - yMin) / (yMax - yMin)) * plotH;
  ctx.strokeStyle = COLORS.axis;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(PAD.left, yZero);
  ctx.lineTo(PAD.left + plotW, yZero);
  ctx.stroke();

  // Bars: one per feature, coloured by sign
  measured.forEach((f, i) => {
    const x = PAD.left + i * barWidth;
    const bw = Math.max(barWidth - 6, 4);
    const v = f.mean_delta_pct ?? 0;
    const barTop = v >= 0
      ? PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH
      : yZero;
    const barH = Math.abs(
      v >= 0
        ? yZero - barTop
        : PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH - yZero,
    );

    ctx.fillStyle = v > 0 ? COLORS.win : v < 0 ? COLORS.reg : COLORS.zero;
    ctx.fillRect(x + 3, barTop, bw, Math.max(barH, 1));

    // value label on top
    ctx.fillStyle = COLORS.text;
    ctx.font = "10px monospace";
    ctx.textAlign = "center";
    const lblY = v >= 0 ? barTop - 4 : barTop + barH + 12;
    ctx.fillText(`${v.toFixed(1)}%`, x + barWidth / 2, lblY);

    // x-label (feature name, rotated -45° if long)
    ctx.save();
    ctx.translate(x + barWidth / 2, PAD.top + plotH + 14);
    ctx.rotate(-Math.PI / 6);
    ctx.fillStyle = COLORS.text;
    ctx.font = "10px monospace";
    ctx.textAlign = "right";
    const truncated = f.feature.length > 16 ? f.feature.slice(0, 14) + "…" : f.feature;
    ctx.fillText(truncated, 0, 0);
    ctx.restore();
  });

  // Y-axis
  ctx.strokeStyle = COLORS.axis;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD.left, PAD.top);
  ctx.lineTo(PAD.left, PAD.top + plotH);
  ctx.stroke();
}

// ── Per-feature stats table ───────────────────────────────────────────────────

function renderFeaturesTable(features) {
  featuresTableBody.innerHTML = "";

  if (features.length === 0) {
    const row = featuresTableBody.insertRow();
    row.className = "empty-row";
    const cell = row.insertCell();
    cell.colSpan = 7;
    cell.textContent = "No features tracked in this window";
    return;
  }

  // Sort by absolute mean delta (interesting first), null-mean last
  const sorted = [...features].sort((a, b) => {
    if (a.mean_delta_pct === null && b.mean_delta_pct === null) return 0;
    if (a.mean_delta_pct === null) return 1;
    if (b.mean_delta_pct === null) return -1;
    return Math.abs(b.mean_delta_pct) - Math.abs(a.mean_delta_pct);
  });

  for (const f of sorted) {
    const row = featuresTableBody.insertRow();
    row.insertCell().textContent = f.feature;
    row.insertCell().textContent = f.count.toLocaleString();
    row.insertCell().textContent = f.win_count.toLocaleString();
    row.insertCell().textContent = f.regression_count.toLocaleString();
    row.insertCell().textContent = f.neutral_count.toLocaleString();

    const meanCell = row.insertCell();
    if (f.mean_delta_pct === null) {
      meanCell.textContent = "—";
      meanCell.className = "delta-zero";
    } else {
      meanCell.textContent = `${f.mean_delta_pct.toFixed(2)}%`;
      meanCell.className = f.mean_delta_pct > 0
        ? "delta-win"
        : f.mean_delta_pct < 0
        ? "delta-reg"
        : "delta-zero";
    }

    const stdCell = row.insertCell();
    stdCell.textContent = f.std_dev !== null ? f.std_dev.toFixed(2) : "—";
  }
}

// ── Drill-down ────────────────────────────────────────────────────────────────

function renderDrilldown(runs, feature) {
  if (!feature) {
    drilldownPanel.style.display = "none";
    return;
  }
  drilldownPanel.style.display = "";

  drilldownTableBody.innerHTML = "";
  if (!runs || runs.length === 0) {
    const row = drilldownTableBody.insertRow();
    row.className = "empty-row";
    const cell = row.insertCell();
    cell.colSpan = 6;
    cell.textContent = `No comparisons recorded for ${feature} in this window`;
    return;
  }

  for (const r of runs) {
    const row = drilldownTableBody.insertRow();
    row.insertCell().textContent = new Date(r.ts).toISOString().slice(11, 19);
    row.insertCell().textContent = r.query_hash;
    row.insertCell().textContent = r.baseline_value !== null ? r.baseline_value.toFixed(4) : "—";
    row.insertCell().textContent = r.shadow_value !== null ? r.shadow_value.toFixed(4) : "—";
    const deltaCell = row.insertCell();
    if (r.delta_pct === null) {
      deltaCell.textContent = "—";
      deltaCell.className = "delta-zero";
    } else {
      deltaCell.textContent = `${r.delta_pct.toFixed(2)}%`;
      deltaCell.className = r.delta_pct > 0
        ? "delta-win"
        : r.delta_pct < 0
        ? "delta-reg"
        : "delta-zero";
    }
    const verdictCell = row.insertCell();
    const v =
      r.delta_pct === null ? "neutral"
      : r.delta_pct > 0 ? "win"
      : r.delta_pct < 0 ? "regression"
      : "neutral";
    const pill = document.createElement("span");
    pill.className = `verdict-pill verdict-${v === "win" ? "win" : v === "regression" ? "reg" : "zero"}`;
    pill.textContent = v;
    verdictCell.appendChild(pill);
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function drawEmpty(ctx, W, H, msg) {
  ctx.fillStyle = COLORS.text;
  ctx.font = "12px monospace";
  ctx.textAlign = "center";
  ctx.fillText(msg, W / 2, H / 2);
}

function setStatus(msg, level) {
  statusLabel.textContent = msg;
  statusDot.className = `dot dot-${level}`;
}

// ── Event handlers ────────────────────────────────────────────────────────────

windowSelect.addEventListener("change", () => {
  currentWindow = windowSelect.value;
  stopPoll();
  fetchAndRender();
  startPoll();
});

featureSelect.addEventListener("change", () => {
  currentFeature = featureSelect.value;
  stopPoll();
  fetchAndRender();
  startPoll();
});

refreshBtn.addEventListener("click", () => {
  stopPoll();
  fetchAndRender();
  startPoll();
});

// ── Poll management ───────────────────────────────────────────────────────────

function startPoll() {
  pollTimer = setInterval(fetchAndRender, POLL_MS);
}

function stopPoll() {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────

fetchAndRender();
startPoll();
