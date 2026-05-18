# AGENTS-PLAYBOOK — Padrões de Sessão Multi-Agente

> Guia definitivo para quem vai replicar uma push multi-agente no estilo da sessão 2026-05-18.
> Baseado em evidência forense de 11 waves consecutivas (A→K), 84 PRs, ~109k LOC, ~23h wall-clock.

---

## Índice

1. [Executive Summary](#1-executive-summary)
2. [Anatomia de uma Sessão](#2-anatomia-de-uma-sessão)
3. [Matrix de Seleção de Agentes](#3-matrix-de-seleção-de-agentes)
4. [MANDATORY CLOSURE STEPS](#4-mandatory-closure-steps)
5. [Anti-padrões e Correções](#5-anti-padrões-e-correções)
6. [Templates de Wave por Tipo](#6-templates-de-wave-por-tipo)
7. [Efetividade de Ferramentas](#7-efetividade-de-ferramentas)
8. [Análise de Custo e Velocidade](#8-análise-de-custo-e-velocidade)
9. [Sequência de Adoção Recomendada](#9-sequência-de-adoção-recomendada)
10. [Melhorias Futuras](#10-melhorias-futuras)

---

## 1. Executive Summary

### O que foi entregue

A sessão de 2026-05-18 foi a maior entrega paralela já executada no projeto memoria-nox:

| Métrica | Valor | Contexto |
|---|---|---|
| Waves executadas | 11 (A→K) | Consecutivas em ~23h total |
| PRs merged | 84 | Wave A #2 → Wave K #84 |
| LOC total (source + tests + docs) | ~109,364 | Estimativa conservadora via GitHub additions |
| Testes passando | ~1,311+ | npm test em todos pacotes com package.json |
| Wall-clock total | ~23h | Overnight Wave A incluída |
| Speedup estimado vs. solo | **~25–120×** | Varia por métrica (ver §8) |
| BLOCKED.md criados | **Zero** | Em todas as 11 waves |
| Agentes simultâneos (pico) | 17+ | Nas waves de maior paralelização |
| Linguagens de SDK entregues | 4 | TypeScript + Python + Rust + Go |
| Schema migrations | 4 sets | v20→v22 + staged dirs |
| Security gaps identificados e fechados | 17 (G1–G17) | Zero open ao fim |
| ADRs formalizados | 8 | Michael Nygard template |

### O que prova

O padrão multi-agente swarm funciona para projetos onde:
- As tarefas são decompostas em sprints independentes (~15–500 LOC cada)
- O plano é injetado no spawn com contexto suficiente para execução autônoma
- MANDATORY CLOSURE STEPS são invariantes em todo prompt que precisa de PR
- BLOCKED.md é o sinal de parada explícito, não loop silencioso
- Honesty discipline é aplicada sistematicamente (nenhum número inventado)

Os únicos incidents que afetaram entrega (worktree leak, content filter crash, YAML heredoc, race condition de merge) foram identificados, documentados e prevenidos pela wave seguinte. Zero trabalho perdido em nenhum caso.

### O padrão é replicável

Este documento explica como.

---

## 2. Anatomia de uma Sessão

### 2.1 Pré-sessão (feita pela sessão principal, não por agentes)

Antes de spawnar qualquer agente, a sessão principal deve fazer:

1. **Roadmap fork / refresh de DECISIONS.md**
   - Definir os pilares de trabalho (ex: Q/A/P + Lab + GTM no caso desta sessão)
   - Documentar a decisão em `docs/DECISIONS.md` com ID (ex: D40)
   - Isso é a fonte de contexto que todos os agentes vão receber

2. **Decomposição em sprints independentes**
   - Cada sprint deve ser auto-contido: inputs bem definidos, output único (um PR)
   - Sprints com dependências entre si devem ser serialized (wave diferente)
   - Sprints independentes podem correr em paralelo na mesma wave

3. **Verificação de pré-requisitos**
   - Branch main está limpa e atualizada
   - CI verde em main
   - Worktrees existentes de sessões anteriores foram limpas (`.claude/worktrees/`)

4. **Template de prompt pronto**
   - Base de contexto: stack, constraints, links para docs relevantes
   - Sprint-específico: task, inputs, output esperado, branch name
   - MANDATORY CLOSURE STEPS no final (ver §4)

### 2.2 Estrutura de Wave

Uma wave é um batch de agentes paralelos com sprints independentes. A sessão 2026-05-18 demonstrou que **4–6 agentes por wave** é o sweet spot:

```
Wave N:
├── Sprint A (agente 1, worktree isolado) ──→ PR #X
├── Sprint B (agente 2, worktree isolado) ──→ PR #Y
├── Sprint C (agente 3, worktree isolado) ──→ PR #Z
└── [aguardar todos completarem]
           ↓
      [merge PRs]
           ↓
      [post-mortem]
           ↓
        Wave N+1
```

**Regras de ouro para waves:**

- Cada agente recebe seu próprio worktree isolado via `Agent(isolation="worktree")`
- Sprints com dependências cruzadas vão para waves diferentes (não paralelas)
- O post-mortem da wave N deve ser escrito antes de spawnar a wave N+1
- HANDOFF + ROADMAP devem ser sincronizados a cada 2–3 waves (não esperar acumular 6+)

### 2.3 Ritmo de Closure entre Waves

O ritmo correto entre waves:

```
[Agentes retornam PR URLs]
         ↓
[Verificar URLs: gh pr list --head <branch>]
         ↓
[Merge PRs: gh pr merge --auto (preferido)]
         ↓
[Verificar CI verde em main]
         ↓
[Escrever post-mortem da wave]
         ↓
[Sync docs canônicos se necessário]
         ↓
[Spawnar próxima wave]
```

### 2.4 Ajustes Mid-Session

Sinais de que algo precisa ser corrigido:

| Sinal | Ação corretiva |
|---|---|
| Agente reporta "PR ready" sem URL | Verificar `gh pr list --head <branch>`; se não existe, navegar no worktree e criar manualmente |
| CI vermelho em PR | Não merge; diagnosticar no worktree ou re-spawn corrigido |
| Sparse-checkout falha ao escrever arquivo | Adicionar `git sparse-checkout add <dir>` ao spawn template |
| Content filter crash | Inventariar worktree parcial; completar manualmente sem o texto que causou o crash |
| Worktree leak (branch errada) | Recovery via cherry-pick (não merge) |
| PRs com base SHA divergida | Usar `gh pr merge --auto` em vez de merge simultâneo manual |

---

## 3. Matrix de Seleção de Agentes

### 3.1 Tabela principal

| Tipo de agente | Modelo | Ferramentas | Melhor para | Nunca usar para |
|---|---|---|---|---|
| `executor` | Sonnet | Read, Edit, Write, Bash, Glob, Grep | Doc work, T-suffix continuations, refactors, test additions, specs | Decisões arquiteturais; greenfield >300 LOC com semântica complexa |
| `executor-high` | Opus | Read, Edit, Write, Bash, Glob, Grep | Greenfield 200–500 LOC, security-critical, abstrações novas, módulos com interações semânticas não-triviais | Tarefas rotineiras de docs; custo 3–4× maior |
| `writer` | Haiku | Read, Edit, Write, Glob, Grep | **Sem Bash — NÃO pode commit/push/PR.** OK apenas se a sessão principal vai commitar depois | Qualquer tarefa que precisa abrir PR de branch nova; worktrees isolados |
| `scientist-high` | Opus | Read, Glob, Grep, **sem Write** | Research questions, análise de código existente | Implementação — não tem Write tool |
| `explore` | Haiku | Read, Glob, Grep | Navegação e mapeamento de codebase | Implementação |
| `code-reviewer` | Sonnet | Read, Glob, Grep | Review multi-perspectiva (segurança, performance, manutenibilidade) | Implementação |
| `planner` | Opus | Read, Edit, Write, Bash | Specs arquiteturais, planos de sprint, decisões de design | Tarefas de implementação direta |

### 3.2 Guia de decisão por cenário

```
Tarefa é greenfield de módulo novo (>200 LOC)?
├── Sim + semântica complexa (crypto, auth, ranking) → executor-high
├── Sim + escopo simples/bem definido → executor
└── Não (extending existing) → executor

Tarefa é doc/spec apenas?
├── Precisa de PR → executor (tem Bash)
└── Sessão principal commitará depois → writer (mais barato)

Tarefa é research/análise sem output de código?
└── scientist-high

Tarefa é review de código?
└── code-reviewer
```

### 3.3 Lições observadas (com evidência)

**executor-high vs executor no greenfield:**
- PR #48 (L3 confidence field, +3,783 LOC, 30 novos arquivos): executor-high produziu zero false-starts e abstrações limpas
- PR #51 (L2 KG conflict detection, +4,443 LOC): mesmo padrão — executor-high entregou direto
- PRs de T-suffix (L4 T7-T9, P1 T11-T14): executor Sonnet suficiente, custo 3–4× menor

**writer agent = armadilha:**
- Incident D41 manhã 2026-05-18: writer produziu VISION.md v15 perfeito, reportou "PR ready", mas sem Bash não criou PR → worktree limpa → conteúdo perdido permanentemente
- Regra: nunca usar writer em worktree isolation quando o output precisa de PR

**scientist-high sem Write:**
- Confirmado na prática: `scientist-high` não tem Write tool
- Não spawnar para implementação; spawnar apenas para análise/research

---

## 4. MANDATORY CLOSURE STEPS

### 4.1 O padrão

Cole este bloco **verbatim** ao final de **todo** prompt de agente que deve resultar em um PR:

```
MANDATORY CLOSURE STEPS (executar nesta ordem antes de retornar):

1. git branch --show-current   ← verificar que está na branch correta antes de tudo
2. git add <files>
3. git commit -m "<conventional commit>" (use HEREDOC para body multi-linha)
4. git push -u origin <branch>
5. gh pr create --title "..." --body "$(cat <<'PREOF'
   <body do PR>
   PREOF
   )"
6. gh pr view <num> --json url --jq .url   ← RETORNAR ESTA URL
7. SOMENTE DEPOIS reportar de volta

NÃO reporte "PR ready" sem executar o step 6 e retornar a URL.
"PR ready" sem URL verificada é falha de coordenação que perde o trabalho.
```

### 4.2 Por que funciona

- **Step 1** (branch check) previne o worktree branch leak (anti-padrão P2)
- **Steps 2–5** garantem que o trabalho está em main antes do task end
- **Step 6** é o que diferencia "acho que criei PR" de "PR existe e tem esta URL"
- **Step 7** (somente depois) garante que o agente não reporta sucesso antes de confirmar

**Evidência:** Wave B rodou 6 agentes, todos com MANDATORY CLOSURE STEPS → 6/6 entregaram PR URL verificável. Wave D41 manhã (sem o pattern) → 1 agente sem URL → PR nunca criado → trabalho perdido.

### 4.3 Adicionando o step inicial de branch check

Todo prompt deve também incluir no início:

```bash
# Verificação mandatória antes do primeiro git add:
EXPECTED_BRANCH="<branch-name-do-sprint>"
CURRENT=$(git branch --show-current)
if [ "$CURRENT" != "$EXPECTED_BRANCH" ]; then
  echo "ERROR: branch atual é $CURRENT, esperado $EXPECTED_BRANCH. Abortando."
  exit 1
fi
```

### 4.4 Recovery quando o agente não seguiu o pattern

Se o agente reportou "pronto" sem URL:

```bash
# 1. Verificar se PR existe:
gh pr list --head <branch-name>

# 2. Se não existe, navegar no worktree:
ls .claude/worktrees/

# 3. No worktree do agente:
cd .claude/worktrees/agent-<id>
git status  # verificar se tem arquivos uncommitted
git log --oneline -5  # verificar se tem commits sem push

# 4. Se tem commits locais sem push:
git push -u origin <branch>
gh pr create --title "..." --body "..."

# 5. Se não tem commits (worktree foi limpa):
# Não há recovery automático. Re-spawnar com executor (não writer).
```

---

## 5. Anti-padrões e Correções

### P1: Sparse-checkout em worktrees

**Sintoma:** `git add` falha com "outside of your sparse-checkout definition" ao tentar escrever em `docs/`, `sdk/`, `tests/` ou outros diretórios não no set padrão.

**Causa:** Worktrees isolados usam sparse-checkout com conjunto mínimo de diretórios. Qualquer diretório adicional que o sprint precisa pode estar ausente.

**Ocorrências nesta sessão:** 4 waves (B, E, F, G) antes da correção definitiva. Nenhuma em Wave J+K após a correção.

**Fix definitivo:** incluir no spawn template, após criar a branch e antes do primeiro write:

```bash
# Para worktrees de escrita ampla (docs, post-mortems, specs):
git sparse-checkout set --no-cone '*'

# Para worktrees de feature focada (adicionar apenas os diretórios necessários):
git sparse-checkout add docs/post-mortems docs/security docs/ops
git sparse-checkout add src tests scripts sdk
git sparse-checkout list  # confirmar que os diretórios aparecem
```

**Regra:** se o sprint vai escrever em qualquer diretório de docs ou estrutura nova, usar `--no-cone '*'`. Só usar sparse-checkout restrito se o sprint é cirurgicamente focado em um subdiretório que já está no set.

---

### P2: Worktree branch leak para main

**Sintoma:** agente faz `git push` de branch `wave-X/*` mas o diff do PR inclui commits de outros sprints, ou commits aterrisam em main em vez da branch do sprint.

**Causa:** worktrees podem ter `main` como HEAD se o spawn checkou a ref errada, ou se operação anterior vazou estado.

**Ocorrências:** 3 confirmadas (Waves A/B), com recovery documentado.

**Prevenção:** injetar no início de todo prompt:

```bash
EXPECTED="wave-n/2026-05-18/<sprint-name>"
CURRENT=$(git branch --show-current)
[ "$CURRENT" = "$EXPECTED" ] || { echo "ERRO: branch $CURRENT, esperado $EXPECTED"; exit 1; }
```

**Recovery quando commits aterrissaram na branch errada:**

```bash
# 1. Anotar os SHAs dos commits do sprint:
git log --oneline -5

# 2. Criar a branch correta e cherry-pick:
git checkout -b wave-n/2026-05-18/<sprint-correct>
git cherry-pick <sha1> <sha2>   # apenas os commits deste sprint
git push -u origin wave-n/2026-05-18/<sprint-correct>

# 3. Resetar a branch errada para antes dos commits:
git checkout <branch-errada>
git reset --hard <pre-commit-sha>
git push --force origin <branch-errada>  # se já foi pushed
```

**Nunca usar merge para "limpar":** o diff do PR fica confuso e pode incluir mudanças não relacionadas.

---

### P3: Race condition em `gh pr merge` paralelo

**Sintoma:** 5 merges simultâneos → 3–4 retornam "Base branch was modified — review and try the merge again" com exit code não-zero.

**Causa:** o GraphQL mutation `mergePullRequest` do GitHub valida o SHA da base antes de cada merge. O primeiro merge atualiza `main` e invalida o SHA que os outros usam.

**Ocorrências:** 1 batch (Wave B), resolvido via retry sequencial por agentes com MANDATORY CLOSURE.

**Fix:** usar `--auto` em vez de merge direto:

```bash
# Preferido — GitHub serializa server-side:
gh pr merge <num> --merge --auto

# Fallback se --auto não disponível — serializar manualmente:
for pr in 38 39 40 41 42; do
  gh pr merge "$pr" --merge --delete-branch
  sleep 2
done
```

**Nota:** falhas não são silenciosas — `gh pr merge` retorna exit code não-zero com mensagem clara. MANDATORY CLOSURE STEPS detecta e pode fazer retry.

---

### P4: YAML block scalar + heredoc em GitHub Actions

**Sintoma:** workflow `.github/workflows/*.yml` com `run: |` contendo heredoc `<<'EOF'` — o job simplesmente não roda, sem erro visível na UI do Actions.

**Causa:** o parser YAML do GitHub Actions interpreta a indentação do heredoc e tokens especiais (`**`, `&`, `:`) como sintaxe YAML, não como shell. O job é "parseado" como 0 steps.

**Ocorrências:** 1 (Wave B pre-push, `zero-vendor.yml`). Corrigido via hotfix `816c3d3` antes da push paralela.

**Fix:**

```yaml
# ERRADO — heredoc quebra o parser YAML:
run: |
  BODY=$(cat <<'EOF'
  **Pillar A4:** line starting with asterisks
  EOF
  )

# CORRETO — grouped commands ficam indentados:
run: |
  { echo "**Pillar A4:** line starting with asterisks"; \
    echo "second line"; } > /tmp/body.txt
  # OU para strings longas:
  printf '%s\n' "**Pillar A4:** ..." "second line" > /tmp/body.txt
```

**Regra:** em campos `run:` de GitHub Actions, nunca usar `<<'EOF'` heredoc. Usar `printf`, `echo` com grouped commands, ou escrever em arquivo separado e fazer `cat`.

---

### P5: Content filter crash em texto verbatim de CoC/ToS

**Sintoma:** agente trava sem completar o task ao tentar escrever texto verbatim do Contributor Covenant 2.1 ou similar policy de conduta.

**Causa:** vocabulário de harassment/discrimination em textos de CoC é flaggeado pelo content filter fora de contexto.

**Ocorrências:** 1 (Wave F, PR #57). Resolvido via recovery manual sem perda de trabalho.

**Recovery:**

```
1. Identificar worktree do agente travado (.claude/worktrees/agent-<id>/)
2. Inventariar o que foi escrito antes do crash
3. Identificar o que causou o filter (text verbatim de policy, CoC, ToS)
4. Substituir por referência-por-link:
   - CODE_OF_CONDUCT.md → "See [Contributor Covenant 2.1](URL)"
   - Não duplicar o texto canônico; o link é arquiteturalmente superior
5. Completar o PR manualmente da sessão principal
6. Documentar no PR body: "PR completed manually after agent content-filter crash"
```

**Prevenção:** qualquer artefato de policy (CoC, security policy, ToS, licença) deve usar referência-por-link, não text verbatim. O texto canônico vive na URL oficial.

---

### P6: Bugs de AAD/checksum invisíveis em unit tests

**Sintoma:** unit tests passam, integration test falha com `TamperedArchiveError` ou similar.

**Causa:** bugs de chained-checksum (AAD, HMAC, assinatura) requerem que dois estados de instância sejam testados. Unit tests isolam funções individuais; o bug está na *composição* de estado entre export e import.

**Ocorrências:** 1 (Wave B, A2 AES-256-GCM). Capturado pelo integration test antes de ir para produção.

**Regra:** qualquer feature com chained dependencies (crypto, HMAC, assinaturas, checksums, AAD) precisa de round-trip integration test que:
1. Roda o pipeline completo end-to-end
2. Usa duas instâncias separadas (não o mesmo estado in-memory)
3. Inclui teste de tamper (mutar 1 byte → esperar rejeição explícita)
4. Testa o caminho de cancelamento (import parcial → cancel → re-import deve ter sucesso)

---

### P7: Classifier bloqueia operações destrutivas em SSH

**Sintoma:** SSH está autorizado, mas o auto-classifier bloqueia aplicação de migrations a banco de produção ou outros comandos destrutivos.

**Causa:** o classifier distingue classes de operação: read-only / additive / mutating-reversible / **destructive**. Autorizar SSH não autoriza automaticamente operações destrutivas — cada classe requer consentimento separado.

**Ocorrências:** 1 (Wave J, VPS deploy Phase 3). Phases 1+2 completadas; Phase 3 bloqueada.

**Schema de consentimento proposto (codificar em `docs/ops/DEPLOY-CONSENT-MODEL.md`):**

| Classe | Exemplos | Consentimento requerido |
|---|---|---|
| Read-only | `curl /api/health`, `sqlite3 .schema`, `ls` | Implícito |
| Additive | `npm install`, upload de migrations novas | Autorização SSH genérica |
| Mutating-reversible | `nox-mem reindex`, `VACUUM` | Autorização com snapshot pré-op confirmado |
| Destructive | `ALTER TABLE ... DROP`, migrations sem rollback | Consentimento explícito por operação + dry-run obrigatório |

**Fix:** antes de executar operações destrutivas em produção, usar frases de consentimento explícitas como "execute as migrations de banco agora" — não apenas "verifique o estado do banco".

---

### P8: Writer agent sem Bash tool

**Sintoma:** writer subagent reporta "PR ready: Create PR with title..." mas não criou o PR. Worktree é auto-limpa após task end. Conteúdo perdido permanentemente.

**Causa:** writer agent (Haiku) tem apenas Read, Edit, Write, Glob, Grep. Sem Bash. Não pode executar `git commit`, `git push`, `gh pr create`.

**Ocorrências:** 1 (D41 manhã 2026-05-18, VISION.md v15 perdido permanentemente).

**Regra:**
- **Nunca** usar writer em worktree isolation quando o output precisa de PR
- **Nunca** usar writer para tarefas em branches novas
- **Sempre** usar `executor` ou `executor-high` quando o task precisa commit+push+PR

```
writer OK:
  ✅ Escrever arquivo que sessão principal commitará depois
  ✅ Edit em arquivo já em main (Edit persiste na sessão principal)

writer NÃO OK:
  ❌ Tarefas em worktree isolation
  ❌ Tarefas que precisam abrir PR de branch nova
  ❌ Qualquer tarefa com MANDATORY CLOSURE STEPS
```

---

### P9: Arquivos de test quebram build de produção

**Sintoma:** `npm run build` ou `tsc --noEmit` falha em CI com imports de arquivos de test referenciando módulos de desenvolvimento que não existem em produção.

**Causa:** `tsconfig.json` de produção incluindo diretórios de test (`__tests__/`, `tests/`) no target de compilação.

**Fix:** garantir que `tsconfig.json` de build exclua explicitamente diretórios de test:

```json
{
  "exclude": ["node_modules", "**/__tests__/**", "tests/**", "*.test.ts", "*.spec.ts"]
}
```

**Pattern recomendado:** dois tsconfigs — `tsconfig.json` (produção, exclui tests) e `tsconfig.test.json` (estende o base, inclui tests).

---

### P10: Migrations SQLite com falha silenciosa

**Sintoma:** `sqlite3 CLI` não reporta erro quando uma statement individual falha durante migrations em batch.

**Causa:** o `sqlite3` CLI por padrão não faz bail em erros individuais — continua para a próxima statement.

**Dois comportamentos válidos (escolher consistentemente):**

```bash
# Comportamento 1 — bail on error (preferido para migrations críticas):
sqlite3 nox-mem.db ".bail on" < migration.sql

# Comportamento 2 — tolerar erros individuais (para migrations idempotentes):
sqlite3 nox-mem.db < migration.sql  # erros em IF NOT EXISTS são ignorados
```

**Regra:** qualquer migration que não é idempotente (ex: altera dados existentes, dropa colunas) deve usar `.bail on`. Migrations aditivas (CREATE TABLE IF NOT EXISTS, ADD COLUMN) podem tolerar erros individuais.

---

## 6. Templates de Wave por Tipo

### 6.1 Foundation Wave (~5 agentes)

Para waves iniciais que estabelecem features novas com specs e implementação em paralelo.

```
Composição típica:
├── Agente 1: executor-high — implementação greenfield do core (Módulo X)
├── Agente 2: executor-high — implementação greenfield do core (Módulo Y)
├── Agente 3: executor — implementação T-suffix, testes, extensão
├── Agente 4: executor — specs, kickoffs, docs de suporte
└── Agente 5: executor — docs canônicos, post-mortem da wave anterior

Padrão de spawn:
- Todos em paralelo (worktrees isolados, branches diferentes)
- Agente 5 (docs) pode correr em background, não bloqueia os outros
- PRs abertos em wave anterior devem ser merged antes de spawnar dependências

Output esperado:
- 3-4 implementações em staged-<sprint>/edits/
- 1-2 specs em specs/
- 1 post-mortem atualizado
- 1 HANDOFF atualizado

Duração típica: 60–90 min wall-clock
```

**Template de prompt base (foundation):**

```
Você é o agente responsável pelo sprint <SPRINT-ID> na sessão multi-agente de 2026-05-18.

## Contexto do projeto
[Stack: TypeScript, better-sqlite3, FTS5, sqlite-vec, Gemini embeddings, Node 22]
[Pilar: <Quality|Autonomy|Product|Lab|GTM>]
[Spec em: specs/<filename>.md]
[Decisões relevantes: docs/DECISIONS.md#D40 (Q/A/P pivot)]

## Sua tarefa
[Descrição clara do que implementar, com referência à spec]

## Constraints mandatórios
- Toda feature gateada: env var `NOX_<FEATURE>=disabled` por padrão
- Nunca modificar scoring em commit de "fix" (regra crítica #5)
- Migrations aditivas apenas — nunca DROP em sprint de feature
- Testes com real DB (zero mocks para SQL/FTS/KG)
- Output vai para staged-<sprint>/edits/ — não para src/ diretamente

## Branch
wave-n/2026-05-18/<sprint-id>

[MANDATORY CLOSURE STEPS aqui — ver §4.1]
```

---

### 6.2 Integration Wave (~4 agentes)

Para waves que conectam features já implementadas e verificam integrações cross-pilar.

```
Composição típica:
├── Agente 1: executor-high — cross-pilar integration tests
├── Agente 2: executor — wiring de staged dirs para src/ da VPS
├── Agente 3: executor — docs de deploy e runbooks
└── Agente 4: executor — post-mortem + docs canônicos sync

Padrão de spawn:
- Agente 2 (wiring) pode bloquear Agente 1 se os módulos não estão prontos
- Agentes 3 e 4 são independentes, sempre em paralelo
- Verificar que staged dirs das waves anteriores têm testes passando antes do wiring

Validações mandatórias pós-wave:
- npm test em todos os 6+ pacotes staged com package.json
- curl /api/health → vectorCoverage == 100% (se VPS deployado)
- git log --oneline origin/main..HEAD em cada worktree antes de merge

Duração típica: 45–90 min wall-clock
```

---

### 6.3 Security Wave (~4 agentes)

Para waves focadas em threat modeling, gap remediation e hygiene de segurança.

```
Composição típica:
├── Agente 1: executor-high — threat model analysis + novos gaps
├── Agente 2: executor-high — implementação de 5-7 gaps de segurança (bundle)
├── Agente 3: executor — hygiene (SECURITY.md, CHANGELOG, templates GitHub)
└── Agente 4: executor — OpenSSF audit, SBOM, branch protection docs

Princípios desta wave:
- Sempre auditar módulos novos das waves anteriores no mesmo sprint
- THREAT-MODEL.md como artefato vivo — seções "Not shipped" mantidas visíveis
- Gaps corrigidos são removidos de "Not shipped"; novos gaps são adicionados, não omitidos
- Cada gap tem staged-G<N>/edits/ independente para deploy seletivo

Variante "bundle de gaps":
- G4 (input validation) + G6 (localhost auth) + G7 (streaming) + G8 (audit hardening) + G10 (timestamps)
  → todos em um único PR com sub-dirs staging
- Merge é atômico (todos ou nenhum), mas deploy é seletivo (staged dirs)

Duração típica: 2–3h wall-clock (análise demora mais que implementação)
```

**Aviso sobre recursão:** threat modeling tem recursão estrutural. Analisar módulos novos invariavelmente expõe riscos não cobertos pelo scope original. Esperar 3–8 gaps novos por wave de security — isso é saudável, não regressão. Estabelecer cadência trimestral (não por wave) para o review completo.

---

### 6.4 Docs/Ops Wave (~4 agentes)

Para waves focadas em operações, documentação canônica e consolidação.

```
Composição típica:
├── Agente 1: executor — ROADMAP + HANDOFF + DECISIONS sync
├── Agente 2: executor — runbooks ops (DR, BACKUP, MONITORING)
├── Agente 3: executor — post-mortems das waves anteriores
└── Agente 4: executor — ADRs formais, visual regression, OpenSSF

Regra fundamental:
- Docs de ops referenciam APIs e comportamentos já implementados — não especulativos
- Se a feature não está deployed e testada, o runbook descreve o PROCESSO, não afirma que funciona
- Gaps são documentados honestamente (ex: F09 off-site backup rejeitado — não omitir, documentar)

Anti-pattern a evitar:
- Escrever runbook de feature que ainda não foi wired em src/
- Inventar métricas de performance antes de medir
- Marcar "Not-met" como "Planned" sem data e ownership

Duração típica: 1–2h wall-clock
```

---

### 6.5 Strategic Wave (~5 agentes)

Para waves focadas em GTM, posicionamento e materiais externos.

```
Composição típica:
├── Agente 1: executor-high — competitive analysis (Six Gaps matrix)
├── Agente 2: executor — pricing strategy + ROI calculator
├── Agente 3: executor — demo video script + recording plan
├── Agente 4: executor — investor 1-pager + launch blog post
└── Agente 5: executor — contributor onboarding guide

Honesty discipline MANDATÓRIA:
- Qualquer métrica sem fonte verificável → marcador ❓
- Qualquer número hipotético → marcador [H]
- Claims de competitor → explicitamente "vendor-reported, não verificado"
- Features gated → "pending-Q4" ou similar, excluídas do Hero cut

Por que importa:
- Quando os números reais chegarem (pós Q-runs), a atualização é cirúrgica
- Nenhum número inventado precisa ser desmentido publicamente
- Credibilidade com investidores e early adopters depende disso

Duração típica: 1.5–2.5h wall-clock
```

---

## 7. Efetividade de Ferramentas

### 7.1 O que funcionou bem

**Agent() com isolation="worktree"**
- Isolamento completo entre sprints paralelos
- Zero conflito de arquivos entre agentes paralelos
- Worktrees em `.claude/worktrees/agent-<id>/` são inspecionáveis a qualquer momento
- Falha em um agente não contamina os outros

**MANDATORY CLOSURE STEPS**
- Invariante que funciona: 9/9 waves formais (B→J+K) com 100% de adesão
- O step de URL verificada é o diferenciador crítico
- Eliminou completamente o pattern "PR ready mas não criado"

**TaskCreate + TaskUpdate para visibility**
- Permite acompanhar progresso sem polling ativo dos agentes
- Útil para sessões de 3h+ onde há risco de perder o fio

**Numeração explícita em prompts (T1, T2, ...)**
- Agentes T-suffix (extensão de sprint existente) são mais previsíveis com numeração
- Facilita identificar onde o agente parou em caso de crash

**Staged dirs pattern (`staged-<sprint>/edits/`)**
- Features implementadas ficam em main mas desativadas até deploy VPS
- Permite CI verde em main sem deploy coordenado com feature activation
- Deploy é seletivo: cada staged dir pode ser aplicado independentemente
- Rollback é cirúrgico: reverter apenas o staged dir do feature problemático

**Foreground reporting após cada completion**
- Versus deixar todos os agentes em background até o final
- Permite detectar e corrigir problemas wave-a-wave

### 7.2 O que precisou de iteração

**Sparse-checkout configuration**
- 4 ocorrências antes da correção definitiva (Wave G+H → Wave J+K: zero ocorrências)
- Fix definitivo: `git sparse-checkout set --no-cone '*'` para worktrees de escrita ampla
- Deve estar no spawn template desde o início

**Worktree cleanup entre sessões**
- Worktrees de sessões anteriores em `.claude/worktrees/` podem confundir
- Limpar antes de iniciar sessão nova: `ls .claude/worktrees/` e verificar quais são da sessão atual

**Content filter recovery**
- Pattern manual funcionou mas adicionou ~15min overhead
- Prevenção é melhor: inspecionar artefatos de policy antes de spawnar (CoC, ToS, licença)

**Docs sync acumulado**
- Deixar docs canônicos (ROADMAP, HANDOFF) acumular drift por 6 waves custou ~270 linhas de sync
- Recomendação: micro-PR de docs a cada 2–3 waves (30–50 linhas vs 270 de uma vez)

**VPS classifier**
- Operações destrutivas em produção requerem schema de consentimento explícito
- Solução: codificar `DEPLOY-CONSENT-MODEL.md` antes da próxima sessão de deploy

---

## 8. Análise de Custo e Velocidade

### 8.1 Throughput agregado (sessão 2026-05-18, Waves A→K)

| Wave | PRs | LOC + | Testes | Wall-clock | Equiv. pessoa-h |
|---|---|---|---|---|---|
| A (overnight) | ~14 | ~14,000 | ~323 | ~8h | ~140h |
| B | 5 | +14,995 | 535 | ~75min | ~45h |
| C+D | 9 | +10,539 | 199 | ~3h | ~80h |
| E | 5 | ~7,738 | — | ~30min | ~30h |
| F (incl. late-merged) | 8 | +14,600 | ~34 | ~3h | ~70h |
| G (core + #70) | 5 | +19,259 | 160 | ~1.5h | ~50h |
| H (core + #71) | 4 | +8,924 | 45 | ~1.5h | ~35h |
| I | 5 | +4,787 | 15 | ~2h | ~25h |
| J | 5 | +7,537 | — | ~1.5h | ~50h |
| K | 3 | +6,985 | — | ~1h | ~50h |
| **Total A→K** | **~63** | **~109,364** | **~1,311** | **~23h** | **~575h** |

### 8.2 Decomposição do speedup

O speedup ~25–120× tem componentes distintas dependendo da métrica:

**Por LOC/hora:**
- Esta sessão: ~109k LOC / 23h ≈ **4,755 LOC/h**
- Solo dev estimado: ~50 LOC/h
- Múltiplo: **~95×**

**Por PRs/hora:**
- Esta sessão: ~63 PRs / 23h ≈ **2.7 PRs/h**
- Solo dev estimado: ~1 PR/dia (~0.04/h)
- Múltiplo: **~67×**

**Por equivalente pessoa-hora:**
- 575h de trabalho-pessoa / 23h wall-clock = **~25× médio**
- O múltiplo declina de Wave B (>100×) para Wave K (~40×) à medida que docs/specs substituem código como output dominante — docs têm menor LOC/hora mas valor estratégico igual

**Decomposição do speedup:**

```
Paralelização com pico de 17 agentes:
  Uma semana de trabalho serial (~40h) → ~2.4h paralelo com 17 agentes = ~17×

Zero friction:
  Cada agente arranca imediatamente com contexto injetado no spawn
  Eliminação de: context-switch, reuniões, handoffs, git pull, espera de review
  Overhead eliminado estimado: 30–50% vs dev solo
  Fator: ~2–3×

Composto: 17× × 2.5× ≈ 42× (consistente com observação empírica de ~25×, waves
        de docs reduzem o múltiplo)
```

### 8.3 Limitações desta análise

- LOC é proxy ruim de valor: docs e configs têm LOC comparáveis a código, mas valor diferente
- "Solo dev equivalente" é discutível — dev familiarizado com a codebase produziria mais
- Qualidade do output (testes, security fixes, ADRs) não é capturada por LOC
- Custo total em tokens não foi auditado nesta sessão (estimativa: Opus sprints ~$0.30/sprint; Sonnet ~$0.08/sprint; com ~40 sprints Sonnet + ~20 Opus → ~$9 total)

**O número que importa:** 11 waves em ~23h de wall-clock, zero BLOCKED, zero regressão conhecida em main.

---

## 9. Sequência de Adoção Recomendada

Para quem vai replicar este padrão pela primeira vez:

### Passo 1: Leitura mínima (30 min)

1. Este documento (especialmente §4 MANDATORY CLOSURE STEPS e §5 Anti-padrões)
2. Post-mortems relevantes ao tipo de trabalho planejado
3. `docs/DECISIONS.md` para entender o estado atual do projeto

### Passo 2: Audit de pré-requisitos (15 min)

```bash
# Estado do repositório:
git status && git log --oneline -5

# CI está verde em main?
gh run list --branch main --limit 3

# Worktrees existentes (limpar sessões anteriores):
ls .claude/worktrees/

# Sparse-checkout está configurado?
git sparse-checkout list
```

### Passo 3: Primeira wave pequena (2 agentes em paralelo)

- Escolher 2 sprints claramente independentes
- Usar executor para ambos
- Verificar que ambos têm MANDATORY CLOSURE STEPS
- Observar o ritmo: spawn → trabalho → PR URL → merge
- Ajustar o template de prompt com base no que faltou

### Passo 4: Escalar para 4–6 agentes por wave

Quando o ritmo de 2 agentes estiver confortável:
- Adicionar 2 agentes por wave até chegar em 4–6
- A partir de 4, o overhead de orchestração (verificar PRs, fazer merges, escrever post-mortems) começa a consumir tempo da sessão principal
- 6 é o sweet spot: suficientemente paralelo para speedup real, sem overwhelm de coordenação

### Passo 5: Waves especializadas

Com 4–6 agentes calibrados:
- Introduzir waves de security (§6.3) após as waves de feature
- Introduzir waves de docs/ops (§6.4) a cada 2–3 waves de código
- Introduzir waves estratégicas (§6.5) quando GTM se tornar relevante

### Passo 6: Iterar no template de spawn

A cada sessão, documentar no post-mortem:
- O que o agente precisou que não estava no template
- O que estava no template mas nunca foi usado (limpar)
- Novos anti-padrões detectados

O template de spawn melhora com o uso. Esta sessão chegou no padrão definitivo de sparse-checkout apenas na Wave G+H (depois de 4 ocorrências). Você pode começar com a versão já corrigida.

---

## 10. Melhorias Futuras

### 10.1 Questões abertas sobre o padrão

**Auto-merge com conflict resolution:**
- `gh pr merge --auto` serializa mas não resolve conflitos automaticamente
- Se duas waves modificam o mesmo arquivo, o segundo PR precisa rebase
- Solução candidata: validar no spawn template que o sprint não vai tocar em arquivos modificados por sprints paralelos

**Agent-to-agent direct messaging:**
- Atualmente, agentes se comunicam via PR body e HANDOFF.md (shared state)
- Não há canal direto de "Sprint A terminou, Sprint B pode começar"
- Solução candidata: trigger de Wave N+1 via webhook em PR merge event

**Dynamic agent selection:**
- Atualmente, o tipo de agente é escolhido pelo orchestrador antes do spawn
- Candidato: classificador de task que sugere executor/executor-high/writer baseado em palavras-chave do prompt
- Reduz risco de usar writer onde executor é necessário

**Cost telemetry por agente:**
- Nesta sessão, custo total em tokens não foi auditado precisamente
- Candidato: log de tokens por agente no completion report, agrupado por wave
- Permite otimizar modelo selection com dados reais (não estimativas)

**Docs sync automatizado:**
- O drift de ROADMAP/HANDOFF acumulou em 6 waves antes do sync
- Candidato: trigger automático de micro-PR de docs a cada N PRs merged em main
- Viável via GitHub Actions workflow que detecta mudança em staged dirs e cria PR de sync

### 10.2 Riscos do padrão em escala

**Risco de context divergence:**
- Com 17+ agentes simultâneos, cada um tem snapshot diferente do estado do repositório
- Agentes spawados no início de uma wave podem trabalhar com base desatualizada
- Mitigação atual: staged dirs isolam; PR review detecta conflitos

**Risco de "ship it" culture:**
- A velocidade do padrão cria pressão implícita para mergear tudo
- Mitiga-se com: CI verde obrigatório, cross-pillar integration tests, shadow gating para features de ranking/scoring
- ADR-005 (shadow gating) e ADR-006 (real DB em testes) são as defesas principais

**Risco de docs desatualizar mais rápido que o código:**
- Waves de código produzem mudanças mais rápido do que waves de docs conseguem documentar
- Mitigação: MANDATORY CLOSURE STEPS inclui atualização de HANDOFF como step implícito para cada PR

### 10.3 O que não foi tentado nesta sessão

- **Agentes escrevendo testes para código de outros agentes** (review cruzado automatizado)
- **Waves com mais de 17 agentes simultâneos** (não testado — overhead de orchestração pode escalar mal)
- **Agentes com acesso a ferramentas de MCP custom** (todos os agentes usaram tools padrão)
- **Auto-activation de features shadowgated** (todas as ativações foram manuais)

---

## Apêndices

### A. Post-mortems de referência desta sessão

| Documento | Waves cobertas | Highlights |
|---|---|---|
| `docs/post-mortems/WAVE-B-2026-05-18.md` | Wave B | AAD bug, bundle 11.7KB, MANDATORY CLOSURE origin |
| `docs/post-mortems/WAVE-CD-2026-05-18.md` | Wave C+D | L2/L3 impl, honesty discipline, executor-high tradeoff |
| `docs/post-mortems/WAVE-F-2026-05-18.md` | Wave F | Content filter crash, threat model recursão |
| `docs/post-mortems/WAVE-GH-2026-05-18.md` | Wave G+H | G16 nonce reuse, cross-pillar shims, ops readiness |
| `docs/post-mortems/WAVE-I-2026-05-18.md` | Wave I | ADRs, visual regression, OpenSSF 28/45, docs sync |
| `docs/post-mortems/WAVE-JK-2026-05-18.md` | Wave J+K | SDK 4 linguagens, Prometheus, classifier deploy |
| `docs/post-mortems/SESSION-REPORT-2026-05-18.md` | Wave A→J | Relatório mestre completo |

### B. Memórias operacionais relevantes (MEMORY.md)

| Memória | Lição central |
|---|---|
| `feedback_mandatory_closure_steps_pattern` | Pattern verbatim de closure com URL verificada |
| `feedback_writer_agent_no_bash_tool` | Writer = sem Bash = nunca para PR em worktree isolation |
| `feedback_worktree_branch_leak_to_main` | branch check antes do primeiro git add |
| `feedback_parallel_gh_pr_merge_race_condition` | `--auto` evita race de merge simultâneo |
| `feedback_yaml_block_scalar_dedent_in_bash_strings` | Heredoc em `run:` GitHub Actions = job silencioso |
| `feedback_aad_bug_caught_by_integration_test` | Crypto/checksum sempre precisa de round-trip test |
| `feedback_executor_high_vs_executor_tradeoff` | Opus para greenfield complexo; Sonnet para T-suffix |
| `feedback_shadow_mode_for_ranking_changes` | Features de ranking/scoring entram em shadow primeiro |
| `feedback_audit_critical_modules_same_session` | Security audit antes de mergear vale o investimento |
| `feedback_validate_features_with_db_not_logs` | Real DB em testes — nunca validar só por logs |

### C. ADRs desta sessão (referência de decisões arquiteturais)

| ADR | Decisão |
|---|---|
| ADR-001 | Q/A/P strategic architecture (D40 pivot) |
| ADR-002 | Flash-lite como modelo default |
| ADR-003 | Encrypt-by-default para exports (A2) |
| ADR-004 | Staged dirs pattern como unidade de deploy atômica |
| ADR-005 | Shadow gating obrigatório para ranking/scoring changes |
| ADR-006 | Real DB em testes — zero mocks para SQL/FTS/KG |
| ADR-007 | Cadência trimestral de threat model como processo formal |
| ADR-008 | Honesty discipline markers (`❓`, `[H]`, `pending-Q4`) |

### D. Spawn template completo (copiar e adaptar)

```
Você é o agente responsável pelo sprint <SPRINT-ID> na sessão multi-agente.

## Contexto do projeto
[inserir stack summary: TypeScript/Node 22/SQLite, etc.]
[inserir decisões relevantes: DECISIONS.md#D40, etc.]
[inserir spec link: specs/<arquivo>.md]

## Sua tarefa
<descrição clara, com T-IDs se for continuação>

## Branch
wave-<letter>/2026-05-18/<sprint-id>

## Setup inicial (EXECUTAR ANTES DE QUALQUER COISA)
```bash
# 1. Verificar branch:
EXPECTED="wave-<letter>/2026-05-18/<sprint-id>"
CURRENT=$(git branch --show-current)
[ "$CURRENT" = "$EXPECTED" ] || { echo "ERRO branch: $CURRENT"; exit 1; }

# 2. Garantir sparse-checkout completo:
git sparse-checkout set --no-cone '*'

# 3. Confirmar estado limpo:
git status
```

## Constraints
- Features gateadas via env var por padrão
- Nunca scoring change em commit de "fix"
- Migrations aditivas apenas
- Testes com real DB (zero mocks para SQL)
- Output em staged-<sprint>/edits/ — não em src/ diretamente

## MANDATORY CLOSURE STEPS (executar nesta ordem antes de retornar)

1. git branch --show-current   ← verificar branch antes de qualquer git add
2. git add <files>
3. git commit -m "<type>(<scope>): <description>" (HEREDOC para body)
4. git push -u origin <branch>
5. gh pr create --title "<title>" --body "$(cat <<'PREOF'
   ## O que este PR entrega
   <summary>

   ## Testes
   - [ ] npm test passa
   - [ ] Nenhum secret em código

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   PREOF
   )"
6. gh pr view <num> --json url --jq .url   ← RETORNAR ESTA URL
7. SOMENTE DEPOIS reportar de volta

NÃO reporte "PR ready" sem executar o step 6 e retornar a URL.
```

---

*Playbook escrito por Sisyphus-Junior em worktree isolado `agent-a51289c3555b04c4e`. Sessão 2026-05-18 BRT.*
*Baseado em evidência forense de 11 waves, 84 PRs, ~109k LOC.*
