---
chunk_type: reference
source: internal
date: 2026-04-20
tags: [policy, agents, memory, nox-mem, onboarding]
audience: [forge, nox, atlas, boris, cipher, lex]
supersedes: notion-mission-control
---

# Policy: Onde registrar lições, decisões, erros e melhorias

**Vigência:** 2026-04-20 em diante
**Vale para:** todos os agentes (Forge, Nox, Atlas, Boris, Cipher, Lex) + Toto
**Substitui:** Notion Mission Control — Nox (agora read-only legacy)

## TL;DR (decisão em 30 segundos)

```
Tenho uma info pra guardar. É:
├── Insight técnico, padrão, postmortem → shared/lessons/YYYY-MM-DD-<slug>.md
├── Decisão de arquitetura / trade-off → nox-mem decision-set <key> <value>
│                                        OU shared/decisions/YYYY-MM-DD-<slug>.md (narrativa longa)
├── Incident (bug + root cause + fix) → shared/lessons/YYYY-MM-DD-<slug>.md
│                                        + append CLAUDE.md do projeto (Incident Log)
├── Contexto de pessoa/projeto/stack → CLAUDE.md do projeto
│                                      OU shared/context/<slug>.md (cross-project)
├── TODO / melhoria não-urgente → memory/pending.md (append com prioridade)
├── Task urgente (action required) → WhatsApp Toto → ele escreve pending.md
├── Work log diário (o que fiz) → NADA (session-distill cron faz auto)
├── Referência externa (URL, doc) → shared/references/<tema>.md
│                                    OU CLAUDE.md se for do projeto
└── Configuração / segredo → /root/.openclaw/.env (nunca em código commitado)
```

## O que GRAVAR (critério)

Grava se passa em pelo menos um:

- **Não-óbvio:** conhecimento que exige debug ou investigação pra descobrir (file:line, comportamento surpresa, constraint escondida)
- **Reutilizável:** você ou outro agente vai precisar disso de novo (procedimento de recovery, fix de bug, workaround)
- **Custou:** levou mais de 15 min pra descobrir/decidir
- **Decisão com trade-off:** opção A vs B com razão documentada
- **Ponta de iceberg:** bug que pode ter outras ramificações, padrão que pode se repetir

**Não grava** (é lixo):
- Comando que qualquer `--help` responde
- Restating do que tá na doc oficial
- "O comando X funciona" sem contexto
- Daily work log detalhado (session-distill cuida)
- Decisão trivial sem trade-off
- Summary de conversa sem insight novo

## O que NÃO gravar

❌ **Nunca escreva no Notion Mission Control** a partir de 2026-04-20. Ele é read-only legacy. Se algum prompt/SOUL pediu isso, é bug — reportar.

❌ Não gravar duplicata. Antes de escrever, rodar `nox-mem search "<keyword>"` pra ver se já existe.

❌ Não gravar chave secreta, token, password em arquivo shared/ (fica no repo git). Segredos só em `.env`.

❌ Não gravar summary de sessão na mão — session-distill cron extrai automaticamente domingo 05:00.

## COMO gravar (formato)

### Frontmatter obrigatório

```yaml
---
chunk_type: lesson | decision | context | reference | daily_note
source: internal | external
date: YYYY-MM-DD
tags: [tag1, tag2, tag3]   # lista curta, lowercase-dash
---
```

### Estrutura de lição (padrão)

```markdown
# Título claro do problema/insight

## TL;DR
3 linhas: o que, impacto, fix resumido.

## Contexto
Qual sistema, qual versão, qual ambiente.

## Root cause
Explicar o porquê (não só o o-quê).

## Fix aplicado
Comandos/código exatos. Usar file:line.

## Validação
Como confirmamos que funcionou.

## Lições / regras derivadas
Bullets curtos.

## Referências
Links, issues, file:line.

## Entidades pra KG
Lista de projetos/componentes/pessoas mencionadas — ajuda o kg-build a extrair.
```

### Filename

- Padrão: `YYYY-MM-DD-<slug-kebab-case>.md`
- Slug: 3-5 palavras descritivas. Ex: `2026-04-20-openclaw-gateway-fratricide.md`
- Ordenável cronologicamente + descritivo

### Decisões atômicas (chave-valor)

Pra decisão curta do tipo "usamos X em vez de Y":
```bash
nox-mem decision-set <key> <value>
# ex: nox-mem decision-set embedding-model gemini-embedding-001
# ex: nox-mem decision-set primary-fallback anthropic/claude-sonnet-4-6
```

Pra decisão longa com narrativa/contexto: arquivo em `shared/decisions/`.

## ONDE gravar (tabela completa)

Todos os paths são em `/root/.openclaw/workspace/`.

| Tipo | Path | Ingest automático? |
|---|---|---|
| **Lição aprendida** | `shared/lessons/YYYY-MM-DD-<slug>.md` | ✅ watcher inotify (~15s) |
| **Decisão narrativa** | `shared/decisions/YYYY-MM-DD-<slug>.md` | ✅ watcher |
| **Decisão atômica** | `nox-mem decision-set` (CLI) | ✅ direto no DB |
| **Contexto cross-project** | `shared/context/<slug>.md` | ✅ watcher |
| **Referência externa** | `shared/references/<tema>.md` | ✅ watcher |
| **Policy / protocolo** | `shared/policies/YYYY-MM-DD-<slug>.md` | ✅ watcher |
| **Incident (+ fix)** | `shared/lessons/...` + edit `memoria-nox/CLAUDE.md` Incident Log | ✅ watcher |
| **Contexto de projeto** | `<repo>/CLAUDE.md` no projeto específico | Depende do projeto ingerir |
| **Contexto de pessoa** | `shared/USER-PROFILE.md` (Toto) / `shared/TEAM_MEMORY.md` | ✅ watcher |
| **Pendência / TODO** | `memory/pending.md` (append) | ✅ (usado pelo briefing) |
| **Daily work log** | Auto via session-distill (Dom 05:00) — NÃO escrever manual | ✅ auto |
| **Draft de comment upstream** | `shared/github-comments/<issue>-draft.md` | ✅ watcher |

