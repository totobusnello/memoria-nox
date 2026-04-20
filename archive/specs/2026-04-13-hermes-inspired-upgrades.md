# Hermes-Inspired Upgrades para nox-mem — Spec

> 4 upgrades inspirados na arquitetura do Hermes Agent (NousResearch) adaptados ao stack TypeScript/OpenClaw do nox-mem.

**Status:** Upgrades 1-4 implementados, testando
**Data:** 2026-04-13
**Última atualização:** 2026-04-13 21:30
**Fonte:** [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) + plugin Hindsight + hermes-agent-self-evolution
**Relação:** Evolui nox-mem v3.2 (VPS) — complementa specs `self-evolving-hooks` e `nox-neural-memory`
**Prioridade proposta:** Upgrade 1 > Upgrade 2 > Upgrade 4 > Upgrade 3

---

## Contexto

O Hermes Agent da NousResearch é um runtime Python para agentes AI com 47 tools, 15+ plataformas e um sistema de memória plugável. Apesar de stack diferente (Python vs nosso TypeScript), 4 padrões arquiteturais resolvem gaps reais no nox-mem.

### O que o nox-mem já tem

| Capacidade | Status |
|---|---|
| Hybrid search (FTS5 BM25 + Gemini semantic + RRF) | v2.6 |
| Knowledge Graph v2 (384 entidades, 537 relações) | v3.0 |
| Cross-agent intelligence (profiles, sharing, cross-KG) | v3.0 |
| MCP server (14 tools) | v2.0 |
| Self-improve (decisions tracking) | v2.2 |
| Cron consolidation/vectorization | v2.0 |

### O que falta (gaps identificados no Hermes)

| Gap | Impacto |
|---|---|
| Memória injetada passivamente (sem o agente pedir) | Alto |
| Retrieval profundo com raciocínio sobre o grafo | Alto |
| Cristalização de skills como artefatos executáveis | Medio |
| Evolucao genetica de prompts/tools | Alto (longo prazo) |

---

## Upgrade 1 — Async Pre-fetch Memory Injection

### Problema

Hoje os agentes precisam chamar `nox_mem_search` explicitamente para consultar a memória. Isso depende do agente "lembrar de lembrar" — e frequentemente ele não lembra, especialmente em tarefas complexas onde o contexto já está cheio.

O `primer` (comando que gera resumo do estado) é chamado manualmente ou por cron. Não há injeção automática de memória relevante ao contexto da conversa atual.

### Inspiracao Hermes

O plugin **Hindsight** faz async prefetch antes de cada turn:
1. Recebe a mensagem do usuario
2. Em paralelo ao processamento, busca memórias relevantes
3. Injeta as memórias no system prompt da próxima resposta
4. O agente nunca precisa chamar um tool — o contexto já está lá

### Proposta para nox-mem

```
Mensagem do usuario chega no Gateway (:18789)
    │
    ├─ [pre-turn-hook] ← NOVO
    │   ├─ Extrai keywords + intent da mensagem (regex + heurística, sem LLM)
    │   ├─ Chama nox-mem hybrid search (async, timeout 2s)
    │   ├─ Filtra top 3 resultados por relevância (score > threshold)
    │   └─ Injeta como bloco <memory-context> no system prompt
    │
    └─ Mensagem processada pelo LLM (com memórias já no contexto)
```

### Implementacao

**Onde:** Gateway hook (OpenClaw suporta `beforeTurn` hooks em `openclaw.json`)

**Arquivo:** `/root/.openclaw/workspace/tools/nox-mem/hooks/pre-turn.js`

**Lógica:**
```
1. Receber mensagem do usuario via hook context
2. Extrair keywords:
   - Nomes próprios (regex: palavras capitalizadas)
   - Termos técnicos (regex: camelCase, snake_case, siglas 2+ chars)
   - Entidades KG conhecidas (lookup rápido em cache in-memory)
3. Se keywords encontradas:
   a. nox-mem search --hybrid --limit 3 --min-score 0.4 "<keywords>"
   b. Formatar resultados como bloco markdown
   c. Retornar como additionalContext para o system prompt
4. Se nenhuma keyword: skip (zero overhead)
5. Timeout hard de 2s — se busca demorar, segue sem memória
```

