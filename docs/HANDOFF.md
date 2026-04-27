# nox-mem HANDOFF — estado vivo

> **Atualizado:** 2026-04-27 manhã BRT
> Substitui a sequência `handoffs/MASTER-HANDOFF-<date>.md`. Este arquivo único é mantido vivo a cada sessão.
> Histórico individual em `handoffs/_archive/`. Para "o que vem" → `docs/ROADMAP.md`. Para "por quê" → `docs/DECISIONS.md`.

---

## 1. Sanity check (1-cmd)

```bash
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq "{
  total: .chunks.total,
  embedded: .vectorCoverage.embedded,
  salience: .salience.mode,
  section: .sectionDistribution,
  opsAudit: .opsAudit,
  db: .dbSizeMB
}"'
```

**Última leitura (2026-04-27 07:00 BRT):**
```
total:    20831 chunks
embedded: 20662 / 20831 (99.2%)
salience: shadow (gate 04-30)
section:  compiled=183, frontmatter=183, timeline=366, legacy=20099
opsAudit: 1 op 24h (compact 02:00 ✓)
db:       318MB
```

## 2. Improvements audit

```bash
ssh root@100.87.8.44 '/root/bin/improvements check'
```

**Última leitura:** **13/13 OK** (7 critical + 6 warn-only, todos pass).

## 3. Onde paramos

Sessão 2026-04-26 entregou:
- Hardening total (audit triplo 47 findings → 11 HIGH fechados; Wave 2 cleanup 11 MEDIUM/LOW)
- E2E test suite (27 tests pass)
- Fase 4 Obsidian view-only (antecipado de 05-02 pra 04-26)
- B3 backlog 7/8

Sessão 2026-04-27 entregou:
- **OpenClaw upgrade defense system** completo (commit 3b9e23c, pushed) — 4 sprints: ckpt + improvements + watcher + orchestrator
- **Consolidação documental** — ROADMAP.md + DECISIONS.md + HANDOFF.md (este) como single source of truth
- Move 25 plans + 9 handoffs antigos pra `_archive/`

Sistema saudável. Em **holding pattern** até gate 04-30.

## 4. Próxima ação concreta

Hoje é **2026-04-27** (segunda). 3 dias até gate.

**Opção 1 — esperar gates** (recomendado se ocupado):
- Gates 04-30 / 05-01 / 05-02 são automáticos (cron + script)
- Sistema mantém shadow telemetry sozinho
- Reabrir sessão em **2026-04-30 manhã** com:
  ```bash
  ssh root@100.87.8.44 'bash /root/.openclaw/scripts/activate-salience.sh check'
  # Se "READY" → activate-salience.sh --apply
  ```

**Opção 2 — pre-gate productive** (se quiser avançar):

| # | Trabalho | Esforço (recalibrado) | Valor | Risco |
|---|---|---|---|---|
| 1 | Design A6 POC spec (Entity-Facts SPO Injection) | ~40min | Alto (próximo step) | Zero |
| 2 | Design A7 POC spec (Session Focus Boost) | ~40min | Alto | Zero |
| 3 | Decisão "1.7b dormente vs W1.5 executável" | ~30min | Médio (destrava Maio) | Zero |
| 4 | B3 #8 último item residual | ~20min | Baixo | Zero |
| 5 | Wave 3 cleanup (test isolation + 5 LOW polish) | ~1h | Médio (hygiene) | Baixo |

Combo recomendado: **#1 + #2 + #3** (~2h totais) → 3 design docs prontos pra executar 05-02.

## 5. Eventos agendados

- **2026-04-30** terça — `gate.salience` (`activate-salience.sh check` → `--apply` se READY)
- **2026-05-01** quarta — `gate.section_boost` (`analyze-shadow-telemetry.sh 7`)
- **2026-05-02** quinta — `gate.archive_3files` + iniciar Bloco III (B2 PDFs + A6/A7)
- **Maio 2026** — Wave 1 (W1.1 + W1.2 + W1.3 + W1.5 candidate)
- **Jun-Jul 2026** — Wave 2 (W2.1 + W2.2 candidate)
- **Ago 2026** — Wave 3 (W3.1 paper)

## 6. Contexto necessário pra retomar

**Mínimo absoluto (3 arquivos):**
1. Este arquivo (`docs/HANDOFF.md`) — estado atual
2. `docs/ROADMAP.md` — o que vem, capacity, gates
3. `CLAUDE.md` — regras críticas operacionais 1-15

**Quando precisar entender "por que":**
4. `docs/DECISIONS.md` — NÃO FAZEMOS, decisões arquiteturais, lições

**Quando precisar referência histórica:**
- `plans/_archive/2026-04-25-integration-roadmap-v1.6.md` — v1.6 original
- `plans/_archive/2026-04-26-clawmem-analysis.md` — Section 9 candidates
- `handoffs/_archive/MASTER-HANDOFF-2026-04-26.md` — última sessão detalhada

**Memory auto-load:**
- `MEMORY.md` (em `~/.claude/projects/-Users-lab-Claude-Projetos-memoria-nox/memory/`) — 36+ feedback files

## 7. Comandos úteis quick-ref

```bash
# Sanity check
ssh root@100.87.8.44 'curl -s http://127.0.0.1:18802/api/health | jq .'

# Improvements audit (13/13 baseline)
ssh root@100.87.8.44 '/root/bin/improvements check'

# Schema invariants
ssh root@100.87.8.44 'tail -5 /var/log/nox-schema-invariants.log'

# Tests (rodar individualmente, race condition em --test dir)
ssh root@100.87.8.44 'cd /root/.openclaw/workspace/tools/nox-mem && node --test dist/__tests__/retention.test.js dist/__tests__/op-audit-e2e.test.js 2>&1 | tail -5'

# OpenClaw release watcher state
ssh root@100.87.8.44 'cat /root/.openclaw/upgrade-watcher/state.json'

# Latest checkpoint
ssh root@100.87.8.44 'ckpt list | head -3'

# Logs gateway
ssh root@100.87.8.44 'journalctl -u openclaw-gateway --since "10 min ago" --no-pager | tail -30'

# CLI nox-mem (lembrar source env primeiro)
ssh root@100.87.8.44 'set -a; source /root/.openclaw/.env; set +a; nox-mem --help'
```

## 8. Convenções obrigatórias (lembrete rápido)

Ver `CLAUDE.md` para detalhes completos das 15 regras. Top 5:

1. **Secrets só via env** (`${VAR_NAME}` em configs, gitleaks pre-commit)
2. **Antes de CLI nox-mem em SSH/cron:** `set -a; source /root/.openclaw/.env; set +a`
3. **Validar features com DB state, não só logs** (`/api/health` JOIN é a fonte)
4. **Modelo Gemini default = `gemini-2.5-flash-lite`** (flash full estoura quota)
5. **claude-cli backend zero-cost** — `chattr +i` em `.credentials.json`, NO `CLAUDE_CODE_OAUTH_TOKEN` em env

**PT-BR:** "você" não "tu". Registro Brasil/Hotmart.

---

**Próxima atualização deste arquivo:** quando estado mudar (gates passarem, sprint completar, incident).
