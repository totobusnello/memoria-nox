# Copy of /Users/lab/Claude/skills/memory/memory-recompile/SKILL.md (version-tracked here)

See the live skill at: `~/Claude/skills/memory/memory-recompile/SKILL.md`
(Deployed to `~/.claude/skills/memory/memory-recompile/` via nightly sync.)

---
name: memory-recompile
description: Recompile the `compiled truth` section of a nox-mem entity file (memory/entities/<type>/<slug>.md) from its timeline using Gemini Flash-Lite. Preserves frontmatter and timeline, rewrites the middle section only. Trigger when user says "recompile entity X", "atualiza compiled do X", "/memory-recompile X", or when an entity's timeline has grown significantly and compiled is stale.
---

# memory-recompile

Skill for the nox-mem "compiled truth + timeline" entity format (Fase 1.7b-c).

## Purpose

Entity files in `memory/entities/<type>/<slug>.md` have 3 sections (frontmatter, compiled truth, timeline). Over time timeline grows but compiled stays stale. This skill rewrites compiled based on full timeline via Gemini Flash-Lite.

## When to use

- User asks "recompile entity X", "atualiza compiled do X", or `/memory-recompile <entity>`
- User reports entity has "outdated compiled" or "timeline has new events not reflected above"
- After a batch of timeline entries are appended
- Never automatic — always user-triggered

## Workflow

1. Locate entity file on VPS: `find /root/.openclaw/workspace/memory/entities -name "*<slug>*.md"`
2. Read file, parse 3 sections via `---`
3. Call Gemini Flash-Lite (`gemini/gemini-2.5-flash-lite`) with recompile prompt
4. Validate output (plain MD, 50-300 words, no frontmatter)
5. Write back preserving frontmatter + timeline
6. Re-ingest via `nox-mem ingest-entity <file>`
7. Re-vectorize
8. Show diff old vs new compiled to user

## Safeguards

- Backup first (`<path>.bak-<timestamp>`)
- Dry-run mode if user says "preview"
- Never edit timeline (append-only evidence)
- Preserve HTML retention override (`<!-- retention: never -->`)

## Related

- Fase 1.7b-c spec: plans/2026-04-24-fase-1.7b-c-close.md
- Entity format: reference_entity_file_format.md (auto-memory)
- CLI: `nox-mem ingest-entity` (added 2026-04-24)
