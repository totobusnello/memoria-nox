# Q4 nox_mem LIVE validation — Sat 2026-05-24 evening (canonical)

**Date:** 2026-05-24 23h30 BRT
**Source:** Prod instance LoCoMo benchmark (n=100, prod-flavored corpus)
**Feature stack:** section_boost + source_type_boost + Hard Mutex (t=2) + salience v2 + temporal v2

## Numbers (final, no revisions)

| Métrica | Valor | Gate target | Status |
|---|---|---|---|
| nDCG@10 | 0.6380 | ≥0.401 (+15%) | ✅ **+83.0%** vs baseline |
| MRR | 0.3700 | n/a | ✅ Measured |
| R@10 | 0.5417 | n/a | ✅ Measured |
| Gold hits | 13/20 | n/a | ✅ Strong |
| p50 latency | 12ms | <100ms | ✅ Excellent |
| p95 latency | 43ms | <100ms | ✅ Excellent |

## Gate D43 verdict

**Gate D43:** Threshold ≥+15% nDCG@10 vs baseline (0.3487).
**Result:** +18.8% (G5 V3) → +83.0% (Q4 LIVE validation). **OPEN** with margin.

**Interpretation:** Nox_mem LIVE production validates beyond gate. COMPARISON.md credible. GTM Phase 2 desbloqueada condicionalmente (no additional wins required from competitors).

## Adapter validation snapshot

- **nox_mem:** 13/20 gold, p50 12ms (live prod, Gemini 3072d embeddings)
- **mem0:** gold_hits unlocked post-PR #285; E2E ingest OK; 281ms avg latency
- **agentmemory:** REST adapter (iii-engine v0.9.21 OSS); 1/13 gold sample; full ~52min ETA
- **zep:** 3/5 gold (session-aware); 38ms latency
- **letta:** graceful fallback (SDK missing on eval machine)
- **evermind:** repo 404; skipped

## Cross-references

- Sat closure HANDOFF section (new §1)
- ROADMAP §8 "PRÓXIMO MÊS" — Q4 gate fulfilled
- PR #285, #281, #280, #283 (validation drivers)
- Memory entry `[[shared-loader-canonical-pattern]]` (corpus_loader.py lesson)

## Action items (post-validation)

- ✅ D43 gate verified; no further Q4 harness runs needed
- ✅ mem0 canonical pattern shared (corpus_loader.py)
- 🔄 agentmemory P3 impl (full ingest ETL; queued)
- 🔄 F10 Phase D enablement (phase C baseline sufficiency confirmed)
- 📋 Blog post / social copy — embed these numbers (Sat evening PRs #221/#224/#226 placeholders filled)
