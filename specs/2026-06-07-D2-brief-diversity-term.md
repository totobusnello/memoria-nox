# Spec D2 — Brief diversity/novelty term

> **Status:** DESENHO (aguarda decisão Toto + dados limpos do D3). Não implementado.
> **Origem:** sessão 2026-06-07 (D1 — feedback loop do canário). Ver `docs/HANDOFF.md#Sun 2026-06-07` e memória `[[feedback_probe_search_must_not_feed_ranking_signals]]`.
> **Repo de impl:** `nox-workspace/tools/nox-mem/src/api/brief.ts`.

## 1. Problema

O priming brief serve **88 chunks distintos em 21.337 serves** (0,4% de diversidade). O conteúdo recente (id 250k+, o que o próprio loop produz) nunca entra: a salience é dominada por `importance` (0.55) + `pain` (0.10) de incidents antigos (abril, pain=1.0), e `recency` (0.15) não desloca.

Parte disso era o **feedback loop do canário** (D1, já corrigido + 52 chunks descontaminados). Mas **~74 dos 88** eram staleness de *design*, não auto-reforço — e esse fica de pé. O brief é estável demais: top-salience perpétuo.

**Diagnóstico do que falta:** o brief já tem diversidade de **conteúdo** (dedup exato + near-dup por containment, `isNearDup`). Falta diversidade **temporal** (rotação ao longo do tempo) e **freshness** (novidade relevante entrando).

## 2. Invariantes (NÃO violar)

1. **Não forkar `calculateSalience`** — regra #17 + #5 do repo. O brief consome a salience canônica as-is. O termo de diversidade é um **re-rank pós-salience dentro do brief**, não um peso novo na fórmula (que afetaria search também).
2. **Read-only sobre `chunks`** — não tocar `access_count`/`last_accessed_at` (promessa F1). A serve-history vem de `brief_log` (tabela própria), não de `chunks`.
3. **Fail-open** — diversidade nunca derruba o priming. Erro/timeout no termo ⇒ cai pro brief atual.
4. **High-pain floor** — incidents críticos (pain ≥ 0.9) que *devem* ser servidos sempre não podem ser penalizados pra fora. Diversidade não é "esconder o importante".

## 3. Opções consideradas

