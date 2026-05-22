# Auditoria VPS — Prontidão Q4 Execution (Sáb 2026-05-24)

**Data:** 2026-05-21 (Sex noite)
**Auditor:** agent (Sisyphus-Junior / Sonnet 4.6)
**VPS alvo:** `187.77.234.79` (Hostinger — IP atualizado 2026-05-20)
**Scope:** read-only checks pré-Q4 COMPARISON execution

> NOTA DE METODOLOGIA: SSH calls além do primeiro (`/api/health` via tunnel) foram bloqueados pelo
> auto-classifier da sessão (Production Reads SOFT BLOCK). As seções que dependem de SSH adicional
> são marcadas como **BLOCKED/UNKNOWN** com recipes de verificação Sáb manhã.

---

## §1 Network Reachability

| Check | Resultado |
|---|---|
| `ping -c 3 187.77.234.79` | **OK** — 3/3 packets, RTT avg 26.1ms (min 22.1 / max 30.8ms) |
| Port 18802 público (external curl) | **FECHADO** — porta não exposta à internet (firewalled; normal — acesso via SSH tunnel ou local) |
| SSH auth (`ssh root@187.77.234.79`) | **OK** — keychain funcionando; primeira call autenticou sem interação |

**Status §1:** GO

---

## §2 nox-mem Prod Stats

Snapshot capturado via `curl http://127.0.0.1:18802/api/health` através de SSH tunnel às 2026-05-21 ~23h BRT.

```json
{
  "chunks": { "total": 68995 },
  "vectorCoverage": { "embedded": 68995, "total": 68995, "orphans": 0 },
  "knowledgeGraph": { "entities": 15612, "relations": 21518 },
  "salience": { "mode": "active", "mean": 0.4212, "median": 0.3745 },
  "dbSizeMB": 1203.5,
  "opsAudit": { "last_op": { "op_name": "daily-main", "status": "success", "finished_at": "2026-05-21 06:00:23" } },
  "searchTelemetry": { "p95_latency_ms": 5944, "count_24h": 56, "semantic_ratio": 1 }
}
```

### Comparação vs esperado

| Métrica | Esperado | Real | Delta | Status |
|---|---|---|---|---|
| chunks.total | 68995 | 68995 | 0.00% | OK |
| vec embedded | 68995 | 68995 | 0.00% | OK |
| vec orphans | 0 | 0 | — | OK |
| KG entities | ~15k | 15612 | +0.41% vs D51 est. | OK |
| KG relations | ~21k | 21518 | exact | OK |
| salience mode | active | active | — | OK |
| vec coverage | 100% | 100% | — | OK |

### Observações adicionais

- `nox-mem-watcher: false` — watcher de filesystem **parado**. Não é blocker Q4 (Q4 não ingere; usa corpus existente), mas cron de ingest incremental está inativo. Monitorar se corpus não cresce durante Sáb.
- `ollama: false` — OK (não usado em Q4).
- `searchTelemetry.p95_latency_ms: 5944ms` — p95 de 5.9s é **alto**. Este é p95 prod (inclui cold Gemini embedding). Para Q4 eval, Gemini calls serão feitas via `/api/search`; latência real do benchmark = similar. Documentar este número como baseline no `COMPARISON.md`.
- `searchTelemetry.skip_reasons.gemini_failed: 5` — 5 queries nas últimas 24h com falha Gemini (quota ou timeout). Taxa: 5/56 = 8.9%. WATCH durante Q4 run.
- `services.openclaw-gateway: true` — gateway ok.
- `opsAudit.last_op`: `daily-main success` às 06:00 BRT — pipeline diário funcionando.

**Status §2:** GO (com watchpoint em gemini_failed rate)

---

## §3 Disk Space

**BLOCKED** — SSH call para `df -h` foi negado pelo auto-classifier após primeira call autorizada.

### Estimativa baseada em dados disponíveis

- `dbSizeMB: 1203.5` — DB atual ~1.2GB
- VPS Hostinger padrão: 100GB storage
- Q4 requer: ~2GB Docker images (Zep+Postgres) + ~500MB pip packages + ~200MB eval output = ~3GB adicionais
- `/var/backups/nox-mem` retém snapshots 7d; cada snapshot ~1.2GB → até ~8.4GB de backups

### Recipe Sáb manhã (OBRIGATÓRIO — verificar antes do Q4 kickoff)

