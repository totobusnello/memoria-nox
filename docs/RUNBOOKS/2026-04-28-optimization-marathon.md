# Optimization Marathon — 2026-04-28

> **Contexto:** sessão multi-stage de optimização após upgrade OpenClaw v.25 → v.26.
> **Resultado:** -74% turn latency, -99% .git size, -50% cron load, -62.5% heartbeat tokens, 0 skills missing, 0 token revogado.
> **Tempo total:** ~4h.
> **Reproducível:** todos comandos abaixo são idempotentes; rodar este runbook em cima de uma stack não-otimizada deve produzir resultados similares.

---

## Métricas finais

| Métrica | Início | Fim | Δ |
|---|---|---|---|
| OpenClaw versão | 2026.4.25 | **2026.4.26** | upgrade |
| Turn latency média | 39.8s (range 18-65s) | **10.4s** (range 6-14s) | **-74%** |
| Boot gateway | ~10s (v.25) | **5.7s** | -43% |
| Graph context tokens/turn | 5.158 | 3.542 | -31% |
| `.git` workspace | 11GB | **134MB** | **-99%** |
| Disk free `/` | 114GB | 116GB | +2GB total |
| chunks vectorized | 95.7% (5 orphans) | **100%** (62.840/62.840) | clean |
| Skills missing requirements | 39 | **0** | clean |
| Heartbeat turns/dia | 384 | 144 | -62.5% |
| Cron starts/dia (críticos) | ~1.008 | ~384 | -62% |
| Token revogado em 6 personas | sim (silent 401) | **resolvido** | fim do fallback dance |
| 3 services | active | active | OK |

---

## Sequência das mudanças

### Fase 1 — Upgrade OpenClaw v.25 → v.26

Tipo: **incremento puro** (não big-bang da v.25).

**Validação prévia:**
- Tarball offline diff confirmou `cleanStaleGatewayProcessesSync` body **byte-for-byte idêntico** entre v.25 e v.26 → monkey-patch reapply zero-risco.
- `package.json` deps **sem mudança** → zero risco peer-deps.
- Schema `agentRuntime.id = claude-cli` canonical preservado.

**Surpresas v.26:**
- Cerebras anunciado mas **não embarcado** no install final (0 matches em tarball).
- `openclaw plugins list --json` schema mudou: agora retorna `{registry, plugins, diagnostics}` (era array direto). Adapter jq pra `.plugins[]`.
- Boot inicial 49.7s (instalou 24 deps runtime — feature `OPENCLAW_PLUGIN_STAGE_DIR` layered da v.26). Boots subsequentes 5.7s.

**Comandos chave:**
```bash
# Stop services em ordem reversa
systemctl stop nox-mem-watcher nox-mem-api openclaw-gateway

# Install pinned
npm install -g openclaw@2026.4.26

# Reapply monkey-patch (hash mudou: CSJWMprl → BQxFGeFd)
bash /root/reapply-monkey-patch.sh

# Validar fn body (NÃO grep -c — false positive conhecido)
awk '/function cleanStaleGatewayProcessesSync/,/^}/' \
  /usr/lib/node_modules/openclaw/dist/restart-stale-pids-*.js | head -10
# Esperar: "// MONKEY-PATCH: Issue #62028 fratricide fix" + "return [];"

# Daemon reload + start sequencial
systemctl daemon-reload
systemctl start openclaw-gateway nox-mem-api nox-mem-watcher
```

### Fase 2 — Token sync nos 6 personas (debt da v.25)

**Problema descoberto:** auth-profiles dos 6 personas (nox/atlas/boris/cipher/forge/lex) tinham token Anthropic REVOGADO (`sk-ant-oat01-4S1jClmz...`). HTTP test retornava **401 invalid x-api-key**.

Token canônico (`sk-ant-oat01-Ry9UjsXu...`) estava em `credentials.json` + `ANTHROPIC_MAX_API_KEY` do `.env` + main agent — esses respondiam 429 (válido, rate-limited).

