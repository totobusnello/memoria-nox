# MEMORY.md Sync Check — 2026-05-21

Comparison of `MEMORY.md` (auto-memory index, append-order, source-of-truth) vs the actual files present in `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/`.

## Summary

| Metric | Count |
|---|---|
| `MEMORY.md` index entries (markdown `[title](filename.md)` links) | 105 |
| Unique filenames referenced in `MEMORY.md` | 105 |
| Memory files present on disk (excluding `MEMORY.md` itself) | 106 |
| Files referenced in `MEMORY.md` but missing on disk | **0** |
| Files on disk but NOT in `MEMORY.md` index | **1** |

Result: **highly synced — only one discrepancy**, and it's expected (see below).

## Files in MEMORY.md but missing on disk

None. Every `[title](filename.md)` link in MEMORY.md resolves to an existing file.

## Files on disk but NOT indexed in MEMORY.md

| File | Age | Reason |
|---|---|---|
| `MEMORY-INDEX.md` | 1d | **Expected.** `MEMORY-INDEX.md` is itself an overlay index (topical alternative to MEMORY.md). Its preamble explicitly states: *"O `MEMORY.md` original (linear, append-order) continua sendo source-of-truth — este arquivo é apenas overlay temático."* It would be circular to index it in `MEMORY.md`. |

## MEMORY.md warning observed

The MEMORY.md file emits a self-diagnosed warning at the end:

> ⚠️ WARNING: MEMORY.md is 26.2KB (limit: 24.4KB) — index entries are too long. Only part of it was loaded. Keep index entries to one line under ~200 chars; move detail into topic files.

This is a session-start-hook size-limit warning. It is **not** a sync issue but worth surfacing because:

- The index is currently being **truncated** at load time
- Some entries cross 200 chars (e.g. multi-clause descriptions of overnight bursts)
- Migration plan: split into multiple topical indexes (MEMORY-INDEX.md is already a step in this direction) and shrink individual entries

## Recommendations

- **No sync remediation needed.** The 1 missing-from-index file is the alternate index, and the 0 orphan-link case is clean.
- **Address the 26.2KB warning separately** — shrink long entries OR migrate to MEMORY-INDEX.md as primary, deprecating linear `MEMORY.md`.
