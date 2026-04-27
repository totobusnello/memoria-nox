# Guia de Contribuição — memoria-nox

> Última atualização: 2026-04-26

Este repo é ao mesmo tempo documentation hub, ops toolbox e research record do projeto `nox-mem` (sistema de memória multi-agent em produção na VPS) e do produto comercial **NOX-Supermem**.

---

## 1. Quem pode contribuir

| Perfil | Status |
|---|---|
| Maintainer (Toto) | Ativo — acesso direto à main |
| AI assistants (Claude Code) | Ativo — via terminal/Cursor, seguindo `CLAUDE.md` |
| Contribuidores externos via PR | Futuro — após NOX-Supermem launch |

Hoje a main branch recebe commits diretos do maintainer e de AI assistants. O processo de PR descrito na seção 7 está documentado para uso futuro.

---

## 2. Setup local

### Clone

```bash
git clone https://github.com/totobusnello/memoria-nox.git
cd memoria-nox
```

### Acesso à VPS (produção)

```bash
ssh root@100.87.8.44          # via Tailscale (preferencial)
ssh root@187.77.234.79        # via IP público (fallback)
```

nox-mem roda em `/root/.openclaw/workspace/tools/nox-mem/` na VPS.

### Stack para rodar nox-mem localmente

Requisitos:

- Node.js v22.12+ (preferencialmente v22.22.x)
- `npm install` no diretório do nox-mem (instala better-sqlite3, sqlite-vec, etc.)
- Variáveis de ambiente em `.env` (ver `.env.example`):

```bash
set -a; source .env; set +a   # obrigatório antes de qualquer comando nox-mem
```

Sem isso, `vectorize` e `kg-extract` falham silenciosamente com `Done: 0 embedded, N errors`.

### Rodar testes

```bash
node --test dist/__tests__/*.test.js
```

Cobertura alvo: 80%+. Cada novo comportamento precisa de ao menos um teste.

### Audit de melhorias

```bash
improvements check
```

Rodar antes de abrir PR ou fechar sessão de trabalho.

### Checkpoint antes de mudanças destrutivas

Antes de qualquer operação que toque o DB em produção (`reindex`, `consolidate`, `compact`, `crystallize`, `kg-prune`):

```bash
# ou usar o wrapper withOpAudit() que cria snapshot automático
nox-mem reindex --dry-run     # preview JSON sem mutar
```

Ver regra 15 em `CLAUDE.md` e referência em `audits/2026-04-25-A1-A2-review.md`.

---

## 3. Convenções de commit

### Formato