**Por que não estava estourando:** `agentRuntime.id = claude-cli` força roteamento via subprocess CLI (lê `credentials.json`, ignora auth-profiles em uso normal). Profile só seria tocado em path alternativo de fallback — risk silencioso de pay-per-token.

**Fix aplicado:**
```bash
TS=$(date +%Y%m%d-%H%M)
CANON=$(jq -r ".claudeAiOauth.accessToken" /root/.claude/.credentials.json)

mkdir -p /var/backups/auth-profiles-pre-token-sync-$TS
for a in nox atlas boris cipher forge lex; do
  cp /root/.openclaw/agents/$a/agent/auth-profiles.json \
     /var/backups/auth-profiles-pre-token-sync-$TS/$a.json
done

systemctl stop openclaw-gateway

for a in nox atlas boris cipher forge lex; do
  F=/root/.openclaw/agents/$a/agent/auth-profiles.json
  jq --arg t "$CANON" '
    .profiles["anthropic-max:default"].apiKey = $t |
    (if .profiles["anthropic-max:default"].key then .profiles["anthropic-max:default"].key = $t else . end) |
    (if .profiles["anthropic:default"].key then del(.profiles["anthropic:default"].key) else . end) |
    (if .profiles["anthropic:default"].token then del(.profiles["anthropic:default"].token) else . end) |
    .profiles["anthropic:default"].type = "token"
  ' $F > $F.tmp && mv $F.tmp $F
  chmod 600 $F
done

systemctl start openclaw-gateway
```

**Validação:** todos 6 profiles agora apontam pro canônico. HTTP test 200/429 (não 401).

### Fase 3 — Schema preservado + `bootstrapMaxChars` 6000 → 18000

Doctor reportou TOOLS.md (50%) e MEMORY.md (57%) truncados em 6000 chars. Aumento direto do per-file limit:

```bash
openclaw config set agents.defaults.bootstrapMaxChars 18000
openclaw config validate
systemctl restart openclaw-gateway

# Doctor recheck: "near limits" ao invés de "truncated"
```

**Efeito:** +14.652 chars de contexto por agent.

### Fase 4 — Fallback chain rule 5 compliant

Antes: `[openai-codex/gpt-5.5, gemini/gemini-2.5-pro]` (sem caminho zero-cost via CLI).
Depois: `[anthropic/claude-sonnet-4-6, openai-codex/gpt-5.5, gemini/gemini-2.5-pro]`.

```bash
openclaw config set agents.defaults.model.fallbacks \
  '["anthropic/claude-sonnet-4-6","openai-codex/gpt-5.5","gemini/gemini-2.5-pro"]'
```

**Efeito:** se Opus falha, cai pra Sonnet via claude-cli (zero-cost) antes de provedores pagos. Rule 5 do `CLAUDE.md`.

### Fase 5 — Sessions cleanup

Doctor reportou 213 orphan transcripts em `agents/main/sessions/`. Cleanup:

```bash
openclaw sessions cleanup --store /root/.openclaw/agents/main/sessions/sessions.json \
  --enforce --fix-missing
# Resultado: 82→72 entries

# Archive orphans com mtime > 3d (script archive-orphans.sh)
TS=$(date +%Y%m%d-%H%M)
ARCHIVE=/var/backups/orphan-transcripts-$TS
mkdir -p $ARCHIVE
jq -r 'to_entries[].value.sessionId // empty' \
  /root/.openclaw/agents/main/sessions/sessions.json | sort -u > /tmp/active-ids.txt
ls /root/.openclaw/agents/main/sessions/*.jsonl | xargs -n1 basename | \
  sed -E 's/\.(trajectory\.)?jsonl$//' | sort -u > /tmp/fs-ids.txt
comm -23 /tmp/fs-ids.txt /tmp/active-ids.txt > /tmp/orphan-ids.txt
NOW=$(date +%s)
while IFS= read -r id; do
  for ext in jsonl trajectory.jsonl; do
    F=/root/.openclaw/agents/main/sessions/$id.$ext
    [ -f "$F" ] || continue
    AGE=$(( (NOW - $(stat -c %Y "$F")) / 86400 ))
    [ $AGE -gt 3 ] && mv "$F" "$ARCHIVE/"
  done
done < /tmp/orphan-ids.txt
```

