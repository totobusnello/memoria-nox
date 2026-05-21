# Orphan Memory Candidates — 2026-05-21

Memory files with `name:` frontmatter that have **zero incoming `[[name]]` references** from any other memory file. Threshold: older than 7 days (recent files excluded — new memories take time to be cross-linked).

## Summary

- **38** orphan candidates (>7 days, zero incoming refs)
- **15** recent no-refs (<= 7 days, monitor but not yet orphan)
- **34 of 38 orphans** are actually false positives caused by the **naming-convention drift** identified in `broken-links.md` — these files DO have refs pointing at them, but the refs use slug-form while the `name:` field uses sentence-form

## False-positive correlation with broken-links.md

The following files appear in this orphan list AND have broken refs trying to reach them (see `broken-links.md`). These would NOT be orphans if `name:` were slug-normalized:

| File | "Slug" refs expect | `name:` actually is | Hits |
|---|---|---|---|
| `feedback_validate_features_with_db_not_logs.md` | `validate-features-with-db-not-logs` | "Validate features with DB state, never logs alone" | 7 |
| `reference_a1_op_audit_module.md` | `a1-op-audit-module` | "A1 op-audit module — atomic snapshot + audit log for destructive ops" | 4 |
| `feedback_long_running_batch_use_tmux.md` | `long-running-batch-use-tmux` | "Long-running batch jobs use tmux + standalone script" | 3 |
| `feedback_no_secrets_in_git.md` | `no-secrets-in-git` | "Never push API keys to git — all secrets live only in .env" | 3 |
| `feedback_esm_static_import_hoisting_captures_env.md` | `esm-static-import-hoisting-captures-env` | "ESM static imports hoist before body — env overrides too late" | 2 |
| `feedback_closedb_mid_function_invalidates_withopaudit.md` | `closedb-mid-function-invalidates-withopaudit` | "closeDb mid-function invalidates withOpAudit" | 2 |
| `feedback_shadow_mode_for_ranking_changes.md` | `shadow-mode-for-ranking-changes` | "Always ship ranking-changing features in shadow-mode first" | 2 |
| `feedback_audit_critical_modules_same_session.md` | `audit-critical-modules-same-session` | "Auditar módulos críticos de segurança..." | 1 |
| `feedback_serial_pipeline_steps_need_timeout.md` | `serial-pipeline-steps-need-timeout` | "Serial pipeline steps need per-step timeouts" | 1 |
| `feedback_no_hardcoded_secrets.md` | `no-hardcoded-secrets` | "No hardcoded API keys in OpenClaw configs" | 1 |
| `reference_a5_dry_run_mode.md` | `a5-dry-run-mode` | "A5 dry-run mode em ops destrutivas" | 1 |
| `feedback_never_sed_binary_files.md` | `never-sed-binary-files` | "NUNCA sed -i em arquivos binários..." | 1 |
| `feedback_fts5_vanilla_and_strict_explains_zero_recall.md` | `fts5-vanilla-and-strict-explains-zero-recall` | "FTS5 vanilla é AND-strict..." | 1 |
| `reference_a3_a4_invariants_canary.md` | `a3-a4-invariants-canary` | "A3 retention tests + A4 schema invariants canary" | 1 |
| `feedback_kg_relations_uses_fk_ids_not_inline_strings.md` | `kg-relations-uses-fk-ids-not-inline-strings` | "kg_relations schema usa FK ids..." | 1 |
| `feedback_eod_cron_reindex_was_the_real_trigger.md` | `eod-cron-reindex-was-the-real-trigger` | "end-of-day OpenClaw cron drives daily reindex..." | 1 |

Fixing the naming-convention drift de-orphans 16 files (47% of the list).

## True orphans (>7d, no refs anywhere, no fixable mismatch)

These are files with sentence-style names that no one references — they may be genuinely abandoned or simply lack outgoing references from peer memories:

| Age | File | `name:` |
|---|---|---|
| 29d | `feedback_model_selection_for_agent_infra.md` | "Default to gemini-flash-lite for low-cognition agent infra tasks" |
| 28d | `feedback_validate_features_with_db_not_logs.md` | "Validate features with DB state..." *(would not be orphan if slug-normalized — see above)* |
| 27d | `feedback_validate_secondary_agent_diagnostics.md` | "Validate secondary agent diagnostics before acting" |
| 27d | `reference_entity_file_format.md` | "nox-mem entity file format (compiled truth + timeline)" |
| 27d | `reference_nox_mem_cli_entry_and_ingest_entity.md` | "nox-mem CLI entry point + ingest-entity command" |
| 26d | `feedback_reindex_must_route_entity_files.md` | "Reindex/watcher must route entity files via ingestEntityFile" |
| 26d | `reference_a0_query_logging_extension.md` | "A0 query logging extension — search_telemetry +4 columns" |
| 26d | `reference_a2_ingest_router.md` | "A2 ingest-router — single dispatch entry point para ingestão" |
| 25d | `feedback_audit_must_check_prod_state_not_only_code.md` | "Audit must verify prod state, not only code" |
| 24d | `feedback_extract_messages_filter_all_roles.md` | "Noise filters in distill/consolidate must cover all roles" |
| 24d | `feedback_no_f09_offsite_backup.md` | "F09 off-site backup rejeitado — VPS já tem backup" |
| 24d | `feedback_rsync_delete_must_exclude_local_only_dirs.md` | "rsync --delete must exclude local-only dirs" |
| 24d | `feedback_validate_grep_after_edit_before_commit.md` | "Validate edits via grep AFTER Edit, BEFORE commit" |
| 23d | `feedback_scanned_pdf_heuristic.md` | "Scanned PDF detection via output char count" |
| 23d | `feedback_subagent_findings_validate_critical.md` | "Sub-agent findings são hipótese..." |
| 23d | `reference_markitdown_adopted_stack.md` | "Markitdown adopted on VPS conversion stack" |
| 21d | `reference_session_wrap_up_threshold.md` | "session-wrap-up MEMORY.md threshold" |
| 18d | `feedback_cli_api_session_id_sync_needs_env_override.md` | "CLI + API com session-derived state precisam env override..." |
| 18d | `feedback_js_regex_unicode_word_boundary_fails.md` | "JavaScript regex \\b não trata caracteres Unicode..." |
| 18d | `feedback_no_require_in_esm_modules.md` | "require() proibido em ESM modules..." |
| 17d | `feedback_buffer_pool_aliasing_in_typed_arrays.md` | "Node Buffer pool aliasing corrupts Float32Array views..." |
| 17d | `feedback_execfilesync_over_execsync_for_user_input.md` | "Always execFileSync (array args) when interpolating user input into shell" |
| 17d | `feedback_llm_optional_field_default_drives_undercoverage.md` | "LLM optional field + 'DEFAULT — never invent' prompt drives undercoverage" |

## Recent no-refs (monitor — not yet orphans, <=7d old)

| Age | File | `name:` |
|---|---|---|
| 0d | `feedback_executor_high_vs_executor_tradeoff.md` | executor-high-vs-executor-tradeoff |
| 0d | `feedback_user_accepts_gemini_key_risk.md` | user-accepts-gemini-key-risk |
| 0d | `project_d44_stripe_first_pivot.md` | d44-stripe-first-pivot |
| 0d | `project_morning_2026_05_21_burst.md` | morning-2026-05-21-burst |
| 0d | `project_personality_files_markdown_layer.md` | personality-files-markdown-layer |
| 0d | `reference_path_layout_canonical.md` | path-layout-canonical |
| 1d | `feedback_agent_stall_on_multi_phase_pipelines.md` | agent-stall-on-multi-phase-pipelines |
| 1d | `feedback_unicode_aware_sanitize_for_fts5.md` | unicode-aware-sanitize-for-fts5 |
| 1d | `project_lightrag_kg_incremental_merge_pattern.md` | lightrag-kg-incremental-merge-pattern |
| 2d | `feedback_pre_trigger_orphan_residue_cleanup.md` | pre-trigger-orphan-residue-cleanup |
| 2d | `feedback_stderr_redirect_breaks_json_capture.md` | stderr-redirect-breaks-json-capture |
| 3d | `feedback_use_voce_not_tu_in_portuguese.md` | "HARD RULE — Use 'você' not 'tu' in Portuguese (cross-project, escalated 3×)" |
| 3d | `feedback_writer_agent_no_bash_tool.md` | writer-agent-no-bash-cant-commit |
| 3d | `reference_staged_dirs_pattern.md` | staged-dirs-pattern |
| 3d | `user_location_timezone.md` | "User location and timezone — São Paulo BRT (re-confirmed 2026-05-17))" |

Note: all recent (<=7d) files use slug-style `name:` — confirms the naming convention has switched. Older files need migration.

## Recommendations

- **Do NOT delete orphans.** They may be referenced by external systems (CLAUDE.md, MEMORY.md, docs, etc.) or simply lack peer connections.
- **Slug-normalize older `name:` fields** — single action de-orphans 16 files immediately and resolves 35 broken refs.
- **Add MEMORY.md or MEMORY-INDEX.md as the "ref source"** in the audit logic — many files are listed there even if no peer memory refs them.
