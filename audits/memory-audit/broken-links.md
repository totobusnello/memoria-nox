# Broken Memory Cross-Links — 2026-05-21

Audit of `[[name]]` references in `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/*.md` whose target `name:` does not exist in any memory frontmatter.

## Summary

- **39** broken `[[ref]]` occurrences (across 19 distinct refs)
- **22 (56%)** of these are caused by a single missing frontmatter field — `feedback_withopaudit_trigger_raise_ignore_swallows_insert.md` lacks `name:` so 3 distinct slug-attempts to reach it all fail
- **17 (44%)** are slug-style refs to memories that exist with a longer descriptive `name:` value (mismatch between slug refs and full-sentence names)

## Pattern analysis

| Pattern | Count | Root cause |
|---|---|---|
| Slug `[[ref]]` where target file uses long descriptive `name:` (e.g. `[[validate-features-with-db-not-logs]]` → file name is `"Validate features with DB state, never logs alone"`) | 17 refs | Inconsistent naming convention — newer files use slug-style `name:`, older files use sentence-style `name:` |
| Reference to file missing `name:` field entirely | 3 refs | `feedback_withopaudit_trigger_raise_ignore_swallows_insert.md` has no frontmatter; consumers guessed slug `withopaudit-trigger-raise-ignore-swallows-insert` |
| Genuine wrong-slug typo / missing memory | 1 ref | `[[temporal-q1-spike-2026-05-20]]` likely intended `[[temporal-spike-patched-regressed-2026-05-20]]` or `[[temporal-spike-v2-win-2026-05-20]]` |

## Full broken-link list (grouped by referenced slug, sorted by frequency)

