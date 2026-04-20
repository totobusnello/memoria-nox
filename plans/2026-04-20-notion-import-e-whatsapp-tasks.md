# Plan — Notion Import + Migração Tasks WhatsApp

> Data: 2026-04-20
> Contexto: Mission Control — Nox (workspace Notion) passa a ser read-only legacy. Forge/Nox registram direto no nox-mem. Tarefas saem do Notion DB → WhatsApp → pending.md.
> Handoff: `plans/2026-04-19-session-handoff-noite.md`
> Principio: tier inicial = working (nunca Core — lição v3.4: boost stacking)

## Decisões aprovadas (2026-04-20)

- **Idioma:** PT-BR (mantém canário PT-BR existente)
- **Pós-import:** Notion fica read-only legacy. Forge/Nox registram direto via `nox-mem ingest`
- **NOX-Supermem page (#9):** SKIP — desatualizada, paper/CLAUDE.md cobrem
- **Health & Crons DB (#3):** SKIP — estado live, não memória
- **Tasks do Time DB (#5):** importar TUDO, agrupado por contexto (não task-por-task)
- **Tokens notion-api MCP:** removido (token inválido); usa claude.ai Notion MCP oficial

## Escopo final: 6 imports + 1 snapshot

| # | Item | Ação | chunk_type | source_file prefixo |
|---|---|---|---|---|
| A | Tarefas & Pendências (ativas) | Snapshot → pending.md | — | `memory/pending.md` |
| B | Projetos & Deals — Itens | Import 6 linhas | `project` | `notion/mission-control/projetos/<slug>.md` |
| C | Memória & Decisões — Registro | Import por linha | `decision\|lesson\|context\|daily_note` (por Categoria) | `notion/mission-control/decisoes/<slug>.md` |
| D | Tasks do Time | Import agregado por contexto | `task_history` | `notion/mission-control/tasks/<cluster>.md` |
| E | Lições Aprendidas | Import por linha | `lesson` | `notion/mission-control/licoes/<slug>.md` |
| F | Claude Code Setup (page) | Import por seção | `reference` | `notion/mission-control/claude-setup.md` |
| G | Biblioteca Jurídica Lex (page) | Import por categoria | `reference` | `notion/mission-control/lex-biblioteca.md` |

## Mapeamento Categoria → chunk_type para item C (Memória & Decisões)

| Categoria Notion | chunk_type nox-mem |
|---|---|
| Decisão, Decisão Técnica | `decision` |
| Lição, Aprendizado, Correção | `lesson` |
| Insight, Contexto, Registro, Daily Note, daily | `daily_note` |
| Sistema Openclaw, Infra, Infraestrutura, Sistema, Arquitetura, Configuracao | `reference` |
| Produto, Estratégia, Processo, Protocolo | `decision` |
| Pendência | **descartar** (conflita com pending.md) |

## Estratégia de agregação para item D (Tasks do Time)

Tasks individuais fragmentam o corpus. Agrupar como:

- **source_file por agente responsável + mês:** `tasks/<agente>-YYYY-MM.md`
- **Dentro do arquivo:** seções `## <Task title>` com Status, Prioridade, Prazo, De→Para, Notas
- **Pilot:** começar com 1 agente (Nox) num mês, validar semantic retorna queries contextuais, depois escalar

Exemplo:
```
tasks/nox-2026-03.md:
## Atualizar SOULs com protocolo agents-hub [Concluído, Alta]
- De: Toto → Para: Nox
- Prazo: 2026-03-27
- Notas: (conteúdo)
## Investigar suporte OpenClaw per-agent process isolation [Aberto, Média]
...
```

## Chunk boundaries por item

- **B (Projetos):** 1 chunk por deal. ~500-1500 tokens cada.
- **C (Memória):** 1 chunk por entry. Categoria vira tag no frontmatter.
- **D (Tasks):** 1 chunk por arquivo agregado (pode render múltiplos se >4k tokens).
- **E (Lições):** 1 chunk por lição.
- **F/G (Pages):** chunk por seção H2 (matches padrão existente no nox-mem).

## Forge/Nox nova política de registro

Após import, workflow dos agentes muda:

1. **Nova decisão/lição/insight:** `nox-mem ingest --file memory/decisions.md` (ou append em topic file + watcher reingesta automaticamente)
2. **Nova task cross-agent:** Toto manda WA → Nox → `memory/pending.md` (já decidido)
3. **Nova lição após incident:** Forge append em `shared/lessons/YYYY-MM-DD-<slug>.md` (padrão já existente após incident v3.4)
4. **Notion:** read-only; se alguém editar, Forge pega no próximo sync (mas sync semanal será desativado pós-migração)

## Plano de execução (sequencial, com pilot)

### Fase 1 — Preparação (sem risco)

- [ ] T1.1 Snapshot Tarefas ativas do Notion → entries em `memory/pending.md`
  - Query filtros: `Status=Pendente OR Em andamento`, ordenado Prioridade
  - Preservar prioridade via frontmatter ou emoji (🔴🟡🟢)
  - Incluir Prazo e Agente responsável se existir
- [ ] T1.2 Patch `prepare-briefing-context.sh` na VPS
  - Comentar bloco `A) Notion — tarefas ativas` (linhas ~32-56)
  - Manter bloco B (pending.md)
  - Testar: rodar briefing manualmente, conferir que mostra entries do pending.md
- [ ] T1.3 Criar branch `notion-import` em nox-workspace (VPS)
- [ ] T1.4 Criar diretório `shared/notion-mission-control/` na VPS pra receber os MDs gerados

### Fase 2 — Pilot (1 item, validar end-to-end)

- [ ] T2.1 Converter **Projetos & Deals** (item B, 6 linhas) para MDs
  - Gerar localmente: fetch cada page do database → escrever `<slug>.md` com frontmatter (Tipo, Valor, Status, Agente, Prazo) + corpo (Notas)
  - Copiar pra VPS: `scp shared/notion-mission-control/projetos/*.md root@100.87.8.44:/root/.openclaw/workspace/shared/notion-mission-control/projetos/`
- [ ] T2.2 Ingest + vectorize
  - `set -a; source /root/.openclaw/.env; set +a`
  - `nox-mem ingest /root/.openclaw/workspace/shared/notion-mission-control/projetos/`
  - `nox-mem vectorize`
- [ ] T2.3 Validar com 3 queries PT-BR
  - `curl http://127.0.0.1:18802/api/search?q=FII%20São%20Thiago` → esperar match_type=semantic
  - `curl http://127.0.0.1:18802/api/search?q=Casa%20Boa%20Vista` → idem
  - `curl http://127.0.0.1:18802/api/health | jq .vectorCoverage` → esperar embedded==total
- [ ] T2.4 **Checkpoint com Toto** — aprovar antes de seguir pra fase 3

### Fase 3 — Full import (5 items restantes)

- [ ] T3.1 Item C: Memória & Decisões (centenas linhas → 1 chunk cada, por Categoria)
- [ ] T3.2 Item D: Tasks do Time (agrupado por agente+mês)
- [ ] T3.3 Item E: Lições Aprendidas (1 chunk por lição)
- [ ] T3.4 Item F: Claude Code Setup (chunked por H2)
- [ ] T3.5 Item G: Biblioteca Jurídica Lex (chunked por categoria)
- [ ] T3.6 Rodar vectorize full + validar `/api/health.vectorCoverage == 100%`
- [ ] T3.7 Rodar `nox-mem kg-build` pra atualizar KG com entidades novas
- [ ] T3.8 Canário semântico: validar `match_type: "semantic"` em 5 queries PT-BR amostrais

### Fase 4 — Transição definitiva

- [ ] T4.1 Comunicar Forge: registro direto no nox-mem, Notion read-only
- [ ] T4.2 Comunicar Nox: idem + confirmar protocolo WA→pending.md
- [ ] T4.3 Remover cron `sync-notion` (se existir; checar com `crontab -l`)
- [ ] T4.4 Adicionar menção "Notion read-only" no CLAUDE.md do memoria-nox
- [ ] T4.5 Commit na VPS: `feat(memory): import mission control Notion → nox-mem`
- [ ] T4.6 Push para github.com/totobusnello/nox-workspace

## Rollback plan

Todos os chunks importados têm `source_file LIKE 'notion/mission-control/%'`. Em caso de problema (ex: dominação de ranking, volume demais, conteúdo desatualizado):

```bash
ssh root@100.87.8.44
# DB path real: /root/.openclaw/workspace/tools/nox-mem/nox-mem.db (sem subdir db/)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "DELETE FROM chunks WHERE source_file LIKE 'notion/mission-control/%';"
# trigger trg_chunks_delete_cascade limpa vec_chunks + vec_chunk_map automaticamente
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

## Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Volume importado domina ranking | Média | Tier `working` (não Core), aditivo não multiplicativo |
| Chunks pequenos fragmentam contexto | Média | Item D agregado por agente+mês |
| Categoria "Pendência" duplica pending.md | Baixa | Descartar no mapping |
| Conteúdo Notion desatualizado vs realidade VPS | Alta | Tag no frontmatter `source: notion-mission-control`, `last_synced: 2026-04-20`. Forge ingere correções via lessons pós-incident |
| Fake-green (import "pronto" mas vectorize falhou) | Média | T3.6 obrigatório conferir `/api/health.vectorCoverage == 100%` antes de declarar done (lição v3.4) |

## Critérios de sucesso

- 6 items importados, todos vetorizados (`embedded == total`)
- Queries PT-BR retornam `match_type: "semantic"` pra conteúdo importado
- Briefing matinal lê só de `pending.md` (sem bloco Notion)
- Forge e Nox confirmam nova política por escrito (lesson ou decision ingerido no próprio nox-mem)
- Canário diário continua verde 7 dias pós-import
