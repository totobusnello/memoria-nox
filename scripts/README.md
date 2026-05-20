# scripts/ — Operational Scripts

This directory contains bash scripts for operational maintenance of the memoria-nox repo and VPS. All scripts depend only on standard Unix tools + git — no Node.js or npm required unless noted.

---

## cleanup-worktrees.sh

Removes accumulated Claude agent worktrees under `.claude/worktrees/agent-*`.

### Why this exists

Each wave session dispatches 10–30 agents, each in an isolated git worktree. After PRs are merged (or abandoned), these worktrees accumulate indefinitely. After 3 wave sessions the directory grows to 50+ entries, consuming disk and making `git worktree list` noisy.

### When to run

After each wave session completes and PRs are either merged or closed:

```bash
# Preview what would be removed (safe, no changes):
./scripts/cleanup-worktrees.sh --dry-run

# Remove merged worktrees only (recommended daily job):
./scripts/cleanup-worktrees.sh --force --merged-only

# Full cleanup — merged + clean unmerged, all ages:
./scripts/cleanup-worktrees.sh --force

# Full cleanup — keep worktrees newer than 1 day:
./scripts/cleanup-worktrees.sh --force --keep-days 1
```

### Safety guarantees

| Situation | Behavior |
|-----------|----------|
| Dry-run mode | Default when `--force` not passed. Prints `WOULD REMOVE` but mutates nothing. |
| Uncommitted changes | Worktree is **skipped** with a warning. Use `--force-dirty` to override (rarely needed). |
| Unique commits not in main | Worktree is **kept** — the work has not been merged. |
| Agent lock (`claude agent …`) | Lock is removed automatically before deletion. |
| Foreign lock (non-agent reason) | Worktree is **skipped** — manual intervention required. |
| Main worktree | Never touched. Only paths under `.claude/worktrees/agent-*` are candidates. |
| Named worktrees outside .claude | Never touched (e.g., `memoria-nox-P1-answer-spec`). |

### Recovery if a worktree is accidentally removed

1. **Branch still exists** (most common): the branch survives worktree removal.
   ```bash
   git checkout <branch-name>
   # Or create a new worktree:
   git worktree add /tmp/recovery-wt <branch-name>
   ```

2. **Branch was also deleted**: find the tip via reflog:
   ```bash
   git reflog | grep <branch-keyword>
   git checkout -b <branch-name> <sha>
   ```

3. **Admin files corrupted** (very rare, only if script was interrupted mid-prune):
   ```bash
   git worktree repair
   ```

### Flags reference

```
--dry-run       Preview only (default when --force not passed)
--force         Actually remove worktrees
--force-dirty   Remove even worktrees with uncommitted changes (use sparingly)
--merged-only   Only remove branches already merged to main
--keep-days N   Skip worktrees newer than N days
--verbose       Extra per-worktree decision logging
```

Environment variables: `DRY_RUN`, `KEEP_DAYS`, `WORKTREE_BASE`, `GIT_MAIN_BRANCH`.

---

## cleanup-worktrees.test.sh

Smoke tests for `cleanup-worktrees.sh`. Creates isolated temporary git repos, exercises 8 scenarios, and validates outcomes.

```bash
./scripts/cleanup-worktrees.test.sh
./scripts/cleanup-worktrees.test.sh --verbose
```

Test scenarios covered:

| # | Scenario |
|---|----------|
| 1 | Dry-run mode — removes nothing even for merged worktrees |
| 2 | Merged worktree is removed with `--force` |
| 3 | Unmerged worktree with unique commits is kept |
| 4 | `--merged-only` skips clean unmerged worktrees |
| 5 | Agent-locked + merged worktree is unlocked and removed |
| 6 | `--keep-days 9999` keeps recently committed worktrees |
| 7 | Empty worktrees directory exits cleanly without error |
| 8 | Dirty merged worktree is skipped without `--force-dirty` |

---

## vps-healthcheck.sh

Detecta IP swaps ou outages na VPS nox-mem cedo — criado após incident 2026-05-20 (Hostinger floating-IP rebalance silencioso, ~30min de downtime).

### Checks (em ordem)

| # | Check | Falha → exit code |
|---|-------|-------------------|
| 1 | Ping (3 packets, 2s timeout) | 1 |
| 2 | SSH `root@<IP>` — executa `hostname` | 2 |
| 3 | `GET /api/health` porta 18802, valida `.vectorCoverage` | 3 |

### Uso

```bash
# Teste manual (com output colorido):
./scripts/vps-healthcheck.sh --ip 187.77.234.79

# Usando IP do arquivo .vps-current-ip (default):
./scripts/vps-healthcheck.sh

# Cron silencioso a cada 15 min com alerta macOS:
*/15 * * * * /Users/lab/Claude/Projetos/memoria-nox/scripts/vps-healthcheck.sh --quiet || /usr/bin/osascript -e 'display notification "VPS unreachable" with title "nox-mem"'

# Com webhook customizado em caso de falha:
./scripts/vps-healthcheck.sh --quiet --alert-cmd 'curl -s -X POST https://hooks.slack.com/... -d "{\"text\":\"VPS down\"}"'
```

### IP atual

O IP atual da VPS fica em `.vps-current-ip` (gitignored — atualizar manualmente após rebalance do Hostinger).

```bash
echo "187.77.234.79" > .vps-current-ip
```

### Flags

```
--ip <IP>          IP da VPS (sobrescreve env VPS_IP e arquivo .vps-current-ip)
--quiet            Output somente em falha (ideal para cron)
--alert-cmd <CMD>  Comando shell executado quando qualquer check falha
--help             Exibe help completo
```

---

## Other scripts

| Script | Purpose |
|--------|---------|
| `activate-salience.sh` | Flip `NOX_SALIENCE_MODE=active` on VPS and restart API |
| `analyze-shadow-telemetry.sh` | Aggregate `search_telemetry` shadow vs active comparison |
| `check-nox-mem.sh` | Quick health check: vectorCoverage, schema version, ops audit |
| `deploy-validator/` | Node.js CI helper for deployment smoke tests |
| `migrate-flat-to-entities.py` | One-time: migrate flat memory files to entity file format |
| `migrate-projects-to-entities.py` | One-time: migrate project chunks to entity files |
| `rollback-zero-downtime.sh` | Rollback OpenClaw upgrade with zero restart overlap |
| `sync-obsidian-vault.sh` | Rsync Obsidian vault from VPS to local (dry-run safe) |
| `upgrade-zero-downtime.sh` | Zero-downtime OpenClaw upgrade with monkey-patch reapply |

---

*All scripts assume a bash 4+ interpreter. macOS ships bash 3 at `/bin/bash` — use `/usr/bin/env bash` (done in all scripts here) and install bash 5 via Homebrew if test scripts fail on macOS 10.x.*
