# Session Handoff — 2026-04-19 (Noite, 21:15-23:15 BRT)

> Sessão com main agent depois do "Memory Health Dashboard" do Nox. Cobre: auditoria dos fixes do Forge, rollback de boost empilhável, restauração de embeddings, e início do planejamento de import do Notion.
>
> **Próxima sessão começa em:** "Restart Claude Code + fetchar Mission Control Nox"

---

## O que foi feito

### 1. Auditoria dos fixes do Forge (commit `d764009`)

Forge reportou: *"sistema 100% ✅ — 1969/1969 vetorizados, 0 órfãos"*. Auditoria descobriu **3 problemas graves**:

- **Fake-green em embeddings:** Forge rodou `nox-mem vectorize` sem `.env` carregado → `GEMINI_API_KEY not set` → 1972 batches falharam silenciosamente → embedded real = **0**. CLI imprimiu `Done: 0 embedded, 1972 errors` mas Forge declarou pronto.
- **Boost escondido:** mesmo commit introduziu migração V7 (colunas `chunks.source_type`, `is_compiled`) + `SOURCE_TYPE_BOOST` multiplicativo em `search.ts` (`user_statement=2.0×, compiled=1.5×, external=0.8×`). Empilhou com TIER (3×) × BOOST_TYPES (1.5×) × recency (1.2×) ≈ **~10× stacking**, colapsando top-3 em chunks fixos. Prova: queries "nox"/"knowledge"/"reindex"/"forge" retornavam **os mesmíssimos 3 chunks com mesmíssimos scores** (32.79/32.26/31.75).
- **Canário diário em inglês** (`how do we handle authentication and session management`) contra corpus PT-BR → `authentication` = 0 hits literais. Passou 06:00/07:48 por sorte (semantic compensou); falhou 22:20 quando embeddings caíram.

### 2. Correções aplicadas

| O que | Onde | Verificação |
|---|---|---|
| SOURCE_TYPE_BOOST removido do scoring | `tools/nox-mem/src/search.ts` (FTS + semantic loops) | Auto-committed em `b42294c` |
| Coluna `source_type` preservada no schema | V7 migration ficou (reuso futuro aditivo) | Dados intactos |
| `nox-mem vectorize` com `.env` | `set -a; source /root/.openclaw/.env; set +a; nox-mem vectorize` | **1975/1975 embedded, 0 orphans, 110s** |
| Canário trocado pra PT-BR | `/root/.openclaw/scripts/semantic-canary.sh` query: `"como funciona a memória persistente e o knowledge graph do sistema"` | Exit 0, `total=10 semantic=10 fts=0` |
| Lição ingerida no nox-mem | `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md` (3 chunks vetorizados) | Forge lê no boot |

### 3. Commits

- VPS (nox-workspace): `b42294c` (auto-commit search.ts) + `418b52f` (lesson file, pushed origin/main)
- Local (memoria-nox): `563c567` (CLAUDE.md: v3.4 entry, incident log, 4 novas convenções, schema v7)

### 4. Convenções adicionadas ao CLAUDE.md

- Sempre `set -a; source /root/.openclaw/.env; set +a` antes de `nox-mem` CLI via SSH/cron/script.
- Pós-operação de memória: `curl /api/health.vectorCoverage` para confirmar `embedded == total`. Nunca confiar na última linha do CLI.
- Canário roda 06:00 daily, query em PT-BR (EN dá falso-positivo/negativo).
- Mudança de ranking/scoring em commit separado (`tune(search):` ou `feat(search):`), com A/B test.
- Boost multiplicativo é veneno quando empilhável — usar aditivo ou normalizar.

---

## Estado final do sistema nox-mem

- **Chunks:** 1,975 (was 2,694 pre-Forge-reindex — delta de ~722 são stale chunks de arquivos deletados, não bug)
- **Embeddings:** 1,975 / 1,975 = 100% coverage
- **Orphans:** 0
- **Canário:** verde (OK total=10 semantic=10 fts=0 orphans=0)
- **KG:** 399 entidades, 516 relações (última build: Sun 21:35)
- **Schema:** v7 (`source_type`, `is_compiled` backfilled por heurística — legado preservado)

