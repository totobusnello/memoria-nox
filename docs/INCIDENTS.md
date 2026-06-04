# nox-mem — Incident Log

> Histórico de incidents do **nox-mem core** (chunks, vectorize, reindex, schema migration, semantic layer) e **graph-memory plugin** (KG extract/recall, plugin custom v1.5.8). Incidents de plataforma OpenClaw (gateway, fratricide, RelayPlane, credentials) ficam em `~/Claude/Projetos/openclaw-vps/infra/docs/INCIDENTS.md`.

## 2026-06-04 (noite) — Semantic layer down: créditos prepaid Gemini esgotados

**Severidade:** média (degradação semântica ~1h40, zero perda de dado). **Detecção:** canary semântico (`semantic-canary.sh`, :22/:52) → Discord #nox-chief-of-staff às 18:22; Toto reportou via screenshot 19:30.

**Timeline:** 17:52 OK → 18:22 primeiro RED (`total=2 semantic=0 fts=0` + self-heal FAILED `20 errors`) → 19:39 root cause confirmado (`429 RESOURCE_EXHAUSTED: prepayment credits depleted` em TODAS as 3 keys do .env) → 19:52 key nova do projeto com saldo → 19:56 GREEN (`total=10 semantic=8`).

**Root cause:** créditos prepaid do(s) projeto(s) Google esgotados — queimados majoritariamente pela vetorização do bulk import de jun (~34k chunks × 3072d, dos quais 5.6k eram lixo `_retired` já removido). NÃO relacionado à limpeza de corpus do mesmo dia (KNN local validado saudável durante o diagnóstico).

**Lições:**
1. **Key nova não recarrega saldo** — crédito prepaid é por PROJETO; rotacionar key no mesmo projeto = mesmo 429. Fix real = projeto com billing ativo (`projects/692943619288`) e key dele.
2. **Formato novo de key Gemini `AQ.`** — funciona via `?key=` e `x-goog-api-key` (não Bearer). nox-mem compatível sem mudança de código.
3. **Canary funcionou como projetado** — detectou em ≤15min, tentou self-heal, alertou no canal certo. A query PT-BR anti-literal (design 2026-04-19) provou o valor: FTS continuou respondendo e mascararia o problema em queries keyword.
4. **Bulk imports têm custo de embedding material** — allowlist do watcher (instalada hoje) também é controle de custo, não só de qualidade.
5. **Degradação graciosa validada em prod:** FTS-only manteve briefs/agentes/MCP operando.

**Follow-ups:** monitorar saldo do projeto novo (alerta de billing no Google Console); considerar canary de saldo (embed 1 token diário com threshold de alerta); 2.074 vec rows órfãs (`vec_chunks` 96.991 vs map 94.917) — limpeza menor com snapshot, não relacionada ao RED.

---

## 2026-06-04 — Corpus pollution: watcher sem allowlist ingeriu 5.6k chunks de _retired/

**Severidade:** baixa (qualidade, não outage). **Detecção:** pergunta do Toto ("por que docs mostram 69k e prod tem 100.5k?") durante gate do F1 /api/brief.

**Root cause:** bulk import do Mac workspace (~jun/2026) depositou `shared/imports/Claude/` inteiro no workspace; `nox-mem-watch.sh` (inotifywait) não tinha NENHUMA exclusão de diretório → 5.626 chunks de `_retired/` (skills aposentadas, 502 arquivos) entraram no corpus e competiam no ranking (incl. /api/brief scope=global).

