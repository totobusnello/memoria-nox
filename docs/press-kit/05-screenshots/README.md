# Screenshots — F10 Observability Dashboards

Captured **2026-05-23 22:13 BRT** from live production VPS via Tailscale tunnel.
All dashboards are F10 Phase A–D, LIVE in prod since 2026-05-21.

> **Access note:** dashboards require Tailscale or SSH tunnel to VPS port 18802.
> Public access is not exposed. VPS: `root@187.77.234.79` / Tailscale peer `100.87.8.44`.

---

## Screenshots

### `f10-phase-a-health.png` — Prod Health Dashboard (F10 Phase A)

| Field | Value |
|---|---|
| URL | `http://nox-vps.tailnet:18802/observability/health.html` |
| Captured | 2026-05-23 22:13 BRT |
| Dimensions | 1280×800 |
| Size | 112 KB |

Live production health at capture: 69,032 chunks · 99.95% vec coverage · salience active ·
1.18 GB DB · 15,612 KG entities · 21,518 relations · schema invariants canary all-green.
Shows "Recent failed / crashed ops" panel (reindex failures on persona DBs are expected —
they use a separate nox-mem instance not connected to this canary).

---

### `f10-phase-b-evals.png` — Eval Dashboard (F10 Phase B)

| Field | Value |
|---|---|
| URL | `http://nox-vps.tailnet:18802/observability/evals.html` |
| Captured | 2026-05-23 22:13 BRT |
| Dimensions | 1280×800 |
| Size | 58 KB |

nDCG@10 and MRR over time for G-series ablation runs (G4–G10d). Scatter plots with
dashed gate-event markers. Source: `audits/data-G*/` JSON artifacts. Filter by DB source
after G6 fiasco (eval-DB sha + chunk-count drift). Shows 8 ablation runs tracked.

---

### `f10-phase-c-telemetry.png` — Telemetry Collector (F10 Phase C)

| Field | Value |
|---|---|
| URL | `http://nox-vps.tailnet:18802/observability/telemetry.html` |
| Captured | 2026-05-23 22:13 BRT |
| Dimensions | 1280×800 |
| Size | 45 KB |

Live search telemetry: avg 1,611 ms · p50 1,401 ms · p95 1,821 ms · p99 1,821 ms ·
semantic ratio 100% · 2 queries / 0 `/api/answer` calls in 24h window.
Latency-per-hour bar chart + requests-per-hour chart. Source: `search_telemetry` table.

---

### `f10-phase-d-shadow.png` — Shadow Tracker (F10 Phase D)

| Field | Value |
|---|---|
| URL | `http://nox-vps.tailnet:18802/observability/shadow.html` |
| Captured | 2026-05-23 22:13 BRT |
| Dimensions | 1280×800 |
| Size | 47 KB |

Shadow mode A/B tracker. At capture: no active shadow experiments (0 features tracked,
0 comparisons). Accurate — temporal spike v2 (PR #181) graduated from shadow to active
2026-05-21. Dashboard design shows win/regression/neutral delta bars per feature.
Ready for next shadow experiment.

---

## Planned additions (pre-launch 2026-06-03)

| File | Description | Status |
|---|---|---|
| `cli-demo.gif` | Full nox-mem CLI walkthrough: ingest → search → reflect | Planned 2026-05-30 |
| `architecture-diagram.png` | High-res arch diagram from ARCHITECTURE.md | Planned 2026-05-30 |

---

## Usage License

All screenshots in this directory are released under **CC BY 4.0**.
Attribute as "Toto Busnello, nox-mem" with a link to
`github.com/totobusnello/memoria-nox`.

Contact lab@nuvini.com.br for specific crops, resolution variants, or format requests.