**Resultado:** 270→241 jsonl files, ~9MB liberados.

### Fase 6 — Skills cleanup (39 missing → 0)

OpenClaw lacks native `skills disable`. Movemos dirs pra `_disabled/` via script idempotente.

**Trap descoberta:** dirs em `/usr/lib/node_modules/openclaw/dist/extensions/<x>/` são **plugins**, não skills. Script v1 acidentalmente movia plugins quando skill name coincidia (`bluebubbles`, `voice-call`) → gateway config inválido + restart loop.

**Fix em v2:** safeguards pra detectar `openclaw.plugin.json` na raiz e pular.

**Script idempotente:** `/root/.openclaw/scripts/disable-unused-skills.sh` (rodar pós cada `npm install -g openclaw@<X>`).

```bash
# Lista de 39 skills missing requirements
SKILLS="1password amazon-product-api-skill apple-notes apple-reminders bear-notes \
        blucli bluebubbles camsnap eightctl failure-memory gemini ggshield-scanner \
        gifgrep goplaces himalaya imsg model-usage morning-email-rollup nano-pdf \
        obsidian openai-whisper openhue oracle ordercli peekaboo research \
        restart-guard sag session-logs sherpa-onnx-tts songsee sonoscli \
        spotify-player summarize things-mac trello video-frames voice-call wacli"

DISABLED_DIR=/root/.openclaw/skills/_disabled
mkdir -p $DISABLED_DIR

SEARCH_PATHS=(
  /usr/lib/node_modules/openclaw/skills
  /root/.openclaw/skills
  /root/.openclaw/workspace/skills
  /root/.openclaw/extensions/graph-memory/node_modules/openclaw/skills
)
EXT_PATTERN=/usr/lib/node_modules/openclaw/dist/extensions/*/skills

for skill in $SKILLS; do
  for sp in "${SEARCH_PATHS[@]}"; do
    while IFS= read -r P; do
      [ -z "$P" ] && continue
      [ -f "$P/openclaw.plugin.json" ] && continue  # SAFEGUARD
      DEST="$DISABLED_DIR/$skill"
      [ -d "$DEST" ] && DEST="$DISABLED_DIR/${skill}-$(date +%H%M%S)"
      mv "$P" "$DEST" 2>/dev/null
    done < <(find "$sp" -maxdepth 2 -type d -name "$skill" 2>/dev/null | grep -v "_disabled")
  done
  for sp_ext in $EXT_PATTERN; do
    P="$sp_ext/$skill"
    [ -d "$P" ] && [ ! -f "$P/openclaw.plugin.json" ] && \
      mv "$P" "$DISABLED_DIR/${skill}-ext-$(basename $(dirname $sp_ext))" 2>/dev/null
  done
done
```

**Resultado:** 88 → 49 skills total, 49 eligible / **0 missing** / 0 blocked.

### Fase 7 — Cron + heartbeat optimization

**Heartbeats per-agent (ajustado em `agents.list[].heartbeat.every`):**
- nox/forge/boris: 15m → **30m** (mantém alta granularidade)
- atlas/cipher/lex: 15m → **60m** (work bursty, não exige polling rápido)
- Total: 384 → 144 turns/dia (-62.5%)