```bash
df -h /
# Expectativa: > 20GB free pra margem confortável
# Se < 5GB free: BLOCKER — limpar snapshots antigos antes de docker pull
du -sh /var/backups/nox-mem/
# Se > 10GB: prunar snapshots > 3d (manter os 3 mais recentes como margem)
```

**Status §3:** UNKNOWN — verificar Sáb 09h00

---

## §4 Memory Headroom

**BLOCKED** — SSH `free -h` negado pelo auto-classifier.

### Contexto do spec

- VPS spec (Q4 spec §4): Hostinger 8 cores, 16GB RAM
- Zep + Postgres Docker: ~2GB RAM
- Mem0 + Letta: ~500MB cada em runtime
- nox-mem-api rodando: ~300MB estimado
- Headroom necessário: 8GB+ livre

### Recipe Sáb manhã

```bash
free -h
# Expectativa: available > 8GB
# Se < 4GB free: verificar processos inesperados (top -b -n1 | head -20)
```

**Status §4:** UNKNOWN — verificar Sáb 09h00

---

## §5 Docker Availability

**BLOCKED** — SSH para `docker version` negado pelo auto-classifier.

### Contexto

Q4 requer Docker + Compose para Zep self-host (Zep + Postgres containers). Se Docker não instalado, setup de Zep leva ~15min Sáb manhã.

### Recipe Sáb manhã

```bash
docker version 2>&1 | head -5
docker compose version 2>&1 | head -3
# Se DOCKER MISSING:
apt-get install -y docker.io docker-compose-plugin
systemctl enable --now docker
```

**Status §5:** UNKNOWN — verificar Sáb 09h00

---

## §6 Python Environment

**BLOCKED** — SSH para `python3 --version` negado pelo auto-classifier.

### Requisito Q4

Python >= 3.10 para SDKs: `mem0ai`, `zep-python`, `letta`, `agentmemory`.

### Recipe Sáb manhã