| Opção | Mecanismo | Veredito |
|---|---|---|
| **A — Novelty penalty (serve-recency)** | Re-rank: `brief_score = salience − λ·penalty(serves recentes via brief_log)`. Chunks muito servidos descem, abrindo espaço. | ✅ **Recomendada (parte 1)** — usa dado existente, ataca a repetição direto, não forka salience |
| **B — Freshness quota** | Reserva F dos N slots pro conteúdo mais recente que passe um threshold de relevância e não tenha sido servido na janela. | ✅ **Recomendada (parte 2)** — garante novidade, simples, auditável |
| **C — Recency boost mais forte na salience** | Subir o peso 0.15 → maior na fórmula. | ❌ **Rejeitada** — forka a salience canônica + muda search (viola invariante #1) |
| **D — MMR re-rank (diversity de conteúdo)** | Penalização gradual de similaridade vs já-selecionados. | ❌ **Fora de escopo** — ataca redundância *intra-brief* (já coberta pelo near-dup); o problema é *temporal*, não similaridade no mesmo brief |

## 4. Recomendação: A + B (leves, combinados)

`N=10` slots → **~8 por `brief_score` (salience − novelty penalty)** + **~2 freshness slots**. Tudo respeitando o dedup existente (`tryPick`).

### 4a. Novelty penalty (A)
Em `buildBrief`, após `calculateSalience` e antes do sort/`tryPick` final:
- **1 query agregada** no `brief_log` (indexado por `idx_brief_log_chunk`):
  ```sql
  SELECT chunk_id, COUNT(*) AS n
    FROM brief_log
   WHERE chunk_id IN (<candidatos>) AND served_at > datetime('now', ?)  -- janela T
   GROUP BY chunk_id
  ```
- `penalty(id) = min(P_max, λ · log1p(n))` — log satura (servir 2.000× ≈ servir 100×), `P_max` impede zerar críticos.
- `brief_score = salience − penalty`. Re-rank por `brief_score`.
- **High-pain floor:** se `pain ≥ PAIN_FLOOR`, `penalty = 0` (incidents críticos imunes).

### 4b. Freshness slot (B)
- Reservar `F` slots pro candidato de menor `age_days` que: (a) `importance ≥ FRESH_MIN_IMP` OU `pain ≥ FRESH_MIN_PAIN` (não trazer lixo recente), e (b) `n_serves(T) == 0` (genuinamente novo no brief).
- Preenchidos via o mesmo `tryPick` (dedup-safe), após os slots de salience.

### 4c. Parâmetros (env, default conservador)
| Param | Default | Papel |
|---|---|---|
| `NOX_BRIEF_DIVERSITY` | `off` | `off`\|`shadow`\|`active` |
| janela `T` | `72h` | quão "recente" conta como já-servido |
| `λ` | a calibrar | força do penalty |
| `P_max` | ~0.15 | teto do penalty (≈ 1 termo de salience) |
| `PAIN_FLOOR` | 0.9 | acima disso, imune ao penalty |
| `F` | 2 | slots de freshness |
| `FRESH_MIN_IMP` / `FRESH_MIN_PAIN` | a calibrar | piso de relevância do freshness slot |

## 5. Plano de implementação (quando aprovado)

- [ ] **T1 — Shadow:** computar `brief_score` (salience − penalty) + freshness em paralelo ao brief atual; logar diff (itens que entrariam/sairiam, métricas) em stderr/`brief_log` extra. Surface = brief atual. (`NOX_BRIEF_DIVERSITY=shadow`)
- [ ] **T2 — Query brief_log agregada** + high-pain floor + cap. TDD: penalty satura, floor imune, fail-open.
- [ ] **T3 — Freshness slot** com thresholds. TDD: lixo recente não entra, novidade relevante entra, dedup-safe.
- [ ] **T4 — Métricas + gate** (§6). Rodar shadow ~3-5 dias sobre dados limpos (pós-D1).
- [ ] **T5 — Flip `active`** se gates passarem; senão calibrar `λ`/`F`/thresholds e repetir shadow.

## 6. Métricas + gate de decisão (amarrado ao D3)

Medir sobre `brief_log` com `served_at > <pós-D1>` (sinal limpo):

| Métrica | Baseline (pré) | Alvo |
|---|---|---|
| Diversidade `distinct/serves` (7d) | 0,4% | subir substancialmente (rotação real) |
| Freshness: mediana `age_days` dos itens | ~44-50d | baixar (recente entra) |
| **Guarda:** high-pain (≥0.9) ainda aparecem quando relevantes | sim | **não pode cair** |
| Follow-up rate (D3, proxy de utilidade) | indistinguível de ruído (contaminado) | mensurável + ≥ baseline |

**Gate:** flip pra `active` só se diversidade ↑ E freshness ↑ E high-pain floor preservado E follow-up não-pior. Decisão de produto do Toto com os números na mesa.

## 7. Riscos

- **Penalizar demais → esconder crítico.** Mitigação: `P_max` cap + `PAIN_FLOOR` + freshness é aditivo (não remove). 
- **Novidade vira ruído.** Mitigação: thresholds de relevância no freshness slot.
- **Custo da query brief_log.** Mitigação: 1 query agregada, índice existente.
- **Reavaliar o peso real:** com D1 corrigido, parte da "staleness" some sozinha. Medir o baseline limpo ANTES de calibrar — pode ser que a staleness residual seja menor do que os 88 sugeriam.

## 8. Dependências
- **D3** (medir follow-up real sobre dados limpos) é pré-requisito do gate §6 — precisa de ~3-5 dias de `brief_log` pós-2026-06-07.
- Decisão Toto pra sair de DESENHO → implementação.
