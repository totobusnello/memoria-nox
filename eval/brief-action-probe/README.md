# 7b — brief action probe

Implements `specs/2026-10-14-7b-brief-action-probe-design.md` (plan: `plans/2026-10-14-7b-brief-action-probe-plan.md`).

Data never enters this repository: inputs, outputs, manifest, rubrics, authored requests and control
scenarios live on the VPS under `/root/medicoes/7b/`. Committed outputs are `frozen/params.json` and
`out/aggregates.json`, which hold no session content.

Tests: `python3 -m unittest discover -s tests -v` (stdlib only; Python ≥ 3.12).
Sync to the VPS: `scripts/sync_to_vps.sh` (needs `NOX_VPS`, e.g. `root@<host>`; the host is never written here).