```bash
declare -A TARGETS=([1]=30m [2]=60m [3]=30m [4]=60m [5]=30m [6]=60m)
declare -A NAMES=([1]=nox [2]=atlas [3]=boris [4]=cipher [5]=forge [6]=lex)
for i in 1 2 3 4 5 6; do
  openclaw config set "agents.list[$i].heartbeat.every" "${TARGETS[$i]}"
done
```

**Canary bundle 15-min** (consolidou 3 cron entries em 1):
- Antes: `gateway-drift-check.sh */10` + `check-monkey-patch.sh */15` + `check-schema-invariants.sh */15` = 288 cron starts/dia
- Depois: `canary-bundle-15min.sh */15` = 96 cron starts/dia

Script em `/root/.openclaw/scripts/canary-bundle-15min.sh` (cada componente em subshell, falhas independentes, log unificado via `logger -t nox-canary-bundle`).

**Frequency reductions:**
- `health-probe.sh`: */5 → */10 (288→144/dia)
- `bvv-extract.py`: */5 → */15 (288→96/dia, monitor WhatsApp obra BVV)
- `heartbeat-sync.sh`: */15 → */30 (96→48/dia)

**Collision fixes:**
- `0 2 *` (backup-all.sh + ckpt save) → ckpt move pra `5 2 *`
- `0 9 * * 1` (forge-cc + version-monitor) → version-monitor move pra `5 9 * * 1`

### Fase 8 — Plugin browser + chromium zombie

Descoberta: 4 chromium processes idle (~900MB RAM), 48min uptime, parent PID=1 (orphan), zero uso em 30 dias.

```bash
pkill -TERM -f chromium
# Plugin browser permanece enabled — relança lazy via CDP se algum agent invocar
```

**Resultado:** -900MB RAM permanente. Plugin não respawnou (lazy-load comprovado).

### Fase 9 — Backups + journal cleanup

```bash
# Backups antigos
find /var/backups -maxdepth 2 -mtime +14 -type f \
  | grep -vE "dpkg.status|placeholder" \
  | xargs rm -f
find /var/backups -maxdepth 2 -type d -empty -delete

# Journal vacuum 7d
journalctl --vacuum-time=7d

# graph-memory WAL checkpoint
sqlite3 /root/.openclaw/graph-memory.db "PRAGMA wal_checkpoint(TRUNCATE);"
# 5.1MB WAL → 0 (next writes faster)
```

### Fase 10 — graph-memory tuning (-74% turn latency)

Antes:
```json
{
  "recallMaxNodes": 6,
  "recallMaxDepth": 2,
  "freshTailCount": 10
}
```

Depois (conservative):
```bash
openclaw config set plugins.entries.graph-memory.config.recallMaxNodes 4
openclaw config set plugins.entries.graph-memory.config.recallMaxDepth 1
systemctl restart openclaw-gateway
```

**Validação medida:**
- Graph context: 5.158 → **3.542 tokens/turn** (-31%)
- Turn latency: 39.8s → **10.4s** (-74%, mais que esperado)

### Fase 11 — Git workspace cleanup (11GB → 134MB)

#### Stage A — git gc safe

`memory/mac-docs/` 11GB de docs pessoais (PPR/SELJ paralímpico, processos VERRE, etc) versionado em git, inflando packs (`tmp_pack_KZKfFo` 1.3GB garbage + 7.8GB pack consolidado).

```bash
cd /root/.openclaw/workspace

# .gitignore
echo "memory/mac-docs/" >> .gitignore

# Remove from tracking (NOT from filesystem)
git rm -r --cached memory/mac-docs

git -c user.email=root@srv1465941 -c user.name=root commit \
  -m "chore(workspace): exclude memory/mac-docs from git tracking"

# Aggressive gc + prune
git gc --aggressive --prune=now
```

**Resultado:** 11GB → **8.7GB** (1 pack consolidado, garbage removido). Files físicos intactos. Auto-commits nightly param de inflar.

#### Stage B — git filter-repo

