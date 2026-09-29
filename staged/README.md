# `staged/` — Implementation patch sets

This directory holds the **staged implementation patches** that the paper
(`paper/paper-tecnico-nox-mem.md`) and the docs reference as *"Implementation:"*
pointers. Production code runs on the live deployment; each `staged/<id>/`
sub-tree is the reviewable patch set (usually under `edits/`) for one wave,
ablation, or feature, kept here so every claim in the paper is traceable to the
exact diff that produced it.

> These are **not** dead code or scratch. They are cited from the paper and from
> `docs/` and `audits/`. If you are reorganizing, update the references — do not
> delete.
>
> They are also **frozen snapshots, not shipped code**: nothing builds or runs
> from `staged/`. The engine people install is the `nox-mem` npm package
> ([github.com/totobusnello/nox-mem](https://github.com/totobusnello/nox-mem)),
> and fixes land there and in the production tree, not here. For that reason
> CodeQL skips this directory (`.github/codeql/codeql-config.yml`); its alerts
> here would describe patches as they were, not code anyone executes.

## Naming convention

| Prefix | Meaning | Examples |
|---|---|---|
| `1.6` … `1.8` | Version waves (early phases) | `staged/1.7a`, `staged/1.8` |
| `A*` | **Autonomy** pillar (privacy, encrypted export, provider abstraction) | `staged/A1.1`, `staged/A2`, `staged/A2-T3`, `staged/A3` |
| `P*` | **Product** pillar (answer primitive, temporal, SSE viewer, mobile, extension) | `staged/P1`, `staged/P3`, `staged/P5`, `staged/P6-mobile`, `staged/P7-browser-extension` |
| `L*` | **Lab** / retrieval research | `staged/L2`, `staged/L3`, `staged/L4` |
| `G4` … `G17` | Ablation **generations** (the G3→G10d boost-stack trajectory + Wave G/J fixes) | `staged/G5`, `staged/G10`, `staged/G11-G17` |
| *named* | Standalone features / fixes | `staged/cors`, `staged/graphify-ingest`, `staged/migrations`, `staged/observability`, `staged/prometheus`, `staged/privacy`, `staged/temporal-spike`, `staged/reindex-emergency`, `staged/watcher-healthcheck-fix`, `staged/wire-up`, `staged/wire-up-adapters` |

## How to read a patch set

Most sub-trees follow `staged/<id>/edits/<path-mirroring-prod>` — the files are
laid out as they land in the production tree, so a diff against the deployed
source is direct. See the paper's `§5`–`§6` and `docs/` for which `staged/<id>`
backs each result.
