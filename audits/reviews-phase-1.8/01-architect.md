# Architect Review — Fase 1.8 (2026-04-19)

**Verdict: SHIP-WITH-CHANGES** (split 1.8a audit + 1.8b execution; defer inbox until after Path A)

## Top 3 Architectural Gaps

1. **CRITICAL — `agent_inbox` writes violate Path A pre-req.** Roadmap Fase 2 is explicitly blocked on Path A because concurrent writers cause SQLITE_BUSY + partial writes. Adding a new high-frequency writer before Path A reopens the fail-silent write paths closed on 2026-04-18. **Fix:** Discord thread_id as primary state (free, persistent); DB table as read-model projection post-Path A.

2. **HIGH — Consolidation risks losing Forge's missing BOOTSTRAP.md + schema drift.** Snapshot shows Forge has no BOOTSTRAP.md; Nox has an extra INBOX.md; TEAM.md is identical 773-byte stub for all 6 (never customized — matcher-in-TEAM.md will drift); CHANNELS.md dated Apr 5 while gateway evolved daily. **Fix:** audit must produce provenance map (which file is read by which subsystem at runtime) before deprecating anything.

3. **HIGH — Matcher in markdown has no schema, no test, no CI.** Regex-in-prose inside TEAM.md is the same drift pattern that killed CHANNELS.md. **Fix:** matcher lives in `meta` table (Fase 1.6 doctrine) with cron drift check.

## Hidden Risks

- **1.7a dependency inverted.** Audit should inform 1.7a ontology, not the reverse
- **Nox proactive + graph-memory (Fase 2.5) collision** — matcher in TEAM.md gets compacted out
- **Discord webhook persona ≠ bot identity** — bot can't react to messages posted as personas
- **No A/B rollback** for Nox behavioral change

## Decisions That Cannot Wait

1. Inbox storage: Discord threads as SSOT NOW (not DB)
2. Matcher location: `meta` table (Fase 1.6 precedent)
3. Split 1.8a (audit, read-only) + 1.8b (consolidation + Nox proactive, after 1.7a)