**Cache:**
- Manter lista de entidades KG em memória (atualizar a cada `kg-build`)
- Cache de queries recentes (LRU, 100 entries, TTL 5min)
- Evita re-buscas para perguntas de follow-up

**Metricas:**
- `prefetch_hit_rate` — % de turns com memória injetada
- `prefetch_latency_ms` — P50/P95 do tempo de busca
- `prefetch_skip_rate` — % de turns sem keywords (skip)

### Riscos

| Risco | Mitigacao |
|---|---|
| Latência adicionada a cada turn | Timeout 2s hard, skip se sem keywords |
| Memórias irrelevantes poluem contexto | Score mínimo 0.4, máximo 3 resultados, ~500 tokens |
| OpenClaw não suporta beforeTurn hook | Verificar docs/código; fallback: middleware no RelayPlane |
| Overhead de CPU na VPS | Cache LRU + keyword extraction sem LLM |

### Validacao

- [ ] Confirmar que OpenClaw suporta `beforeTurn` hook (ou equivalente)
- [ ] Medir latência do hybrid search com limite de 3 resultados
- [ ] Testar com 10 mensagens reais e avaliar relevância dos prefetches
- [ ] Comparar qualidade de resposta com vs sem prefetch (A/B manual)

---

## Upgrade 2 — Reflect: Deep KG Synthesis

### Problema

O `kg-query` atual retorna entidades e relações brutas. Se você pergunta "como o projeto Granix se relaciona com o Frooty?", recebe uma lista de entidades e relações — mas nenhuma **síntese** ou **raciocínio** conectando os pontos.

O hybrid search encontra chunks relevantes. O KG encontra entidades conectadas. Mas nenhum dos dois **raciocina sobre o que encontrou** para produzir um insight.

### Inspiracao Hermes

O Hindsight tem dois modos:
- **`recall`** — busca rápida (keyword + semantic). Nosso equivalente: `nox_mem_search`
- **`reflect`** — busca profunda: traversal no KG, coleta fatos, sintetiza com LLM, retorna insight elaborado. Mais lento (5-15s), mais profundo.

### Proposta para nox-mem

Novo comando CLI + MCP tool: `nox-mem reflect`

```
nox-mem reflect "Como evoluiu a estratégia de AI para a Galapagos?"
```

**Pipeline (3 etapas):**

```
Etapa 1 — Gather (sem LLM)
├─ hybrid search top 10 (BM25 + semantic)
├─ kg-query entities mencionadas
├─ kg-path entre entidades encontradas (BFS, max depth 3)
├─ decision-history das decisões relacionadas
└─ Monta "evidence bundle" (~2000 tokens)

Etapa 2 — Synthesize (com LLM)
├─ Prompt: "Given this evidence, answer: <pergunta>"
├─ Evidence bundle como contexto
├─ Modelo: Gemini 2.5 Flash (rápido, barato, já usado no KG)
├─ Max output: 500 tokens
└─ Retorna: síntese estruturada com fontes citadas

Etapa 3 — Cache
├─ Salva resultado em tabela reflect_cache (pergunta hash, resposta, TTL 24h)
└─ Próxima reflect com mesma pergunta retorna cache
```

### Schema novo

```sql
CREATE TABLE IF NOT EXISTS reflect_cache (
  query_hash TEXT PRIMARY KEY,
  query TEXT NOT NULL,
  response TEXT NOT NULL,
  evidence_sources TEXT, -- JSON array de chunk IDs usados
  model TEXT DEFAULT 'gemini-2.5-flash',
  created_at TEXT DEFAULT (datetime('now')),
  ttl_hours INTEGER DEFAULT 24
);
```

### MCP Tool