```bash
python3 --version
# Se < 3.10:
apt-get install -y python3.11 python3.11-venv python3-pip
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

**Status §6:** UNKNOWN — verificar Sáb 09h00

---

## §7 Eval Gold Sets (VPS)

**BLOCKED** — SSH para `ls /root/.openclaw/.../eval-data/` negado pelo auto-classifier.

### Contexto local

O repo local (`/Users/lab/Claude/Projetos/memoria-nox/eval/`) contém apenas scripts de download (`download.ts`, `parser.ts`, `run.ts`) com `dry-run-sample.json` — não os gold sets completos. Gold sets ficam exclusivamente na VPS em `/root/.openclaw/workspace/tools/nox-mem/eval-data/`.

Histórico de MEMORY confirma:
- `longmemeval-n100/` — "already on VPS pré-Q2 done" (spec Q4 §2)
- `locomo/` — "already on VPS pré-Q1 done" (spec Q4 §2)

Mas Q2 rodou em 2026-05-19 com `entity-eval-v2` (500 chunks isolado), não o gold set longmemeval completo. Há risco de os gold sets estarem em subdiretório diferente ou com nome ligeiramente diferente.

### Recipe Sáb manhã (OBRIGATÓRIO)

```bash
ls -la /root/.openclaw/workspace/tools/nox-mem/eval-data/
# Verificar presença de longmemeval-n100/ e locomo/
# Contar arquivos:
find /root/.openclaw/workspace/tools/nox-mem/eval-data/longmemeval-n100 -name "*.json" | wc -l
# Esperado: >= 100 queries
find /root/.openclaw/workspace/tools/nox-mem/eval-data/locomo -name "*.json" | wc -l
# Se ausentes: rodar download.ts antes do Q4 runner (30-60min de download)
```

**Status §7:** UNKNOWN (provável OK, mas verificação mandatória)

---

## §8 Service Health

### nox-mem-api

Inferido do `/api/health` snapshot:

- `opsAudit.last_op.status: "success"` às 06:00:23 BRT — serviço está vivo e executando ops agendadas
- `searchTelemetry.count_24h: 56` — queries nas últimas 24h sendo processadas
- `salience.mode: "active"` — salience fórmula ativa em prod (não shadow)

O serviço não respondeu na porta pública (18802 firewalled), mas respondeu via SSH tunnel interno — comportamento correto.

**BLOCKED** — `systemctl status nox-mem-api` e `journalctl` calls negados.

### Recipe Sáb manhã

```bash
systemctl status nox-mem-api --no-pager | head -15
journalctl -u nox-mem-api --since "1 hour ago" --no-pager | grep -iE "error|warning|fatal" | head -10
```

**Status §8:** PROVÁVEL GO (health inferido via telemetria) — confirmar Sáb

---

## §9 Cron Sanity

**BLOCKED** — SSH `crontab -l` negado.

### Crons conhecidos (de audits anteriores)

| Cron | Frequência | Função | Status último |
|---|---|---|---|
| `daily-main` | 02:00 UTC | Backup nox-mem.db | SUCCESS 06:00:23 BRT 05-21 |
| `check-schema-invariants.sh` | `*/15min` | Canary invariants | Desconhecido agora |
| `healthcheck` | `*/15min` | PR #186 fix | Desconhecido agora |

### Recipe Sáb manhã

```bash
crontab -l
# Verificar: schema-invariants, healthcheck, daily-main presentes
# Verificar: nenhum cron desabilitado inesperadamente
```

**Status §9:** UNKNOWN — verificar Sáb

---

## §10 API Keys

**BLOCKED** — SSH `cat .env | grep -E "GEMINI|OPENAI"` negado.

### Keys necessárias Q4

| Key | Sistema | Obrigatória | Notas |
|---|---|---|---|
| `GEMINI_API_KEY` | nox-mem embeddings | SIM | Presente historicamente (infra usa desde v1) |
| `OPENAI_API_KEY` | Mem0 + Letta defaults | SIM | Necessária para competidores; verificar presença |
| Zep | Self-hosted | NÃO | Docker local, sem API key |

### Recipe Sáb manhã

```bash
grep -E "GEMINI|OPENAI" /root/.openclaw/.env | sed 's/=.*/=<REDACTED>/'
# Confirmar que ambas as variáveis existem (valor não importa aqui — só presença)
# Se OPENAI_API_KEY ausente: adicionar antes de instalar Mem0/Letta
```

**Risco adicional**: `searchTelemetry.skip_reasons.gemini_failed: 5` sugere quota ou timeouts ocasionais Gemini. Se taxa subir durante Q4 run (6 sistemas × 2 datasets × 100 queries = 1200 calls potenciais), considerar throttle no runner.

**Status §10:** UNKNOWN — verificar Sáb

---

## §11 Harness Q4 — Status no Repo

### ATENÇÃO: PR #219 NÃO ENCONTRADO no main local

O enunciado da tarefa menciona "Q4 harness PR #219 just landed in `eval/q4-comparison/`", mas:

```
git log --oneline | grep -E "q4|#219|comparison|harness"
# Resultado: apenas #218 (spec) — #219 não está no main local
ls eval/q4-comparison/
# Resultado: diretório NÃO EXISTE no repo local
```

**Hipótese A:** PR #219 foi merged depois do commit mais recente no local (09c8311 = #218). VPS pode ter código mais recente se fez pull.

**Hipótese B:** PR #219 ainda não foi aberto/merged (agent overnight ainda não rodou).

### Recipe Sáb manhã (CRÍTICO)

```bash
# No VPS:
ls /root/.openclaw/workspace/tools/nox-mem/eval/q4-comparison/
# Se ausente: harness não foi deployado — Q4 não pode iniciar
# Fix: git pull na VPS (se PR merged) ou aguardar agent overnight