```bash
apt install -y git-filter-repo

cd /root/.openclaw/workspace
TS=$(date +%Y%m%d-%H%M)
tar czf /var/backups/workspace-git-pre-rewrite-$TS.tar.gz .git
REMOTE_URL=$(git remote get-url origin)

git filter-repo --invert-paths --path memory/mac-docs/ --force

git remote add origin "$REMOTE_URL"
git push --force origin main
```

**Resultado:** 8.7GB → **134MB** (-99%). 773 commits rewritten em 1.5s. GitHub remote sincronizado.

**Validação prévia ao push:**
- Smoke test memory neural: `nox-mem search "relatório paralimpico"` retornou conteúdo de mac-docs ✓
- Search Mac local: 0 clones do `nox-workspace.git` (safe pra force push)
- Backup tar criado antes do filter-repo

### Fase 12 — Legacy `claude-cli/claude-haiku-4-5` removido

`FailoverError: Unknown model` aparecia em logs. Vestígio v.23 em `agents.defaults.models`.

```bash
openclaw config unset 'agents.defaults.models[claude-cli/claude-haiku-4-5]'
systemctl restart openclaw-gateway
```

**Sintaxe importante:** `bracket notation` necessário pra keys com `/`. Aspas dentro do path NÃO funcionam.

---

## Scripts criados/atualizados

| Script | Propósito |
|---|---|
| `/root/.openclaw/scripts/canary-bundle-15min.sh` | 3 canaries consolidados (gateway-drift + monkey-patch + schema-invariants) |
| `/root/.openclaw/scripts/disable-unused-skills.sh` | mv 39 skills missing pra `_disabled/` (idempotente, com plugin safeguard) |
| `/root/.openclaw/scripts/restart-gateway.sh` | Restart com delay 8s (forge pode invocar via bash skill sem se matar) |
| `/root/.openclaw/agents/forge/TOOLS.md` | + seção "Restart do OpenClaw Gateway" com instrução pro forge |

---

## Backups disponíveis (rollback)

| Backup | Tamanho | Conteúdo |
|---|---|---|
| `/var/backups/workspace-git-pre-rewrite-20260428-1212.tar.gz` | 8.7GB | `.git` antes do filter-repo |
| `/var/backups/preupgrade-v26-*.tar.gz` | configs | Configs pré-upgrade v.26 |
| `/var/backups/auth-profiles-pre-token-sync-20260428-*` | KB | 6 auth-profiles pré-sync |
| `/var/backups/openclaw.json.bak` | KB | Auto-backup de cada `config set` |
| `/var/backups/orphan-transcripts-20260428-*` | MB | 11+29 jsonl arquivados |
| `/var/backups/nox-mem-pre-vacuum-20260428-1203.db` | 1015MB | DB nox-mem pré-VACUUM (idempotente — 0MB freed, mantém pra audit) |

---

## Lições aprendidas

### L1 — Tarball diff offline antes de tocar VPS

`npm pack` ambas versões + `comm` + `diff` na fn crítica. 5min local que evitam descoberta de breaking change em Phase 4.

### L2 — `grep -c "MONKEY_PATCH"` é falso positivo

Marker tem hífen (`MONKEY-PATCH`) não underscore. **Sempre validar pelo CORPO da função:**
```bash
awk '/function cleanStaleGatewayProcessesSync/,/^}/' restart-stale-pids-*.js | head -10
```

### L3 — Schema OpenClaw v.26 mudou `plugins list --json`

De array direto pra `{registry, plugins, diagnostics}`. Adapter jq pra `.plugins[]`.

### L4 — Skill names podem colidir com plugin names em `extensions/`

Bluebubbles, voice-call têm `extensions/<name>/` (plugin) e `extensions/<plugin>/skills/<name>/` (skill). Script v1 quebrou gateway ao mover plugin dir. **Safeguard:** skip dirs com `openclaw.plugin.json`.

### L5 — Force push em main é destrutivo no remote

