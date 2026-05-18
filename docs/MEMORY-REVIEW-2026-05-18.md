# Memory review 2026-05-18

Reviewed 88 auto-memories post-Wave B/C/D (all PRs #38–#53 merged).

## Summary

| Action | Count |
|---|---|
| Keep as-is | 53 |
| Updated | 3 |
| Archived | 32 |
| Deleted | 0 |

**Active memories after review: 56** (was 88).

---

## Rationale

The main axis for archiving was **scope relevance**: 32 memories concern OpenClaw platform internals (gateway, monkey-patch, openclaw.json, RelayPlane, fallback chain, bedrock plugin, systemd units, upgrade scripts, v.24/.25 migration, Obsidian UX). These belong to `openclaw-vps` project context. They remain historically valid but are no longer actionable in a `memoria-nox` session — they add noise without benefit. All moved to `_archive/`, not deleted.

Four early session recap memories were archived as superseded:
- `project_2026_04_23_gateway_recovery_session.md` — incident fully resolved
- `project_2026_04_27_corpus_triplicate_session.md` — state superseded by v3.7
- `project_2026_04_29_post_marathon_audit.md` — audit applied, closed loop
- `project_2026_05_01_marathon_session.md` — superseded by Q/A/P pivot session

`project_e05b_decision_matrix.md` archived because E05b was CUT (D38 decision), gate expired.

---

## Details

### Updated (3)

- `MEMORY.md` — INDEX updated to reflect 32 archived files and corrected entry for `feedback_writer_agent_no_bash_tool.md` (slug was `feedback_writer_agent_no_bash_tool` not `feedback_writer_agent_no_bash_cant_commit` in the actual filename).
- Three entries that referenced old slug names in MEMORY.md corrected.

### Archived (32) — moved to `_archive/`

All moved to `/Users/lab/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/_archive/`.

#### OpenClaw platform — operational incidents (resolved)

| File | Reason |
|---|---|
| `feedback_openclaw_models_auth_login_removes_registry.md` | OpenClaw config incident, resolved, openclaw-vps scope |
| `feedback_models_auth_login_reinstalls_node_modules.md` | OpenClaw monkey-patch incident, resolved |
| `feedback_monkey_patch_grep_count_is_false_positive.md` | OpenClaw #62028 patch specifics |
| `feedback_amazon_bedrock_plugin_broken_remove_physically.md` | OpenClaw plugin bug, resolved |
| `feedback_gateway_drift_pgrep_regex_bug.md` | OpenClaw pgrep bug, fixed |
| `feedback_graph_memory_probe_errors_are_stale.md` | OpenClaw graph-memory probe, stale |
| `feedback_graph_memory_startup_log_is_misleading.md` | OpenClaw plugin local patch, wiped on reinstall |
| `feedback_heartbeat_regression_false_positive.md` | OpenClaw heartbeat noise |
| `feedback_heartbeat_design_uses_gemini.md` | OpenClaw design fact, narrow |
| `feedback_npm_install_g_resets_relayplane_baseurl.md` | OpenClaw upgrade artifact |
| `feedback_user_systemd_units_can_run_rogue.md` | OpenClaw systemd quirk, resolved |
| `feedback_openclaw_config_set_required_for_persistence.md` | OpenClaw config CLI pattern |
| `feedback_openclaw_fallback_should_include_claude_cli_sonnet.md` | OpenClaw fallback routing |
| `feedback_chattr_keep_immutable.md` | OpenClaw .credentials.json quirk |
| `feedback_financial_services_hooks_json_workaround.md` | OpenClaw vertical plugin bug |
| `feedback_agents_md_slim_pattern.md` | OpenClaw AGENTS.md slim pattern |
| `feedback_skills_cleanup_protect_plugin_dirs.md` | OpenClaw plugin dir collision |
| `project_openclaw_key_rotation_workflow.md` | OpenClaw key rotation runbook |
| `reference_vps_infra_triage_commands.md` | OpenClaw VPS triage bundle |
| `reference_sync_verify_activity_log.md` | OpenClaw cross-agent-sync |
| `reference_openclaw_upgrade_scripts.md` | OpenClaw upgrade scripts |

#### OpenClaw v.24/.25 migration (superseded)

| File | Reason |
|---|---|
| `feedback_openclaw_24_breaks_claude_cli_harness.md` | Superseded by v.25 fix |
| `feedback_v25_native_cli_via_wizard.md` | One-time wizard config, applied |
| `feedback_v25_premature_optimization_metrics.md` | Transition noise, resolved |
| `reference_v25_canonical_paths.md` | v.25 config reference, applied |
| `feedback_token_audit_check_values_not_just_presence.md` | v.25 token audit, one-time |

#### Obsidian UX

| File | Reason |
|---|---|
| `reference_obsidian_3d_graph_ribbon.md` | Obsidian UI quirk, not nox-mem scope |

#### Old session recaps (superseded)

| File | Reason |
|---|---|
| `project_2026_04_23_gateway_recovery_session.md` | Gateway incident, fully resolved |
| `project_2026_04_27_corpus_triplicate_session.md` | State superseded by v3.7 |
| `project_2026_04_29_post_marathon_audit.md` | Audit applied, closed |
| `project_2026_05_01_marathon_session.md` | Superseded by Q/A/P pivot |

#### Decision gates closed

| File | Reason |
|---|---|
| `project_e05b_decision_matrix.md` | E05b CUT (D38), gate expired |

### Deleted (0)

None deleted. Default-to-archive applied throughout.

---

## Active memories after review

56 memories remain active in `MEMORY.md`. Categories:

| Category | Count |
|---|---|
| feedback (code patterns, process lessons) | 35 |
| reference (A0–A5, entity format, staged dirs, etc.) | 9 |
| project (session summaries, strategic decisions) | 11 |
| user | 1 |

---

## Archive location

`/Users/lab/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/_archive/` — 32 files.
No files deleted; everything is recoverable.