## QUANDO gravar

### Imediato (na hora que descobre)

- **Incident em andamento:** append em `shared/lessons/` durante o debug. Evita perder detalhes.
- **Decisão tomada:** registrar antes de executar a mudança.
- **Workaround/fix aplicado:** logo depois de validar que funcionou.

### Batch (final da sessão)

- **Lições pequenas acumuladas:** ok agrupar 2-3 em uma lesson se do mesmo tema.
- **Contextos aprendidos:** ao final de um trabalho grande, consolidar.

### Automático (não escrever manual)

- **Daily work log:** session-distill extrai dos JSONL dos agentes (Dom 05:00).
- **Knowledge graph:** kg-build extrai entidades/relações das lições (23:00 nightly).
- **Embeddings:** vectorize roda Sun 04:00 OU sob demanda.

### Nunca espera

Não deixe pra "depois" info crítica. A regra é: **se custou mais de 15min descobrir, registra imediatamente**.

## Fluxo completo (passo-a-passo)

### Cenário: descobri um bug e apliquei fix

```bash
# 1. Create lesson file
cat > /root/.openclaw/workspace/shared/lessons/2026-04-20-<slug>.md <<EOF
---
chunk_type: lesson
date: 2026-04-20
tags: [area, componente, tipo]
---
# Título
## TL;DR
...
EOF

# 2. Watcher auto-ingesta em ~15s. Para forçar:
set -a; source /root/.openclaw/.env; set +a
nox-mem ingest /root/.openclaw/workspace/shared/lessons/2026-04-20-<slug>.md

# 3. Verificar estado real (nunca confiar na última linha do CLI — lição v3.4)
curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage
# Esperar: embedded == total

# 4. Validar que está searchable
nox-mem search "<keyword do bug>"
# Deve aparecer no top N resultados com match_type=semantic
```

### Cenário: decisão atômica (simples)

```bash
nox-mem decision-set retry-backoff-base-ms 1000
nox-mem decision-set embed-batch-size 10
```

## Verificação pós-registro

Sempre confirmar:

1. `curl /api/health | jq .vectorCoverage` — `embedded == total`?
2. `nox-mem search "<termo>"` — aparece o conteúdo novo com `match_type=semantic`?
3. Para decisions: `nox-mem decision-get <key>` — retorna o valor?

Se falhar qualquer um: problema no ingest/vectorize, investigar antes de continuar.

## Regras institucionais derivadas

Estas regras **devem ser seguidas** por todos os agentes:

1. **Notion Mission Control é read-only legacy.** Zero gravação ali a partir de 2026-04-20.
2. **Verificar antes de declarar sucesso.** Se disse "feito", incluir output da verificação (lição v3.4 fake-green).
3. **Sempre `set -a; source /root/.openclaw/.env; set +a` antes de `nox-mem` CLI** via SSH/cron/script.
4. **Duplicata: checar antes de escrever.** `nox-mem search "<keyword principal>"` 30s.
5. **Frontmatter com `chunk_type` correto.** Sem isso, KG extrai mal e search rankear mal.
6. **Filename ordenável** `YYYY-MM-DD-<slug>.md`.
7. **Se custou mais de 15min descobrir, vira lesson.**
8. **Segredos nunca em shared/.** Só em `.env`.

## Para Forge e Nox especificamente

Vocês são os agentes com autoridade de escrita. Daqui pra frente:

- **Ao terminar code review ou fix:** lesson em `shared/lessons/`
- **Ao decidir entre 2+ opções técnicas:** `nox-mem decision-set` (curto) ou `shared/decisions/` (longo)
- **Ao detectar incident:** lesson + edit `memoria-nox/CLAUDE.md` na seção Incident Log
- **Sem** criar/editar nada no Notion Mission Control

## Pra quando precisa buscar depois

```bash
# Busca semântica PT-BR
nox-mem search "como funciona o gateway openclaw"

# Busca em tipo específico
nox-mem search "fratricide" --type lesson

# Hybrid (default) vs só FTS
nox-mem search "issue 62028"              # híbrido
nox-mem search "issue 62028" --no-hybrid  # só FTS5

# Decisions
nox-mem decision-list
nox-mem decision-get embedding-model

# Graph
nox-mem kg-query "openclaw gateway"
nox-mem kg-path "openclaw" "systemd"
```

## Referências

- **Plan principal:** `memoria-nox/plans/2026-04-20-notion-import-e-whatsapp-tasks.md`
- **Policy WhatsApp→pending:** `memoria-nox/CLAUDE.md` seção "Convenções"
- **Lição v3.4 (verificar pós-operação):** `shared/lessons/2026-04-19-boost-stacking-and-fake-green.md`
- **Lição Gateway fratricide:** `shared/lessons/2026-04-20-openclaw-gateway-fratricide-issue-62028.md`

## Revisão desta policy

Cada 3 meses OU após incident que envolva problemas de registro. Próxima revisão: **2026-07-20**.