Sandbox bloqueia automaticamente. Aprovação explícita do user requerida. **Backup tar prévio é mandatory** (rollback safe se algo errado pós-push).

### L6 — graph-memory tuning rende -74% latency

Default `recallMaxNodes: 6 / recallMaxDepth: 2` = 5.158 tokens overhead permanente em **todo turn**. Reduzir pra `4 / 1` derruba pra 3.542 tokens, latency 40s → 10s. Ganho 4× maior que estimado por tokens (LLM thinking time não é linear).

### L7 — `openclaw config unset` requer bracket notation pra keys com `/`

```bash
# Errado (não casa)
openclaw config unset 'agents.defaults.models."claude-cli/claude-haiku-4-5"'

# Certo
openclaw config unset 'agents.defaults.models[claude-cli/claude-haiku-4-5]'
```

### L8 — VACUUM em SQLite saudável é no-op

`nox-mem.db` 1015MB pré + 1013MB pós VACUUM. Cron `prune-pre-op-snapshots.sh */7d` já mantém o DB enxuto. **VACUUM só vale se cron prune está quebrado**.

### L9 — Backups acumulados podem mascarar disk leak

`/var/backups/` 2.3GB inicial era 1.5GB nox-mem (cron já pruna 7d retention) + 700MB preupgrade-v25. **Verificar antes de assumir cleanup vai render** — pode estar tudo dentro da retention.

### L10 — Files com mtime <X dias ≠ "ativos"

JSONL transcripts com mtime <24h são apenas WRITES recentes. Compaction preflight em 30MB **bloqueia turn** se transcript ultrapassa, então threshold dev ser **acima do steady state** (aplicamos 50MB pra forge que tinha 36MB). Saber baseline antes de ativar.

---

## Backlog (não feito, baixo ROI vs risco)

| Item | Por que não | Quando reabrir |
|---|---|---|
| AGENTS.md slim (~7KB injection saved) | OpenClaw NÃO concatena workspace + per-agent (provei via `grep "Time de Agentes" atlas-trajectory.jsonl` = 0 matches). Só per-agent é injetado. Sem dedupe estrutural possível. Compactação interna risk médio, ganho cosmético. | Se sistema começar a truncar bootstrap (hoje 36KB / 60KB = 60% capacity). |
| graph-memory mais agressivo (`recallMaxNodes: 4→3`) | Latency já em 10s, diminishing returns. | Só se base growr pra >5000 nodes e latency voltar a subir. |
| JSONL consolidate manual por agent (transcripts 36-50MB) | Bloqueante por agent (~20min cada). Compaction preflight 50MB cuida automaticamente quando crescerem. | Se algum agent passar 50MB sem compaction disparar. |

---

## Como reproduzir tudo isso (futuro upgrade v.27+)

1. Ler este runbook + `docs/UPDATE-TO-V25-GUIDE.md` + `docs/UPDATE-TO-V26-GUIDE.md`
2. Tarball diff offline
3. Phase 0-7 do upgrade (do guia v.26)
4. Phase pós-upgrade — rodar:
   - `bash /root/.openclaw/scripts/disable-unused-skills.sh` (skills cleanup)
   - `bash /root/.openclaw/scripts/canary-bundle-15min.sh` (testar canary)
   - HTTP test do token canônico (rule 5)
   - `openclaw doctor --non-interactive` (sanity check)
5. Se nada quebrou em 30min, sistema OK.

---

## Referências

- `docs/UPDATE-TO-V26-GUIDE.md` — guia operacional v.26
- `plans/2026-04-28-openclaw-v2026.4.26-upgrade.md` — plan original da sessão
- `docs/RUNBOOKS/openclaw-upgrade-runbook.md` — runbook genérico
- `docs/RUNBOOKS/openclaw-v25-upgrade-postmortem.md` — post-mortem da v.25
- `CLAUDE.md` rules 5, 6, 9, 11, 12, 13, 14, 15
