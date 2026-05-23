# project-sat-2026-05-24-final-closure

**Date:** 2026-05-24 ~22h30 BRT
**Type:** project milestone closure

## Wave 1–13 cumulative summary

| Metric | Value |
|---|---|
| Total PRs merged | ~42 (#265–#308) |
| Direct commits | ~6 |
| CI workflows | 8/8 green pre-launch |
| Worktree leaks | 9 total (all recovered via layer 2 pre-commit hook + manual rebase) |

## Q4 cross-system final state (Decision A: ship 4/6)

| System | nDCG@10 | p50 (ms) | Corpus | Status |
|---|---:|---:|---:|---|
| nox_mem (FTS5-only) | 0.3753 | 7ms | 6830 full | Measured |
| nox_mem (Gemini hybrid) | **0.6380** | 12ms | 6830 full | HEADLINE |
| agentmemory | 0.1376 | 14ms | 1401 (20% cap) | Measured |
| mem0 | 0.1315 | 263ms | 500 (7% cap) | Measured |
| Letta | partial | 14,978ms | 200-chunk cap | Partial |
| Zep | — | — | — | GATED |
| EverMind-AI | — | — | — | SKIP (404) |

## Gate D43 verdict

OPEN. nox-mem +83.0% vs baseline (0.6380 vs 0.3487). GTM Phase 2 unblocked.

## Zep gated rationale

OpenAI embedding mandatory in `zep_python` SDK default path. Fair comparison requires adapter rewrite to swap embedding backend to Gemini. Deferred post-launch. Not a retrieval quality issue — an embedding comparability issue.

## EverMind-AI skip rationale

Repo `EverOS-AI/EverMind-AI` returns HTTP 404. Confirmed Sat 2026-05-24 via PR #281. No accessible codebase.

## GTM Phase 2 P0 — 2 cleared, 3 manual remaining

- Cleared: Gemini grep (no hardcoded keys) + v1.0.0-rc1 tag
- Manual: arXiv submit (Tue 06-02) + Demo recording + Product Hunt (Wed 06-03)

## Sun 2026-05-25 priorities

1. Worktree spawn hardening (layer 1 root cause fix)
2. Canonical 100-query Q4 run (uniform corpus, 4 systems)
3. Paper §6 final update
4. F10 Phase D dispatch
5. A2 Tier 3 P3

## Cross-references

- `docs/COMPARISON.md` — updated Sat FINAL
- `docs/HANDOFF.md` — new §1 Sat FINAL closure
- `paper/paper-tecnico-nox-mem.md` §6.3 — Zep/EverMind FALHA rows + updated status
- `[[q4-real-numbers-sat-2026-05-24]]`
- `[[multi-agent-worktree-leak-5x-2026-05-24]]`
- `[[worktree-isolation-sparse-checkout-root-cause]]`