```
<tipo>(<área>): descrição curta em imperativo

Corpo opcional: detalhes técnicos, motivação, contexto.

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Tipos válidos

| Prefixo | Uso |
|---|---|
| `feat(área):` | Nova funcionalidade |
| `fix(área):` | Correção de bug |
| `fix(safety):` | Correção com implicação de segurança |
| `docs(área):` | Documentação pura |
| `docs+ops(área):` | Doc + mudança operacional acoplada |
| `test(área):` | Testes novos ou ajustes |
| `tune(search):` | Ajuste de ranking/scoring (nunca esconder em fix) |
| `chore(área):` | Manutenção sem impacto funcional |
| `refactor(área):` | Refactor sem mudança de comportamento externo |

Exemplos reais do histórico do repo:

```
feat(search): hybrid RRF fusion BM25 + semantic
fix(safety): withOpAudit snapshot antes de reindex
docs(plans): v1.6 Section 9 redesign — timeline ASCII + cross-refs
docs+ops(B3): closeDb lifecycle fix + zombie rows cleanup
test(safety): 14 casos node:test pra parseRetentionOverride
```

### Proibido

- `git add -A` — pode incluir secrets ou arquivos de build não intencionais
- `git push --force` na branch main
- `git commit --no-verify` — o hook gitleaks é obrigatório
- `git commit --amend` depois de push

---

## 4. Estrutura de docs — onde adicionar o quê

| O que você quer registrar | Arquivo alvo | Política |
|---|---|---|
| Estado vivo + próxima ação | `docs/HANDOFF.md` | Atualizar in-place |
| Roadmap e sequência de fases | `docs/ROADMAP.md` | Tabela mestre, 1 fonte de verdade |
| Decisões arquiteturais + NÃO FAZEMOS | `docs/DECISIONS.md` | Append-only — nunca editar entradas antigas |
| System design e arquitetura | `docs/ARCHITECTURE.md` | Manter atual |
| Visão estratégica longo prazo | `docs/VISION.md` (antigo `nox-neural-memory.md`) | Versionar (v14, v15...) |
| Regras críticas para AI assistants | `CLAUDE.md` | Manter regras 1-15 sempre inline |
| Incidents e post-mortems | `docs/INCIDENTS.md` + memory feedback file | Append-only |
| Runbooks operacionais | `docs/RUNBOOKS.md` | Atualizar in-place |
| Audits de infra e segurança | `audits/<data>-<tema>.md` | Um arquivo por audit |
| Specs técnicas | `specs/<feature>.md` | Um arquivo por spec |
| Scripts de ops | `scripts/` | Scripts permanentes; nunca em `/tmp/` |
| Paper acadêmico | `paper/` | Versionar junto com `.docx` |

---

## 5. Standards de código (TypeScript)

- **Strict mode** em todos os módulos (`"strict": true` no tsconfig)
- **Sem `any`** exceto com comentário justificado (`// eslint-disable-next-line @typescript-eslint/no-explicit-any — reason`)
- **Testes com `node:test`** built-in — sem dependências externas de test runner
- **Cobertura alvo: 80%+** para cada novo comportamento
- **Entry point do CLI é `dist/index.js`** (não `cli.js` — confusão comum; ver `package.json.bin`)
- ESLint + Prettier: TODO — configurar quando primeiro contribuidor externo entrar

### Padrão para novos módulos

```typescript
// src/lib/meu-modulo.ts
import { getDb } from "./db.js";

export async function minhaFuncao(param: string): Promise<Result> {
  const db = getDb();
  // nunca closeDb() aqui — lifecycle pertence ao caller (CLI/daemon)
  // ...
}
```

`closeDb()` no meio de função wrapper invalida `withOpAudit()` — lição do bug B2 de 2026-04-26.

---

## 6. Standards de documentação (Markdown)

- **Idioma:** Português Brasil em toda a prosa. "você" — nunca "tu/te/ti/teu/tua"
- **Code blocks** com linguagem explícita: ` ```bash`, ` ```typescript`, ` ```sql`, ` ```json`
- **Tabelas** para dados estruturados (comparações, mapeamentos, campos)
- **Diagramas ASCII** quando ajuda entender fluxo — preferível a Mermaid para arquivos que abrem no terminal
- **Links relativos** entre docs: `[Decisions](DECISIONS.md)`, não URLs absolutas do GitHub
- **Header de data** em arquivos vivos: `> Última atualização: YYYY-MM-DD`
- **DECISIONS.md é append-only**: nunca editar entradas antigas; adicionar nova entrada com contexto de revisão se necessário

### Exemplo de tabela bem-formatada

```markdown
| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `retention_days` | INTEGER | NULL | NULL = never-decay |
| `pain` | REAL | 0.2 | Severidade 0.1–1.0 |
```

---

## 7. Pull request process (futuro)

### Branch

```bash
git checkout -b feat/minha-feature    # nova funcionalidade
git checkout -b fix/nome-do-bug       # correção
```

1 PR = 1 concern. Não bundlar doc + feature + fix no mesmo PR.

### Descrição obrigatória

```
**TL;DR:** uma linha do que muda

**Motivação:** por que isso é necessário

**Como testar:** comandos exatos para validar

**Breaking changes:** sim/não — se sim, o quê muda
```

### Checklist de review