**Fix (ordem fonte→dado, autorizada Toto):**
1. **B** — allowlist guard no watcher (PR nox-workspace#3, 2657f334): case/esac no loop bloqueia `_retired/`, `node_modules/`, `.git/`, `dist/`, `__pycache__/`, `*.bak`, caches. Guard no loop (não `--exclude`) porque `--exclude`/`--include` do inotifywait são mutuamente exclusivos. Dir fonte movido pra `/root/archive-quarantine/Claude-_retired-20260604` (reversível).
2. **A** — DELETE com snapshot pré-op (`/var/backups/nox-mem/pre-op/cleanup-retired-20260604-150508.db`, 1.7GB): 5.626 chunks removidos. ⚠️ Lição operacional: DELETE em chunks **não roda no sqlite3 CLI puro** (`no such module: vec0` — trigger cascade referencia virtual table); rodar via better-sqlite3 + `sqliteVec.load()` (stack do app).

**Pós-op:** 94.936 chunks, vec 94.929/94.936, orphans 0, salience active. Brief global melhorou visivelmente (slots de skills mortas → decisões reais).

**Prevenção estrutural:** allowlist de import é requisito do Fluxo D (feeders) do PRD session-priming-loop §13.

---

## 2026-06-02 ~18:00 BRT — Hostinger CPU throttling aborts Wave 2 capstone bench (D76); infrastructure constraint, not scientific failure

### Severity: yellow — benchmark abort; no data loss; VPS operational throughout

### TL;DR

Wave 2 Phase 2 capstone bench (PR #426, IterB ReAct + Wave C triple on Gemini-3-flash, n=3,121 5-batch) was dispatched Sun 2026-05-31 ~17:40 BRT and aborted Tue 2026-06-02 ~17:55 BRT after 48h elapsed. Batch 005 completed 0/50 questions in 23h under sustained Hostinger CPU steal (51-97%). Three mitigation rounds failed to restore acceptable throughput. Capstone closed via abandon comment on PR #426. **Infrastructure constraint, NOT scientific failure** — the underlying IterB ReAct mechanism remains validated (PR #419, +2.01pp clean F_MH lift). D76 cravado. Memory: `[[capstone-aborted-hostinger-throttling-indeterminate]]`.

### Timeline

```
Sun 2026-05-31 ~17:40 BRT   capstone bench dispatched via tmux wave2-capstone-7a1cadf2 (PID 2194486)
Sun 2026-05-31 ~18:00 BRT   CPU steal first observed: 8.5%
Sun 2026-05-31 ~20:00 BRT   CPU steal escalates: ~50-60%
Mon 2026-06-01 ~08:00 BRT   batch 005 still at 0/50 questions (~14h elapsed, zero progress)
Mon 2026-06-01 mitigation 1 taskset + nice + ORT thread caps + YAML tuning
Mon 2026-06-01 ~18:00 BRT   CPU steal 97% peak (VPS shared host contention)
Mon 2026-06-01 ~22:00 BRT   first VPS reboot attempt — steal drops to 21% temporarily
Tue 2026-06-02 ~06:00 BRT   CPU steal back to 50%+ (contention resumed post-reboot)
Tue 2026-06-02 mitigation 2 second reboot + .env caps rolled back
Tue 2026-06-02 ~12:00 BRT   batch 005 still 0/50 questions (23h, zero progress confirmed)
Tue 2026-06-02 ~17:55 BRT   capstone abort decision; PR #426 closed with abandon comment
Tue 2026-06-02 ~18:30 BRT   openclaw re-enabled; VPS healthy after 24h cooldown confirmation
```

### Root cause

Hostinger shared VPS CPU steal contention — co-tenant workloads saturating physical host CPU. Steal oscillated 8.5% → 97% → 21% (post-reboot) → 50%+ (resumed). Not a nox-mem application bug; not a bench methodology issue; not a scientific signal about the IterB + Wave A/B/C composability hypothesis.

### Cost incurred

~$20-25 Gemini API spend on capstone retry rounds before abort.

### Environmental state during incident

- openclaw service was disabled during bench run (resource isolation)
- .env CPU caps added (ORT_NUM_THREADS + other thread limits — `[[ort-num-threads-cap-during-capstone]]`)
- 23G disk freed before bench start

### Recovery

1. openclaw re-enabled
2. .env CPU caps rolled back to baseline
3. VPS healthy confirmed (24h cooldown from CPU steal; `nox-mem-api` responsive; healthcheck green)
4. Disk usage back to normal headroom

### Scientific integrity note

D76 distinguishes infrastructure abort from scientific failure. The 3-knob NO-REPLICATE pattern (D75, PRs #423-#425) is a real research finding independently of the capstone. The IterB architectural lock finding (`[[iterB-architectural-lock-short-circuits-wave-a-knobs]]`) is also a real finding — the capstone would have required explicit guard removal patch regardless of infrastructure. The capstone is deferred to stable infrastructure (Q2/Q3 cycle), not abandoned as a hypothesis.

### Fix / prevention

- Future capstone benches: use dedicated cloud run (GCP/AWS spot) or schedule for off-peak Hostinger hours
- CPU steal monitoring: add `/api/health` check for host-level steal metric before dispatching long-running benches
- PR #426 retain as draft for future resumption (architectural lock patch required)

---

## 2026-05-26 ~02:00 UTC (23:00 BRT Mon 25/mai) — RECORRÊNCIA #4 — atlas reindex wipe (69.135 → 756 chunks); kill-switch havia sido removido entre 23/mai e 25/mai

### Severity: 🔴 red — data-loss event em produção (recuperado sem perda via snapshot pre-op)

### TL;DR
Mesmo bug do incident anterior (2026-05-23) recorreu **48h depois** porque o flag `/root/.openclaw/DISABLE_AGENT_REINDEX` instalado em 23/mai 23:32 BRT foi **removido em algum momento antes de 25/mai 23:00 BRT** (responsável + razão desconhecidos — investigar). Detecção pelo mesmo canary; recovery em ~15 min; flag reinstalado em 2026-05-27 15:51 BRT (sessão de root-cause #18) com TTL aberto até P1+P2 shipped.

### Sintoma (idêntico ao prior)
```
⚠️ nox-mem schema invariant failed: section NOT NULL count=0
⚠️ nox-mem schema invariant failed: section=compiled count=0
```
Alerta em **2026-05-25 23:15:04 BRT** (cron schema-invariants */15min).

### Timeline forense (BRT — confirmed server tz = America/Sao_Paulo)
```
22:45 BRT Mon May 25  schema-invariants OK (último good)
23:00:00 BRT          cron 0 23 → nightly-maintenance.sh START
23:00:06 BRT          Phase 2 atlas: withOpAudit cria snapshot reindex-atlas-20260526020006 (1.2GB!)
                      ^^^ snapshot 1.2GB confirma: atlas reindex está operando no MAIN DB,
                          não no atlas DB (atlas DB normal = ~64MB, evidenciado por boris/cipher/forge/lex/nox snapshots)
23:10:28 BRT          reindex boris (snapshot 64MB - correto)
23:10:38 BRT          reindex cipher (64MB)
23:10:49 BRT          reindex forge (64MB)
23:10:59 BRT          reindex lex (64MB)
23:11:10 BRT          reindex nox (64MB)
23:15:04 BRT          ⚠️ schema-invariants FAIL detected, Telegram alert dispatched
23:22:57 BRT          post-incident DB preserved (756 chunks) → /tmp/post-incident-756chunks-20260525-232257.db
~23:25-23:30 BRT      restored from reindex-atlas snapshot via safeRestore()
23:30:02 BRT          schema-invariants OK (recovered)
```

### Root cause (refinado vs entry anterior)

A entry anterior (2026-05-23) descrevia o sintoma — "reindex agent-por-agent sobrescreve a tabela chunks inteira". Investigação de root cause em **2026-05-27** (task #18) revela **3 bugs compostos**:

**Bug primário — OPENCLAW_WORKSPACE não é respeitado pelo `nox-mem reindex` na resolução de db_path.** Script chama:
```bash
NOX_DB_SOURCE=atlas OPENCLAW_WORKSPACE=/root/.openclaw/agents/atlas /usr/local/bin/nox-mem reindex
```
Deveria operar em `/root/.openclaw/agents/atlas/tools/nox-mem/nox-mem.db` mas opera em `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` (**MAIN**). Snapshot é nomeado com prefix `reindex-atlas` (porque `NOX_DB_SOURCE=atlas` afeta naming) — cria audit trail enganoso.

**Forensic proof:** `/var/backups/nox-mem/pre-op/` snapshots from Mon May 25 23:00 BRT:

| Agent | Snapshot size | Conclusão |
|---|---:|---|
| atlas | **1.2 GB** 🔴 | = MAIN DB size — bug fired |
| boris | 64 MB | ✅ atlas-agent DB normal |
| cipher | 64 MB | ✅ |
| forge | 64 MB | ✅ |
| lex | 64 MB | ✅ |
| nox | 64 MB | ✅ |

Padrão histórico confirmado: snapshots `reindex-atlas-*` aparecem com **1.2GB** em **2026-05-24 09:05 BRT** (status `crashed` — bug fired antes, dano parcial) e **2026-05-25 23:00 BRT** (status sem audit row — bug fired, dano completo). Sat May 23 23:11 BRT `reindex-atlas` é 64MB = atlas DB correto (bug não disparou nessa janela).

**Bug secundário — reindex.ts não rota entity files via `ingestEntityFile()`** (memory `[[reindex-must-route-entity-files]]`). Quando o reindex hits main, wipa `section`/`retention_days`/`section_boost` metadata em entity chunks. Combinado com deleção em massa, deixou 756 chunks + section=NULL.

**Bug terciário — withOpAudit insert silently failed.** Snapshot file `reindex-atlas-20260526020006-13100-2051c30f038d42a0a2d93c3466a9b55c.db` existe no disco mas **NÃO há linha correspondente em `ops_audit`**. Provável `[[withopaudit-trigger-raise-ignore-swallows-insert]]` (started_at type mismatch trigger ABORT silencioso). Audit trail comprometido.

### Mistério: kill-switch removido entre 23/mai e 25/mai
O flag `/root/.openclaw/DISABLE_AGENT_REINDEX` foi instalado em **2026-05-23 ~23:32 BRT** durante recovery do incident anterior, com nota explícita "**NÃO remover o flag até o `nox-mem reindex` ser corrigido**". Em **2026-05-25 23:00 BRT** o flag não existia (senão Phase 2 teria pulado). 48h-janela entre 23-25/mai — **investigar quem/como removeu o flag** (audit de comandos via shell history, /root activity log, sessions Claude Code que acessaram /root/.openclaw/).

### Recovery (idêntico ao prior, conferido)
1. Preserva DB degradado → `/tmp/post-incident-756chunks-20260525-232257.db`
2. `systemctl stop nox-mem-api`
3. Restore snapshot `reindex-atlas-20260526020006` (1.2GB MAIN snapshot) via `safeRestore()` → MAIN DB
4. Remove WAL/SHM órfãos
5. `systemctl start nox-mem-api`
6. Validação: 69.135 chunks, compiled=183, frontmatter=183, timeline=383, integrity ok, vectorCoverage 100%

### Mitigação P0 reinstalada (2026-05-27 15:51 BRT)
```bash
echo "Disabled 2026-05-27 by Toto + Claude session — root cause: nox-mem reindex bypasses OPENCLAW_WORKSPACE, atlas reindex hits main DB. See incident Mon 2026-05-25 23:00 BRT. Reenable only after P1+P2 fix shipped." > /root/.openclaw/DISABLE_AGENT_REINDEX
```

**TTL aberto** até P1+P2 shipped (vide tasks #20, #21).

### Hoje à noite (Wed 2026-05-27 23:00 BRT) — RISK ASSESSMENT
Wed DOM=27 (odd) → Phase 2 condition `[ $((DOM % 2)) -eq 1 ]` é TRUE.
DOW=3 (Wed) → Phase 3 RUNS (session-wrap-ups). Auditado: `session-wrap-up.sh` é puro verificação read-only + git commit + Discord alert; zero `nox-mem` mutator → safe.
Phases 4/5/8 skip (não-Sun/Mon/1st-Sun). Phases 1, 6, 7 são intencionalmente MAIN e idempotentes/safe.
**Conclusão:** hoje à noite green com flag P0 ativo.

### Fix tiers (tasks abertas)
| Task | Fix | Tipo |
|---|---|---|
| #20 (P1) | Safety guard em `nox-mem reindex`: abort if resolved db_path ≠ OPENCLAW_WORKSPACE-derived path | Defense layer |
| #21 (P2) | Root fix: `OPENCLAW_WORKSPACE` resolution em CLI (db.ts + index.ts) | Bug primário |
| #22 (P3) | `reindex.ts` rotear entity files via `ingestEntityFile()` | Bug secundário |
| #23 (P4) | Audit `withOpAudit` silent insert failure (catch + log + alert) | Bug terciário |

**Critério pra remover flag:** P1 + P2 shipped E deploy validado em prod E re-run de Phase 2 manual com `--dry-run` confirma db_path correto.

### Defesa adicional sugerida (não-task ainda)
1. **Hard-lock no flag:** mover `/root/.openclaw/DISABLE_AGENT_REINDEX` para `/etc/nox-mem/safety-flags/` com perm 0644 root:root + auditd watch.
2. **Pre-flight check em `nightly-maintenance.sh`:** se flag está faltando E última instalação foi nos últimos 14d (per `find /root/.openclaw -name "DISABLE_AGENT_REINDEX" -newer ...`), alertar antes de prosseguir.
3. **Snapshot size sanity:** após cada `withOpAudit` snapshot, comparar size com expected agent DB size; alertar se mismatch >50%.

### Contexto da investigação
Root-cause encontrado em sessão **Wed 2026-05-27 15:40-15:55 BRT** (task #18) usando: journalctl 72h + `sqlite3 ops_audit` + forensic snapshot size analysis + audit de `nightly-maintenance.sh` Phase 2 logic. Memory crítica salva em `[[reindex-bypasses-openclaw-workspace-hits-main]]`.

---

## 2026-05-24 ~02:11 UTC (23:11 BRT 23/mai) — nox-mem reindex zerou chunks 69.032 → 730 (recovery completo, kill-switch instalado)

### Severity: 🔴 red — data-loss event em produção (recuperado sem perda via snapshot pre-op)

### Sintoma
Alerta Discord do canary `check-schema-invariants.sh` (cron */15):
```
⚠️ nox-mem schema invariant failed: section NOT NULL count=0 (expected >=600 — possible entity wipe)
⚠️ nox-mem schema invariant failed: section=compiled count=0 (expected >=150)
```

### Causa raiz
A **Phase 2 (Agent reindex) do `/root/.openclaw/scripts/nightly-maintenance.sh`** (cron `0 23 * * *`, roda em dia ímpar do mês) executa `nox-mem reindex` agent-por-agent (atlas→boris→cipher→forge→lex→nox) com `NOX_DB_SOURCE=<agent>` no **DB compartilhado** `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db`. Cada reindex **sobrescreve a tabela `chunks` inteira** em vez de fazer upsert por `source_file` — restou apenas o último agent (nox, 730 chunks de 77 files). Evidência em `ops_audit` (ops 76-81): a reindex do atlas levou 626457ms e o `snapshot_bytes` caiu de 1.26GB (pre-atlas) para ~66MB nas seguintes; todos os 730 chunks finais com `created_at = 2026-05-24 02:11:25`. KG (`kg_entities` = 15.612) sobreviveu — só `chunks` zerou. Arquivo não encolheu (sem VACUUM) — consistente com deleção em massa.

**Recorrência:** mesmo padrão em 2026-04-25 e 2026-05-19 (ver histórico). Bug conhecido do reindex, não regressão nova.

### Recovery (sem perda de dados)
1. Snapshot defensivo do estado degradado → `/root/backups/nox-mem-incident-20260523-2317/` (db+wal+shm bruto + `.backup` consistente).
2. Validado snapshot pre-op automático: `/var/backups/nox-mem/pre-op/reindex-atlas-20260524020006-2340271-*.db` = **69.032 chunks, section NOT NULL 749, is_compiled 1.046, 11.151 source_files, KG 15.612** (estado de ~02:00, ~11min antes do dano; perda efetiva ~zero — madrugada sem escrita nova).
3. `systemctl stop nox-mem-watch nox-mem-api` → `mv` DB degradado p/ `.degraded-20260523-2332` → `rm` wal/shm → `cp` snapshot pre-op → `systemctl start` → validado (69.032 chunks, `/api/search` funcional, `/api/health` OK).

### Kill-switch instalado (preventivo até o fix de código)
- Arquivo: `/root/.openclaw/DISABLE_AGENT_REINDEX`
- Guard adicionado na linha 29 do `nightly-maintenance.sh`: `if [ ! -f /root/.openclaw/DISABLE_AGENT_REINDEX ] && [ $((DOM % 2)) -eq 1 ]; then`
- Backup do script: `nightly-maintenance.sh.bak-pre-reindex-freeze-20260523`
- **NÃO remover o flag até o `nox-mem reindex` ser corrigido para upsert incremental (não wipe+repopulate do DB compartilhado).** Enquanto isso, só a Phase 6 vectorize (idempotente) mantém o vector layer; a memória não se atualiza via reindex noturno.

### Fix de código pendente (TODO)
`nox-mem reindex` com `NOX_DB_SOURCE=<agent>` deve reindexar SÓ os `source_file` daquele agent (DELETE WHERE source do agent + INSERT), preservando os demais. Hoje faz wipe global + repopulate. Avaliar também isolar DBs por agent em vez de DB compartilhado.

### Contexto
Detectado durante sessão de health-check da VPS (ver `openclaw-vps/infra/docs/INCIDENTS.md` 2026-05-23 23:00 — mesma sessão tratou grep zumbi, rollback 5.22-beta.1→5.20 e canais mudos).

---

## 2026-05-21 ~10h30 BRT (~3min/recovery) — Multi-agent branch leak ×3 + pre-commit hook installed

### Severity: 🟡 yellow — defense-only event (no data loss, no prod impact)

3 branch leaks no mesmo dia despite `isolation: "worktree"` setado em todos agent spawns:

1. **Agent G10c (affa68cd)** — branch `research/g10c-per-style-mutex` contaminou parent HEAD; HANDOFF commit landed wrong branch
2. **Re-leak após recovery** — G10c artifacts commit landed em same leak branch
3. **Agent G10d (a31ee9f7)** — branch `impl/g10d-conditional-mutex` contaminou parent HEAD; pre-commit hook (just installed) ABORTED paper §5.5 commit

### Root cause

`isolation: "worktree"` cria filesystem space isolado MAS shared `.git/`. Agents podem:
- `cd` para path absoluto saindo do worktree
- Usar `git -C <abs-path>` redirecting ops pro main
- Resultado: parent HEAD mutated silently

### Recovery

Cada leak ~3min via cherry-pick:
```bash
git checkout main
git pull --ff-only
git cherry-pick <leak-commit>
git push origin main
git branch -D <leak-branch>
```

### Fix permanente

**Pre-commit hook global** instalado em `~/.git-hooks-global/pre-commit`:
- Detecta non-main branch em parent repo path (worktrees exempt)
- Aborts commit com mensagem clara apontando recovery
- Override: `COMMIT_TO_NON_MAIN_OK=1 git commit ...`

Memory `[[pre-commit-hook-blocks-non-main-commits]]` documenta.
Memory `[[multi-agent-branch-checkout-race]]` updated com 3rd violation.

### Hook prova de fogo

Mesma manhã o hook DISPAROU em commit que tentou subir paper §5.5 enquanto branch leak ativo. Recovery automático (stash + checkout main + commit + push) ~30s. Sem hook, teria sido 4ª leak.

---

## 2026-05-21 morning (~1h investigation, ~3h fix+deploy) — opsAudit 3-issue investigation + Issue #2 vec0 reindex PROD RISK fixed

### Severity: 🟠 orange — Issue #2 was prod risk (could escalate); Issues #1/#3 were metric noise

`/api/health.opsAudit` mostrou 48 phantom rows em "unknown" bucket em 24h window. Investigation revelou 3 issues distintos:

**Issue #1 (metric noise):** `started_at` type chaos
- 56 rows com `typeof=TEXT` em 3 formatos misturados (epoch ms float-as-text, ISO datetime, INT)
- Filter `started_at > strftime('%s','now','-24h')*1000` falha com TEXT vs INT (lexicographic compare)
- Rows de Abril aparecem como "last 24h"

**Issue #2 (PROD RISK):** Reindex `no such module: vec0`
- 6× sequencial fail em 2026-05-20 02:00 UTC
- `api-server.js` carrega sqlite-vec no startup; `index.js` (CLI entry) NÃO carrega
- `DELETE FROM chunks` dispara `trg_chunks_delete_cascade` → `vec_chunks` → fail
- Vetores atuais OK mas próximo cron escalaria

**Issue #3 (metric noise):** Test ops + db_source NULL polluem
- 11/12 "crashed unknown" = test-bad-fn/test-failure/ocr-batch kills legítimos
- Test fixtures não setam db_source

### Fixes

| Issue | PR | Status |
|---|---|---|
| #2 vec0 fix | `9ad77eb` bundle | ✅ DEPLOYED VPS, smoke validated |
| #1+#3 hygiene | #193 (`7362b29`) | ✅ DEPLOYED VPS — table rebuild + 2 INTEGER-enforcement triggers + test rows cleanup |
| #3B db_source enforce | (in flight) | 🔄 fix/opsaudit-3b agent rodando |

### Before / After Issues #1+#3

| Metric | Before | After |
|---|---|---|
| `typeof(started_at)` | text × 56 | integer × 36 |
| Test-% rows | 20 | 0 |
| `total_24h` | 48 phantom | 1 real |
| `crashed_24h` | 12 | 0 |
| `byDbSource` | main/unknown/test | main only |

### Deployment surprises (memory `[[sqlite-text-affinity-coerces-int-back]]`)

4 SQLite gotchas:
1. better-sqlite3 binds JS number as REAL not INTEGER → `CAST(? AS INTEGER)` wrapper
2. TEXT column affinity coerces INTEGER back → full table rebuild required (UPDATE-in-place fails)
3. sqlite3 CLI needs `.load vec0.so` (cascade trigger references)
4. sqlite3 CLI defaults `.bail off` → partial corruption risk; needs `.bail on`

---

## 2026-05-20 ~10h BRT (~30min recovery) — VPS IP swap silencioso (false alarm offline)

**Sintoma:** durante deploy Wave A novo (PRs #154/#158), ping em `45.43.85.86` retornou 100% packet loss + curl HTTP 000 em portas 22/2222/2200/18802. Agent VPS-cleanup retornou "host inacessível"; verificação direta da main session confirmou.

**Hipóteses iniciais:** (1) maintenance window, (2) bloqueio por uso CPU/network, (3) firewall mudou, (4) disk full, (5) hardware failure.

**Realidade:** Hostinger fez floating IP swap silencioso. Toto deu novo IP `187.77.234.79`. SSH funcionou de primeira (mesma chave ed25519). Hostname `srv1465941`, uptime **20 days, 50 min** intacto — sem reboot, sem maintenance, sem downtime. Apenas redirecionamento de rota.

**Impact:** ~30min de incerteza, deploy Wave A novo atrasado mas executado com sucesso após IP atualizado. Zero dados perdidos. Service `nox-mem-api` continuou rodando o tempo todo.

**Root cause:** Hostinger floating IP rebalance silencioso (sem notif). Cronograma típico de prov cloud sem mensagem ao tenant.

**Recovery time:** ~30min (ping fail → user verification → SSH retry com novo IP).

**Action items:**
- Adicionar healthcheck script com IP atual em cron (`ssh -o ConnectTimeout=3 root@$VPS_IP 'hostname' || alert`)
- Atualizar `~/.ssh/config` se houver Host alias com IP antigo
- Memory `[[vps-ip-change-2026-05-20]]` cravada como reference
- Memory anterior `[[vps-down-2026-05-20]]` ficou desatualizada — não era outage real

**Cross-links:** PR #158 (api-server fix doc), deploy Wave A novo (sed+scp+build em 187.77.234.79), HANDOFF morning + midday 2026-05-20.

## 2026-05-20 ~09h30 BRT (~15min recovery) — Multi-agent branch checkout race condition

**Sintoma:** PR #154 polish commit landed em `feat/visual-identity-g5-v3-canonical` em vez de `feat/source-type-boost-map-2026-05-20`. `git push` complained sobre upstream errado.

**Root cause:** main session estava trabalhando em `feat/source-type-boost-map-2026-05-20` (PR #154 polish). Spawned designer agent em paralelo pra atualizar README/SVGs em NOVO branch `feat/visual-identity-g5-v3-canonical`. Agent fez `git checkout -b feat/visual-identity-g5-v3-canonical` dentro do MESMO working tree. Quando main thread fez `git commit` em seguida, commit landed na DESIGNER's branch, não na intended.

**Mecânica do bug:** git checkout em same working directory é process-global state — não há per-thread/per-agent HEAD isolation. Ambos main session E spawned agent compartilham mesmo `.git/HEAD`. Quem rodar `git checkout` por último ganha para subsequent operations no working tree.

**Recovery:**
1. `git reset --hard f49660e` na branch errada (remove design commit vazado)
2. `git checkout feat/source-type-boost-map-2026-05-20`
3. `git cherry-pick f49660e` (mesmo SHA, branch certa)
4. `git rebase --onto main f49660e feat/visual-identity-g5-v3-canonical` (descross dos commits)
5. `git push --force-with-lease` em ambas branches

Total: ~15min de git surgery + recovery completa, 0 perdido.

**Fix protocol (cravado):**
- Parallel agents que tocam git devem usar `isolation: "worktree"` na chamada Agent tool
- OR serializar (esperar agent terminar antes de main session continuar)
- Defaulting `isolation: "worktree"` pra qualquer agent que toca git remove entire class de bug
- Sanity check before commit em multi-agent sessions: `git branch --show-current` ANTES de `git add`/`git commit`

**Cross-links:** PRs #154/#155 (recuperados com sucesso após surgery), memory `[[multi-agent-branch-checkout-race]]`, CLAUDE.md `[[worktree-branch-leak-to-main]]` (pattern relacionado).

## 2026-05-18 16:23 BRT (~10min fix) — Deploy Validator CI 100% fail por stderr→JSON contamination

**Sintoma:** 5 PRs consecutivos (#92, #95, #98, #99 e mais um) com Deploy Validator falhando em ~25s. Email do GitHub: "Deploy Validator: All jobs have failed". Run logs mostravam `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` na step "Parse validator output", mas o validator em si passava (summary.fail=0).

**Workflow:** `.github/workflows/deploy-validator.yml`. Trigger: pull_request paths que incluem `docs/DEPLOY-WAVE-B.md`, `staged-*/**`, `scripts/deploy-validator/**`.

**Root cause:** linha 50 invocava `node --loader ts-node/esm src/cli.ts ... > /tmp/validator-report.json 2>&1`. O flag `--loader` é experimental em Node, e emite `(node:XXXX) ExperimentalWarning: --loader is an experimental feature` em stderr. O `2>&1` mergia stderr no stdout antes do redirect, então o warning entrava no JSON file ANTES do `{`. A step seguinte rodava `python3 -c "import json; json.load(sys.stdin)"` → choke em char 0 → exit 1 sempre.

**Fix (commit `62be1f6`):**
1. `node dist/cli.js` em vez de `node --loader ts-node/esm src/cli.ts` — `npm test` (step anterior) já roda `npm run build` per `package.json:7`, então dist/cli.js existe.
2. `2> /tmp/validator-stderr.log` em vez de `2>&1` — stderr separado do JSON.
3. Print de ambos com headers + upload de stderr.log como artifact pra debug futuro.

**Validação:** workflow só dispara em PR (linha 4-5), não em push. Próximo PR aberto valida o fix end-to-end. Fix testado mentalmente: validator escreve JSON via `console.log` (stdout) e errors via `console.error` (stderr) — separação por design.

**Lesson:** [[feedback_stderr_redirect_breaks_json_capture]] — JSON capture via shell redirect deve usar `>` SEM `2>&1`. Pra debug, redirecionar stderr a outro arquivo, nunca mergir.

**Affected runs:** 26055289735, 26055156560, 26054093674, 26053675928, 26053179030.

---

## 2026-05-17 17:03 BRT (~45min trabalho) — graph-memory turn extract parse failure 19.7% → 0%

**Sintoma:** logs do gateway mostravam ~73 falhas/dia (sobre 297 sucessos = **19.7% rate**) com `[graph-memory] extraction parse failed: SyntaxError`. 1 em cada 5 turns NÃO entrava no Knowledge Graph → cross-session recall degradado.

**Plugin:** `graph-memory v1.5.8` (custom mods sobre `adoresever/graph-memory`) em `/root/.openclaw/extensions/graph-memory/`. Extrai triplets `{nodes: [TASK/SKILL/EVENT], edges: [USED_SKILL/SOLVED_BY/REQUIRES/PATCHES/CONFLICTS_WITH]}` de cada turn via LLM (gemini-2.5-flash-lite).

**Root cause:** `src/extractor/extract.ts:365` usava `s.slice(s.indexOf("{"), s.lastIndexOf("}")+1)` — quando LLM gerava `{json válido} ... texto extra/exemplo ... {json2}` (~20% dos casos mesmo com system prompt "禁止解释文字"), o slice englobava lixo no meio → `JSON.parse` quebrava.

**Fix:** substituído `extractJson` por **bracket-balance matcher** depth-counting que respeita strings e escapes (para no primeiro JSON object completo). Build via `bun build` (não tsc — tem `noEmit: true`), restart gateway.

**Validação prod:** 6 extracts seguidos pós-restart, **0 falhas** (100% sucesso). Nodes capturados úteis: `TASK:monitor-context-usage`, `SKILL:execute-script`, `EVENT:script-still-running`, etc.

**Lesson completa:** `lessons/2026-05-17-graph-memory-parse-failure-fix.md` (causa raiz + diff + bracket-matcher code + pegadinhas tsc/bun + rollback procedure).

**Backups:** `dist/index.js.bak-pre-extractjson-fix-20260517` + idem para extract.ts.

---

## 2026-04-27 06:48 BRT (~15min recovery) — Vector coverage 54% gap por session-distill hung 8h (N² em checkpoints HEARTBEAT)

**Sintoma:** morning report às 06:30 BRT alertou `🔴 vectorCoverage: 9390/20201 embedded (54% gap — vectorize not running)`. Health endpoint confirmou `{embedded: 9390, total: 20548, orphans: 0}` — sem corrupção, mas embedded congelado enquanto total cresceu via watcher.

**Root cause:** Phase 4 do `nightly-maintenance.sh` (Sunday tasks, DOW=7) roda `nox-mem session-distill` ANTES do Phase 6 Daily Vectorize. Domingo 26/04 23:00 BRT, session-distill iniciou e ficou pendurado 7h48min (PID 1799773 + 1800385) segurando `/tmp/nox-maintenance.lock`. Phases 5/6/7 nunca executaram. Watcher continuou ingestando chunks normais (digests, USER-PROFILE, sessions wrap-ups) — total foi de 9390 → 20548 sem nenhum embedding novo.

**Causa do hang em session-distill:** algoritmo é O(N²) — para cada candidato extraído pelo LLM Gemini, roda cosine similarity contra todos os chunks distilled existentes. Sessões `cipher:650b0642` (27 checkpoints, 4.5-6MB cada, voltando até 8/abr) e `atlas:cd72e874` (30 checkpoints) acumularam meses de heartbeats redundantes. Filtro de noise em `extractMessages()` cobria SOMENTE `role === "user"` (linha 148, `text.startsWith("HEARTBEAT")`) — respostas do assistant paraphrasing HEARTBEAT.md (`"The user wants the agent to read the file..."`, `"A pending task for Cipher in Notion is..."`, `"HEARTBEAT_OK"`) passavam pelo filtro, eram enviadas ao LLM, viravam memórias candidatas, e cada uma rodava cosine contra o pool inteiro. Log da maintenance virou 2.1MB de `[DEDUP] Suppressed (cosine=9X%)` — dedup funcionando, mas custo CPU explosivo. 4576 dedup events vieram só de `cipher:650b0642`, 1966 de `atlas:cd72e874`.

**Trigger temporal:** primeira execução pós-acúmulo crítico de checkpoints. Não havia timeout no `session-distill` invocation — `|| true` capturava erros mas não duração. Cada checkpoint adicional aumentava N² quadraticamente; o 27º checkpoint do cipher (combinado com o 30º do atlas) cruzou o limite onde a run não termina em 24h.

**Recovery (07:00-07:15 BRT 27/04):**
1. `kill 1799772 1799773 1800385` → script + session-distill mortos sem corromper DB (idempotente)
2. `rm /tmp/nox-maintenance.lock` → libera próximo nightly
3. `nox-mem vectorize` foreground → 11272 embedded, 0 erros, 518s; vectorCoverage 20662/20662 (100%) confirmado via `/api/health`

**Fixes preventivos (mesma sessão):**
1. **Prune de checkpoints velhos:** mtime>14d em cipher+atlas → `/var/backups/checkpoints-pruned/{cipher,atlas}/` (115MB total, restore via `mv`). Cipher 27→18, Atlas 30→23. Reduz ~60% do trabalho do próximo session-distill.
2. **Hard timeout 30min em session-distill:** `nightly-maintenance.sh:75` agora `timeout 1800 nox-mem session-distill ... || log "TIMEOUT/ERROR — continuing"`. Soft-fail garante Phases 5/6/7 sempre rodam mesmo se distill estourar tempo. Backup do script em `.bak-20260427`.
3. **Filtro HEARTBEAT extendido:** `src/session-distill.ts:147-160` — `extractMessages()` filtra agora **user E assistant** (era só user). Cobre `[cron:`, `HEARTBEAT*`, regex `/^heartbeat[_ ]ok\b/i`, conversation history, text<5chars. Build TypeScript OK. Backup em `.bak-pre-heartbeat-filter-20260427`.

**Aprendizados:**
- Pipelines seriais **sem timeout por step** = uma fase travada congela tudo downstream. Cada `>> "$LOG" 2>&1 || true` precisa ser `timeout N ... || log_fallback`.
- Filtros de noise devem cobrir TODOS os roles, não só `user`. LLM extrai memórias de respostas do assistant também — heartbeat-loops paraphrasados pelo LLM são tóxicos pro dedup downstream.
- Algoritmos O(N²) em nightlies acumulam tech debt invisível — um threshold de "max candidates per run" é defesa em profundidade que precisa entrar em V1.7.
- Morning-report deveria expor não só `vectorCoverage` mas TAMBÉM "última nightly completou? duração? Phases pendentes?" — ausência dessa visibilidade atrasou detecção em ~7h.

## 2026-04-25 ~07:00 BRT (~12min recovery) — Section/retention metadata wipe via reindex (não-nightly)

**Sintoma:** sanity check matinal mostrou `sectionDistribution.compiled=0, frontmatter=0, timeline=0` (esperado 183/183/366), `retention.never_decay=25` (esperado 104), total 9173 vs 9541. Shadow telemetry às 23:45 BRT 24/04 ainda mostrava sections populadas — regressão entre 23:45 e o próximo sanity check.

**Root cause arquitetural:** `reindex.ts` (callable manualmente OU via `nightly-maintenance.sh`) faz `DELETE FROM chunks` + loop chamando `ingestFile()` (genérico) sobre **todos** os `.md` do workspace, incluindo os 183 arquivos `memory/entities/<type>/*.md`. `ingestFile()` não conhece o formato 3-section (compiled/frontmatter/timeline) — gera 1-2 chunks genéricos por arquivo com `section=NULL`, ignorando o N+2 split que `ingestEntityFile()` produz. `accessSnapshot` em reindex.ts só preserva `tier/access_count/importance/last_accessed_at`, não `section` nem `retention_days` — metadados nukados sem aviso. Mesmo padrão arquitetural que watcher (`watch.ts:71` chama `ingestFile`).

**Trigger temporal (forensic post-recovery):** investigação dos timestamps no DB mostrou que TODOS os 8808 chunks não-entity foram criados num **único minuto às 01:03 UTC 25/04 = 22:03 BRT 24/04** (assinatura clássica de reindex full). NÃO foi o nightly cron OS (esse rodou 23:00 BRT, 1h depois — e Phase 2/agent-reindex foi skipped por ser DOM par dia 24). **Foi a OpenClaw cron `end-of-day`** (id `ee15b430-ec10-4698-b25f-7fc4e1169417`, schedule `0 22 * * *`) — cron interno da plataforma OpenClaw que dispara um agent turn diariamente às 22:00 BRT. O prompt do agent tem 14 steps; **step 11 é literalmente `Execute: nox-mem reindex`**.

**Timeline:**
- 22:03 BRT 24/04 — reindex full disparado; 8808 chunks recriados via `ingestFile()` genérico, sections nukadas
- 23:00 BRT 24/04 — nightly cron dispara `nightly-maintenance.sh` mas Phase 2 skipped (DOM par); só Phase 6 vectorize roda + Phase 7 WAL
- 23:03 BRT — vectorize embed 3923 chunks; total 9173, vc 100%
- 23:45 BRT — section-shadow-telemetry roda mas mede events da janela 24h ANTES — não detecta a regressão
- 06:50 BRT — sanity check matinal expõe regressão
- 07:05 — backups: `ingest.ts.bak-pre-section-fix-20260425`, `reindex.ts.bak-pre-section-fix-20260425`
- 07:06 — patch em `ingest.ts`: guard no topo de `ingestFile()` rotando `memory/entities/*.md` → `ingestEntityFile()`. Cobre reindex AND watcher num só lugar.
- 07:07 — `npx tsc` build OK; `systemctl restart nox-mem-watcher`
- 07:09-07:10 — loop `nox-mem ingest-entity` × 183 files (100% sucesso, 0 fail)
- 07:11 — `nox-mem vectorize`: 732 novos chunks embedded em 40s
- 07:12 — `/api/health`: `compiled=183, frontmatter=183, timeline=366, embedded=9540/9540, orphans=0` ✅

**Fix permanente:** routing fica em `ingestFile()`, não em caller — qualquer entry point (reindex, watcher, future bulk imports) automaticamente roteia entity files corretos. Próximo nightly 23:00 BRT (25/04) deve mostrar zero regressão. Validação canônica = `/api/health.sectionDistribution.compiled == 183`.

**Fix #2 (paralelo):** patch no end-of-day cron via `openclaw cron edit ee15b430-... --message "..."` — step 11 mudado de `nox-mem reindex` → `nox-mem consolidate`. Consolidate é leve (não DELETE chunks).

**Aprendizado:**
- **Validar com section data, não só logs** — shadow telemetry às 23:45 capturou estado bom porque agrega events de search 24h ANTES; o reindex de 22:03 já tinha quebrado tudo. Section count + recently-modified file timestamps são canaries melhores
- **Routing por path → handler especializado pertence ao entry point comum** (ingestFile), não ao caller — senão cada novo caller (reindex.ts E watch.ts) duplica o erro
- **Cron interno do OpenClaw é separado de cron OS** — investigação precisa cobrir AMBOS: `crontab -l` (OS) E `openclaw cron list` (internal)

> NOTA: Eventos paralelos da mesma janela (gateway crash loop user-systemd v4.15, logrotate copytruncate) migrados pra `~/Claude/Projetos/openclaw-vps/infra/docs/INCIDENTS.md`.

---

## 2026-04-21 06:30-07:50 (~1h20 recovery) — Semantic layer wipe + systemic audit

Alert Discord `nox-mem alerts` 06:30 UTC: `🔴 vectorCoverage: 0/2073 embedded` + `🔴 Canary: FAIL`.

**Root cause:** reindex rodado às 01:09 UTC (1884 chunks recriados em 1min) — `DELETE FROM chunks` em `dist/reindex.js:41` cascadeou via `trg_chunks_delete_cascade` → `vec_chunks`/`vec_chunk_map` zerados → reindex terminou sem chamar `vectorize()` → semantic layer morto até próximo Sunday (5 dias).

**Fix imediato:** `set -a; . /root/.openclaw/.env; set +a; nox-mem vectorize` → 2073/2073 embedded em 114s.

**Auditoria sistêmica (mesmo turno, 6 fixes — itens nox-mem):**
1. DB path errado em `nightly-maintenance.sh` (Phase 2 pulava silenciosamente há 1 mês)
2. Watcher duplicado (`nox-mem-watch.service` legado) stopped+disabled
3. Canary cron `0 6 → */30`
4. `dist/reindex.js` patchado pra auto-vectorize inline

> Itens OpenClaw (RelayPlane ressuscitado, logrotate /etc/logrotate.d/nox) migrados pra `openclaw-vps/infra/docs/INCIDENTS.md`.

**Aprendizado:**
- cascade trigger é correto mas incompleto sem contrapartida no escritor
- single point of truth pra ranking/embeddings é o caller (reindex/ingest/consolidate)
- canary 1×/dia é insuficiente — */30min é o mínimo viável
- duplo-watcher em produção passou meses despercebido — `systemctl list-units | grep -i watch` deve ser parte do audit mensal

---

## 2026-04-19 19:13-22:41 (3h28 silent) — Fake-green incident pós-Forge fix

Forge declarou sucesso ao Toto ("sistema 100% ✅, 1969/1969 vetorizados, 0 órfãos") mas três coisas estavam erradas:
1. `nox-mem vectorize` rodou sem `.env` carregado → 1972 batches falharam silenciosamente
2. Mesmo commit (`d764009`) introduziu `SOURCE_TYPE_BOOST` multiplicativo empilhado em cima de TIER×BOOST_TYPES×recency (~10× stacking)
3. Canário diário em inglês contra corpus PT-BR passou por sorte

**Detecção:** canário falhou exit=3 + api logs `Vector index empty — Falling back to FTS5` + `/api/health.vectorCoverage.embedded=0`.

**Fix:** `SOURCE_TYPE_BOOST` desativado em `search.ts`; `set -a; source /root/.openclaw/.env; set +a` antes de `nox-mem vectorize`; canário trocado pra PT-BR.

**Aprendizado:** Forge reincidiu em "declarar sucesso sem verificar". Regras adicionadas:
- Sempre `curl /api/health` pós-operação
- Separar commits de ranking de commits de fix
- Boost multiplicativo é veneno quando empilhável — usar aditivo

Lição: `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`.

---

## 2026-04-18 (silent, multi-week) — Semantic search silenciosamente morta

**Causa raiz compounded:**
1. Chrome com `--remote-debugging-port=18800` ocupou a porta; `nox-mem-api` migrou pra :18802; `health-probe.sh` continuou batendo em :18800 hardcoded → 12 restarts/hora (288/dia) matando writes mid-flight
2. `vectorize.ts:39` consultava `SELECT chunk_id FROM vec_chunks` mas coluna não existe (chunk_id mora em `vec_chunk_map`) → "already embedded" check sempre vazio
3. Sem FK CASCADE nem trigger, cada `DELETE chunks` por consolidation/dedup deixava órfãos
4. `busy_timeout=0` causava SQLITE_BUSY silencioso sob contenção

Acumulado: 6,627 linhas em `vec_chunk_map` 100% órfãs, 2,587 vetores unreferenced, 0 chunks vivos embedded. `/api/health` mentia `embedded: 6627`. Hybrid search era FTS-only disfarçado.

**Fix (Tier 0+1):** probe port via env; `busy_timeout=5000`; DELETE órfãos + trigger `trg_chunks_delete_cascade`; `vectorize.ts` corrigido (INNER JOIN); `embedBatchAPI` usando `batchEmbedContents` (3→26.4 chunks/s); re-embed full em 74s.

**Aprendizado:** `/api/health` nunca deve derivar de tabela — sempre JOIN com source-of-truth (chunks). Embedding layer precisa de teste canário diário.

---

> **Incidents OpenClaw plataforma migrados em 2026-05-01 pra `~/Claude/Projetos/openclaw-vps/infra/docs/INCIDENTS.md`:**
> - 2026-04-23 models auth login overwrite + graph-memory zombie
> - 2026-04-21 ~15:30 Gemini + Perplexity keys exposed/revoked
> - 2026-04-20 Gemini quota blowout + Anthropic burn oculto
> - 2026-04-20 09:07 Gateway fratricide #62028
> - 2026-04-01 12:00 Gateway crash punycode
> - 2026-04-01 07:15 Gateway crash providers key
> - 2026-03-31 todos (gateway crashes, agentes lentos, RelayPlane cascade, agents.defaults removido)
