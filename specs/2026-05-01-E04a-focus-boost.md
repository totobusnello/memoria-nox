# E04a — Session Focus Topic Boost

> Comando `nox-mem focus set <topic>` define um foco de sessão; search aplica 1.4× a chunks que tocam topic + 0.75× a chunks que NÃO tocam. Multiplicador aditivo ao section_boost atual, não stacking destrutivo.

**Status:** Design spec (CANDIDATE)
**Data:** 2026-05-01
**ID novo:** E04a (parte do split E04a/E04b — ver `docs/ROADMAP.md §4`)
**ID antigo:** A7 (Section 9 v1.6) / Q2 (ClawMem analysis)
**Vision §:** ClawMem Q2 (cross-ref)
**Esforço estimado:** 1.5h implement + 7d shadow wall + 0.3h activate (E04b)
**Dependências:** ≥G03 ✅, search() pipeline atual estável (✅ pós section_boost active 05-01)
**Bloqueia:** E04b activate após 7d shadow + delta recall ≥3% OU subjective improvement
**Cross-ref:** `docs/ROADMAP.md` (E04a/b row), `plans/_archive/2026-04-26-clawmem-analysis.md` §5 Q2, `MEMORY.md:feedback_shadow_mode_for_ranking_changes.md`

---

## Problema

Quando Toto trabalha numa frente específica (ex: "schema v11 edge typing"), search atual não distingue queries dessa frente vs queries gerais. Chunks irrelevantes (ex: docs sobre Granix-App enquanto investigando nox-mem) competem por slots no top-K.

Hoje:
```
$ nox-mem search "kg relations" --hybrid
 #1: Granix-App/docs/relations.md (FTS hit "relations")
 #2: nox-mem/specs/edge-typing.md (semantic hit "kg")
 #3: random old project mentioning "relation"
 #4: docs/DECISIONS.md (kg_relations decision)
```

Toto está focado em **nox-mem schema v11** — quer que `nox-mem` chunks subam, off-topic baixe.

**Não é re-rank cross-encoder** (D01 deferred). É um **bias contextual leve** controlado pelo usuário, baseado em palavra-chave/topic explícito.

---

## Solução: Focus boost aditivo

### Conceito

```bash
$ nox-mem focus set "schema v11 edge typing"
focus set: topic="schema v11 edge typing", session=abc123, expires=2026-05-08

$ nox-mem search "kg relations" --hybrid
 #1: nox-mem/specs/edge-typing.md       (boost 1.4× = on-topic)
 #2: docs/DECISIONS.md (kg_relations)    (boost 1.4× = on-topic)
 #3: Granix-App/docs/relations.md        (demote 0.75× = off-topic)
 #4: nox-mem/lib/op-audit.ts             (boost 1.0× = neutral, nox-mem mas não bate topic)

$ nox-mem focus clear
focus cleared (was: "schema v11 edge typing")
```

### Match logic

Chunk match = `topic_terms ∩ chunk_text ≠ ∅` (case-insensitive substring de qualquer term do topic).

```typescript
function matchesFocus(chunk: Chunk, focus: FocusState): 'on' | 'off' | 'neutral' {
  if (!focus || focus.expired) return 'neutral';
  const text = chunk.chunk_text.toLowerCase();
  const terms = focus.topic.toLowerCase().split(/\s+/).filter(t => t.length >= 3);
  const hits = terms.filter(t => text.includes(t)).length;

  if (hits >= Math.ceil(terms.length / 2)) return 'on';   // ≥50% terms match
  if (hits === 0) return 'off';                            // zero terms
  return 'neutral';                                         // partial match (1 term em N)
}
```

**v1 simples:** substring case-insensitive. **v2 (E04b+):** stemming PT-BR + bigram match.

### Boost factors

```typescript
const FOCUS_BOOST = {
  on:      1.40,  // chunks com ≥50% terms do topic → up
  neutral: 1.00,  // partial match → neutral
  off:     0.75,  // zero terms → demote
};
```

### Aditividade (não stacking)

Já temos:
- `section_boost` (compiled 2.0× / frontmatter 1.5× / timeline 0.8×) — ATIVO desde 2026-05-01
- `salience` formula (recency × pain × importance) — ACTIVE desde 2026-04-30
- `tier_boost` (TIER_BOOST mapping)