---

## Novo tópico iniciado: Import do Notion "Mission Control Nox"

### Contexto
Toto quer importar 9 páginas do Notion (conectadas em "Mission Control Nox") pro sistema de memória gráfico.

### O que foi decidido
- **Quando:** não imediatamente após os incidents — esperar estabilidade. Com 9 páginas sendo pequeno, dá pra fazer em 24-48h (≠ 72h previsto pra volumes maiores).
- **Como:** **híbrido** — ingest único + `sync-notion` semanal (domingo, junto com o vectorize existente).
- **Rollback plan:** chunks taggeados via `source_file LIKE '%notion/mission-control%'`, fácil de deletar em bulk se der ruim.

### O que foi configurado
- **Notion MCP `notion-api`** instalado em `~/.claude.json` (user config) via `claude mcp add notion-api -- npx -y @notionhq/notion-mcp-server --auth-token ntn_...` — **conectado**.
- **Token armazenado** em `~/.zshrc` como `NOTION_API_KEY` (também embedado no comando MCP porque o server usa `--auth-token` em vez de env).
- **⚠️ SECURITY NOTE:** token foi colado no transcript da conversa (compromised). Toto optou por não rotacionar. Se no futuro decidir rotacionar: revogar em https://www.notion.so/profile/integrations, criar novo, atualizar `~/.zshrc` + rodar `claude mcp remove notion-api --scope user && claude mcp add notion-api ...` com o novo.
- **MCP existente `claude.ai Notion`** (endpoint `https://mcp.notion.com/mcp`) está conectado mas suas tools estavam retornando "Tool not found" — por isso instalamos o oficial como backup.

### Bloqueador atual
**Restart do Claude Code pendente.** Os tools do MCP `notion-api` (provavelmente `mcp__notion-api__*`) só aparecem em sessão nova.

---

## Onde continuar na próxima sessão

**Ordem sugerida:**

1. **Confirmar reinício** — primeira coisa: `claude mcp list | grep notion-api` + testar uma fetch de página simples.
2. **Fetchar "Mission Control Nox"** (URL: `https://www.notion.so/Mission-Control-Nox-31d8e29911ab81b08906c7ebc95d4af0`) + subpáginas.
3. **Coletar respostas pendentes do Toto:**
   - **Idioma** das 9 páginas (PT-BR ou EN)? Determina ajuste do canário.
   - **Continua editando no Notion** depois, ou vira read-only pós-import? Determina frequência do sync-notion (semanal vs mensal).
4. **Avaliar conteúdo** e propor estrutura de ingest:
   - Chunk boundaries (por seção? por página?)
   - `chunk_type` apropriado (project? decision? reference?)
   - Tier inicial (**working** por padrão — NÃO Core, pra evitar o problema de dominação que acabamos de corrigir)
   - `source_file` prefixo padrão: `notion/mission-control/<slug>.md`
5. **Escrever spec + plan** em `plans/2026-04-20-notion-import-mission-control.md`:
   - Pilot: 1 página primeiro, validar semantic search retorna ela
   - Full: 9 páginas restantes
   - Cron: `nox-mem sync-notion` domingo 05:30 (antes do vectorize 06:00)
6. **Executar pilot + full com aprovação do Toto** entre etapas.
7. **Atualizar canário** se for preciso suportar idioma adicional (ex: rodar 2 queries, uma PT-BR, uma EN — só falha se AMBAS falharem).

---

## Migração de tarefas: Notion DB → WhatsApp → pending.md (decidido no final da sessão)

### Descobertas técnicas