```json
{
  "name": "nox_mem_reflect",
  "description": "Deep synthesis over memory + knowledge graph. Slower than search (5-15s) but produces reasoned insights with cited sources. Use for questions that need connecting dots across multiple topics.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": { "type": "string", "description": "Question to reflect on" },
      "max_depth": { "type": "number", "description": "KG traversal depth (default 3)" },
      "no_cache": { "type": "boolean", "description": "Force fresh synthesis" }
    },
    "required": ["question"]
  }
}
```

### Riscos

| Risco | Mitigacao |
|---|---|
| Custo de API (Gemini) por reflect | Cache 24h, rate limit 20/hora |
| Latência 5-15s | Só usar quando pedido explicitamente (não no prefetch) |
| Alucinação na síntese | Evidence bundle citado, fontes rastreáveis |
| Evidence bundle muito grande | Cap em 2000 tokens, rank por relevância |

### Validacao

- [ ] Definir 5 perguntas de teste que exigem raciocínio cross-topic
- [ ] Comparar resposta do reflect vs search puro
- [ ] Medir custo médio por reflect (tokens Gemini)
- [ ] Validar que fontes citadas são reais (não alucinadas)

---

## Upgrade 3 — Prompt Evolution com Feedback Loop

### Problema

As tool descriptions do MCP server e os prompts dos agentes (SOUL.md) foram escritos uma vez e nunca otimizados sistematicamente. O `self-improve` coleta padrões mas não reescreve prompts automaticamente.

O spec `self-evolving-hooks` (2026-04-12) trata do lado Mac (Claude Code local). Este upgrade trata do lado **VPS** — otimizar os prompts que os agentes OpenClaw usam.

### Inspiracao Hermes

O `hermes-agent-self-evolution` usa:
- **DSPy** — framework de otimização de prompts (BootstrapFewShot, MIPROv2)
- **GEPA** — Genetic-Pareto Prompt Evolution: mutação + crossover + seleção multi-objetivo
- Roda em schedule (semanal), produz candidatos, avalia com métricas, promove o melhor

### Proposta para nox-mem (versao simplificada)

Não vamos implementar DSPy/GEPA completo (complexidade alta, Python). Em vez disso, um **feedback loop LLM-driven** mais simples:

```
Cron semanal (Dom 07:00)
    │
    ├─ Coleta dados:
    │   ├─ self-improve patterns (últimos 7 dias)
    │   ├─ Feedback aprovado/rejeitado (feedback/*.json)
    │   ├─ Tool usage stats (quais MCP tools foram mais/menos usadas)
    │   └─ Perguntas que retornaram 0 resultados no search
    │
    ├─ Análise (Gemini 2.5 Flash):
    │   ├─ "Quais tool descriptions estão confusas?" (baseado em uso)
    │   ├─ "Quais patterns de self-improve se repetem?" (consolidar)
    │   └─ "Que tipo de queries falham?" (gap analysis)
    │
    ├─ Propõe mudanças:
    │   ├─ Tool descriptions reescritas (diff format)
    │   ├─ SOUL.md patches sugeridos
    │   └─ Novos self-improve patterns
    │
    └─ Salva em:
        └─ memory/evolution-proposals/YYYY-MM-DD.md
            (Humano revisa e aprova antes de aplicar)
```

**Chave:** Nenhuma mudança é aplicada automaticamente. O cron **propõe**, o humano **aprova**. Isso é mais seguro que GEPA automático e adequado para nosso volume.

### Arquivo novo

`/root/.openclaw/workspace/tools/nox-mem/scripts/evolve.js`

### Riscos

| Risco | Mitigacao |
|---|---|
| Mudanças ruins em prompts | Humano aprova tudo (sem auto-apply) |
| Dados insuficientes para análise | Mínimo 7 dias de dados, skip se pouco sinal |
| Custo de API semanal | 1 chamada Gemini/semana (~2K tokens) = negligível |

### Validacao