**Regra crítica** (CLAUDE.md §5, lição v3.4): boost multiplicativo empilhável é veneno. Solução:

```typescript
// Em search() — após RRF mas antes do sort final:
const finalScore = baseScore * sectionBoost;       // existente
const focusFactor = FOCUS_BOOST[matchesFocus(chunk, focus)];
const adjustedScore = finalScore + (finalScore * (focusFactor - 1.0));  // ADITIVO
```

Equivale a: `adjustedScore = finalScore * focusFactor` matematicamente, MAS expressa como adição do delta. Telemetria registra `delta = (focusFactor - 1.0) × finalScore` separadamente do score base — fácil revogar/auditar.

### Persistência (cache file)

Focus state vive em arquivo curto, não em DB. **NÃO usar `/tmp`** (world-readable, session hijacking trivial via `hostname+ppid` enumeration).

```
${OPENCLAW_WORKSPACE}/tools/nox-mem/focus/<sha256(session_id)>.json
{
  "topic": "schema v11 edge typing",
  "set_at": "2026-05-01T20:35:00-03:00",
  "expires_at": "2026-05-08T20:35:00-03:00",
  "session_id": "<derived hash, never raw>"
}
```

**Permissões:** dir `0700`, file `0600`. ACL hardening obrigatório.
**TTL: 7 dias.** Após expiração, `focus get` retorna nada e search vira neutro.
**Session ID:** `sha256(hostname + ppid + uid + NOX_FOCUS_SESSION_SALT)`. Override via env `NOX_FOCUS_SESSION` permite shared session entre CLI + API quando intencional (workflow Toto roda ambos simultâneos com ppids diferentes).

### Validação (zod schema)

Antes de aplicar focus, validar shape + invariantes:

```typescript
import { z } from 'zod';

const FocusStateSchema = z.object({
  topic: z.string().min(1).max(200).regex(/^[\w\s\-.:]+$/),
  set_at: z.string().datetime({ offset: true }),
  expires_at: z.string().datetime({ offset: true }),
  session_id: z.string().length(64), // sha256 hex
}).refine(
  (s) => new Date(s.expires_at) <= new Date(s.set_at).getTime() + 7 * 86400_000,
  { message: 'expires_at > 7 days from set_at — possible tamper' }
).refine(
  (s) => new Date(s.set_at).getTime() <= Date.now(),
  { message: 'set_at in future — possible tamper' }
);
```

### Fail-open

Se cache file corrupto / unreadable / disk full / **validation fail** → search ignora focus, comporta como neutral. Tamper attempt → log warning + audit trail. Zero crash, zero degradação.

```typescript
function loadFocus(): FocusState | null {
  try {
    const dir = path.join(process.env.OPENCLAW_WORKSPACE || '/root/.openclaw/workspace', 'tools/nox-mem/focus');
    const file = path.join(dir, `${sha256(getSessionId())}.json`);
    if (!existsSync(file)) return null;
    const stat = statSync(file);
    if ((stat.mode & 0o077) !== 0) {
      console.error(`[focus] insecure perms ${stat.mode.toString(8)} on ${file} — ignoring`);
      return null;
    }
    const raw = JSON.parse(readFileSync(file, 'utf8'));
    const validated = FocusStateSchema.parse(raw); // throws on invalid
    if (Date.now() > new Date(validated.expires_at).getTime()) return null;
    return validated;
  } catch (e) {
    // fail-open: log warning (incl. zod ValidationError), return null
    console.error(`[focus] failed to load (tamper or corruption?): ${e.message}`);
    return null;
  }
}
```

---

## Implementação

### Arquivos novos

| Arquivo | LOC | Descrição |
|---|---|---|
| `src/lib/focus.ts` | ~100 | load/save/match/expire focus state |
| `src/cli/focus.ts` | ~50 | subcommands `focus set <topic>` / `focus clear` / `focus get` |
| `src/__tests__/focus.test.ts` | ~80 | unit tests (10 cenários) |

### Arquivos modificados

