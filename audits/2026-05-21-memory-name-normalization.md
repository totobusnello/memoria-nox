# Memory Name Normalization — Audit Report

**Date:** 2026-05-21  
**Branch:** `housekeeping/memory-name-normalization`  
**Scope:** `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/` (107 files)

---

## Summary

Normalized `name:` frontmatter fields across memory files to slug-form (kebab-case lowercase).
Resolved 18 of 19 broken `[[ref]]` cross-links. One remaining ref (`temporal-q1-spike-2026-05-20`)
is a genuine orphan — no corresponding file exists.

| Metric | Before | After |
|---|---|---|
| Broken `[[ref]]` occurrences | 19 | 1 |
| Files with missing frontmatter | 1 | 0 |
| Files updated | 18 | — |

---

## Root Cause

Naming convention drift between April and May 2026:

- **April files** — verbose sentence-style names: `"Validate features with DB state, never logs alone"`
- **May files** — slug-style names: `validate-features-with-db-not-logs`
- **All `[[refs]]`** — slug-style (the newer convention)

April-era files were never migrated to slug-style, causing refs to miss on exact-string match.

---

## Files Updated

| File | Old `name:` | New `name:` |
|---|---|---|
| `feedback_audit_critical_modules_same_session.md` | `Auditar módulos críticos de segurança na mesma sessão que entregaram` | `audit-critical-modules-same-session` |
| `feedback_closedb_mid_function_invalidates_withopaudit.md` | `closeDb mid-function invalidates withOpAudit` | `closedb-mid-function-invalidates-withopaudit` |
| `feedback_eod_cron_reindex_was_the_real_trigger.md` | `""` (empty) | `eod-cron-reindex-was-the-real-trigger` |
| `feedback_esm_static_import_hoisting_captures_env.md` | `ESM static imports hoist before body — env overrides too late` | `esm-static-import-hoisting-captures-env` |
| `feedback_fts5_vanilla_and_strict_explains_zero_recall.md` | `FTS5 vanilla é AND-strict — queries linguagem natural completas raramente batem` | `fts5-vanilla-and-strict-explains-zero-recall` |
| `feedback_kg_relations_uses_fk_ids_not_inline_strings.md` | `kg_relations schema usa FK ids (source_entity_id/target_entity_id), NÃO strings inline` | `kg-relations-uses-fk-ids-not-inline-strings` |
| `feedback_long_running_batch_use_tmux.md` | `Long-running batch jobs use tmux + standalone script` | `long-running-batch-use-tmux` |
| `feedback_never_sed_binary_files.md` | `NUNCA sed -i em arquivos binários (SQLite, etc)` | `never-sed-binary-files` |
| `feedback_no_hardcoded_secrets.md` | `No hardcoded API keys in OpenClaw configs` | `no-hardcoded-secrets` |
| `feedback_no_secrets_in_git.md` | `Never push API keys to git — all secrets live only in .env` | `no-secrets-in-git` |
| `feedback_serial_pipeline_steps_need_timeout.md` | `Serial pipeline steps need per-step timeouts` | `serial-pipeline-steps-need-timeout` |
| `feedback_shadow_mode_for_ranking_changes.md` | `Always ship ranking-changing features in shadow-mode first` | `shadow-mode-for-ranking-changes` |
| `feedback_validate_features_with_db_not_logs.md` | `Validate features with DB state, never logs alone` | `validate-features-with-db-not-logs` |
| `feedback_withopaudit_trigger_raise_ignore_swallows_insert.md` | *(missing frontmatter)* | `withopaudit-trigger-raise-ignore-swallows-insert` |
| `feedback_writer_agent_no_bash_tool.md` | `writer-agent-no-bash-cant-commit` | `writer-agent-no-bash-tool` |
| `reference_a1_op_audit_module.md` | `A1 op-audit module — atomic snapshot + audit log for destructive ops` | `a1-op-audit-module` |
| `reference_a3_a4_invariants_canary.md` | `A3 retention tests + A4 schema invariants canary` | `a3-a4-invariants-canary` |
| `reference_a5_dry_run_mode.md` | `A5 dry-run mode em ops destrutivas` | `a5-dry-run-mode` |

---

## Special Case: Missing Frontmatter

`feedback_withopaudit_trigger_raise_ignore_swallows_insert.md` had no YAML frontmatter at all —
it started directly with a markdown `#` heading. Added full frontmatter block:

```yaml
---
name: withopaudit-trigger-raise-ignore-swallows-insert
description: trg_ops_audit_started_at_server_side compares TEXT datetime('now') vs epoch-ms integer
             — TEXT always wins, so RAISE(IGNORE) fires on every INSERT, silently swallowing all
             ops_audit rows since trigger creation
type: feedback
---
```

---

## Remaining Broken Ref (Genuine Orphan)

| Ref | Source File | Status |
|---|---|---|
| `temporal-q1-spike-2026-05-20` | `project_temporal_spike_patched_regressed_2026_05_20.md` (line 73) | No corresponding file exists — ref was written pointing to a memory that was never created or used a different name. Manual action required: either create the missing file or remove the `[[temporal-q1-spike-2026-05-20]]` ref from the source file. |

---

## Validation

```
Before: 19 broken refs
After:   1 broken ref (genuine orphan, no file exists)
```

Validation command used:

```bash
cd ~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/
grep -rh "^name: " *.md | sed 's/^name: //' | sort -u > /tmp/names.txt
grep -ohE '\[\[[a-z0-9][a-z0-9_-]*\]\]' *.md | sed 's/\[\[//;s/\]\]//' | sort -u > /tmp/refs.txt
comm -23 /tmp/refs.txt /tmp/names.txt
# Output: temporal-q1-spike-2026-05-20 (only)
```

---

## Safe Rollback

All memory files are outside the git repo (auto-memory managed by Claude Code session layer).
A backup was created before any edits:

```
/tmp/memory-backup-20260521-<timestamp>/
```

To restore: `cp /tmp/memory-backup-20260521-*/  ~/.claude/projects/.../memory/`

Git rollback of this audit report: `git revert HEAD` on `housekeeping/memory-name-normalization`.

---

## Convention Going Forward

All new memory files MUST use slug-style `name:` fields — kebab-case, lowercase, no punctuation,
no spaces. The `[[ref]]` syntax resolves via exact match on `name:` field. Verbose sentence-style
names are NOT resolvable by refs and will create silent orphans.

Pattern: `feedback_<slug>.md` → `name: <slug>` where `<slug>` matches the filename stem.
