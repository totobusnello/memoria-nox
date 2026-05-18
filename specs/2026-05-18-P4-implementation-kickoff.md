# P4 Implementation Kickoff — `nox-mem connect <ide>`

**Status:** ready to start (planning artifact, not implementation)
**Date:** 2026-05-18
**Owner:** overnight automode push (memoria-nox)
**Spec:** `specs/2026-05-17-P4-connect-ide.md` (PR #7, 2,904 words, 423 lines)
**Pillar:** **P4 — Multi-IDE Convergence** (Q/A/P framework)
**Branch:** `overnight/2026-05-18/P4-impl-kickoff`

---

## 1. Cross-references

| Ref | Source | Why it matters |
|---|---|---|
| **PR #7** | `[overnight] P4 — Spec: nox-mem connect <ide>` | Authoritative spec — backup-first atomic merge, per-IDE merger registry, manifest at `~/.nox-mem/connections.json`, drift-aware disconnect. |
| **PR #4 (P2)** | `[overnight] P2 — Spec: Claude Code hooks auto-capture` | Dependency. Tier A (Claude Code / Cursor / Codex) **degrades to "Tier A-shallow" until P2 lands**. P4 ships AFTER P2 per D41 #5. |
| **D41 #5** | OPS log — D41 pillar sequencing | **Ship order is P1 → A2 → P2 → P4.** P4 is FOURTH. No reordering. |
| **L3** | Cross-agent coordination primitives | Required ONLY for Tier A "lease" feature (Atlas/Boris/Cipher/Forge/Lex persona awareness). Tier A persona-injection ships without leases if L3 not yet ready. |
| **A1** | Privacy filter | Applies at ingest layer regardless of IDE — orthogonal to P4. P4 must NOT bypass A1. |

> **Single source-of-truth for "what we ship":** `specs/2026-05-17-P4-connect-ide.md`. This kickoff doc lists tasks, DoD, file structure — does NOT redefine the spec.

---

## 2. Tier A / Tier B locked breakdown

### Tier A — Deep MCP + hooks (where supported) + persona awareness (3 IDEs)

| IDE | MCP | Hooks (via P2) | Persona awareness | Project profile | Cross-agent leases (L3) |
|---|---|---|---|---|---|
| **Claude Code** | yes | yes (PreToolUse/PostToolUse/Notification) | full (Atlas/Boris/Cipher/Forge/Lex routing) | yes | yes (when L3 ready) |
| **Cursor** | yes | no native hook API → tail `~/.cursor/logs/` | shallow (persona via MCP context only) | yes | yes (when L3 ready) |
| **Codex** | yes | partial (OpenAI Codex CLI emits events) | shallow | yes | yes (when L3 ready) |

### Tier B — MCP passive only (10 IDEs)

| IDE | Config format | MCP block shape | Hooks | Sandboxed? |
|---|---|---|---|---|
| **Cline** | JSON | `mcpServers` | no | no |
| **Gemini CLI** | YAML | `mcp.servers[]` | no | no |
| **OpenCode** | JSON | `mcpServers` | no | no |
| **Goose** | YAML | `extensions.mcp` | no | no |
| **Windsurf** | JSON | `mcpServers` | no | no |
| **Continue** | JSON | `experimental.modelContextProtocolServers` | no | no |
| **Aider** | YAML / `.aider.conf.yml` | `mcp:` list | no | no |
| **Roo Code** | JSON | `mcpServers` | no | no |
| **Zed** | JSONC | `context_servers` | no | possible (Flatpak Linux) |
| **JetBrains AI** | XML+JSON hybrid | `mcpClients` | no | possible (Snap Linux) |

**Locked:** 3 Tier A + 10 Tier B = **13 IDEs**. No Vim / Emacs / Sublime / NeoVim / Helix in v1 (out-of-scope per spec §17).

---

## 3. Task breakdown (16 tasks)

| # | Task | Module / File | Est. hours |
|---|---|---|---|
| **T1** | IDE detection | `src/lib/connect/detect.ts` | 1.5h |
| **T2** | Per-IDE merger modules (13 files) | `src/lib/connect/ides/*.ts` | 6.5h |
| **T3** | Manifest layer | `src/lib/connect/manifest.ts` → `~/.nox-mem/connections.json` | 1.5h |
| **T4** | Backup strategy (write-or-abort) | `src/lib/connect/backup.ts` | 1.0h |
| **T5** | CLI `nox-mem connect <ide>` | `src/cli/connect.ts` (`--list`, `--dry-run`, `--force`, `--scope`, `--agent`, `--verify`) | 2.0h |
| **T6** | CLI `nox-mem disconnect <ide>` w/ drift detection prompt | `src/cli/disconnect.ts` | 2.0h |
| **T7** | Tier A — Claude Code (MCP + P2 hooks block + persona) | `src/lib/connect/ides/claude-code.ts` | 2.0h |
| **T8** | Tier A — Cursor (MCP + log-tail shim + persona MCP context) | `src/lib/connect/ides/cursor.ts` | 1.5h |
| **T9** | Tier A — Codex (MCP + CLI event integration) | `src/lib/connect/ides/codex.ts` | 1.5h |
| **T10** | Tier B batch 1 — `mcpServers` JSON shape: Cline, OpenCode, Windsurf, Roo Code | `src/lib/connect/ides/{cline,opencode,windsurf,roo}.ts` | 2.0h |
| **T11** | Tier B batch 2 — YAML shape: Gemini CLI, Goose, Aider | `src/lib/connect/ides/{gemini-cli,goose,aider}.ts` | 2.0h |
| **T12** | Tier B batch 3 — quirky JSON: Continue (`experimental.*`) | `src/lib/connect/ides/continue.ts` | 1.0h |
| **T13** | Tier B batch 4 — JSONC + hybrid: Zed, JetBrains AI | `src/lib/connect/ides/{zed,jetbrains-ai}.ts` | 1.5h |
| **T14** | Sandboxed client probe (Flatpak / Snap detection + LAN-IP suggestion) | `src/lib/connect/sandbox-probe.ts` | 1.5h |
| **T15** | Tests — per-IDE fixture round-trip + drift detection | `tests/connect/*.test.ts` | 3.5h |
| **T16** | Docs — `docs/CONNECT.md` + `--help` strings + README section | `docs/CONNECT.md`, README patch | 1.5h |

**Total:** ~31.5h → rounded to **28–32h band**.

---

## 4. Per-task DoD

| # | Definition of Done |
|---|---|
| T1 | `detect()` returns `{found: IdeDescriptor[], missing: string[]}`; covers all 13 IDEs; safe on missing dirs; unit test passes for present/absent/multi-install. |
| T2 | 13 `.ts` files exporting `{ configPath, format, mergeFragment(), unmergeFragment(), schemaHash() }`; each callable independently. |
| T3 | `connections.json` reads/writes with atomic tmp+rename; records `{ide, configPath, backupPath, schemaHash, ts, scope}`; corrupt file → quarantine + warn, not crash. |
| T4 | Backup write to `<config>.nox-mem-backup-<ts>.json` SUCCEEDS or merge **aborts** with non-zero exit; never partial; mode 0600. |
| T5 | `nox-mem connect <ide>` runs end-to-end on Claude Code happy path; `--list` prints 13-row table; `--dry-run` prints unified diff, no writes; `--force` skips drift prompt; `--scope=user|project` resolves correct path. |
| T6 | `disconnect` removes ONLY nox-mem keys; preserves user edits; drift prompt offers `[k]eep user / [r]estore backup / [d]iff / [a]bort`; default = keep. |
| T7 | Claude Code config receives `mcpServers.nox-mem` block + (if P2 merged) hooks block; persona routing key present; round-trip clean. |
| T8 | Cursor config receives MCP block; log-tail shim path recorded in manifest (not yet active — feature-flagged off until log-format frozen). |
| T9 | Codex MCP block written; CLI-event integration is best-effort (warn-not-fail if Codex version < threshold). |
| T10 | 4 IDEs share JSON `mcpServers` shape; all 4 round-trip clean; one shared helper in `ides/_shared/json-mcp-servers.ts`. |
| T11 | 3 YAML IDEs preserve comments + indentation (use `yaml` lib in `keepCstNodes` mode); round-trip clean. |
| T12 | Continue's `experimental.modelContextProtocolServers` path handled; warn-banner that key may move in future Continue release. |
| T13 | Zed JSONC comments preserved (use `jsonc-parser` with edits API); JetBrains hybrid XML+JSON config touches ONLY the JSON sidecar, never XML. |
| T14 | Probe detects Flatpak (`/var/lib/flatpak`) / Snap (`/snap`); suggests `127.0.0.1` → LAN IP swap + Flatpak `--filesystem=host` override snippet; non-Linux returns "n/a". |
| T15 | Per-IDE fixture round-trip test (13 IDEs); idempotency test (`connect` 2× = same hash); drift simulation test (manual edit → disconnect prompt fires); coverage > 85% on `src/lib/connect/**`. |
| T16 | `docs/CONNECT.md` covers all 13 IDEs with config paths + screenshots-of-CLI; README has new "Connect your IDE" section; `--help` lists all flags. |

---

## 5. File structure

```
src/
  cli/
    connect.ts                       # T5
    disconnect.ts                    # T6
  lib/
    connect/
      detect.ts                      # T1
      manifest.ts                    # T3
      backup.ts                      # T4
      sandbox-probe.ts               # T14
      mergers/
        json.ts                      # shared JSON deep-merge
        jsonc.ts                     # JSONC (Zed)
        yaml.ts                      # YAML w/ comment preservation
        toml.ts                      # reserved for future
      ides/
        _shared/
          json-mcp-servers.ts        # T10 shared helper
        claude-code.ts               # T7
        cursor.ts                    # T8
        codex.ts                     # T9
        cline.ts                     # T10
        opencode.ts                  # T10
        windsurf.ts                  # T10
        roo.ts                       # T10
        gemini-cli.ts                # T11
        goose.ts                     # T11
        aider.ts                     # T11
        continue.ts                  # T12
        zed.ts                       # T13
        jetbrains-ai.ts              # T13
tests/
  connect/
    fixtures/                        # per-IDE config snapshots before/after
    detect.test.ts
    manifest.test.ts
    backup.test.ts
    round-trip.test.ts               # property: connect→disconnect = byte-identical
    drift.test.ts
    idempotency.test.ts
docs/
  CONNECT.md                         # T16
```

Total new files: **27** (13 ides + 4 mergers + 1 shared helper + 3 core lib + 2 CLI + 6 tests + 1 doc).

---

## 6. IDE coverage matrix (full 13)

| IDE | Tier | Config path (macOS / Linux) | Format | MCP block key | Hooks? | Quirks |
|---|---|---|---|---|---|---|
| Claude Code | A | `~/.claude/settings.json` | JSON | `mcpServers` | yes (P2) | `permissions.allow` array sensitive |
| Cursor | A | `~/.cursor/mcp.json` | JSON | `mcpServers` | no native | no hook API; tail `~/.cursor/logs/` |
| Codex | A | `~/.codex/config.toml` | TOML | `[mcp_servers.nox-mem]` | partial | TOML reserved — use `toml.ts` merger |
| Cline | B | `~/.vscode/extensions/cline*/settings.json` | JSON | `mcpServers` | no | VSCode extension dir varies by version |
| Gemini CLI | B | `~/.gemini/config.yaml` | YAML | `mcp.servers[]` | no | comments must survive |
| OpenCode | B | `~/.config/opencode/config.json` | JSON | `mcpServers` | no | XDG path resolution |
| Goose | B | `~/.config/goose/config.yaml` | YAML | `extensions.mcp` | no | nested under `extensions` |
| Windsurf | B | `~/.codeium/windsurf/mcp_config.json` | JSON | `mcpServers` | no | path is `.codeium`, not `.windsurf` |
| Continue | B | `~/.continue/config.json` | JSON | `experimental.modelContextProtocolServers` | no | key likely to rename — warn-banner |
| Aider | B | `~/.aider.conf.yml` | YAML | `mcp:` | no | top-level list |
| Roo Code | B | `~/.config/roo/settings.json` | JSON | `mcpServers` | no | fork of Cline shape |
| Zed | B | `~/.config/zed/settings.json` | JSONC | `context_servers` | no | JSONC comments mandatory preserve; Flatpak possible |
| JetBrains AI | B | `~/Library/Application Support/JetBrains/<IDE><ver>/options/aiAssistant.xml` + sidecar JSON | XML+JSON | `mcpClients` (sidecar) | no | NEVER touch XML; only sidecar JSON; Snap on Linux |

Coverage: **13/13** = 100% of locked tier list.

---

## 7. Merge strategy contract

**Contract (all 13 IDEs MUST implement):**

```ts
interface IdeMerger {
  configPath(): string;                        // expanded abs path
  format: 'json' | 'jsonc' | 'yaml' | 'toml';  // dispatch merger
  mergeFragment(current: any, fragment: NoxMemFragment): any;
  unmergeFragment(current: any, manifestEntry: ManifestEntry): any;
  schemaHash(): string;                        // SHA-256 of expected schema
}
```

**Hard rules:**
1. **Backup-first.** Call `backup.write(configPath)` BEFORE any merge. Abort on backup failure.
2. **Deep merge, never replace.** Existing `mcpServers.<other>` entries MUST survive. Only `mcpServers.nox-mem` (or equivalent) is added.
3. **Manifest hash.** After successful merge, write `{schemaHash, configHash}` to `~/.nox-mem/connections.json`. Used by disconnect drift detection.
4. **Atomic write.** tmp file in same dir + `rename()`. Never partial.
5. **Format preservation.** YAML comments / JSONC comments / TOML formatting MUST round-trip byte-identical when no fragment changes are needed.

---

## 8. Drift detection (disconnect)

```
disconnect <ide>:
  1. Load manifest entry → expect {schemaHash, configHash, backupPath}
  2. Compute current configHash
  3. If currentHash == manifest.configHash:
       → clean removal: subtract nox-mem keys, restore byte-identical
  4. Else (drift detected):
       → diff(currentConfig, backup) → show unified diff
       → prompt: [k]eep-user-edits / [r]estore-backup / [d]iff / [a]bort
       → default: keep-user-edits (remove only nox-mem keys)
  5. Update manifest: remove entry on success
```

**Edge cases:**
- Manifest missing → best-effort key removal + warn.
- Backup missing → refuse `[r]`, force `[k]` or `[a]`.
- Config file missing → remove manifest entry + warn (already-disconnected).

---

## 9. Tests plan + overall DoD

### Test plan (T15)

- **Round-trip** (per IDE × 13): `connect → disconnect` produces byte-identical config when no user edits.
- **Idempotency** (per IDE × 13): `connect` twice = same final config + same manifest hash.
- **Drift simulation**: connect → manual edit → disconnect → prompt fires with correct diff.
- **No-manifest disconnect**: best-effort path removes nox-mem keys without crashing.
- **Sandboxed probe**: Linux fixture with `/var/lib/flatpak` triggers LAN-IP suggestion.
- **Format preservation**: YAML/JSONC fixtures with comments survive a no-op connect/disconnect.
- **Property test**: 100 randomized configs → connect → disconnect → byte-equal.

### Overall DoD (6 criteria — matches PR #7 spec §13)

1. **All 13 IDEs**: `connect`, `disconnect`, `--list`, `--dry-run` all functional.
2. **Backup-first contract**: ≥1 test per IDE proves backup-failure aborts merge.
3. **Manifest as source-of-truth**: `disconnect` works correctly even after `connect` from a different shell session.
4. **Drift detection**: end-to-end test passes for manual-edit-between-connect-and-disconnect.
5. **Sandboxed probe**: Linux Flatpak/Snap fixture suggests correct fix.
6. **Tier A persona awareness**: Claude Code config contains persona routing key after `connect --agent atlas` (or default).

---

## 10. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **IDE schema changes** (Continue rename `experimental.*` key likely; Cursor reshuffles `mcp.json`) | Per-IDE `schemaHash()` triggers warn-banner on mismatch; manual override flag `--ignore-schema-drift`. |
| R2 | **User-edit overwrite** during connect (race: user editing config while we merge) | File lock via `proper-lockfile` lib for duration of read+merge+write; abort with friendly error if lock contested. |
| R3 | **13 IDE drift simultaneous** in one user's machine — disconnect-all sequence partial-fails leaving manifest inconsistent | `disconnect --all` runs each IDE in tx-style: collect all drift prompts up front, then execute; partial failure rolls back manifest entries already removed. |
| R4 | **JSONC/YAML comment loss** breaks user trust | Use `jsonc-parser` edits API (preserves comments) + `yaml` lib `keepCstNodes` mode; round-trip property test gate. |
| R5 | **Sandboxed clients** (Flatpak Zed, Snap JetBrains) can't reach 127.0.0.1 nox-mem-api | `sandbox-probe.ts` detects + suggests LAN IP + Flatpak `--filesystem=host` override snippet. |
| R6 | **JetBrains XML corruption** — accidental write to XML config | T13 contract: NEVER touch XML, only sidecar JSON; unit test asserts XML mtime unchanged. |
| R7 | **P2 not yet merged** when P4 ships | Tier A degrades to "Tier A-shallow" — MCP block written, hooks block deferred with TODO comment + manifest flag `pendingP2: true`; `connect --re-link-hooks` re-runs hooks merge once P2 lives. |
| R8 | **L3 not yet ready** for persona leases | Persona routing key written but lease coordination disabled with feature flag; UX shows "leases pending L3" in `--list`. |

---

## 11. Timeline

**Aggregate:** ~28–32h sequential. Splits cleanly into 4 work-blocks for parallel execution:

| Block | Tasks | Hours | Notes |
|---|---|---|---|
| **B1 — Core scaffold** | T1, T3, T4 + mergers/{json,yaml,jsonc,toml} | 6h | Unblocks all per-IDE work |
| **B2 — Tier A** | T7, T8, T9 | 5h | Parallelizable after B1 |
| **B3 — Tier B (4 batches)** | T10, T11, T12, T13 | 6.5h | Parallelizable after B1 |
| **B4 — CLI + sandbox + tests + docs** | T5, T6, T14, T15, T16 | 10.5h | Sequential after B2+B3 |

**Critical path:** B1 → B4 = ~16.5h. Tier A/B in parallel saves ~5h vs strict sequential.

---

## 12. Open questions (non-blocking)

1. **Continue rename watch:** key `experimental.modelContextProtocolServers` may move to stable `mcpServers` in Continue v0.10+. Decide: pin to current key + warn-banner, or auto-detect both? → defer to T12 author call.
2. **JetBrains plugin discovery:** which JetBrains products (IDEA / WebStorm / GoLand / PyCharm) — install AI plugin in each? → T13: detect ALL installed JetBrains IDEs with AI plugin via plugin directory scan.
3. **Codex CLI version threshold:** which Codex CLI version supports event hooks? → T9: warn-not-fail below threshold; document min-version in CONNECT.md.
4. **`--scope=project`** semantics — does project-scope config override user-scope? Spec says "user is default"; project-scope writes to `./.nox-mem/connections.json`. → T5: implement both, project takes precedence at runtime.

---

## 13. Out-of-scope (locked)

Per spec §17 — NOT in v1:

- Vim / Emacs / Sublime / NeoVim / Helix
- Windows config paths (macOS + Linux only)
- Remote `nox-mem connect` (target machine ≠ nox-mem host)
- TUI wizard (CLI flags only)
- Slack / Discord "connect"
- Auto-update on IDE schema change (warn-banner only)

---

## 14. Handoff

When user confirms this kickoff:

1. Spawn executor agents per work-block (B1 → B2 ∥ B3 → B4).
2. Each task references this kickoff doc + spec §<n> for context.
3. Per-task PRs roll up to a single P4-impl tracking PR.

**Spec authority:** if this kickoff disagrees with `specs/2026-05-17-P4-connect-ide.md`, the spec wins. File an issue + amend.