| Arquivo | Mudança |
|---|---|
| `src/search.ts` | Apply `applyFocusBoost()` no pipeline pós-RRF, antes do sort final |
| `src/cli/index.ts` | Register `focus` subcommand router |
| `src/api.ts` | (opcional) `/api/focus` GET/PUT/DELETE pra debug |

### Env vars

```bash
NOX_FOCUS_MODE=shadow            # shadow (compute+log) | active (apply) | off
NOX_FOCUS_LOG=1                  # log [focus-shadow] events
NOX_FOCUS_TTL_DAYS=7             # default expiration
```

**Default v1:** `shadow` (per regra `feedback_shadow_mode_for_ranking_changes.md`).

### Schema mudanças

**Nenhuma.** Cache file em `${OPENCLAW_WORKSPACE}/tools/nox-mem/focus/` (mode 0700/0600), telemetria via journalctl.

---

## CLI UX

```bash
# Set focus
$ nox-mem focus set "schema v11 edge typing"
focus set: topic="schema v11 edge typing"
session: abc123 | expires: 2026-05-08T20:35:00-03:00 | mode: shadow

# Get current focus
$ nox-mem focus get
topic: "schema v11 edge typing"
session: abc123 | set 2h ago | expires in 6d 22h | mode: shadow

# Search (shadow mode logs delta but doesn't apply)
$ nox-mem search "kg relations" --hybrid
[focus-shadow] topic="schema v11 edge typing" matches: on=2 neutral=1 off=2 delta=+0.42
 #1: ...
 #2: ...

# Clear focus
$ nox-mem focus clear
focus cleared (was: "schema v11 edge typing", lasted 2h 14m)
```

---

## Critério de ativação E04b (7d shadow)

### Métrica primary (objetiva)
- **Delta recall ≥3% positivo** em search_telemetry comparando shadow score vs final score em queries com focus ativo
- Computed via novo script `analyze-focus-shadow.sh 7`:
  ```
  on_topic_chunks_promoted_to_top10 / on_topic_chunks_in_corpus
  vs same metric sem focus
  ```

### Métrica secondary (subjective, fallback se objective inconclusive)
- Toto reporta utility ≥7/10 em pelo menos 5 sessões com focus ativo
- "Sinto que ranking cobre o tópico melhor"

### Kill switches
- Delta recall ≥3% **negativo** (focus piora ranking) → desativar imediato
- Latência search p95 +>30ms vs baseline → bug em focus pipeline
- Toto reporta "ruído" / "atrapalhou" em ≥2 sessões → mode=off
- Cache file corruption ≥3 vezes/semana → repensar persistência (mover pra SQLite)

---

## Riscos + mitigação

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Topic muito genérico ("nox") match em tudo → ranking constante 1.4× = ruído | Alta | Regra: topic ≥2 terms, cada term ≥3 chars; warn no `focus set` se 1 term |
| Multi-term match heuristic 50% threshold inadequado | Média | v1 testar empiricamente; v2 ajusta para 33% se feedback "muito restrito" |
| Boost stacking destrutivo com section_boost ativo | Baixa (regra aditiva já enforces) | Telemetria registra ambos boosts separadamente; sanity check `final/base ≤ 3.0` |
| Cache file colide entre processes paralelos (CLI + API simultâneos com ppids diferentes) | **Média** | Session ID = `sha256(hostname+ppid+uid+SALT)`; override `NOX_FOCUS_SESSION` env pra forçar shared session quando intencional; lockfile opcional v2 |
| Session hijacking — atacante grava JSON malicioso prevendo `hostname+ppid` em world-readable `/tmp` | **Mitigada (security review H1 04-30)** | Cache movido pra `${OPENCLAW_WORKSPACE}/tools/nox-mem/focus/<sha256>.json` mode 0600, dir 0700; zod schema validation antes de aplicar; mtime/expires_at sanity check |
| Tamper attempt detectado (perms inseguras / shape inválido / set_at no futuro) | Baixa | Log `[focus] insecure perms` ou zod ValidationError, fail-open + audit trail |
| TTL 7d arbitrário (Toto esquece focus, ranking enviesa) | Média | `focus get` mostra TTL remaining; cron canary alerta se focus >5d active sem update |
| Fail-open mascara bug real (focus nunca aplica) | Baixa | shadow log SEMPRE roda (mesmo se load falha) com tag `[focus-fail-open]` |

