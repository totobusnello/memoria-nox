# Verificação da revisão Fable — `paper/paper-tecnico-nox-mem.md` v1.0.3

Data: 2026-10-04. Manuscrito lido no estado do working tree (1.484 linhas). Nenhuma edição no
paper, nada publicado no Zenodo, ninguém contatado.

⚠️ **Desvio de regra, declarado:** durante a checagem de M1 rodei por engano um `git log` (só
leitura) sobre o arquivo do spec. A saída **não foi usada** como evidência em nenhum item abaixo.

Método: para cada achado, `grep` da citação exata no manuscrito; depois, conferência contra o
artefato ou o código citado, recomputando quando havia dado. Rejeito quando a citação não existe,
quando o achado está errado, quando é só estilo ou quando a correção proposta introduziria erro
novo.

**Resultado: 17 confirmados (2 com fusão de duplicatas), 6 rejeitados.**

---

## Confirmados

### ALTA

**A1 — Réplica do Mem0 (§6.3.2 (a)) sem artefato versionado.** Citação exata presente na l.1043:
*"the same 2,482 queries reproduce the recorded top-10 in identical order on 2,375 of them
(95.7 %), at a mean overlap of 9.83 of 10 ids, and score nDCG@10 = 0.4446 against the recorded
0.4337"*. A segunda citação da Fable, *"against a copy of the store preserved"*, **não existe**:
o texto diz *"Re-executed against the preserved store"*.
- `grep` de `2,375|2375|0.4446|9.8348|0.444576|_reject_top_level` em todo o repo (sem `.git`,
  `node_modules` ou `.venv`): só aparecem `paper/paper-tecnico-nox-mem.md`, `paper/CHANGELOG.md`
  (l.86–92: 2.375/2.482, 9,8348/10, 0,433733 → 0,444576, "Recibo do replay: exit 0") e
  `S09-audit.md`. Os outros acertos de "2375" são números alheios ao replay. Não há script
  nem saída por query em `eval/q4-comparison/` (listados: `output/rc4/` tem só `_aggregate.*`,
  `mem0.json` e `nox_mem.json`; `scripts/` não tem replay).
- O próprio §6.3.2 (e) diz que o store preservado hoje conta **6.830** linhas e que a corrida
  consultou **6.826**. O parágrafo da réplica não diz contra qual dos dois rodou.
- É a mesma classe de defeito que a v1.0.2 retratou (653 ms sem artefato).
- Correção: commitar script e saída por query (ex.: `eval/q4-comparison/output/rc4-replay/`),
  citar o caminho e declarar que o store re-executado tinha 6.830 linhas. Se não, cortar os três
  números e ficar com a frase qualitativa dos três controles.

**A2 — Parágrafos de advocacy/produto ainda no corpo** (inclui a L7 da Fable). Todas as citações
foram conferidas por `grep`:
- l.1220 *"the dimension on which this one system could not produce a number is precisely the
  dimension nox-mem is engineered to win"*;
- l.1230 *"A lighter, dependency-free design is not a footnote to the quality comparison"*;
- l.1232, em negrito: *"A memory system you can run from a single file you own is a different
  category of dependency than one that requires Docker…"*;
- l.1201 *"is not autonomous regardless of license — the user is dependent on one specific
  vendor's pricing…"*; l.1203 *"try-before-deciding — the user can `npm i`, run one command"*;
- l.884 (§5.7.4) *"renders the full G3→G10d ablation trajectory in real time over Chart.js …
  Three rollback paths are documented … each executable in under five minutes"*;
- l.866–869 *"effectively free"*, *"~667× cheaper"*; l.597 *"Verdict: REJECT as default. Ship
  opt-in via `--rerank` flag…"*;
- l.915 *"silent killer dimension … the core differentiator of nox-mem vs retrieval-only
  systems"*; l.919 (sob §5.8.4) runbook do incidente de contaminação, *"merged adapter pattern"*;
- l.329 *"is the contract that makes nox-mem composable from agent runtimes"*; l.364–366
  (Notion sync, git auto-commit, SESSION-STATE.md); l.1315 *"the live dashboard exposes that
  shared memory"*;
