// nox-mem viewer — vanilla JS, no framework.
// Connects to /api/events/stream via EventSource. Default-redact policy
// means SearchEvent.query already arrives "<redacted>" unless server has
// NOX_VIEWER_SHOW_QUERY=1.

const MAX_VISIBLE = 100;
const STATS_REFRESH_MS = 1000;

const state = {
  filters: new Set(["ingest", "search", "kg", "crystallize", "op_audit"]),
  counts: { ingest: 0, search: 0, kg: 0, crystallize: 0, op_audit: 0 },
  totalToday: 0,
  events: [], // ring of last MAX_VISIBLE rendered entries
  recentTs: [], // for events/sec rolling window
  startOfDay: startOfDayMs(),
  droppedCount: 0,
  connected: false,
};

function startOfDayMs() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

function $(id) {
  return document.getElementById(id);
}

function fmtTime(iso) {
  // Show HH:MM:SS.mmm — local time
  const d = new Date(iso);
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  return (
    pad(d.getHours()) +
    ":" +
    pad(d.getMinutes()) +
    ":" +
    pad(d.getSeconds()) +
    "." +
    pad(d.getMilliseconds(), 3)
  );
}

function renderEvent(ev) {
  if (!state.filters.has(ev.type)) return;
  const li = document.createElement("li");
  li.dataset.type = ev.type;
  li.innerHTML =
    '<span class="ts"></span><span class="badge"></span><span class="summary"></span><span class="meta"></span>';
  li.querySelector(".ts").textContent = fmtTime(ev.ts);
  li.querySelector(".badge").textContent = ev.type;
  li.querySelector(".summary").textContent = ev.summary || "";
  const sourceLabel = ev.source || "";
  li.querySelector(".meta").textContent = sourceLabel;

  // Expand toggle: clone the event into a <pre> JSON on first click.
  li.addEventListener("click", () => {
    if (li.classList.contains("expanded")) {
      li.classList.remove("expanded");
      const pre = li.querySelector("pre");
      if (pre) pre.remove();
      return;
    }
    li.classList.add("expanded");
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(ev, null, 2);
    li.appendChild(pre);
  });

  const log = $("event-log");
  log.prepend(li);
  state.events.unshift(li);
  if (state.events.length > MAX_VISIBLE) {
    const old = state.events.pop();
    if (old && old.parentNode) old.parentNode.removeChild(old);
  }
}

function incrCounter(type) {
  if (state.counts[type] === undefined) state.counts[type] = 0;
  state.counts[type] += 1;
  state.totalToday += 1;
  const el = $("stat-" + type);
  if (el) {
    el.textContent = String(state.counts[type]);
    el.classList.remove("flash");
    void el.offsetWidth; // trigger reflow
    el.classList.add("flash");
  }
  $("stat-today").textContent = String(state.totalToday);
  state.recentTs.push(Date.now());
}

function refreshRate() {
  const now = Date.now();
  const cutoff = now - 10_000;
  state.recentTs = state.recentTs.filter((t) => t >= cutoff);
  const perSec = state.recentTs.length / 10;
  $("stat-rate").textContent = perSec.toFixed(1);
}

function setConnected(on) {
  state.connected = on;
  $("connection-dot").classList.toggle("on", on);
  $("connection-dot").classList.toggle("off", !on);
  $("connection-label").textContent = on ? "live" : "reconnecting…";
}

function bindFilters() {
  const fs = document.querySelectorAll('#filters input[type="checkbox"]');
  fs.forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) state.filters.add(cb.value);
      else state.filters.delete(cb.value);
      // Hide/show currently rendered rows in place.
      state.events.forEach((li) => {
        li.hidden = !state.filters.has(li.dataset.type);
      });
    });
  });
}

function connect() {
  const url = "/api/events/stream";
  const src = new EventSource(url);
  src.addEventListener("open", () => setConnected(true));
  src.addEventListener("error", () => setConnected(false));

  const handler = (ev) => {
    let payload;
    try {
      payload = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (!payload || typeof payload !== "object") return;
    renderEvent(payload);
    incrCounter(payload.type);
  };
  ["ingest", "search", "crystallize", "op_audit"].forEach((kind) =>
    src.addEventListener(kind, handler)
  );
  // kg events arrive as "kg.entity_created" / "kg.relation_created"
  src.addEventListener("kg.entity_created", handler);
  src.addEventListener("kg.relation_created", handler);
  // Fallback for any future kind:
  src.onmessage = handler;
}

function boot() {
  bindFilters();
  connect();
  setInterval(refreshRate, STATS_REFRESH_MS);
  // Reset midnight counters if user leaves the tab open.
  setInterval(() => {
    if (Date.now() - state.startOfDay > 86_400_000) {
      state.startOfDay = startOfDayMs();
      state.totalToday = 0;
      Object.keys(state.counts).forEach((k) => {
        state.counts[k] = 0;
        const el = $("stat-" + k);
        if (el) el.textContent = "0";
      });
      $("stat-today").textContent = "0";
    }
  }, 60_000);
}

document.addEventListener("DOMContentLoaded", boot);