# Localmente:
gh pr list --state open | grep -i "q4\|comparison\|harness"
gh pr view 219 2>/dev/null || echo "PR 219 not found"
```

**Status §11 Harness:** UNKNOWN / POTENTIAL BLOCKER

---

## §12 Checklist GO/NO-GO — Sáb 2026-05-24

| Item | Status | Evidência |
|---|---|---|
| Network OK (ping + SSH auth) | **GO** | ping 26ms avg; SSH autenticou na primeira call |
| nox-mem prod healthy (chunks 68995, vec 100%) | **GO** | /api/health snapshot confirmado exato |
| nox-mem salience active | **GO** | salience.mode = "active" |
| KG entities/relations | **GO** | 15612 / 21518 — dentro do esperado |
| Last daily-main success | **GO** | 2026-05-21 06:00:23 |
| Disk > 5GB free | **UNKNOWN** | SSH df bloqueado — verificar Sáb 09h00 |
| Memory > 8GB free | **UNKNOWN** | SSH free -h bloqueado — verificar Sáb 09h00 |
| Docker + Compose instalado | **UNKNOWN** | SSH bloqueado — verificar Sáb 09h00 |
| Python >= 3.10 | **UNKNOWN** | SSH bloqueado — verificar Sáb 09h00 |
| Gold sets VPS presentes (longmemeval-n100, locomo) | **UNKNOWN** | SSH bloqueado — provável OK por histórico Q1/Q2 |
| nox-mem-api active (systemctl) | **PROVÁVEL GO** | telemetria confirma actividade; systemctl não verificado |
| API keys presentes (GEMINI + OPENAI) | **UNKNOWN** | SSH bloqueado; GEMINI histórico presente |
| Crons saudáveis | **UNKNOWN** | SSH bloqueado |
| Q4 harness `eval/q4-comparison/` presente na VPS | **UNKNOWN / RISCO** | #219 não está no main local; VPS pode estar ahead |
| Gemini failure rate aceitável | **WATCH** | 5/56 = 8.9% nas 24h — monitorar durante Q4 run |

---

## §13 Plano de Ação — Sáb 2026-05-24 (09h00–09h30 BRT, ANTES do runner)

### Sequência obrigatória (30min checklist)

```bash
# 1. Confirmar harness presente
ls /root/.openclaw/workspace/tools/nox-mem/eval/q4-comparison/runner.py
# Se ausente → git pull ou clone manual (BLOCKER se ausente)

# 2. Disk check
df -h /
# Se < 5GB: du -sh /var/backups/nox-mem/ e prunar snapshots > 3d antigos

# 3. Memory check
free -h
# Se < 4GB available: kill processos desnecessários; rodar ulimit check

# 4. Docker check
docker version && docker compose version
# Se ausente: apt-get install -y docker.io docker-compose-plugin && systemctl enable --now docker

# 5. Python check
python3 --version
# Se < 3.10: instalar python3.11

# 6. Gold sets check
ls /root/.openclaw/workspace/tools/nox-mem/eval-data/longmemeval-n100/
ls /root/.openclaw/workspace/tools/nox-mem/eval-data/locomo/
# Se ausentes: rodar download.ts (pode levar 30-60min — planejar antes)

# 7. API keys check
grep -E "GEMINI|OPENAI" /root/.openclaw/.env | sed 's/=.*/=<REDACTED>/'
# Se OPENAI_API_KEY ausente: adicionar antes de instalar Mem0/Letta

# 8. Service health final
systemctl status nox-mem-api --no-pager | head -5
curl -s http://127.0.0.1:18802/api/health | jq '.chunks.total, .vectorCoverage.embedded'
# Esperado: 68995, 68995
```

---

## §14 Veredicto Final

### VEREDICTO: **GO COM FIXES**

**Fatores GO confirmados (via dados capturados):**
- nox-mem prod 100% saudável: chunks, vec coverage, KG, salience, daily op — tudo dentro do esperado
- Network estável: 26ms RTT, SSH autenticado
- Corpus para benchmark está intacto e sem drift detectado

**Fatores UNKNOWN (auto-classifier bloqueou SSH adicional):**
O agente de auditoria não conseguiu executar checks de disk/memory/docker/python/crons/keys além da primeira chamada SSH autorizada. Estes são **desconhecidos, não falhas** — o risco é baixo dado o histórico da VPS, mas a verificação Sáb 09h00 é **mandatória antes de iniciar o runner**.

**Risco mais alto identificado:**
1. **PR #219 (harness):** não confirmado no main local nem na VPS. Se o agent overnight não rodou ou o PR não foi merged, o `runner.py` pode não existir. Verificar PRIMEIRO na Sáb manhã.
2. **Gemini failure rate 8.9%:** se mantiver ou subir durante Q4 (1200+ calls), pode delay parcial. Plano: se rate > 15% durante run, pausar e verificar quota.

**Se os checks Sáb 09h00 passarem todos:** lançar `python runner.py --systems all --datasets locomo,longmemeval --limit 100` às 09h30 conforme plano.

**Se harness ausente:** delay de 1-2h para setup manual do PR #219 ou clone do harness na VPS — ajustar kickoff para 11h Sáb.

---

*Auditoria gerada por agent Sisyphus-Junior em 2026-05-21 Sex noite. Dados primários: `/api/health` snapshot via SSH tunnel. Checks de infraestrutura (§3-§10) bloqueados pelo auto-classifier; recipes de verificação Sáb manhã documentadas em §13.*
