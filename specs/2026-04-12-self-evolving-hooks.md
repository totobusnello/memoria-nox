# Self-Evolving Hooks — Spec

> Sistema de feedback loop automático que transforma correções do usuário em regras permanentes para Claude Code.

**Status:** Proposto
**Data:** 2026-04-12
**Fonte:** [buildthisnow.com/blog/real-examples/self-evolving-hooks](https://www.buildthisnow.com/blog/real-examples/self-evolving-hooks)
**Relação:** Complementa nox-mem (VPS) com aprendizado local (Mac)

---

## Problema

Claude Code começa cada sessão do zero. Quando o usuário corrige algo ("não usa em-dash", "renderiza antes de dizer que terminou"), essa correção morre no fim do contexto. Na próxima sessão, o mesmo erro acontece de novo.

O nox-mem resolve isso para os agentes da VPS (OpenClaw) via hybrid search + Knowledge Graph. Mas no Claude Code local (Mac), não existe feedback loop automático — as correções se perdem.

## Solução: 3 Hooks

### Arquitetura

```
Sessão Claude Code (Mac)
    │
    ├─ [subagent-start.js] ← injeta regras aprendidas no boot de cada subagent
    │
    ├─ (usuário trabalha, corrige, aprova...)
    │
    └─ [on-stop.js] → captura transcript → .claude/learning/sessions/YYYY-MM-DD.jsonl
                                                      │
                                                      ▼
                                            [dream.js] (background)
                                            Condições: 4h+ cooldown, 3+ sessões novas
                                            Spawna: claude -p --model haiku
                                                      │
                                                      ▼
                                            Escreve regras em:
                                            ├─ .claude/learning/global.md
                                            ├─ .claude/learning/agents/{type}.md
                                            └─ .claude/skills/{name}/SKILL.md
```

### Hook 1 — `subagent-start.js` (PreToolUse: Agent)

**Quando:** Antes de qualquer subagent iniciar.
**O que faz:** Lê arquivos de `.claude/learning/` relevantes ao tipo do agente e injeta as regras no prompt do subagent.

**Lógica:**
1. Recebe contexto do Agent tool (tipo do agente, prompt)
2. Verifica se existe `.claude/learning/agents/{type}.md`
3. Se sim, lê as regras e prepend no prompt
4. Sempre inclui `.claude/learning/global.md` (regras universais)

### Hook 2 — `on-stop.js` (Stop)

**Quando:** Sessão Claude Code encerra.
**O que faz:** Parseia o transcript da sessão e extrai sinal bruto (sem interpretação).

**Captura:**
- Todas as mensagens humanas (verbatim)
- Todos os agents que rodaram (tipo, prompt preview, output preview)
- Todas as skills que foram lidas

**Output:** Uma linha JSONL por sessão em `.claude/learning/sessions/YYYY-MM-DD.jsonl`

```json
{
  "ts": "2026-04-12T14:32:11.000Z",
  "session_id": "a7b3c2d",
  "human_messages": ["escreve um post", "não usa em-dash", "agora sim"],
  "agents_run": [{"type": "linkedin-strategist", "prompt_preview": "...", "output_preview": "..."}],
  "skills_read": ["linkedin-strategist"]
}
```

**Design decisions:**
- Sem regex de classificação (correção vs aprovação) — o dream worker faz isso
- Trunca previews em 200 chars para manter JSONL leve
- Um arquivo por dia (não por sessão) para reduzir file count

### Hook 3 — `dream.js` (Background Worker)

**Quando:** Disparado pelo on-stop.js quando duas condições são verdadeiras:
1. 4+ horas desde o último dream run
2. 3+ sessões novas desde o último dream run

**O que faz:** Spawna `claude -p --model haiku` com acesso Write/Edit ao projeto.

**Prompt do dream worker:**
- Recebe últimas 20 sessões como contexto
- Classifica mensagens humanas (correção, aprovação, instrução, neutro)
- Identifica padrões: mesma correção em 2+ sessões → regra
- 1 sessão = ruído, ignora
- Max 5 regras por run (auto-limitação contra drift)

**Onde escreve:**
| Tipo de regra | Destino |
|---------------|---------|
| Universal (todo agente) | `.claude/learning/global.md` |
| Específica de um agente | `.claude/learning/agents/{type}.md` |
| Bug na skill | `.claude/skills/{name}/SKILL.md` |

**Regras boas vs ruins:**
- Bom: "Never use em-dashes. Use commas or short sentences instead."
- Ruim: "Be more careful with formatting."
- Regras devem ser one-line, específicas, acionáveis

### Metadados de controle

O dream worker mantém estado em `.claude/learning/dream-state.json`:
```json
{
  "last_run": "2026-04-12T18:00:00.000Z",
  "sessions_since_last_run": 0,
  "total_rules_written": 12,
  "total_sessions_analyzed": 47
}
```

---

## File Tree Final

```
.claude/
  hooks/
    subagent-start.js       ← injeta regras no boot dos subagents
    on-stop.js              ← captura sessão raw ao encerrar
    dream/
      dream.js              ← analisa padrões, escreve regras
  learning/
    sessions/
      2026-04-12.jsonl      ← observações raw (1 linha por sessão)
    global.md               ← regras universais aprendidas
    agents/
      linkedin-strategist.md
      code-reviewer.md
      ...
    dream-state.json        ← estado do dream worker
  settings.json             ← registro dos hooks
```

---

## Integração com nox-mem (Bridge Local → VPS)

O dream worker pode opcionalmente **ingerir regras aprendidas no nox-mem** via HTTP API (:18800), criando um bridge entre aprendizado local e os agentes da VPS.

```
Dream Worker (Mac)
    │
    ├─ Escreve regras locais (.claude/learning/)
    │
    └─ POST /api/ingest (VPS :18800)
       └─ Chunk tipo "learning-rule", tags: [source:dream-worker, scope:global|agent:{type}]
```

Isso permite que:
- Agentes OpenClaw (nox, atlas, boris, cipher, forge, lex) acessem regras via `nox_mem_search`
- O KG extraia entidades das regras (ex: "em-dash" → entity tipo `concept`, relação `should_avoid`)
- Cross-agent intelligence distribua aprendizados relevantes

### Quando NÃO fazer o bridge

- Regras muito específicas do Claude Code local (ex: formatting de output no terminal)
- Regras que dependem de skills locais que não existem na VPS
- Durante períodos de alta carga na VPS (check health endpoint primeiro)

---

## Comparação de Abordagens

| Dimensão | Self-Evolving Hooks | nox-mem | Combinados |
|----------|-------------------|---------|------------|
| Escopo | Claude Code local (Mac) | VPS agents (OpenClaw) | Full stack |
| Sinal | Correções do user no transcript | Chunks ingeridos + KG | User feedback + knowledge |
| Storage | Arquivos .md flat | SQLite FTS5 + vec + KG | Ambos |
| Latência | Instantâneo (file read) | ~100ms (hybrid search) | Cada um no seu domínio |
| Interpretação | dream.js (Haiku, batch) | KG extraction (Gemini) | Complementares |
| Custo | ~$0.01/dream run (Haiku) | Gemini embeddings + Ollama | Marginal |

---

## Princípios de Design

1. **User é ground truth** — correções do usuário são o sinal mais confiável, sem avaliador AI intermediário
2. **Captura raw, interpreta depois** — on-stop.js não classifica, dream.js interpreta
3. **Noise filtering** — 1 sessão = ruído, 2+ sessões com mesma correção = regra
4. **Auto-limitação** — max 5 regras por dream run, cooldown de 4h
5. **Lê antes de escrever** — dream worker lê o arquivo destino antes de adicionar (sem duplicatas)
6. **Específico > genérico** — "never use em-dashes" > "be careful with formatting"

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Dream worker escreve regra errada | Max 5 por run + user pode editar .md manualmente |
| Regras conflitantes | Dream prompt instrui: "Read the target file first. Do not duplicate or contradict existing rules." |
| Drift acumulativo | Cooldown 4h + threshold 3 sessões + regras one-line acionáveis |
| Transcript muito grande | Trunca previews em 200 chars, só salva human messages + agent metadata |
| Custo API | Haiku é ~$0.01/run, max 1 run a cada 4h = ~$0.06/dia |

---

## Próximos Passos

- [ ] Criar plan de implementação com tasks detalhadas
- [ ] Implementar on-stop.js (captura de sessão)
- [ ] Implementar dream.js (análise de padrões + escrita de regras)
- [ ] Implementar subagent-start.js (injeção de regras)
- [ ] Registrar hooks em settings.json
- [ ] Testar ciclo completo: correção → captura → dream → regra → próxima sessão
- [ ] (Opcional) Bridge para nox-mem via HTTP API