---

## Plano de execução (1.5h)

### Phase 1 — Implementação (45min)
- [ ] Criar `src/lib/focus.ts` com 6 funções (load, save, match, expire, applyBoost, **getSessionId**)
- [ ] Criar `src/cli/focus.ts` com subcommands set/get/clear
- [ ] Modificar `src/search.ts` aplicando focus pós-RRF
- [ ] Adicionar 4 env vars no `.env.example`: `NOX_FOCUS_MODE`, `NOX_FOCUS_BOOST_ON`, `NOX_FOCUS_BOOST_OFF`, **`NOX_FOCUS_SESSION_SALT`** (random hex, gerado uma vez por instalação) + opcional `NOX_FOCUS_SESSION` (override)
- [ ] Register CLI subcommand em `src/cli/index.ts`
- [ ] Garantir dir creation com mode 0700: `mkdirSync(dir, { recursive: true, mode: 0o700 })`
- [ ] `writeFileSync(file, data, { mode: 0o600 })` em todo save

### Phase 2 — Testes (30min)
- [ ] `src/__tests__/focus.test.ts` cobrindo:
  - set + get round-trip
  - clear remove file
  - expire after TTL
  - match: on/neutral/off cases
  - fail-open: corrupted file, missing dir, JSON parse error, **zod ValidationError, insecure perms (mode 0644), set_at no futuro, expires_at >7d set_at**
  - **session_id derivation:** sha256 deterministic (mesmo hostname+ppid+uid+SALT = mesmo hash); diferente SALT = hash diferente; `NOX_FOCUS_SESSION` override força hash custom
  - boost aditivo (não multiplicativo stacking)
  - shadow vs active vs off modes
  - session_id derivation deterministic

### Phase 3 — Deploy + monitor (15min)
- [ ] Build TS → dist/
- [ ] rsync para VPS
- [ ] Adicionar `NOX_FOCUS_MODE=shadow` + `NOX_FOCUS_LOG=1` ao `/root/.openclaw/.env`
- [ ] `systemctl restart nox-mem-api`
- [ ] Smoke: `nox-mem focus set "test"` → `nox-mem search "x"` → tail journalctl `[focus-shadow]`
- [ ] Criar script `/root/.openclaw/scripts/analyze-focus-shadow.sh` (template do `analyze-shadow-telemetry.sh`)

---

## Telemetria shadow (7d)

```
[focus-shadow] topic="..." matches: on=N neutral=M off=K delta=+X.XX
```

Script `analyze-focus-shadow.sh 7`:
- Total search events com focus ativo
- Distribuição on/neutral/off
- Mean delta por categoria
- Top-10 topics mais usados
- p95 latência adicional pipeline
- Output JSON pra `/var/log/nox-focus-shadow-daily.log`

---

## Out-of-scope (v1)

- ❌ Stemming PT-BR (nltk/spacy heavy) — v2 se match heuristic mostrar holes
- ❌ Bigram matching ("schema v11" como uma unidade) — v2
- ❌ Per-agent focus (focus diferente Atlas vs Boris) — futuro multi-tenancy P01
- ❌ Auto-focus inferido de query history — over-engineering pra v1
- ❌ Focus em DB (não cache file) — só se cache file falhar repetidamente

---

## Cross-reference

| Item | Onde |
|---|---|
| Decision shadow-mode 7d obrigatório | `MEMORY.md:feedback_shadow_mode_for_ranking_changes.md` |
| Lição boost stacking veneno | `CLAUDE.md §5` (incident v3.4) |
| ClawMem Q2 origem da ideia | `plans/_archive/2026-04-26-clawmem-analysis.md` linha 54 |
| 1.4× match + 0.75× demote racional | `plans/_archive/2026-04-26-clawmem-analysis.md` linha 36 |
| Roadmap split implement/activate | `docs/ROADMAP.md §4` E04a + E04b rows |
| section_boost active precedente | sessão 2026-05-01 G02 (este HANDOFF) |

---

**Próximo passo:** revisar com Toto (essa spec) → se aprovado, branch `feat/E04a-focus-boost` paralelo a E03a, executar Phase 1-3 em 1.5h.
