# Session Start — próxima sessão

> Última atualização: 2026-04-20 17:40 (fim da sessão maratona)
> Summary completo da sessão anterior: `plans/2026-04-20-session-summary-completo.md`
> Policy nova: `shared/policies/2026-04-20-memoria-registration-policy.md`

## ✅ O que foi feito em 2026-04-20 (resumo)

- **Gateway fratricide (Issue #62028): RESOLVIDO** via monkey-patch em `cleanStaleGatewayProcessesSync`. Sistema estável.
- **Upgrade OpenClaw v2026.4.14 → v2026.4.15**: sem incident. Fix #67436 (manifest.db corruption) ativo.
- **Memory policy nova**: substitui mandato Notion. SOULs Forge + Nox atualizados.
- **Notion snapshot** das 15 entries recentes importado (7 relevantes).
- **Nox-mem v3.4 fixes**: Gemini model migration, embed retry, 9/10 consolidations recovered.
- **Scripts novos**: `reapply-gateway-fix.sh`, `openclaw-version-monitor.sh`.
- **Crons novos**: delivery cleanup (Dom 04:00), version monitor (Seg 09:00).

## 🎯 Próximo passo aprovado: importar repos locais pra nox-mem

### Escopo aprovado pelo Toto

- **Tipo de arquivos**: docs only (`*.md`, specs, plans, audits, CLAUDE.md)
- **Diretórios**:
  - `~/Claude/Projetos/` (10 projetos) — GalapagosApp, Frooty, Future-Farm, Granix-App, daily-tech-digest, Area-Manuel_Nobrega, Area-Campolim, Projeto-AI-Galapagos, nox-supermem, memoria-nox
  - `~/Claude/` raiz (CATALOG.md, INDEX.md, CLAUDE.md global)
- **Approach**: pilot com 1 repo pequeno → validar → batch os outros
- **Tempo estimado**: ~45 min

### Fora do escopo (próxima fase se quiser)

- `~/Claude/skills/` (56 categorias)
- `~/Claude/agents/` (22 categorias)
- `~/Claude/commands/` (26 categorias)
- Source code (*.ts, *.py, *.js)

## 📋 Plan de execução sugerido

### Fase 1 — Inventário (5 min)

- [ ] Listar `*.md` em cada projeto + tamanho
- [ ] Identificar duplicados / versões antigas
- [ ] Escolher pilot (sugestão: `daily-tech-digest` — menor)

### Fase 2 — Pilot (10 min)

- [ ] Criar `shared/imports/<projeto>/` na VPS
- [ ] scp `*.md` do projeto pilot
- [ ] `nox-mem ingest` + vectorize
- [ ] Validar: `nox-mem search "<keyword do projeto>"` retorna match_type=semantic
- [ ] Checkpoint: se ok, seguir

### Fase 3 — Batch (25 min)

- [ ] Script que itera os 9 projetos restantes + raiz
- [ ] Para cada: scp docs → ingest → vectorize
- [ ] Validação sample: 1 query por projeto

### Fase 4 — KG + docs (5 min)

- [ ] `nox-mem kg-build` pra extrair entidades
- [ ] Update CLAUDE.md do memoria-nox com métricas finais (novos chunks, nova coverage)
- [ ] Commit git

## Comandos de arranque

```bash
# 1. Verificar estado pós-sessão-anterior
ssh root@100.87.8.44 'systemctl is-active openclaw-gateway && curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage'

# 2. Inventário local
cd ~/Claude/Projetos && find . -maxdepth 3 -name '*.md' -not -path '*/node_modules/*' | head -30

# 3. Tamanho por projeto
for d in */; do echo "=== $d ===" && find "$d" -name '*.md' -not -path '*/node_modules/*' | wc -l && du -sh "$d"; done
```

## Convenções a respeitar (lições das sessões anteriores)

- **Sempre `set -a; source /root/.openclaw/.env; set +a`** antes de `nox-mem` CLI via SSH
- **Verificar estado real pós-operação:** `curl /api/health | jq .vectorCoverage` — `embedded == total`
- **Nunca confiar na última linha do CLI** — ler contagem de erros
- **Burst control:** usar `vectorize-slow.mjs` (batch=10, pause=3s) se Gemini 429
- **Gateway fragility:** monkey-patch #62028 vai perder em npm update — rodar `reapply-gateway-fix.sh` após qualquer upgrade
- **Não unsettar INVOCATION_ID** do wrapper (v2026.4.14+ precisa pra supervisor detection)
- **Frontmatter obrigatório** em todo arquivo ingerido: `chunk_type`, `date`, `tags`

## Pendências de outras sessões

### Alta
- Monitorar 24h pós-upgrade v2026.4.15 — nenhum sintoma esperado
- Comunicar Atlas/Boris/Cipher/Lex se ainda têm mandato Notion no SOUL (só Forge+Nox foram atualizados)
- Full import Notion (5 DBs restantes) — só quando terminar repos locais

### Média
- Script de audit que compara memory/ vs Notion retroativamente
- 3 consolidations persistentes com content-bug (memory/2026-03-20, 2026-04-05, 2026-04-15)
- Reportar Issue #62028 ao upstream quando reabrir (draft em `shared/github-comments/`)

### Baixa
- Cron de health-check do monkey-patch mensal
- Documentar processo de upgrade OpenClaw em checklist

## Arquivos importantes pra abrir logo

```
plans/2026-04-20-session-summary-completo.md       ← resumo da maratona
plans/2026-04-20-notion-import-e-whatsapp-tasks.md ← plan Notion (Fase 1 done)
shared/policies/2026-04-20-memoria-registration-policy.md ← policy nova
shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md ← lesson gateway
```

## Estado do sistema (snapshot 17:40)

| Métrica | Valor |
|---|---|
| OpenClaw version | 2026.4.15 |
| Gateway state | active (stable) |
| nox-mem chunks | 2069 |
| vectorCoverage | 2069/2069 = 100% |
| Monkey-patch ativo | ✅ |
| Policy enforced | ✅ (Forge + Nox) |
| Cron version-monitor | ✅ Seg 9h |

## Mood do Toto (pra contextualizar)

Sessão muito longa hoje (8h). Gateway foi o grande problema, resolvido. Ele prefere agora:
- Produtividade sobre debug
- Progresso visível rápido
- Não voltar pra gateway se possível

O Forge reincidiu 2× no padrão "fake-green" (declarar sucesso sem verificar). Toto topou reprimendar/reforçar protocolo sem drama.
