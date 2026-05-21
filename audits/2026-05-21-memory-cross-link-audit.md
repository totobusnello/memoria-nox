# Memory Cross-Link Integrity Audit — 2026-05-21

Read-only audit of `[[name]]` cross-references in `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/`. Memory files were **not** modified — this is diagnosis only. Cleanup decisions are left to Toto / main session.

## Headline numbers

| Metric | Count |
|---|---|
| Memory files (excluding `MEMORY.md`) | **106** |
| Files with `name:` frontmatter | **104** |
| Files missing `name:` frontmatter | **2** (1 expected, 1 bug) |
| Unique `[[ref]]` slugs used across corpus | **70** |
| Total `[[ref]]` occurrences | **176** |
| Broken `[[ref]]` occurrences | **39** (22.2%) |
| Distinct broken refs | **19** |
| Orphan candidates (>7d, zero incoming refs) | **38** (37% of corpus) |
| Recent no-refs (<=7d, not yet orphan) | **15** |
| MEMORY.md index entries | **105** |
| Indexed-but-missing-file | **0** |
| On-disk-but-not-indexed | **1** (MEMORY-INDEX.md, expected) |

## Root-cause findings

### 1. Naming-convention drift (primary issue — affects 16 files, 35 broken refs)

Older memory files (April 2026) used **sentence-style** `name:` values:

```yaml
name: Validate features with DB state, never logs alone
```

Newer files (May 2026) adopted **slug-style** `name:` values:

```yaml
name: validate-features-with-db-not-logs
```

Refs in newer files target slug-form (`[[validate-features-with-db-not-logs]]`), but older targets never had that name. Result: **35 broken refs (90% of all broken refs) AND 16 false-positive orphans**.

This is a single structural action away from resolution, not 35 individual typos.

### 2. Missing frontmatter (1 file, 3 broken refs)

`feedback_withopaudit_trigger_raise_ignore_swallows_insert.md` has no `name:` field at all. 3 files reference it via guessed slug `[[withopaudit-trigger-raise-ignore-swallows-insert]]`. Adding that frontmatter de-orphans it AND resolves the 3 refs.

### 3. Genuine typo (1 broken ref)

`[[temporal-q1-spike-2026-05-20]]` in `project_temporal_spike_patched_regressed_2026_05_20.md` does not match any existing slug. Likely intent: `[[temporal-spike-patched-regressed-2026-05-20]]` (self-ref?) or `[[temporal-spike-v2-win-2026-05-20]]`.

### 4. MEMORY.md sync is clean

Every `[title](filename.md)` link in MEMORY.md resolves. No phantom entries, no missing files. The one "not indexed" file (`MEMORY-INDEX.md`) is the topical-overlay index — intentionally not self-referenced.

### 5. MEMORY.md size warning (separate from this audit)

MEMORY.md self-reports 26.2KB > 24.4KB limit, so loaded content is truncated at session-start. Worth tracking but orthogonal to cross-link integrity.

## Per-output-file links

- [audits/memory-audit/broken-links.md](memory-audit/broken-links.md) — 39 broken refs grouped by root cause + per-ref fix suggestions
- [audits/memory-audit/orphan-candidates.md](memory-audit/orphan-candidates.md) — 38 orphans + 15 recent-no-refs + false-positive correlation
- [audits/memory-audit/memory-index-sync.md](memory-audit/memory-index-sync.md) — MEMORY.md vs disk comparison

## Recommended actions (NOT executed — left for Toto / main session)

Ranked by ROI:

1. **Slug-normalize `name:` across older files** (highest ROI). Single corpus-wide migration: convert sentence-style `name:` values to slug-form matching what existing `[[refs]]` already expect. Resolves 35 broken refs (90%) AND de-orphans 16 files in one pass.

2. **Add frontmatter to `feedback_withopaudit_trigger_raise_ignore_swallows_insert.md`** with `name: withopaudit-trigger-raise-ignore-swallows-insert`. Resolves 3 more broken refs.

3. **Fix the one genuine typo** (`temporal-q1-spike-2026-05-20`). Manual decision needed — pick the intended target.

4. **Either embrace MEMORY-INDEX.md as primary** OR **shrink long MEMORY.md entries**. Currently MEMORY.md is being truncated at load time, defeating part of the auto-memory's purpose. (Out of scope for this audit, but flagged.)

5. **Do NOT bulk-delete orphans.** Many "orphans" become connected once #1 is applied; the rest may be referenced externally (CLAUDE.md, docs/) or are just useful islands.

## Methodology

- Inventory: `ls *.md` in memory dir, excluding `MEMORY.md` itself
- Extract `name:` via regex `^name:\s*(.+)$` in each file
- Extract `[[ref]]` via regex `\[\[([a-z0-9_-]+)\]\]`
- Cross-reference: for each `[[ref]]`, check `name:` map for match
- Orphan: zero incoming refs AND file mtime older than 7 days
- MEMORY.md sync: parse `[title](filename.md)` link markdown and compare against directory listing

Script: ran once via `ctx_execute` JavaScript with `fs` / `path` only — no mutations to memory dir.

## Hard rules satisfied

- READ-ONLY on memory dir confirmed (used Node `fs.readFileSync` / `statSync` only, no writes)
- Audit output written only inside repo's `audits/` dir
- No changes to `main` branch — all work on `housekeeping/memory-cross-link-audit`
- No VPS touch
- No merge