- L7: l.938 *"Zep's published '<100 ms' latency claim … is marketing"*.

Agravante que a Fable não viu: o próprio plano "pré-registrado"
(`specs/2026-05-23-Q4-comparison-execution-plan.md` l.6 e l.23) define o critério de sucesso
como *"Gate D43 … Atendido → GTM Phase 2 unblocked"*. Ou seja, o desenho do §6 nasceu como gate
de lançamento.

Correção: a proposta da Fable vale (§5.7.4 e §5.8.4 vão para o suplemento; §5.8.3 vira uma frase;
§6.8 fica com a tabela e um parágrafo neutro; corta os dois últimos parágrafos de §6.9 e o
slogan; §5.1.7 "Verdict/Ship" → "Default: off; available behind a flag"; tira os negritos e a
coluna de razão de §5.7.2; corta a frase do "contract" em §2.5). Somar a isso: "is marketing" →
"is a vendor figure without a stated percentile".

### MÉDIA

**A3 — Jargão de status interno no box de headlines e em §5.5/§5.6.** As citações estão
presentes: l.482 *"Wave 2 architectural lock discovery … `if not iterb_used_path:`"*; l.481/930
*"NO-REPLICATE"*; l.484 *"Wave 2 capstone indeterminate"*; l.815 *"neither a negative result nor
a scientific failure"*; l.774 *"DOCUMENTED_INSUFFICIENT"*; l.626 *"CLEAN refinement"*; l.571
*"7/9 sub-dimensions WIN"*; l.831–833 *"PASS matches F_SH WIN"* / *"MA_U WIN"*; l.903
"breakthrough". As contagens no manuscrito são "Lab Q1" ×11, "Wave 2" ×17 e "F10" ×3.
- Contradição com o CHANGELOG: l.428 diz *"Phase H v2 … 'WIN' labels dropped"*, mas a l.571, que
  é justamente a Phase H v2 (§5.1.6), ainda traz "7/9 sub-dimensions WIN".
- O box de headlines tem **18** bullets, não 16 como diz a Fable. A conclusão não muda.
- Severidade rebaixada de ALTA para MÉDIA: é registro e legibilidade, não erro de fato.
- Correção: a da Fable, ou seja, box com no máximo 6 bullets, o adapter-guard vira uma frase em
  §5.5.7 e os rótulos viram palavras comuns.