- **Briefing matinal** não é cron standalone. Script: `/root/.openclaw/workspace/tools/prepare-briefing-context.sh`. Chamado pelo agente Nox (via heartbeat/wakeup, não cron direto no root).
- **Tarefas vêm de Notion database**, não de página: UUID `31d8e299-11ab-81c8-8379-fed013991e7e` (distinct da página "Mission Control Nox" `31d8e29911ab81b0...`, ambas no mesmo workspace).
- **Filtros aplicados:** `Status=Pendente OR Em andamento`, ordenado por `Prioridade`, top 8.
- **Briefing já combina as duas fontes** (Notion DB + `memory/pending.md`) na mesma seção (linha 27: `🗂 TAREFAS & PENDÊNCIAS (Notion + pending.md)`).
- **Notion API key** lido de `~/.config/notion/api_key` na VPS (distinto do `NOTION_API_KEY` local do Mac).

### Decisão do Toto
Migrar captura de tarefas de **Notion → WhatsApp**. Nox já recebe mensagens diretas no próprio número, o Toto confia nele pra escrever em `pending.md` sem duplo-write.

### Plano de migração (4 passos, baixo risco)

1. **Snapshot das tarefas ativas hoje:** rodar uma vez a query Notion (filtros existentes) → exportar top 8 → adicionar como entries em `memory/pending.md` com prioridade preservada.
2. **Patch em `prepare-briefing-context.sh`:** comentar o bloco `A) Notion — tarefas ativas` (linhas ~32-56). Mantém `B) pending.md` (linha ~58+). Briefing passa a ler só de `pending.md`.
3. **Processo novo:** Toto manda WA → Nox (`"Nox, tarefa: X, prio alta"`) → Nox escreve em `pending.md` com frontmatter `priority`. **Obrigatório:** Nox manda ack (`✅ adicionei: X`) em ≤30s. Se não chegar, Toto adiciona manual.
4. **Notion database** fica read-only legacy. Decisão de apagar fica pra depois — sem pressa.

### Riscos conhecidos
- **Nox indisponível** no momento do WA → captura falha. **Mitigação:** ack + retry + fallback manual pra Notion se ack não chegar.
- **Parsing errado de prioridade.** **Mitigação:** Nox confirma se ambíguo antes de gravar.

### Próxima sessão — ordem clara

1. **Restart Claude Code** (pra MCP `notion-api` surfacear tools).
2. `claude mcp list | grep notion-api` → confirmar.
3. Fetchar a **página "Mission Control Nox"** + descobrir as 8 subpáginas (uma delas deve ser a tasks database).
4. **Decidir por página** (8 decisões): import, manter no Notion, ou apagar. Para cada que for importar: chunk_type, tier, source_file prefix.
5. **Executar snapshot da tasks database** (passo 1 do plano acima).
6. **Patch do prepare-briefing-context.sh** (passo 2).
7. **Escrever `plans/2026-04-20-notion-import-e-whatsapp-tasks.md`** com os detalhes finais e marcar no unified roadmap.
8. **Pilot:** 1 página importada primeiro. Validar que `nox-mem search` acha com `match_type: "semantic"` antes de fazer as outras.

---

## Pendências já conhecidas (carry-over, não tocadas hoje)

Do morning report de hoje:
- **13 itens com pendência aberta** (Invoice Aspen + Ademicon >5 dias — marcados 🔴)
- **agents-hub binding** (carry-over)
- **crons fix** (carry-over) — pode estar parcialmente resolvido com o nightly-maintenance consolidado
- **reindex bug** — ✅ resolvido hoje

## Roadmap futuro (não urgente)

- **Allowlist-Core:** em vez de promoção automática por `access_count ≥ 10` (que é volátil — reindex zera), ter allowlist de arquivos que são *sempre* Core (decisions.md, lessons.md, people.md, projects.md, pending.md, SESSION-STATE.md, etc). Forge já fez manualmente mas deveria virar config persistente.
- **Canário multi-idioma:** quando corpus tiver >20% EN (por causa do Notion import), rodar 2 queries no canário.
- **Telemetria de scoring:** logar `top-N scores distribution` em `/api/search` — se todos os top-3 tiverem scores ~iguais por N requests seguidos, alertar (detecta próxima regressão de ranking automática).