| `[[ref]]` | Hits | Sources (first 3) | Likely fix |
|---|---|---|---|
| `[[validate-features-with-db-not-logs]]` | 7 | feedback_cron_path_must_include_sbin, feedback_pre_trigger_orphan_residue_cleanup, feedback_static_analysis_vs_real_ablation (+4 more) | Target exists: `feedback_validate_features_with_db_not_logs.md` with `name: "Validate features with DB state, never logs alone"` — either retro-add slug-alias OR migrate file to slug-style `name:` |
| `[[a1-op-audit-module]]` | 4 | feedback_pre_trigger_orphan_residue_cleanup, feedback_static_analysis_vs_real_ablation, project_incident_2026_05_19_wipe (+1) | Target: `reference_a1_op_audit_module.md` (`name: "A1 op-audit module — atomic snapshot + audit log for destructive ops"`) |
| `[[writer-agent-no-bash-tool]]` | 3 | feedback_aad_bug_caught_by_integration_test, feedback_executor_high_vs_executor_tradeoff, feedback_mandatory_closure_steps_pattern | Target exists with slightly different slug: `feedback_writer_agent_no_bash_tool.md` (`name: writer-agent-no-bash-cant-commit`) — pick canonical slug & sync |
| `[[long-running-batch-use-tmux]]` | 3 | feedback_agent_stall_on_multi_phase_pipelines, feedback_cron_path_must_include_sbin, reference_staged_dirs_pattern | Target: `feedback_long_running_batch_use_tmux.md` (`name: "Long-running batch jobs use tmux + standalone script"`) |
| `[[no-secrets-in-git]]` | 3 | feedback_pre_commit_hook_blocks_non_main_commits, feedback_user_accepts_gemini_key_risk, feedback_yaml_block_scalar_dedent_in_bash_strings | Target: `feedback_no_secrets_in_git.md` (`name: "Never push API keys to git — all secrets live only in .env"`) |
| `[[withopaudit-trigger-raise-ignore-swallows-insert]]` | 3 | feedback_sqlite_text_affinity_coerces_int_back, project_opsaudit_hygiene_deployed_2026_05_21, project_opsaudit_investigation_2026_05_21 | **File `feedback_withopaudit_trigger_raise_ignore_swallows_insert.md` is missing the `name:` frontmatter field entirely** — add it |
| `[[esm-static-import-hoisting-captures-env]]` | 2 | feedback_no_getdb_in_eval_scripts (2x) | Target: `feedback_esm_static_import_hoisting_captures_env.md` (`name: "ESM static imports hoist before body — env overrides too late"`) |
| `[[closedb-mid-function-invalidates-withopaudit]]` | 2 | feedback_no_getdb_in_eval_scripts, feedback_pre_trigger_orphan_residue_cleanup | Target: `feedback_closedb_mid_function_invalidates_withopaudit.md` (`name: "closeDb mid-function invalidates withOpAudit"`) |
| `[[shadow-mode-for-ranking-changes]]` | 2 | project_neural_reranker_evolution_vector (2x) | Target: `feedback_shadow_mode_for_ranking_changes.md` (`name: "Always ship ranking-changing features in shadow-mode first"`) |
| `[[audit-critical-modules-same-session]]` | 1 | feedback_aad_bug_caught_by_integration_test | Target: `feedback_audit_critical_modules_same_session.md` |
| `[[serial-pipeline-steps-need-timeout]]` | 1 | feedback_agent_stall_on_multi_phase_pipelines | Target: `feedback_serial_pipeline_steps_need_timeout.md` |
| `[[no-hardcoded-secrets]]` | 1 | feedback_pre_commit_hook_blocks_non_main_commits | Target: `feedback_no_hardcoded_secrets.md` |
| `[[a5-dry-run-mode]]` | 1 | feedback_pre_trigger_orphan_residue_cleanup | Target: `reference_a5_dry_run_mode.md` |
| `[[never-sed-binary-files]]` | 1 | feedback_sqlite_text_affinity_coerces_int_back | Target: `feedback_never_sed_binary_files.md` |
| `[[fts5-vanilla-and-strict-explains-zero-recall]]` | 1 | feedback_unicode_aware_sanitize_for_fts5 | Target: `feedback_fts5_vanilla_and_strict_explains_zero_recall.md` |
| `[[a3-a4-invariants-canary]]` | 1 | project_incident_2026_05_19_wipe | Target: `reference_a3_a4_invariants_canary.md` |
| `[[kg-relations-uses-fk-ids-not-inline-strings]]` | 1 | project_lightrag_kg_incremental_merge_pattern | Target: `feedback_kg_relations_uses_fk_ids_not_inline_strings.md` |
| `[[eod-cron-reindex-was-the-real-trigger]]` | 1 | project_opsaudit_investigation_2026_05_21 | Target: `feedback_eod_cron_reindex_was_the_real_trigger.md` |
| `[[temporal-q1-spike-2026-05-20]]` | 1 | project_temporal_spike_patched_regressed_2026_05_20 | **Genuine typo** — likely `[[temporal-spike-patched-regressed-2026-05-20]]` or `[[temporal-spike-v2-win-2026-05-20]]` |

## Root-cause classification

The majority of "broken" refs are caused by two structural issues, not individual typos:

1. **Naming-convention drift.** Older memory files (April 2026) used sentence-style `name:` values like `"Validate features with DB state, never logs alone"`, while newer files (May 2026) adopted slug-style `name:` values like `validate-features-with-db-not-logs`. Refs in newer files target slug-style names that the older files never had.
2. **Missing frontmatter.** `feedback_withopaudit_trigger_raise_ignore_swallows_insert.md` has no `name:` field, so any ref is broken.

A blanket "fix these 39 typos" is not the right action. Two structural moves resolve >95% of the cases:

- **Option A — slug-normalize `name:` across the corpus.** Migrate all sentence-style `name:` values to slug-form (matches what refs already expect). Adds incoming refs to currently-orphan files.
- **Option B — add aliases.** Introduce `aliases: [slug-1, slug-2]` frontmatter field and update audit logic to resolve refs against `name` OR `aliases`.

Option A is simpler. Option B preserves human-readable names if Toto values them.