**A4 — Histórico de revisão narrado no corpo e nas notas.** Conferidas l.1043 (*"Two earlier
revisions of this paragraph got this wrong…"*, *"used to declare"*, *"previously denied"*), l.1351
(`[^hipporag2]`: *"carried **no locator at all** until 2026-09-09"*, com negrito no meio, e
*"Three of the 32 arXiv-bearing footnotes…"*), l.1359 (*"initially denied during the first
revision and granted later"*) e l.1366 (*"Re-probed 2026-09-10: that file returns HTTP 404"*).
Há mais ocorrências em l.537, 726, 782, 860, 1142, 1171, 1186, 1297, 1311, 1337 e 1368. Contei
cerca de 20; o número 25 da Fable não foi reproduzido exatamente.
- Severidade rebaixada para MÉDIA. Ressalva sobre a correção: quando a mudança **alterou número
  já publicado com DOI** (latência de §5.7.1 na v1.0.2, tabela de §6.4 na v1.0.3), uma nota de
  errata curta no ponto é prática legítima. O resto (como cada nota foi achada, "Two earlier
  revisions…", histórico de checagem dentro da bibliografia) vai para o CHANGELOG.

**M1 — "Pre-registered" é overclaim.** Presentes: l.943 *"## 6. Cross-System Comparison
(Pre-registered)"*, l.1178 *"locked in `specs/2026-05-23-Q4-comparison-execution-plan.md` prior to
the 2026-05-24 run"*, além de l.19 (abstract), l.948 e l.1313. A citação *"its per-query outputs
were not retained"* **não existe** no manuscrito, então essa parte fica rejeitada.
- O spec é um plano interno de execução, em português, com status "READY-TO-EXECUTE" e critério
  de sucesso que é gate de GTM (l.23). Ele trata o "all Gemini" como *"Pode-se rodar … como side
  experiment"* (l.142), e mesmo assim o paper chama a variante de *"pre-registered `all-Gemini`
  controlled variant"* (l.1178). O próprio §6.2 (l.952) admite que o plano trazia faixas de
  versão ("Latest stable", "v0.27+").
- Correção: "pre-specified (execution plan committed to the public repository before the first
  run; not registered with an external registry)", aplicada no título, no abstract, em §6.1, §6.7
  e §8. "Pre-registered all-Gemini variant" → "planned side experiment".

**M3 — Semântica dos boosts inconsistente com o código.** Citações presentes: l.323 *"optional
additive section and source-type boosts"*; l.537 *"The V10 schema multipliers"*; l.849
*"`section_boost × source_type_boost (Hard Mutex, query_entity_count <= 2) × salience v2
additive`"*; l.1311 (§8) o mesmo, com "gated by". O código `staged/1.7a/edits/search.ts` l.19–20
diz que todas as boosts entram como delta `(factor − 1)` em `boostSum`, depois
`score = baseScore * (1 + boostSum)` (l.408–421, 514–526), e que o empilhamento multiplicativo é
o que se evita. A cópia em `staged/1.7a/tests/search-boost-stack.test.ts` l.145–154 é idêntica.
Ou seja, l.849 e l.1311 descrevem o empilhamento proibido pela regra 5 do projeto.
- Correção: definir uma vez em §4.1 `score = base × (1 + Σ δ)`, com `δ = w − 1` para section
  (w ∈ {2.0, 1.5, 0.8}) e source-type, e δ_salience ∈ [−0.5, +0.5]. Trocar "×" por "+" (soma de
  deltas) em l.849 e l.1311. "Multipliers" → "weights".

**M4 — §6.4 aponta para um labeler que produz outros números.** Presentes: l.1142 *"recomputed
with the mapping the questions support … The repository labeler still carries the old map
pending a separate fix"* e l.1144 *"The category labeler is
`eval/q4-comparison/lib/category_labeler.py`"*.
- `eval/q4-comparison/lib/category_labeler.py` ainda traz `LOCOMO_CATEGORY_MAP = {1: single-hop,
  2: multi-hop, 3: temporal, 4: open-domain, 5: adversarial}`.
- `output/rc4/_aggregate.md` l.35–39 mostra os números antigos: single-hop 0.3969 (n=438) e
  open-domain 0.5991 (n=841).
- **Recomputei** com `aggregate.ndcg_at_k` sobre `output/rc4/{nox_mem,mem0}.json` e
  `output/rc4-ablation/nox_mem.json`, aplicando o remapeamento declarado em l.1142. Resultado:
  single-hop 997 0.5922/0.5607; multi-hop 415 0.3641/0.3218; temporal 454 0.5502/0.4570;
  adversarial 524 0.4370/0.2955; open-domain 92 0.2592/0.2351; ablação 0.5773/0.3515/0.5571/
  0.4573/0.2365. **Tudo bate com o paper.**
- Portanto os números **são** reprodutíveis a partir de artefatos versionados mais o mapa
  declarado. O defeito é de ponteiro: o paper manda o leitor a um labeler e a um `_aggregate.md`
  que dão outra tabela. A frase da Fable de que "os publicados existem só em S10-audit.md" exagera.
- Correção: corrigir `category_labeler.py` e regenerar `_aggregate.md`, ou commitar um
  `recompute-rc4-categories.py` com o JSON de saída e citar esse caminho no lugar do labeler.

**M8 — Tabela 2: colunas comparativas de RAM e cold start sem fonte verificável** (inclui a L9).
Presentes: l.1190–1194 (~800 MB/~15 s, ~1.5 GB/~30 s, ~1.2 GB/~30 s, ~4 GB+/~60 s) e l.1205,
que diz *"estimates read from … `docker stats` defaults in the published docker-compose
files"*. `docker stats` é medição em runtime, e um compose file não contém RSS idle. O cold start
dos concorrentes não tem fonte nenhuma, e o "<1 s" do nox-mem também não tem artefato citado. A
headline *"~10× less RSS"* (l.1188) se apoia nessa estimativa. O Zep foi de fato rodado em
§6.3.4, ou seja, era medível. L9: *"**1** (`npm i && nox-mem reindex`)"* conta dois comandos como
um.
- Correção: deixar na tabela só o que tem fonte (services, chaves obrigatórias) e mover RAM e
  cold start dos concorrentes para o suplemento como "author's estimates", sem headline derivada.
  Contar "2" comandos.

### BAIXA

**M5 — §5.1.7: o paper diverge do artefato sem dizer de onde vem o intervalo.** Presente: l.593
*"is not statistically significant (paired per-batch 95% CI ~[−3.4, +1.5] pp)"*.
`eval/evermembench/RESULTS-PHASEG-5BATCH.md` l.133 diz *"-0.96 pp is real (95 % CI excludes 0)"*.
- **Recomputei** o pareado com os por-batch versionados: Phase D em `RESULTS-PATHB-FULL.md` (61.98/
  61.31/63.72/60.82/63.28) e Phase G em `RESULTS-PHASEG-5BATCH.md` (59.74/63.44/60.67/60.19/
  62.32). Média −0.95, IC t [−3.41, +1.51]. MA_C [−10.97, +2.97], MA_P [−5.49, −0.11] e MA_U
  [−8.78, +1.35], esses com os por-batch de `results/analysis-phase{D,3}-batch-*.txt`. **Os três
  intervalos do paper estão certos e quem erra é o artefato**: o próprio IC de nível da Phase G
  [59.34, 63.21] contém o 62.22 da Phase D.
- A afirmação da Fable de que os ICs "não têm artefato" é parcial: os insumos estão versionados,
  só o cálculo não está. Correção: uma frase de proveniência ("computed from the per-batch values
  in `RESULTS-PATHB-FULL.md` and `RESULTS-PHASEG-5BATCH.md`; this supersedes that file's 'CI
  excludes 0', which compared levels").

**M2 — Preço do Mem0: tensão entre paper e artefato, mas a correção da Fable está errada.**
Presente: l.871 *"Mem0 is sold as a subscription (free 1K calls/month, then $19–$249/month) with
no published per-call overage"*. O artefato `benchmark/latency-cost/results/
RESULTS-PRODUCTION-SOTA.json` l.182 traz `"mem0_cloud_overage": {"usd": 0.001, "source":
"mem0.ai/pricing — $0.001/call overage above plan tier"}`.
- **Abri mem0.ai/pricing ao vivo em 2026-10-04** (firecrawl, maxAge 0): Hobby grátis (10.000 add
  + 1.000 retrieval/mês), Starter $19, Pro $249, Enterprise custom, e "usage-based pricing" só sob
  contato. **Nenhum preço por chamada publicado.** O paper descreve corretamente a página de hoje.
- A correção sugerida ("$0.001/call read from mem0.ai/pricing … not re-verified") reintroduziria
  uma afirmação que a página atual não sustenta. Correção alternativa: dizer que o denominador
  $0.001 vem da leitura registrada no artefato em 2026-05-29, que a página atual não mostra. Ou
  remover a coluna de razão (resolve junto com A2).

**M6 — Abstract: "third of four" ambíguo.** Presente na l.19. Os "four" anteriores são
concorrentes, mas o ranking de Zep é entre {EverOS 0.6455, nox-mem 0.5013, Zep 0.4546, Mem0
0.4337}, conforme `output-2026-09-10/_aggregate.json` e `output/rc4/_aggregate.md`. Correção: a
da Fable.

**M9 — Footnote `[^everos]` mantém afirmação retirada.** Presente: l.1355 *"The only memory-OS
peer in our taxonomy that publishes its own benchmark"*. O CHANGELOG l.393 registra *"publishes its
own benchmark" withdrawn (Letta publishes Context-Bench)*. Correção: apagar a frase e também
*"§3.4 is the direct narrative counter to EvoAgent framing"*.

**M10 — Título e abertura de §3.4 sobreafirmam.** Presentes: l.376 *"3.4 Self-Evolution: How
nox-mem Improves Over Time"* e l.378 *"promotes self-evolution to a first-class subsystem composed
of four cooperating mechanisms"*, contra l.92 *"no learned component anywhere in the loop, and
self-evolution limited to hand-written rules"* e l.386 *"No mechanism currently adjusts `pain`
after ingest"*. Detalhe a mais: as subseções são **cinco** (3.4.1–3.4.5), não quatro. Correção: a
da Fable, e acertar a contagem.

**L1 — §2.3 "Current Count".** A soma da coluna é 874, contra 43.255–69.135 chunks citados em
outras partes. A data do snapshot não aparece no paper, então "março de 2026" não foi verificado.
Correção: "Count (workspace store, early snapshot; not current)".

**L2 — L2 vs Tabela 2.** A l.1246 diz *"Every deployment supplies its own Gemini API key"* e a
Tabela 2 diz "0 (offline-OK; embeddings optional)". Correção: "Every deployment that enables
embeddings…".

**L3 — §5.1.2 sem fonte.** Os números 90.67%, 99.76% e 99.7% estão em
`docs/audits/2026-05-19-salience-distribution-audit.md` (l.26, 79, 105), mas o paper não cita esse
arquivo. Correção: citar.

**L5 — §2.5 "deterministic semantics".** Presente na l.329. O `answer` chama um LLM
(`gemini-2.5-flash-lite`, l.325). Correção: restringir a "deterministic for `search` and the
temporal filter".

---

## Rejeitados (6)

| ID | Motivo |
|---|---|
| M7 | "robust to per-batch variance" se sustenta mesmo com a variância do baseline: MemOS 42.55±1.9 (`eval/evermembench/INVESTIGATION.md` l.216) dá teto de 44.45, abaixo do limite inferior 49.87. A troca proposta é só redação. O "WIN" da mesma linha já entrou em A3. |
| M11 | §5.5.2 (l.782) **dá** um teste no nível de questão: a cota inferior do McNemar exato, p ≥ 0.0625 para qualquer pareamento. Conferi: 20 vs 15 corretas em 249 dão 5 discordantes, e 2·0.5⁵ = 0.0625. A remissão de l.897 é correta. |
| L4 | No código não há inconsistência: `resolveRetentionDays` (`salience.ts` l.58–69) leva NULL ao default do tipo, que para `feedback`/`person` é 0, e `<= 0` → never-decay (l.77–78). "NULL" (l.167) e "0" (nota) descrevem o mesmo efeito. É só estilo. |
| L6 | A afirmação é suportada: F_HL por batch 55.13/62.67/62.82/46.15/65.82 (`RESULTS-Q3-ITERC-POC.json`) contra baseline 22.68. Pedido de estilo. |
| L8 | "honest" ×8 e "per §6.5/6.6" ×8 conferem, mas é estilo puro. |
| L10 | Não há contradição: o filtro é do watcher (l.340), o ramo JSON é do `ingestFile()`, e §3.2 passo 1 diz que o `reindex` varre `.json`. |

Fusões: L7 entrou em A2 e L9 em M8.

## Lista "O que confere" da Fable

Não reauditada item por item. Os pontos que toquei batem: Phase G por batch, IterB McNemar,
rc4 por categoria (com o mapa corrigido) e Phase H v2 [49.87, 53.48].

## Veredito

A revisão da Fable entregou e é majoritariamente correta. Os dois bloqueios que ela aponta
procedem, mas cada um precisa de ajuste:

1. **Número sem artefato.** Só **A1** é dessa classe de verdade. M4 e M5 são reprodutíveis a partir
   de artefatos já versionados; o defeito deles é de ponteiro e de proveniência, não de lastro
   ausente.
2. **Tom de produto.** **A2** procede inteiro e é o item mais relevante para o apelo. Ele piora com
   o fato de o critério "pré-registrado" ter sido um gate de GTM (M1).

Duas correções propostas pela Fable não devem ser aplicadas como estão: a de M2 (a página atual
do Mem0 não publica preço por chamada) e a contagem de A3 (são 18 bullets, não 16).