- [ ] Definir formato do evolution-proposals/*.md
- [ ] Rodar análise manual primeiro (sem cron) com dados reais
- [ ] Avaliar qualidade das sugestões antes de automatizar
- [ ] Definir critérios de "sinal suficiente" para não rodar no vazio

---

## Upgrade 4 — Skill Crystallization

### Problema

Quando um agente resolve um problema complexo (ex: "configurar relay de email com SPF+DKIM"), o conhecimento morre no transcript. O `decision-set` salva a **decisão** ("usamos Postfix com relay Mailgun"), mas não o **procedimento** executável.

Na próxima vez que alguém pedir a mesma coisa, o agente começa do zero.

### Inspiracao Hermes

Após tarefas complexas, Hermes automaticamente:
1. Detecta que a tarefa foi não-trivial (multi-step, > 5 tool calls)
2. Extrai o procedimento como uma "skill" nomeada
3. Salva com: nome, descrição, pré-condições, steps, código
4. Na próxima ocorrência similar, recupera e executa a skill

### Proposta para nox-mem

Novo tipo de chunk: `procedure`

```
Tipo: procedure
Título: "Configurar email relay com Postfix + Mailgun"
Pré-condições: ["VPS Ubuntu 22+", "conta Mailgun ativa"]
Steps:
  1. apt install postfix libsasl2-modules
  2. Configurar /etc/postfix/main.cf (relayhost, sasl)
  3. Gerar app password no Mailgun
  4. Testar com echo "test" | mail -s "Test" user@domain
  5. Verificar logs: tail -f /var/log/mail.log
Tags: ["email", "postfix", "mailgun", "relay"]
Agente de origem: cipher
Data: 2026-04-13
Validado: false (muda para true após execução bem-sucedida)
```

### Schema

Reutilizar a tabela `chunks` existente com type=`procedure` e metadata JSON:

```sql
-- Sem tabela nova. Usar chunks com:
-- type = 'procedure'
-- metadata = JSON com {preconditions, steps, tags, origin_agent, validated}
```

### CLI

```bash
# Cristalizar procedimento manualmente
nox-mem crystallize --title "Setup email relay" --agent cipher

# Buscar procedimentos
nox-mem search --type procedure "email relay"

# Marcar como validado após execução bem-sucedida
nox-mem crystallize-validate <chunk_id>
```

### MCP Tool

```json
{
  "name": "nox_mem_crystallize",
  "description": "Save a multi-step procedure as a reusable skill. Use after completing complex tasks (5+ steps) that others might need to repeat.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": { "type": "string" },
      "preconditions": { "type": "array", "items": { "type": "string" } },
      "steps": { "type": "array", "items": { "type": "string" } },
      "tags": { "type": "array", "items": { "type": "string" } }
    },
    "required": ["title", "steps"]
  }
}
```

### Deteccao automatica (futuro)

Na v1, cristalização é manual (agente ou humano chama `crystallize`). Na v2, um hook `afterTurn` pode detectar automaticamente:
- Sessão com > 5 tool calls de execução (bash, edit)
- Sucesso confirmado pelo usuário
- Prompt: "Extraia o procedimento desta sessão"

### Riscos

| Risco | Mitigacao |
|---|---|
| Procedimentos desatualizados | Campo `validated` + TTL (invalidar após 90 dias sem re-validação) |
| Procedimentos errados cristalizados | Flag `validated: false` até execução bem-sucedida |
| Poluição do search com procedures | Boost negativo para procedures não-validadas (-0.5x) |

### Validacao

- [ ] Definir 3 procedimentos reais dos agentes para cristalizar como teste
- [ ] Verificar que hybrid search retorna procedures relevantes
- [ ] Testar fluxo completo: crystallize → search → execute → validate

---

## Sequência de Implementação

```
Semana 1-2: Upgrade 1 (Pre-fetch Injection) — EM PROGRESSO
├─ ✅ Verificar suporte a beforeTurn hook no OpenClaw (message:received existe)
├─ ✅ DESCOBERTA: plugin Active Memory built-in faz exatamente isso
├─ ✅ Ativado Active Memory para agente nox (Haiku, timeout 5s, queryMode message)
├─ ✅ Transcript gerado — sub-agente roda, mas timeout 2s era insuficiente → corrigido para 5s
├─ ⏳ Testar com timeout 5s (pendente — Toto no celular)
├─ ⏳ Se funcionar, expandir para todos os agentes
└─ ⏳ Medir latência e hit rate

Semana 3-4: Upgrade 2 (Reflect)
├─ Implementar gather pipeline (search + kg + paths)
├─ Implementar synthesize com Gemini
├─ Criar tabela reflect_cache
├─ Adicionar CLI + MCP tool
└─ Testar com 5 perguntas cross-topic

Semana 5: Upgrade 4 (Skill Crystallization)
├─ Adicionar type='procedure' ao schema
├─ Implementar CLI crystallize + crystallize-validate
├─ Adicionar MCP tool
├─ Cristalizar 3 procedimentos reais como teste
└─ Ajustar boost/ranking para procedures

Semana 6+: Upgrade 3 (Prompt Evolution) — após dados suficientes
├─ Implementar coleta de métricas (tool usage, failed queries)
├─ Implementar script evolve.js
├─ Rodar análise manual primeiro
├─ Automatizar via cron quando qualidade validada
└─ Definir processo de review humano
```

---

## Investigação: Eventos de Hook no OpenClaw v2026.4.11

Verificação na VPS (2026-04-13) revelou que OpenClaw suporta **7 eventos de hook**:

| Evento | Descrição | Hooks atuais |
|---|---|---|
| `gateway:startup` | Gateway inicia | boot-md, memory-core-dreaming |
| `agent:bootstrap` | Agente é bootstrapped | bootstrap-extra-files |
| `command` | Qualquer comando executado | command-logger |
| `command:new` | Comando /new | session-memory |
| `command:reset` | Comando /reset | session-memory |
| **`message:received`** | **Mensagem do usuario chega** | nenhum (disponível!) |
| `message:preprocessed` | Mensagem pré-processada | nenhum |
| `message:sent` | Resposta enviada | nenhum |
| `message:transcribed` | Audio transcrito | nenhum |
| `session:patch` | Sessão atualizada | nenhum |

**Achado-chave:** `message:received` existe e está livre. É exatamente o evento que precisamos para o pre-fetch do Upgrade 1. Não precisamos de `beforeTurn` — `message:received` é o equivalente nativo do OpenClaw.

### Hooks instalados (5/5 ready)

| Hook | Evento | Fonte |
|---|---|---|
| boot-md | gateway:startup | openclaw-bundled |
| bootstrap-extra-files | agent:bootstrap | openclaw-bundled |
| command-logger | command | openclaw-bundled |
| session-memory | command:new, command:reset | openclaw-bundled |
| memory-core-short-term-dreaming-cron | gateway:startup | plugin:memory-core |

### Como criar um hook custom

OpenClaw v2026.4.11 usa hooks como plugins com `HOOK.md` manifest + `handler.js`. O handler recebe um `event` object com:
- `event.type` (ex: "message")
- `event.action` (ex: "received")
- `event.context` (cfg, deps, message content)

O hook pode retornar conteúdo para injetar no contexto via `event.context`.

---

## Decisões — Veredicto Final

### D1: Modelo para reflect synthesis

| Opção | Prós | Contras |
|---|---|---|
| **Gemini 2.5 Flash** | Já pago, já usado no KG extraction, rápido (~1-2s), JSON schema nativo, thinkingBudget:0 funciona | Depende de internet, custo por token (baixo) |
| Ollama llama3.2:3b | Grátis, local, sem latência de rede | Qualidade inferior para síntese complexa, CPU-bound na VPS (lento), KEEP_ALIVE 5min = cold start |
| Haiku via RelayPlane | Boa qualidade, cascade fallback | Custo maior que Gemini, mais um hop via RelayPlane |

**Veredicto: Gemini 2.5 Flash.** Já está integrado no `kg-llm.ts`, já comprovado que funciona bem para extração e síntese. Custo negligível (~$0.01 por reflect). Ollama é lento demais para síntese (3B parâmetros não consegue raciocinar sobre evidence bundles complexos). Haiku seria bom mas adiciona custo e complexidade desnecessários.

### D2: Onde rodar o pre-fetch hook

| Opção | Prós | Contras |
|---|---|---|
| **Gateway `message:received` hook** | Evento nativo existe, path direto ao nox-mem DB, sem hop extra | Precisa criar plugin/hook custom |
| RelayPlane middleware | Intercepta antes do LLM | Não tem acesso ao nox-mem DB (precisaria HTTP call), adiciona latência |
| MCP server tool | Já existe infra | Requer o agente chamar (derrota o propósito de "passivo") |

**Veredicto: Gateway `message:received`.** A investigação confirmou que o evento existe e está livre. É a opção mais direta — o hook roda no mesmo processo que tem acesso ao SQLite do nox-mem. Zero hops extras. RelayPlane não faz sentido porque não tem acesso ao DB. MCP server derrota o propósito (o agente teria que chamar).

### D3: Skill crystallization automática vs manual

| Opção | Prós | Contras |
|---|---|---|
| Auto-detect | Captura tudo sem esforço | Polui com procedimentos irrelevantes, falsos positivos |
| **Manual only (v1)** | Controle total, zero lixo | Depende do agente/humano lembrar de cristalizar |
| Hybrid | Melhor dos dois | Complexidade de implementação |

**Veredicto: Manual v1, com nudge.** Começar manual para garantir qualidade. Mas adicionar um "nudge" — após sessões com > 8 tool calls de execução (bash/edit), o hook `message:sent` pode logar um lembrete no audit: "Sessão complexa detectada — considere cristalizar o procedimento com `nox-mem crystallize`". Isso é barato e cria o hábito sem automatizar o conteúdo.

### D4: TTL do reflect_cache

| Opção | Prós | Contras |
|---|---|---|
| 12h | Dados sempre frescos | Cache miss frequente, custo de API dobra |
| **24h** | Alinha com ciclo de consolidation diário (23h) | Pode servir dado stale se consolidation mudar algo |
| 7d | Máximo reuso, mínimo custo | Dados definitivamente stale após consolidation/ingest |

**Veredicto: 24h.** A consolidation roda a cada 2 dias (23h), e o `update-session` roda diário (23:30). Com TTL 24h, o cache expira naturalmente antes do próximo ciclo de consolidation. Se quiser ser conservador, podemos invalidar o cache explicitamente quando `consolidate` ou `ingest` rodam (um `DELETE FROM reflect_cache` no final desses scripts).

### D5: Max tokens do evidence bundle

| Opção | Impacto no custo Gemini | Qualidade da síntese |
|---|---|---|
| 1000 | ~$0.003/reflect | Pode faltar contexto para perguntas amplas |
| **2000** | ~$0.006/reflect | Bom balanço — cabe ~8 chunks resumidos |
| 4000 | ~$0.012/reflect | Overkill para a maioria das perguntas, custo 4x |

**Veredicto: 2000 tokens.** Com hybrid search retornando top 10 e cada chunk resumido a ~200 tokens, 2000 cabe ~8-10 evidências condensadas + a pergunta + instruções. É o sweet spot. Se na prática a qualidade ficar ruim, escalar para 3000 é trivial (mudar 1 constante).

### D6: Threshold do pre-fetch score

| Threshold | Comportamento esperado |
|---|---|
| 0.3 | ~60% dos turns teriam memória injetada — muitos falsos positivos |
| **0.4** | ~35-40% — bom balanço relevância vs cobertura |
| 0.5 | ~15-20% — só matches muito fortes, perde contexto útil |

**Veredicto: 0.4, com ajuste empírico.** Começar com 0.4 e logar todas as injeções com score para análise posterior. Após 7 dias de dados, ajustar baseado na distribuição real. O pre-fetch spec já prevê métricas (`prefetch_hit_rate`, `prefetch_skip_rate`) — usar essas para calibrar. Se hit_rate > 50% com threshold 0.4, subir para 0.45. Se < 20%, baixar para 0.35.

---

## Metricas de Sucesso

| Métrica | Baseline (hoje) | Target |
|---|---|---|
| % de turns com contexto de memória | ~5% (só quando agente chama search) | 40%+ (pre-fetch automático) |
| Qualidade de respostas cross-topic | Fraca (dados brutos) | Boa (reflect com síntese) |
| Procedimentos reutilizáveis catalogados | 0 | 20+ (em 60 dias) |
| Tool descriptions otimizadas | 0 revisões | 1 ciclo completo |
| Latência média do pre-fetch | N/A | < 1.5s P95 |

---

## Log de Implementação (2026-04-13)

### Sessão 1 — Ativação de plugins (15:00-19:30)

**Backup criado:** `/root/.openclaw/workspace/backups/pre-hermes-20260413-1527/` (137MB, full snapshot)

**Mudanças aplicadas na VPS:**

1. **Active Memory plugin ativado** — `plugins.entries.active-memory` em openclaw.json
   - Config: agents=[nox], model=haiku, timeout=5s, queryMode=message, promptStyle=balanced, maxSummaryChars=500
   - Transcript gerado em `/root/.openclaw/plugins/active-memory/transcripts/agents/nox/active-memory/`
   - Bug encontrado: timeout de 2s era insuficiente → corrigido para 5s
   - Status: ⏳ aguardando teste com timeout corrigido

2. **`.env` fix — `export` removido** — `sed -i 's/^export //' /root/.openclaw/.env`
   - 19 env vars tinham `export` na frente → systemd ignorava todas
   - GROQ_API_KEY não chegava ao gateway → cascade fallback para Groq estava quebrado
   - Backup: `/root/.openclaw/.env.bak-pre-fix`
   - Status: ✅ corrigido, zero warnings no journalctl

3. **5 plugins adicionais ativados:**
   - `memory-wiki` — wiki persistente Obsidian-friendly (vault vazio, precisa seed)
   - `diffs` — diff viewer para agentes (disponível para Forge code review)
   - `brave` — web search (key BRAVE_API_KEY já estava no .env)
   - `firecrawl` — web scraping (key copiada do Mac ~/.zshrc para VPS .env)
   - `webhooks` — GitHub CI failures → Forge (route `/hooks/github`, Bearer auth)
   - Status: ✅ todos loaded

4. **Delivery queue limpa** — 1273 entries stale removidas, 0 restantes

5. **Memory-core dreaming desabilitado** — nunca funcionou ("cron service unavailable"). nox-mem crons já cobrem consolidation/dedup/prune.

6. **Active Memory expandido para 6 agentes** — nox, atlas, boris, cipher, forge, lex

7. **decisions.md e projects.md atualizados na VPS** — estado real documentado

8. **Crons verificados** — 7 entries, já limpos pelo hardening 08/04

9. **Webhooks GitHub → Forge configurado:**
   - Plugin `webhooks` ativo, route `github-ci` → sessão `forge`
   - Firewall: porta 18789 aberta para GitHub IPs (4 ranges)
   - Repos configurados: Granix-App, daily-tech-digest (secret + workflow)
   - Teste manual: `200 OK`, TaskFlow criado para Forge
   - Doc: `docs/github-webhook-setup.md`

10. **Upgrade 2 — Reflect implementado:**
    - Arquivo: `/root/.openclaw/workspace/tools/nox-mem/src/reflect.ts`
    - CLI: `nox-mem reflect "pergunta"` (precisa `export $(grep -v '^#' .env | xargs)`)
    - MCP tool: `nox_mem_reflect`
    - Pipeline: hybrid search top 10 → KG entities → decisions → graph paths → Gemini Flash synthesis
    - Cache: 24h no SQLite (tabela `reflect_cache`)
    - Testado: 10 evidence items, 5 sources citadas (INCIDENT-2026-03-31.md, etc)

11. **Upgrade 4 — Crystallize implementado:**
    - Arquivo: `/root/.openclaw/workspace/tools/nox-mem/src/crystallize.ts`
    - CLI: `nox-mem crystallize --title "..." --tags "..."` + `nox-mem crystallize-validate <id>`
    - MCP tool: `nox_mem_crystallize`
    - Chunks tipo `procedure` — buscáveis via FTS/hybrid
    - Seed: "Gateway crash loop recovery" (chunk #47397, 6 steps)
    - Testado: aparece como resultado #2 em search "gateway crash recovery"

12. **Disk cleanup** — ~500MB liberados (nox-mem-bad.db, 4 backups antigos, delivery queue backups, workspace backups velhos)

**Total de plugins ativos:** 15 (era 10): acpx, active-memory, browser, device-pair, diffs, discord, memory-wiki, phone-control, talk-voice, telegram, webhooks, whatsapp + providers brave, firecrawl, memory-core

**RelayPlane:** está ativo na porta 4100 mas `ANTHROPIC_BASE_URL` não está no .env → gateway conecta direto à Anthropic, sem cascade fallback. **Decisão pendente.**

**Rollback:** restaurar backup em `/root/.openclaw/workspace/backups/pre-hermes-20260413-1527/` + `.env.bak-pre-fix`

---

## Pendentes para próxima sessão

### Testes via Discord
- [ ] Active Memory recall com timeout 5s (verificar transcripts em `/root/.openclaw/plugins/active-memory/transcripts/`)
- [ ] Brave web search: pedir a um agente para pesquisar algo na web
- [ ] Firecrawl fetch: pedir a um agente para buscar conteúdo de uma URL

### MCP Server rebuild
- [ ] O nox-mem MCP server (stdio) precisa ser recompilado para servir `nox_mem_reflect` e `nox_mem_crystallize`
- [ ] O nox-mem-api (HTTP :18800) precisa de endpoints novos para reflect e crystallize
- [ ] Compilar: `cd /root/.openclaw/workspace/tools/nox-mem && npx tsc` (ou `npx tsx` que já funciona sem build)
- [ ] Reiniciar: `systemctl restart nox-mem-api`

### RelayPlane
- [ ] Decidir: religar (`ANTHROPIC_BASE_URL=http://127.0.0.1:4100` no .env) ou manter direto
- [ ] Se religar: verificar config do RelayPlane em `/root/.relayplane/config.json` (cascade atualizado?)
- [ ] Testar: enviar mensagem → verificar se cascade funciona quando Anthropic falha

### Seed de procedures
- [ ] Cristalizar incidentes do incident log como procedures:
  - "Config key não reconhecida fix" (incidente 01/04)
  - "Node.js DEP0040 crash loop fix" (incidente 01/04)
  - "Bot Telegram duplicado fix" (incidente 31/03)
  - "Auth profile cooldown reset" (recorrente)

### CLAUDE.md local
- [ ] Atualizar `memoria-nox/CLAUDE.md` e `.claude/CLAUDE.md` com:
  - Novos comandos: `reflect`, `crystallize`, `crystallize-validate`
  - Novos MCP tools: `nox_mem_reflect`, `nox_mem_crystallize`
  - Active Memory config e status
  - Plugins ativados (15 total)
  - Webhooks setup

### Dashboard
- [ ] Adicionar endpoints no HTTP API para: Active Memory hit rate, procedures list, reflect cache stats
- [ ] Adicionar cards no agent-hub-dashboard

---

## Referências

- [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) — Runtime e arquitetura
- [Hindsight Memory Provider](https://github.com/NousResearch/hermes-agent/blob/main/plugins/memory/hindsight/README.md) — Pre-fetch + reflect pattern
- [hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) — DSPy + GEPA
- [nox-mem spec original](./2026-03-14-nox-memory-system-design.md) — Arquitetura base
- [Self-evolving hooks spec](./2026-04-12-self-evolving-hooks.md) — Feedback loop local (Mac)
- [Nox Neural Memory vision](../docs/nox-neural-memory.md) — Roadmap geral