- [ ] `improvements check` passa sem warnings críticos
- [ ] `node --test dist/__tests__/*.test.js` passa
- [ ] Schema migration é aditiva (ver seção 8)
- [ ] Se ranking/scoring change: shadow-mode 7d antes de ativar (ver `CLAUDE.md` regra 8)
- [ ] Regras 1-15 do `CLAUDE.md` não violadas
- [ ] `docs/DECISIONS.md` atualizado se houver decisão arquitetural nova

---

## 8. Schema migrations

### Regras

- **SEMPRE aditivas:** `ALTER TABLE ADD COLUMN` + backfill
- **NUNCA** `DROP COLUMN`, `DROP TABLE`, ou `ALTER COLUMN type` sem ADR aprovado em `docs/DECISIONS.md`
- **`withOpAudit()` snapshot obrigatório** antes de qualquer migration em produção
- **Testar em cópia local** do DB antes de aplicar na VPS

### Exemplo correto

```sql
-- aditivo: safe
ALTER TABLE chunks ADD COLUMN pain REAL DEFAULT 0.2;
UPDATE chunks SET pain = 0.2 WHERE pain IS NULL;

-- NÃO fazer sem ADR
ALTER TABLE chunks DROP COLUMN campo_antigo;
```

### Validação pós-migration

```bash
curl http://127.0.0.1:18802/api/health | jq .sectionDistribution
# confirmar que compiled == 183 (ou o valor esperado)
```

---

## 9. Segurança

- **Secrets exclusivamente em `.env`** com permissão `0600` — nunca em JSON, YAML ou código
- **Configs usam `${VAR_NAME}`** — nunca valor literal em `apiKey` de providers
- **Gitleaks pre-commit** está ativo e é obrigatório — nunca bypassar com `--no-verify`
- **Nunca commitar** `*.credentials.json`, `*.bak` com dados sensíveis, ou conteúdo de `_archive/` que contenha secrets
- **`.gitignore` enforcement** — verificar antes de `git add` arquivos novos em diretórios de config

Rotação de keys: editar `.env` + `systemctl restart openclaw-gateway nox-mem-api nox-mem-watcher`. Detalhes em [CONVENTIONS.md](CONVENTIONS.md).

Para reportar vulnerabilidades: `lab@nuvini.com.br` (futuro: `SECURITY.md` dedicado).

---

## 10. AI assistants (Claude) trabalhando neste repo

Se você é um AI assistant lendo este arquivo:

1. **Leia `CLAUDE.md` completamente** antes de qualquer operação — as regras 1-15 têm implicações diretas em produção
2. **Checkpoint antes de mudança destrutiva** — `withOpAudit()` ou `--dry-run` em toda op que toca chunks
3. **Valide com estado real do DB**, não com logs ou output do CLI:
   ```bash
   curl http://127.0.0.1:18802/api/health | jq .vectorCoverage
   ```
4. **"você" não "tu"** em todo texto PT-BR que você escrever neste repo
5. **Não bumpe versão** (ex: v1.6 → v1.7) sem POC funcional + 7 dias de shadow-mode validados
6. **Não edite `openclaw.json` com `jq` + `mv`** — use `openclaw config set <path> <val>` (o gateway tem estado in-memory que sobrescreve edits manuais no restart)
7. **`set -a; source /root/.openclaw/.env; set +a`** antes de qualquer `nox-mem` CLI via SSH/cron

---

## 11. Comunicação

| Canal | Uso |
|---|---|
| GitHub Issues | Propostas, bugs, discussões (futuro — após launch) |
| Discord `forge-dev` | Alertas operacionais, code review async |
| Discord `boris-social` | Curadoria de conteúdo pelo agente Boris |
| WhatsApp | Urgências operacionais para o maintainer |
| `lab@nuvini.com.br` | Security disclosures (futuro) |

---

## 12. Licença e conduta

**Licença:** MIT — compatível com contribuições da comunidade quando o repo se tornar público.

**Conduta:** técnico, respeitoso, sem ataques pessoais. Discordâncias são sobre código e decisões, não sobre pessoas. Feedback direto é bem-vindo — brutalidade desnecessária não.
