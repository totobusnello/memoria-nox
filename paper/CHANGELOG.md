# Paper CHANGELOG — *nox-mem: Pain-Weighted Hybrid Memory for LLM Agents*

> Versionamento **interno** do paper rumo à publicação no arXiv. Cada *release candidate* (rc) adiciona um incremento que fortalece o paper; `v1.0.0` = primeira submissão pública (o arXiv a rotula como "v1" na mecânica dele, independente da maturidade do conteúdo).
>
> Autor: Luiz Antonio Busnello (Toto). Sistema: nox-mem v3.8. Decisão de evoluir-antes-de-publicar: 2026-06-28.

## Esquema

- `v1.0.0-rcN` — release candidates pré-publicação **(estamos aqui)**
- `v1.0.0` — sweep final (abstract-claims audit + polish) + submit arXiv
- `v1.0.x` / `v1.1.0` — revisões pós-publicação (arXiv v2+)

Cada rc: bump no header do paper (`**Paper version:**`) + entrada aqui + (opcional) git tag `v1.0.0-rcN`.

---

## Histórico

### v1.0.4 — 2026-10-04 (writing pass; no number, claim, reference or citation changed)

Writing pass over the manuscript with the `avoid-ai-writing` skill, run in ten slices
(Abstract through §8; the References and Footnotes block was left untouched and is
byte-identical to v1.0.3). The pass splits long em-dash chains into separate sentences,
drops emphasis bold from running prose, turns rhetorical questions and "not X but Y"
constructions into plain statements, and cuts throat-clearing openers. Em-dashes go from
318 to 142 and `**` markers from 885 to 525. **No number, claim, reference or citation
changed**, and the only intended non-prose change is the version line on the first page.

Restored from v1.0.3 during assembly, because they broke an invariant: all 32 section
headings the slices had re-punctuated (the headings list must stay byte-identical); the two
§2.5 sentences that had gained a backtick span (`search`, `answer`); and the §6.3.2
sentence "One external datum bears on how to read this, from a **different run** …", which
`claims_check_mutation_test.py` uses as an anchor.

**Mechanical parity, whole document, v1.0.3 → v1.0.4:** numeric-token multiset, footnote
markers and definitions, § references, backtick spans, link targets (bare hosts, DOIs,
arXiv ids), the ordered headings list, table rows and tables, and the references block are
all identical. Script: `paper2-interventional/_sprint-2026-10-04/noxmem-v104/parity-v104.py`.
Output: `paper2-interventional/_sprint-2026-10-04/noxmem-v104/PARITY.txt`. Baseline sha256
`5e20fc05…7a7b36` (v1.0.3 as deposited).

**Abstract mirrors.** `paper/abstract.md` §2, `paper/arxiv-metadata.txt` and
`publication/techrxiv-metadata.md` carry the same condensed block, re-worded to match the
manuscript abstract (pain in its own sentence, the native split, the embedding-matched
variant): 1,912 characters / 288 words (v1.0.3 part G: 1,902 / 281), within the arXiv
limit of 1,920.

**Checks:** `claims_check.py` 21 guards green; `claims_check_mutation_test.py` green;
`build-paper.sh` 0 "Missing character" warnings, 73 pages; density 59 works / 26,205
words = 2.251 per thousand (v1.0.3: 2.259). `censo-lastro-do-manuscrito.py` exits 0 (the
cited smoke outputs are versioned since PR #560).

**Regression review (Codex, receipt
`.remember/adversary-receipt-codex-2026-10-04T185304-2756.txt`, exit 0; question limited to
meaning changes introduced by the writing pass).** One finding, confirmed and fixed: §8 had
turned "a provider-agnostic embedding layer — Gemini in every configuration measured here"
into a standalone "Every configuration measured here used Gemini", which widened the scope
from nox-mem's embedding layer to every measured configuration (FTS5-only runs and
competitors with other embedders). The sentence now keeps the v1.0.3 scope: "…embedding
layer, which used Gemini in every configuration measured here; FTS5-only retrieval is a valid
keyless degraded mode (§4)." Parity, build and guards re-run green after the fix.

### v1.0.0-rc1 — 2026-06-28 (BASELINE atual)

Paper completo e auto-suficiente, zero `[PENDING]`:

- **§5 — 12 dimensões SOTA:** EverMemBench 5-batch (63.28% Overall + 88.42% MA Gemini-3-flash, +20.73/+32.74pp vs MemOS; 62.22% Gemini-2.5; 51.68% GPT-4.1-mini CI [49.88,53.49]); entity golden set nDCG@10 0.6237 (+78.8%); MuSiQue dev F1 58.62%; HotPotQA distractor ans_F1 73.37%; LoCoMo retrieval@10 74.52%; LongMemEval cross-bench n=300; produção (KG path p50 2.5ms / $0/query / 399MB RSS).
- **§6 — Q4 head-to-head n=100** (canonical run 2026-06-15): split honesto nox/Mem0 (nox ganha LongMemEval nDCG@10 0.5234 vs 0.4764; Mem0 ganha LoCoMo 0.4686 vs 0.4263); agentmemory 3º; 3 gaps documentados (Zep/Letta/EverMind).
- HyDE testado e **rejeitado** (−2.72pp, não entra como feature).

### v1.0.0-rc4 — 2026-06-29 (controlled-embedding + per-category)

**Executado local no Mac (sem pod), all-Gemini @ 3072d, full n=2,482 (1.982 LoCoMo + 500 LongMemEval).** Uma única run entregou **rc4** (all-Gemini) **e rc2** (per-category) — o aggregate do full set categorizado produz per-dataset e per-category juntos.

- **§6.3.2 nova — controlled-embedding:** ambos os sistemas em `gemini-embedding-001` @ **3072d** (não 768d — preflight refutou a premissa do plano original, commit `a6e7e4d`; medido nox=3072 / mem0=3072 com a key real). **nox-mem supera o mem0 nos dois**: LongMemEval 0.5255 vs 0.4061 (+0.119); **LoCoMo 0.4952 vs 0.4407 (+0.055) — inverte** o split as-configured do §6.3. Overall 0.5013 vs 0.4337.
- **§6.4 per-category preenchido** (era 100% `[deferred]`): nox-mem supera o mem0 nas 5 categorias representadas; maiores margens em **adversarial** (+0.142) e **temporal** (+0.118), menor em single-hop (+0.006); `numeric` = n/a (n<10). Consistente com a tese §5 (vantagem vem da fusão multi-sinal, não só do embedding).
- **Confounds residuais declarados** (§6.3.2, per §6.6): (a) mem0 mudou de 0.1.x→2.0.10 entre a canonical e o rc4 (exigiu fix de compat na API `search`/`get_all`) → 0.4337 ≠ o mem0 0.4686 do §6.3; **[retificado 2026-09-14 — a versão É estabelecível pelos artefatos e é `mem0ai 2.0.10`; a nota de 2026-09-10, que dizia "inverificável", está retratada. O drift 0.1.x→2.0.10 entre a canonical e o rc4 continua de pé como confound; o *risco de invalidez* que ela declarava, não. Ver a entrada de 2026-09-14 no fim deste Histórico e o §6.3.2 reescrito.]**; (b) vector backend faiss→Chroma; (c) sample scope n=100→2.482. rc4 ≠ isolamento de arquitetura puro.
- **Abstract `[Q4 NUMBERS]` preenchidos** (split as-configured + controlled) em `abstract.md` e `arxiv-submission-ready.md`.
- **Tese atualizada (não substituída):** §6.3 mantém o split honesto as-configured; §6.3.2 mostra que sob embedding controlado a vantagem do nox é robusta (supera o mem0 nos dois). As duas leituras coexistem — mais defensável que apagar o split.

### v1.0.0-rc4 — ablação task-type (2026-06-30, confound (d) neutralizado)

- **Ablação do confound (d) (task-type asymmetry).** O único viés que *favorecia* o nox no rc4 era o task-type do embedding (nox passa `RETRIEVAL_DOCUMENT`/`RETRIEVAL_QUERY`, mem0 não). Re-rodei o nox com **embedding genérico** (`NOX_EMBED_GENERIC_TASKTYPE=1` — sem task-type, exatamente como o mem0 chama o mesmo modelo) contra o **mesmo** baseline mem0, full n=2.482 — comparação simétrica "nenhum dos dois usa task-type", mantendo (a)–(c) constantes.
- **Resultado:** o nox cai só **0.5013 → 0.4979 overall (−0.34 pp)** e **ainda supera o mem0 (0.4337)** em overall, ambos datasets (LoCoMo 0.4920 vs 0.4407; LME 0.5215 vs 0.4061) e **todas as 5 categorias**. O task-type contribui ≤0.34 pp → **não explica a inversão**. A vitória é arquitetural (hybrid FTS5 + dense + RRF), não artefato de modo de embedding.
- **Caveat de rigor declarado:** o corpus genérico re-ingerido teve **99.03% gold coverage** (23 de 2.370 gold chunks distintos ausentes vs 100% no run task-type — variância transitória de ingest), handicap que **só prejudica o nox** — a vitória persiste apesar dele. Raws: `eval/q4-comparison/output/rc4-ablation/`.
- Paper atualizado: §6.3.2 (confounds 4→3 + parágrafo de ablação), §6.4, §6.7, §7.1, status box, abstract (`abstract.md` + `arxiv-submission-ready.md`), `docs/COMPARISON.md`.
- **Infra — 4 bloqueadores de execução corrigidos:** `_self_check` 768→3072 (import quebrado), `google-genai` faltante (mem0 embedder), `runner_rc4.py` criado, mem0 2.0.10 `search`/`get_all` API. Smoke validado (dims 3072=3072, gold-match 100% nos dois datasets, billing path exercitado). Raws: `eval/q4-comparison/output/rc4/_aggregate.{json,md}`.

### v1.0.0 — 2026-06-30 (frozen for arXiv submission)

Sweep final de claims (revisão adversarial multi-voice GLM + Codex + Kimi, read-only) + freeze pra submissão. Conteúdo congelado; resta só a logística do arXiv (endorsement cs.IR + submit), pós a qual atualizamos o arXiv ID.

- **Sweep de claims (PR #446):** GLM limpo; Codex 2 (qualificador backbone MemOS + contagem "ten"→"nine"); Kimi achou a raiz (3 GRAVE convergentes) — o abstract inline + a conclusão não carregavam o split as-configured (pareciam afirmar vitória LoCoMo em todas as condições), violando o próprio §6.6. Corrigido: abstract inline e §15 conclusão agora carregam **as duas leituras** (split as-configured: Mem0 ganha LoCoMo / nox ganha LME; + inversão controlada: nox ganha os dois). + qualificador de métrica no §5.3.1 + forward-pointer pro §6.3 + qualificador de backbone (GPT-4.1-mini) no claim EverMemBench.
- **README + CITATION alinhados** (PR #445): rc1→rc4→v1.0.0, título canônico, corpus 94.9k, §Q4 com rc4+ablação.
- **Confounds residuais:** 3 declarados (mem0 version drift, backend, sample scope) + task-type ablacionado/neutralizado.
- **PDF:** `paper/build/paper-tecnico-nox-mem.pdf`, 0 glyph warnings. arXiv abstract 296 palavras.
- **Pendente (logística, não-conteúdo):** endorsement cs.IR + rebuild do pacote de submissão a partir de `paper/build/` (o `arxiv-package-2026-05-24/` é pré-rc4) + submit → depois preencher arXiv ID em CITATION.cff + README badge.

### v1.0.1 — 2026-09-04 (honesty pass; entry added retroactively on 2026-09-29)

The paper header carried "v1.0.1 (2026-09-04)" from commit `9c11c33` onward, but this
file stopped at v1.0.0. Recorded here so the label points at something.

- **Retracted "dual SOTA"** and every cross-metric SOTA line; installed `paper/claims_check.py` with 8 mechanical guards (`9c11c33`, #458).
- Research-paper form (header, Table 1, appendices; #461) and abstract cut from 807 to 320 words (#463).
- **Zenodo:** record `10.5281/zenodo.22649269` (labelled "v1.0" on Zenodo; concept DOI `10.5281/zenodo.22649268`) was deposited on 2026-09-07 while the header read v1.0.1. The text kept changing under that same label afterwards, which is why v1.0.2 exists.
- **Zenodo v1.0.2:** record `10.5281/zenodo.23041503`, published 2026-09-29 as a new version under the same concept DOI; PDF `md5:0d4059bf07363980f0de71dde830f149` (332,314 B), identical to `paper/build/paper-tecnico-nox-mem.pdf` at `ca83841`.

### Retificação — 2026-09-14 (confound (a): duas revisões erradas, em sentidos opostos)

Commit `18c1bba`. O §6.3.2 afirmava três coisas falsas sobre o confound (a), e a nota
de 2026-09-10 acima afirmava uma quarta. Todas retratadas, com o que os artefatos da
própria corrida medem:

- **A versão É estabelecível — `mem0ai 2.0.10`.** A corrida persistiu a versão duas
  vezes, em strings exclusivas da linha 2.x: `output/rc4-run.log` traz o aviso do
  próprio mem0 de que *"the 'chroma' vector store does not support keyword search"*, e
  `.mem0-chroma-rc4/chroma.sqlite3` traz `text_lemmatized` em **6.830 de 6.830** linhas
  de metadata. Nenhuma das duas ocorre na sdist de 0.1.114 — conferido com controle
  positivo (`def search` em 23 arquivos dela, `user_id` em 21).
- **2.0.10 REJEITA, não absorve.** O texto antigo dizia que uma chamada na forma 0.1.x
  seria *silenciosamente absorvida* por `**kwargs` e buscaria sem filtro a `top_k=20`.
  Não é: 2.0.10 chama `_reject_top_level_entity_params` na entrada e levanta
  `ValueError: Top-level entity parameters frozenset({'user_id'}) are not supported in
  search()`. `**kwargs` na assinatura não é absorção — o corpo pode rejeitar.
- **`n_errors: 0` É discriminador** — o parágrafo negava explicitamente que fosse. O
  adapter embrulha a chamada em `except Exception → RuntimeError` e o `runner.py` conta
  cada exceção em `n_errors`; o artefato traz `error: null` nas 2.482 queries e
  `n_errors: 0`. Sob a forma 0.1.x, as 2.482 carregariam `RuntimeError`.
- **Réplica end-to-end**, sob os três controles assertados a cada rodada (filtro que não
  nomeia usuário → 0 resultados; `top_k=3` → 3; forma 0.1.x → levanta), contra uma
  **cópia** do store preservado: **2.375/2.482 (95,69%)** reproduzem o top-10 gravado em
  ordem idêntica, overlap médio **9,8348/10**, nDCG@10 **0,433733 → 0,444576**
  (delta **+0,011**). O delta **não é atribuído** — ANN aproximado e queries
  re-embeddadas contribuem plausivelmente e esta medição não os separa. Recibo do
  replay: `exit 0`, n=2.482, 0 desistidos.
- `meta.version = "mem0ai==0.1.114"` é o `VERSION_PIN` declarado do adapter — *intenção*,
  não leitura de runtime. ⇒ a tabela §6.2 e o artefato são **uma fonte, não duas**.

**Exigência para qualquer corrida futura, inalterada:** persistir o
`mem0.__version__` que o `validate()` lê dentro de `meta`. Aqui a versão foi recuperável
de uma linha de log e de uma coluna de metadata, o que é sorte, não desenho.

⚠️ **A regra que fica:** nunca escrever *"os artefatos não podem excluir X"* antes de
varrer o que os artefatos de fato registram. Os dois decisivos estavam preservados desde
2026-06-29.

---

### v1.0.2 — 2026-09-29 (latency figures back on artifacts; version labels reconciled)

Everything that changed under the v1.0.1 label after the 2026-09-07 Zenodo deposit, plus
three corrections found in a 2026-09-28 README audit.

**Changes since the deposit (2026-09-08 → 2026-09-14):** §1.5 Related Work and the
bibliography wired into the prose (#491, #492); appendices C–G and the Wave 2 /
cross-backbone material moved verbatim to supplements (#494, #508); EverOS measured —
a competitor that outperforms nox-mem (§6.3.3, #528) — and Zep measured, placing fourth
[sic: third of four — corrected in v1.0.3] (§6.3.4, #534); confounds 3 → 4 and the density guard (#535); TMLR template and
anonymity gate (`fe49755`); the §6.3.2 confound (a) retraction of 2026-09-14 (above).

**Corrections in this version:**
- **Latency without an artifact removed.** §5.7 and the places that cite it (abstract, §5 headline box, §5.8.6, §6.3, §6.3.3, §6.3.4, §6.6, §6.9, §7 L7) quoted a
  2026-06-15 re-check (KG path 2.9 / 5.7 ms, n=10; hybrid 653 / 706 ms, n=20) that was
  never archived; §5.7's own table meanwhile showed ~940 ms, so "653 ms (§5.7)" pointed at
  a section that said something else. Every KG-path and standard-hybrid latency now comes from a versioned artifact:
  KG path 2.5 / 6.1 / 7.9 ms (p50/p95/p99, n=120) and hybrid 529 / 698 / 744 ms (n=100),
  both `benchmark/latency-cost/results/RESULTS-PRODUCTION-SOTA.json` (2026-05-29); hybrid
  ~940 / 2,342 / 2,523 ms (n=95, 2026-05-18, `paper/publication/results/latency-benchmark-summary.json`)
  kept as the earlier run; the two hybrid runs used different query mixes, so their gap is
  not a drift measurement (per-category comparison in §5.7). The cross-encoder row
  (+3,700 ms) has no archived artifact and is now marked indicative. Ratios built on 653 ms were recomputed: Zep vs nox-mem 9.2×
  is dropped (different harness); EverOS vs nox-mem 2.4× becomes "above both archived
  runs"; "5–6 orders of magnitude" vs Letta becomes ~3 (hybrid) to 5.6 (KG path).
  An erratum was added to `paper/publication/supplement-wave2-and-cross-backbone.md`,
  whose body stays verbatim.
- **5-batch scope.** The headline said "all claims use the 5-batch protocol"; §5.8.1 already
  limited it to EverMemBench. MuSiQue and HotPotQA are single full-dev runs — now stated.
- **LoCoMo.** One summary line still read "74.52% retrieval@10 … above Mem0 SOTA F1
  66.88%"; it now says, like the other five places, that the two are different metrics.
- **Adversarial review (Grok, Kimi) of this diff:** accepted — model name removed from the
  hybrid row (the artifact's own label disagrees), corpus size declared, the 529/940 gap
  re-explained as query mix instead of Gemini variance, cross-encoder row marked
  unarchived, "529–940 ms" ranges rewritten as two runs, harness caveat added to the
  Letta row, erratum scope widened. Rejected after checking the text: "p99 caveat is
  stale" (the cross-encoder row still has p50 only) and "CHANGELOG omits the LoCoMo fix"
  (it does not; that reviewer received a condensed prompt).
- Header, README badge and `CITATION.cff` note aligned to v1.0.2. The Zenodo record is
  still the 2026-09-07 deposit; a new Zenodo version is the author's action.

### v1.0.3 — 2026-10-03 (generative-AI disclosure; product framing removed; corrections after review)

Prepared for the arXiv appeal of `submit/7771319`. Parts (A)–(G). **(A)** form and framing.
**(B)** corrections of content, found when two reviewers from other model families (Kimi
and Codex) read the first v1.0.3 draft (`0e1d5d8`). Every finding was checked against the
run artifacts and, for EverMemBench Table 4, against the benchmark paper itself
(arXiv:2602.01313) before being applied or rejected. Part B changes interpretive
statements, comparators and a few reported values (listed below). The external references
(55 works) are unchanged, and so is every headline measurement of nox-mem itself:
nDCG@10 0.6237, 63.28% / 51.68% / 62.22% on EverMemBench, 0.5013 in rc4, and the latency
and cost figures.

**(A) Form and framing**

- **Added: "Disclosure of Generative AI Use"**, an unnumbered section after the
  Conclusion, in line with arXiv's guidance that significant use of text-to-text
  generative AI be reported; v1.0.2 had no such statement.
- **Product/roadmap framing removed:** the D43 "approval gate" and "GTM Phase 2" language
  in §6.1, §6.6, §6.7, §7.2 F1/F6/F7/F8 and the Conclusion; the gate annotation labels in
  §5.7.4. The pre-registered criterion (top three on at least two of the four key metrics)
  stays, in §6.1, §6.7 and the Conclusion, named as a success criterion. F8 is retitled
  "Feedback from use outside the author's deployment".
- **Abstract:** tagline sentence and "no vendor lock-in" removed; MIT license and the
  production envelope (since March 14, 2026, six agents, 2.5 ms, $0, 399 MB) kept.
- **Labels:** §6 heading "Q4 COMPARISON" → "Cross-System Comparison (Pre-registered)";
  §6.8 "Autonomy quantified" and every "Autonomy pillar" / "Q/A/P" reference neutralised;
  the footnote heading "Autonomy table (Table 2) sources" → "Operational-cost table
  (Table 2) sources"; the `[^q-a-p-pivot]` footnote removed (it was `evidencia`, not
  `obra`; `bibitem-census.json` updated). File paths containing `q4` are unchanged.
- **Internal decision codes:** all of them are gone from the manuscript [sic: "D73" in §5.5.1 and the "D2" label in §3.5 remained; removed in part F]. The first draft
  removed D43/D48/D51/D67 and the §5.7.4 occurrences of D68/D69; this version replaces the
  37 that remained (D74 ×9, D75 ×6, D76 ×6, D68 ×6, D69 ×6, D53 ×2, D64, D41) with what
  they denote ("the earlier projection", "the Wave 2 portability study", "the
  infrastructure abort", or nothing). "Lab Q1/Q2" as a scheduling label is removed from
  §5.6 and §7.2 (F3, F5, F6, F8); as the name of the §5.1.8 experiment series it stays,
  as do Wave A/B/C, Q3 and rc4, which name runs defined in the text.
- **Product language:** "a unique competitive position" (§5.7), "a 'build a small team to
  evaluate' decision" (§6.8), "unusable is the worst score" (§6.9) removed.
- **Form:** the empty duplicate "### 6.8 Operational cost" heading removed; §1.3 no longer
  lists the agents' names (they remain in the §2 data table); the third Conclusion
  paragraph narrowed from "institutional learning across the fleet" to cross-agent search
  with per-agent attribution (§4.3) — a narrower capability statement, not only a
  rewording; §6.7 "If it was not met, … was to produce" → "Had it not been met, …";
  §6.8 "Three rows" → "Three columns" (the list is about columns); `refs.bib` comments
  translated to English (the file ships with the arXiv source).

**(B) Corrections of content** (inherited from v1.0.2 unless marked)

1. **Zep ranks third of four**, not fourth (0.6455 / 0.5013 / **0.4546** / 0.4337,
   `output-2026-09-10/_aggregate.json`) — §6.3.4 heading and text; the v1.0.2 entry above
   repeated the error and is annotated.
2. **EverMemBench Table 4 has a Gemini-3-Flash column**, and the "Gemini column" (59.27%)
   is it. The abstract said every MemOS Table 4 number was obtained on GPT-4.1-mini; it now
   gives the same-backbone comparison: 63.28% vs 59.27% (+4.01 pp), below that backbone's
   72.61% full-context baseline. §5.1.10 adds the same-backbone column (MA composite
   88.42 vs 86.70, +1.72 pp; MA_U −4.61 pp), keeps the GPT-4.1-mini column as
   cross-backbone, replaces the approximate per-dimension values with the artifact's
   (`RESULTS-BACKBONE-MATRIX.json`: MA_C ~95 → 89.20, MA_P ~83 → 90.00, MA_U ~87 →
   86.06) and the "+N pp class" deltas with computed ones, corrects "~+25 pp MA composite
   at the gpt-4.1-mini tier" to +17.66 pp, and drops "compose multiplicatively" (the
   decomposition 9.13 + 11.60 = 20.73 is additive by construction). Phase D (+2.95 pp) is
   relabelled cross-backbone: nox-mem on Gemini-2.5-flash vs MemOS on Gemini-3-Flash. The
   portability headline now compares the same swap (Gemini-3-Flash → GPT-4.1-mini:
   nox-mem −11.60 pp, MemOS −16.72 pp); "1.6× more portable", which mixed two different
   swaps, is removed. §5.8.5 and the dual-baseline paragraph follow.
3. **Composition (§5.1.9 and every summary of it).** "Compose additively" and "caps at
   ~+7.25 pp F_MH" confused absolute F_MH with gains: 7.25% is absolute (+4.04 pp), and
   every measured combination is sub-additive (KG+MQ +4.81 vs +6.42 predicted; KG+MAP
   +4.04 vs +6.83; triple +4.02 vs +10.44). KG+MQ was reported as +3.93 pp, a value no
   artifact holds; `RESULTS-WAVE-B-KG-MQ.md` gives +4.81 pp (8.02%). KG+MAP closes ~26% of
   the MemOS F_MH gap (was ~24%), at an MA composite cost of −5.02 pp — the text had said
   "within MA tolerance", and the run's own MA gate failed. The "retrieval-stage ceiling"
   is now an observed plateau, not an established ceiling, and the IterB "ceiling break"
   (8.03% on Gemini-3-flash against 7.25% on gpt-4.1-mini, +0.78 pp) is restated as a
   directional +2.01 pp lift whose comparison with the retrieval-stage results crosses
   backbones.
4. **Embedding-matched comparison (§6.3.2, §6.4).** "Substantially an embedder effect",
   "the win is architectural" and "the reversal is the embedding-matching effect" claimed
   causes that the four declared confounds prevent attributing; the text now states what reverses and
   attributes it to neither. The §6.4 attribution of category margins to the FTS5 channel
   is marked as unmeasured.
5. **EverMemBench scope.** §1.5 said nox-mem had not been measured on Hu et al.'s
   multi-party setting, and F4 listed running it as future work; §5.1.5–§5.1.10 report it
   on the benchmark's five released batches. §1.5, `[^longhorizon]`, `[^everos]` and F4
   (now: re-run the comparators in the same harness) are rewritten.
6. **"99.85% of the gain"** (first v1.0.3 draft; v1.0.2 said "of the full stack" in §5.1.1
   and "of the lift" in the Conclusion): 0.6228 / 0.6237 is a share of the score, not of
   the gain, and rounds to 99.86%. Now "99.86% of the full-stack score" in §5.1.1, §5.1.3
   and the Conclusion.
7. **Numbers and timing.** §5.8.1: batches hold 610–633 queries each (sum 3,121), not
   "120–250". §5.6: 0.9126 → 1.0000 is +8.74 pp (+9.6% relative), not "+9.6 pp", and the
   two runs differ in sample and pipeline, so the rise is no longer attributed to the
   sanitize fix alone. Writeback: "sub-second" (abstract, §1.4) and "< 1 s" (Table 1)
   contradicted the 2-second debounce of §3.1; all now say 2-second debounce.
8. **Cross-references.** The 184-file result is in §3.5, not §4.3. The Conclusion's
   KG-decay claim pointed at §5.6 (LongMemEval); it now points at §2.2 and says the effect
   is not measured. "F-cost-bench" never existed in §7.2; that pointer and four other
   "(§7.2)" pointers to items §7.2 does not contain (HaluMem, the §3.5 active-mode
   numbers, LightRAG/HippoRAG2, the L7 latency benchmark) are removed.
9. **Letta.** "One of five competitors could not be made to produce a single result" (§6.9)
   and "could not be evaluated at all" (L6) overstated: Letta ran, at ~16 min/query, and
   produced no benchmark number. Both now say that (`q4-corridas-census.json` templates
   updated). F1's stale "Target deployment: estimated 2026-05-25" replaced by "not
   deployed at the time of this revision". §6.8: the EverOS row, the "~12× less RSS"
   headline and the cold-start remark are dated to the 2026-06-15 five-service
   configuration, an estimate, not the later library measured in §6.3.3.

**Rejected or partly rejected:** "the CHANGELOG says D43–D69 were removed" (it listed the
specific occurrences removed, which was accurate; the entry is rewritten anyway); "rc4",
"Wave A/B/C" as jargon to remove (they name runs defined in the text; kept); the
alternative disclosure wording "Their use is disclosed here" (the grammar finding is
accepted; Kimi's wording was used).

**Number parity, first v1.0.3 draft (`0e1d5d8`) → this version.** Changed: 99.85 → 99.86
(×4); +3.93 → +4.81 pp (KG+MQ); ~24% → ~26% (gap closure); "n ~ 120–250" → 610–633;
"+9.6 pp" → "+8.74 pp (+9.6% relative)"; §5.1.10 MA_C/MA_P/MA_U ~95/~83/~87 →
89.20/90.00/86.06, "+25/+31/+42 pp class" → +19.30/+38.01/+40.91, "+10/+18/+17 pp class"
→ +4.60/+24.60/+16.03, "~+25 pp" → +17.66 pp; −10.54 vs −16.72 pp "= 1.6×" → −11.60 vs
−16.72 pp; dual-baseline +20.73/+32.74 → +11.60/+15.08 (the backbone's own gain); Zep
"fourth" → "third". Removed: "7.25 pp" as a ceiling (absolute 7.25% kept), "+0.78 pp"
(×2). Added (all from artifacts or Table 4): 59.27 / 86.70 / 81.84 / 87.59 / 90.67 and
the same-backbone deltas +4.01 / +1.72 / +7.36 / +2.41 / −4.61; 72.61 (full context);
73.34 vs 55.68 (+17.66); 8.02, +4.81, +6.42, +6.83, +10.44, 7.23, +4.02, [2.20, 12.27],
2–18%, −5.02; 249 and ~50 F_MH questions per batch; 8.74. Numerals that became words:
"top-3 on >=2 of the 4" → "top three on at least two of the four" (§6.1, §6.7).
"Sub-second" / "< 1 s" → "2-second debounce" / "2 s debounce".
- Density: 55 works / 26,443 words = 2.080 per thousand (floor 2.06), from 2.1147 in
  v1.0.2 and 2.1118 in the first draft.
- `claims_check.py`: 21 guards green; `claims_check_mutation_test.py`: 48 mutations bitten.
- The four points first listed here as "known and not changed" (F_MH called strict EM;
  Table 4's Average vs our Overall; MemOS F_MH 18.94 vs 18.88; the supplement's KG+MQ
  +3.93 pp) are resolved in **(C)** below.
**(C) The four known points, resolved** (same day, after (B); checked against the
EverMemBench paper, arXiv:2602.01313v3, opened for this pass, and the run artifacts)

1. **The F_MH metric is LLM-judged accuracy, not strict EM.** The benchmark scores
   fine-grained recall, F_MH included, with an LLM judge that returns CORRECT or WRONG for
   semantic equivalence (its §4.1 "Evaluation Metrics" and Appendix C.2; the judge model is
   not named there). Our runs use the benchmark's own harness, whose evaluate stage sends
   open-ended answers to an LLM judge (Gemini-2.5-flash, `eval/evermembench/pipeline-*.yaml`),
   and every F_MH question in the five batches is `open_ended`
   (`eval/evermembench/results/phaseG-evaluation-*.json`). The wording now says what the
   metric is in the abstract, the §5 headline box, §5.2.3, §5.4 (table, text and
   explanation 2), §5.8.6, `abstract.md`, `publication/techrxiv-metadata.md` and the Wave 2
   supplement. Explanation 2 is renamed "All-or-nothing scoring": the old text said minor
   wording variations are penalised, which the judge protocol contradicts; what holds is
   that there is no partial credit. `claims_check.py`'s cross-metric arithmetic guard
   matched only "strict EM / exact-match / EM" and would have gone blind to the new
   wording; it now also matches "LLM-judged" and "judged accuracy", and
   `claims_check_mutation_test.py` has a case for it (confirmed: the old regex does not
   match it).
2. **Aggregation of the Table 4 comparison.** Table 4's "Average" is the unweighted mean of
   its nine sub-dimensions (recomputed from the MemOS rows it gives exactly the published
   42.55 and 59.27). Our Overall is accuracy over all 3,121 queries, and it also includes
   F_HL (388 queries), a category of the released batches that Table 4 does not report.
   Recomputed in Table 4's aggregation from per-sub-dimension counts: Gemini-3-flash
   **63.77%** (+4.50 pp vs 59.27; Overall 63.28%, +4.01), GPT-4.1-mini **51.65%** (+9.10 pp
   vs 42.55; Overall 51.68%, +9.13), Gemini-2.5-flash Phase D **59.21%** (−0.06 pp vs
   MemOS on Gemini-3-Flash; Overall 62.22%, +2.95). Sources:
   `eval/evermembench/RESULTS-BACKBONE-MATRIX.json` (`sum_correct`/`sum_total` per
   sub-dimension) and, for Phase D, the five `eval/evermembench/results/results-phase{D,3}-batch-*.json`
   files (they reproduce 1,942/3,121 = 62.22%). The earlier ~63.77 estimate was recomputed
   and holds. Both aggregations are now shown where the comparison is made: abstract, §5
   headline box (four bullets), §5.1.5 and §5.1.6 (new table rows), §5.1.10 (new row and an
   "Aggregation" paragraph), §5.8.5. In Table 4's aggregation the Phase D cross-backbone
   margin changes sign (+2.95 → −0.06 pp), and the Gemini-3-Flash → GPT-4.1-mini swap costs
   nox-mem 12.12 pp (11.60 in our Overall) against MemOS's 16.72.
3. **MemOS F_MH is 18.88%.** Table 4 gives 18.88 ± 4.8, in its GPT-4.1-mini column; 18.94
   appears in none of the three arXiv versions (v1, v2, v3 checked) and traces to
   `eval/evermembench/RESULTS-PHASEG-5BATCH.md`. §5.1.7 now cites 18.88% and says it is a
   GPT-4.1-mini figure (Table 4 has no Gemini-2.5-flash column, so the Phase D/G gap
   crosses backbones); the rerank's share of that gap becomes 11.8% (1.61 / 13.66; was
   11.7% against 18.94).
4. **Wave 2 supplement.** KG+MQ +3.93 pp → +4.81 pp (F_MH 8.02%,
   `RESULTS-WAVE-B-KG-MQ.md`). The same file also carried 18.94% twice (with −13.72 pp, and
   11.7% twice) and the strict-EM / strict-scoring wording in eight phrases; all corrected in
   place, with a v1.0.3 erratum at the top that lists the in-place changes, because that
   file's header promises a verbatim body. The erratum also states that the S5.1.12
   table's Gemini-2.5-flash row compares across backbones and that its composition
   language (a "ceiling" near +7.25 pp, "~24%") is superseded by §5.1.9; that language is
   not rewritten.

**Number parity for (C).** Changed: 18.94 → 18.88 (§5.1.7; supplement ×2); 11.7% → 11.8%
(§5.1.7; supplement ×2); −13.72 → −13.66 pp (supplement); +3.93 → +4.81 pp (supplement);
2,087 → 2,095 characters (`techrxiv-metadata.md`, the abstract block). Added: 63.77,
+4.50, +21.22, +12.12 (§5.1.10 row, abstract, headline box, §5.8.5); 51.65, +9.10
(§5.1.6, headline box); 59.21, −0.06 (§5.1.5, headline box, §5.8.5); 388 (F_HL count);
8.02 (supplement). Unchanged: 63.28 / +4.01, 51.68 / +9.13, 62.22 / +2.95, 88.42 / +1.72,
18.88 everywhere it already stood.
- Density after (C): 55 works / 26,678 words = 2.062 per thousand (floor 2.06; the new
  text was cut to fit).
- `claims_check.py`: 21 guards green; `claims_check_mutation_test.py`: 49 mutations bitten.

**(D) Final review pass, 2026-10-04** (Kimi k3 + Codex gpt-6-astra, both `exit 0`; 16 findings
confirmed, 7 rejected; `paper2-interventional/_sprint-2026-10-04/REVIEW-noxmem-v103-final.md`).
Each fix re-checked against its artifact before applying:
1. **IterB CI (§5.5.2).** `[1.06, 9.39]` belonged to AC threshold=5 on gpt-4.1-mini. Now IterB's
   own t-CI [6.27, 9.79] (per batch 8/6/10/8/8.16, `RESULTS-Q3-ITERB-POC-GEMINI.json`) and the
   paired-difference CI [0.25, 3.76] against `RESULTS-BACKBONE-MATRIX.json` (4/6/8/6/6.12).
   "Directional, not significant" now rests on a named test: 20 vs 15 correct of 249, Fisher
   exact p = 0.48. §5.8.1's claim threshold now says it ignores baseline variance.
2. **"Like-for-like" (§5.1.10, §5.8.6).** Now "uses Table 4's aggregation formula, not its
   population": 2,733 questions in the nine categories against the paper's 2,400 (v3 §3 and
   App., per-category counts listed in the text).
3. **Wave C CI** recomputed with t: [−0.74, 15.21] (artifact stores a z/pstdev [2.20, 12.27]);
   "6–10 pp wide" → "8–16 pp".
4. **F_MH attribution** (abstract, headline box, §5.8.6): "principally task setup" → "the leading,
   not established, account", matching §5.4; §5.4 now cites v3 Table 5's oracle result.
5. **rc4 rows (§6.3.3, §6.3.4):** R@10/MRR filled (0.6656/0.4749; 0.5852/0.4092) and p50 given
   as 515.6 / 349.8 ms, not transport-normalized (`output/rc4/_aggregate.md`).
6. HyperMem 92.73% is **LoCoMo** (arXiv:2604.08256v2 abstract); gbrain 97.6% is any-hit **R@5**,
   corrected by its authors on 2026-08-31 to 83.40% recall_all@5; "empirical upper bound" →
   "projection, untested"; KG+MQ co-fire reframed (MQ fires on 99.3% of queries; overlap is a
   hypothesis); "best published system" → "best published memory-augmented system"; full
   context 26.51% stated once in §5.4.
7. Lows: MAP standalone 7.23 → 7.22%; transfer "~24–40%"/"~30–40%" → "0–40% (24% in
   aggregate)"; `answer` topK 10 → 8 (`config.ts` `DEFAULT_TOPK`); single-hop mechanism
   sentence dropped.
8. **Out-of-scope items carried from (C):** `[^longhorizon]` title → "…Collaborative
   Dialogues"; EverMemBench pinned to **arXiv:2602.01313v3** (footnote, §5.8.6, both
   `refs.bib` entries); `abstract.md` "99.85% of the ablated gain" → "`section_boost` alone
   reaches 99.86% of the full-stack nDCG@10" (the share of the *gain* would be 99.67%).
- Words cut to hold the density floor: the §5.8.5 "Limitations to flag" bullet (duplicated
  §5.8.6), the §5.8.6 IterB-composability bullet (duplicated §5.8.5's capstone bullet), and
  three shortened sentences. Density after (D): 55 works / 26,692 words = 2.061 per thousand.
- `claims_check.py`: 21 guards green; `claims_check_mutation_test.py`: 49 mutations bitten.
  Supplement not edited (its AC row correctly carries [1.06, 9.39]).

**(E) Audit pass, 2026-10-04** (13 slices S01–S13; every finding verified against the artifact or
the external source it names before applying; full apply log in
`paper2-interventional/_sprint-2026-10-04/noxmem-audit/APPLY-REPORT.md`). Where two findings touched
the same sentence they were merged; where a finding contradicted a code-level finding (S04), the code
won.

*Abstract and front matter.* Hardware stated as the host §5.7 measured on (4 vCPU / 16 GB,
`RESULTS-PRODUCTION-SOTA.json` meta), production now 2 vCPU / ~8 GB (§1.3, §2.1, §7.1 L3 aligned).
`pain` is "operator-assignable", otherwise fixed at ingest by a keyword rule (no upward drift — see
§3.4). "A single SQLite file" → one per store. "March 14" → March 2026. EverOS/Zep query set named
(n = 2,482). "The two leaders split" → nox-mem and Mem0 split; new sentence: EverOS outperforms
nox-mem on both datasets (0.646 vs 0.501), mandatory cross-encoder, share unmeasured; Zep third of
four. F_MH: "3–7% vs 18.88%" → 6.02% (4–8% per batch) vs 10.84% for MemOS on the same backbone
(18.88% is GPT-4.1-mini).

*§1.4–§1.5.* "three families" → four; "memanto" (no reference) removed; LightRAG → Findings of EMNLP
2025; MeMo description and footnote corrected to arXiv:2605.15156v2 (*MeMo: Memory as a Model*, Quek
et al.), Table 1 MeMo cells "no — retrain" → "no — memory-model training"; EverOS "only memory OS that
publishes its own benchmark" withdrawn (Letta publishes Context-Bench); Reflexion/crystallize link
rewritten; deployment sentence (Table 1) now names Mem0, Zep, EverOS, Letta and agentmemory
correctly; provenance ref §3.3 → §2.2/§7.1 L4; writeback row and triad → consolidate + crystallize;
self-evolution "two operator-invoked primitives" → hand-written rules on invocation or schedule;
HNSW "binding constraint (§7.1)" → unmeasured ~100k expectation (§7.2 F6); pain "the operator
decides" → a hand-written rule; "Nothing here adapts" → rules never adapt, values do; RMM/ReasoningBank
mapping (wrong §3.4.2 ref, "read-side reflect", "trained policy") rewritten; WebCoach "trained
component" → LLM coach; retention ref §2.3 → §3.4.3; entity files §2.3 → §5.1.3; KG price "§5.4
quantifies" → not isolated; LongMemEval/LoCoMo "descend from" MSC → follow its setting.

*§2–§4 (checked against `nox-workspace/tools/nox-mem/src`).* Port 18800 → 18802 and Ollama marked
initial-deployment only; schema "version 3" marked historical (current v18, columns listed);
tokenizer porter → `unicode61 remove_diacritics 2` (§2.2 note, §4.1, F7: the "decisa" stemming
example was false); primitives "identical across CLI/HTTP/MCP" and "advanced verbs decompose into
primitives" withdrawn; Hard Mutex description corrected (the auditor's own fix inverted it);
`answer` p95 101.74 ms is mostly the 100 ms mock (~1.7 ms overhead), live 1.5–2.5 s unsourced and
dropped; E13/`NOX_TEMPORAL_PATH` reference removed; watcher filter `.md/.json` → `.md/.txt`;
§3.2 extractor Ollama → Gemini 2.5 Flash-Lite (Groq fallback); dedup scope (consolidation and
session distillation only) and fallback threshold 60% → 70%. **§3.4 rewritten to what the code
does:** `crystallize` = caller-supplied procedure capture, no LLM, no pending→lesson promotion, not
wrapped in `withOpAudit()` (footnote fixed); `pain` assigned once at ingest by `inferPain()`, never
raised afterwards; decay keyed on `last_accessed_at`; "Table V8" removed; additive-vs-multiplicative
"ablation" claim withdrawn (active vs shadow only); `reflect` = on-demand answer with TTL cache,
no write-back, no LRU, no `CONFIDENCE_DERIVED`; consolidate = extraction into topic files, does not
call reflect/crystallize, no `withOpAudit()`; closing "grows along the gradient of pain" paragraph
rewritten; headings 3.4.1–3.4.5 retitled. §4.1 boosts 2.0×/1.5× (FTS) and 1.5×/1.2× (semantic) →
additive +1.0/+0.5 and +0.5/+0.2, type list extended; sanitizer splits hyphens; vec distance is
sqlite-vec default L2; §4.2 "significant quality improvements" → anecdotal illustration.

*§5.* Headline box aligned with every change below; "(draft)"/caps label removed; "resolves" →
"refines". Wave A golden-set provenance (`entity-eval.db` vs `g5.db`) declared unresolved and
"curated from production usage" dropped; `source_type` boost inert (A10 = A8); +78.8% decomposed
(hybrid without boosts 0.5126; Wave A stack +21.7%); "archived under `audits/`" → archived handoff
only; section_boost "majority of the headline improvement" → nearly all of the within-G5 gain, not of
the +78.8%; additive-salience mechanism claim replaced by what was measured (+0.0082, single run).
Phase H v2 CI [49.88, 53.49] → [49.87, 53.48] (artifact), "WIN" labels dropped, F_MH row 3.21%
(8/249), CI [−1.64, 8.04], gap −15.67 pp. Phase G: F_MH CI is the Phase G level, not the Δ; MA_C,
MA_U and overall −0.96 pp not significant (paired per-batch CIs; MA_P borderline); MA miss in the
batch-004 gate = missing Phase D MA baseline (not selection bias; batch 004 has the largest MA_C
drop); latency 1.1 → 4.8 s p50 (`RESULTS-PHASEG.md`). "Four orthogonal mechanisms" → four mechanisms
with their own lifts. §5.1.11–12 stub: "retrieval-bound … used in §7" → task setup as leading
account. MuSiQue: EX(SA) 49.70 → 49.80% dev (Δ −8.92 → −8.82 pp), IRCoT 35.80 → 36.50% (Δ −22.82 →
−22.12 pp); Beam Retrieval dev retrieval EM/F1 77.37/89.77 and 79.31/90.51. HotpotQA: DPR+FiD row
(no source) deleted; baseline row "BERT reader ~58%" → Clark & Gardner architecture 58.28%
(−15.09 pp), new footnote `[^clarkgardner]`. LoCoMo: Mem0 66.88% is LLM-judge J (68.44% Mem0^g), not
F1; §5.3.2 ranking table withdrawn (Zep 50.40 / LangMem 50.21 / OpenAI ~55 / LangGraph ~52 are not
in the source); "rank-5" removed everywhere. §5.4 table columns fixed (6 cells), F_MH per backbone,
oracle figures attributed to Tables 4/5, closing "all-or-nothing scoring" attribution dropped.
§5.5: IterC table now shows all measured cells and the 2/4 gate verdict (F_MH 2.81%, F_SH −10.08 pp,
MA −4.36 pp, overall +1.45 pp); "PASS" on F_HL removed; cost row → 1 decomposer + ~3 sub-answers + 1
final call, p95 3,688 ms; Self-Ask mechanism claim → post-hoc, with the published Self-Ask design
contrasted; env var `NOX_Q3_ITERC_ENABLED` (exists nowhere) → `NOX_ITERC_ENABLED` (adapter) and D73
override stated; "validated in §5.5.2" → directional; IterB MA −3.53 pp and overall −0.58 pp added;
+2.01 pp = arithmetic sum of standalone lifts, 24% of the gpt-4.1-mini sum (not a "projection");
composability "measured matrix" → per-knob only; MQ "MA flips sign / strongest MA gain" → inside CI.
§5.6: retrieval at ceiling in every category, so the per-category pattern cannot be attributed to
the retrieval architecture; shared generator and judge disclosed; 96 judge errors, single batch;
nDCG CI was session_hit's; abstention is a variant (n=23); "Q2" defined; gbrain sourced (new footnote
`[^gbrain]`); "win claim on task accuracy" withdrawn. §5.7: MiniLM row now artifact-backed (+3,674
ms p50, p95 6,784, p99 8,696; eval harness); Zep "<100 ms p50" → no percentile; "100–500 ms" range
(no source) → Mem0 "<200 ms", MemOS none; "eliminates network overhead entirely" corrected; long-
query category gap (~390 ms) disclosed; Gemini price history (no source for a Feb-2026 increase)
corrected; RSS under load 414 → 423 MB (+24 MB); "$5/month tier" and "≥3 services, 1.5–3 GB"
(no source; contradicted Table 2) removed. §5.8: overstatement range "3–6×" → 1.27–5.8×; Lab Q1 #4
row (mixed 1-batch treatment vs 5-batch control) deleted; σ list replaced by Phase G/H values;
"GPT-4.1-mini is the only backbone where all memory systems gain" → false per Table 4; opt-in
combination claim narrowed; "Wave A knobs" → "Lab Q1 knobs" throughout.

*§6.* Versions "locked prior to execution" → ranges in the plan, recorded per run; thread-leak ref
§6.3.1 → §6.9; smoke nDCG 0.6380 → 0.4509 (rescored from `output/nox_mem.json`), Mem0 smoke 0.8569
→ 0.1315, p50 273 → 263 ms, p50 8 ms dropped; canonical-run raw outputs not retained (declared);
cost cells ($0 / "subscription") → one Gemini embedding / OpenAI embed per query; "market leader"
→ Mem0; LoCoMo "real retrieval gap" → only the namespace confound is ruled out; §6.3.1 heading
"did not run" → "without a benchmark number" (census template updated); Zep smoke cap applied to
Mem0 only; Letta ~16 min/query marked indicative; EverOS "live service" → in-process API; Mem0 store
6,830 → 6,826 rows at query time (4 back-filled after the run); EverOS duplicate handling 4 rejected
/ 4 accepted; "a fourth" → "a fifth" confound; Zep "no cross-corpus index … property of the design"
→ property of the per-session surface measured (collection search exists, unmeasured); no-rerank
evidence moved to the adapter call, extractor disabling declared. **§6.4 per-category table
recomputed:** LoCoMo categories 1–4 were permuted by `lib/category_labeler.py`; corrected map
1→multi-hop, 2→temporal, 3→open-domain, 4→single-hop gives single-hop n=997 0.5922/0.5607 (+0.031),
multi-hop 415 0.3641/0.3218 (+0.042), temporal 454 0.5502/0.4570 (+0.093), adversarial unchanged,
open-domain 92 0.2592/0.2351 (+0.024); ablation categories likewise (open-domain now a near-tie,
0.2365 vs 0.2351); "open-domain is LongMemEval-only" → LoCoMo-only; dead §5.1.4/G10b ref dropped.
**The labeler file itself is not changed here** (outside `paper/`). §6.5 "uniform hardware
(Hostinger 8 cores / 16 GB)" → hardware declared per run. §6.6: dataset sizes per run; per-category
transparency limited to nox-mem/Mem0; capped-smoke block: "nox-mem LoCoMo-only exceeds mem0 by +40%"
was LoCoMo vs mem0's aggregate — same-scope mem0 is 0.2631, nox-mem −30%; block compressed. §6.7:
smoke figures as above; abort attribution (the 51–97% CPU steal aborted the Wave 2 capstone, not a
canonical attempt) corrected here and in §6.3, §7.1 L5, §8; success criterion declared to carry no
evidential weight. §6.8 Table 2: nox-mem RSS ~341 MB (2026-05-24, ~62k chunks, not "6830 chunks
live") → ~399 MB (2026-05-29, 69,135 chunks), headline ~12× → ~10×, footnote rewritten. §6.9: 415 MB
(no artifact) → 399 MB; 6,822 count attributed to the rc4 artifacts.

*§7–§8 and footnotes.* L2 re-vectorization "30–40 min" (no artifact) and lower-case BYOK sentence
rewritten; L5/L6 abort and confound count fixed, L6 adds §6.3.4; L8 "91.74% at default pain"
(unsourced) → 89% in the E10 snapshot, and the variance-bottleneck reading withdrawn per
`E10-pain-calibration-test.md`; F1 rewritten (SQLCipher + signed chain implemented; offline verifier
not built); F2/F3 phase labels and dead §5.1.4 refs fixed; F4 vendor figures → EverMemOS paper
93.05/83.00, HyperMem 92.73 (new footnote `[^hypermem]`, arXiv:2604.08256v2); F5 now states the opt-in
MiniLM rerank already measured (−0.96 pp) and Nogueira & Cho's actual result (27% relative MRR@10),
model size ~66 MB → ~91 MB; F6 ~100k threshold marked unmeasured, "retention-based pruning" →
documented cleanup; F7 tokenizer corrected; Quati gets footnote `[^quati]`. §8: hybrid
"consistently outperforms single-method" → what was measured; additive salience "validated" →
supported (+1.3%, single run); G10d ref → supplement; EverOS/Zep runs added; success criterion "met,
but weakly". Footnotes: LightRAG venue, MeMo, geminiembed (now the arXiv:2503.07891 paper),
qwen3embed fifth author Xie → Lin, section refs of bm25/rrf/sqlitevec/minilm/locomo/hnsw/
reasoningbank/rmm/mirix/treemem/goldfish/memorybank, Generative Agents score is a sum not a product,
crystallize-src, salience-src line ranges, "32 arXiv-bearing footnotes" dated; CHANGELOG-rounds
sentence; "anonymized supplementary material" → "supplementary material".

*Mirrors.* `abstract.md`: SQLite stores, nox-mem/Mem0 split, EverOS sentence, F_MH 6.02% vs 10.84%
(its §2 block is 2,148+ characters, already above the 1,920 the §4 note claims — pre-existing,
not fixed here). Supplement: same statements corrected in place, listed in its new v1.0.3 part E
erratum. `refs.bib`: LightRAG venue, Gemini Embedding paper, MeMo, HyperMem, Clark & Gardner.
`bibitem-census.json`: +4 works (clarkgardner, hypermem, quati, gbrain), 55 → 59.
`authors-manifest.json` regenerated (56/56 IDs resolved). Mutation test: one anchor updated
(the bm25 footnote's section reference changed).
- Density: the corrections added ~2,200 words. Held above the floor by the four new footnoted
  works and by moving the three measurement paragraphs of §3.5 (diversity term D2) to
  `publication/supplement-operational-appendices.md` §S3.5, with a summary carrying the same numbers
  in §3.5, and compressing the §6.6 capped-smoke block. Density after (E): 59 works / 28,142 words
  = 2.097 per thousand. `claims_check.py`: 21 guards green; `claims_check_mutation_test.py`: 49
  mutations bitten. PDF 79 pages, MD5 `f849896d3aa4373dd3d423a2153e9d36`, uploaded to the Zenodo
  draft 23130276 (readback OK, not published).
- Not applied: the S10 request to fix `LOCOMO_CATEGORY_MAP` in `eval/q4-comparison/lib/category_labeler.py`
  and regenerate `output/rc4/_aggregate.md` (outside `paper/`; the paper now says so).

**(F) Final review and classical-QA/LoCoMo audit, 2026-10-04** (the 12 findings confirmed in
`paper2-interventional/_sprint-2026-10-04/noxmem-audit/REVIEW-FINAL.md`, from Kimi k3 and Codex
gpt-6-astra, plus the verified findings of audit slice S06 on §5.2–§5.4; apply log in
`noxmem-audit/APPLY-REPORT-F.md`).

*Review findings.* §8 said the pre-registered criterion "is met, but weakly"; §6.7 says it is not
reported as passed; §8 now follows §6.7. §5.3.2: the "+2.8 pp from the date-normalization knob" has
no artifact and credited the wrong mechanism; replaced by the measured session-date injection
(temporal F1 28.27% → 44.21%, +15.94 pp; +1.47 pp overall) with the normalizer stated as rejected
(`eval/locomo/RESULTS-LOCOMO-SOTA-PUSH.md`; `temporal_norm_enabled: false` in
`results/RESULTS-FULL-SOTA-PUSH-1986q.json`). Table 2 and footnote: LightRAG's default storage is
in-process (`JsonKVStorage`, `NanoVectorDBStorage`, `NetworkXStorage`, `JsonDocStatusStorage`;
`lightrag/lightrag.py`, `main`, read 2026-10-04): 1 service, RAM and cold start not estimated (was
2 services, ~1 GB, ~20 s). §7.1 L4: `withOpAudit()` no longer listed as covering consolidate
(§3.4.5 says it is not wrapped) or crystallize; the list is what the staged sources wrap.
§5.5.1: the fourth IterC gate is the latency gate (p95 3,688 ms ≤ 5,000 ms, PASS;
`RESULTS-Q3-ITERC-POC.md`). §5.5.2: the Fisher exact p = 0.48 is withdrawn (the 249 F_MH questions
are the same in both runs); the per-question pairing needed for McNemar is not archived, so no
McNemar p is reported; from the marginals (20 vs 15 correct, net 5) the exact two-sided McNemar p
is at least 0.0625 for any pairing; the paired per-batch CI [0.25, 3.76] that excludes zero is now
discussed. "D73" (§5.5.1) and "D2" (§3.5) removed. §5.1.9: MAP's +4.02 pp is against the
artifact's unweighted baseline 3.20% (+4.01 pp against 3.21%). §5.3.1: evidence hit@10 is not
a ceiling of token-F1. §5.7.2: the "$0/query … zero marginal retrieval cost" claim is restricted
to the KG path; the ingest row no longer says $0 for embeddings. §1.5: MemoryBank forgets and
reinforces per item (abstract, arXiv:2305.10250v3), not "uniformly". Preamble: latency in ms and
RSS are hardware-relative, not "machine-independent".

*S06 (§5.2–§5.4).* MuSiQue: each question's own 20 paragraphs in a fresh per-question store
(support_hit@20 99.96%), not a "full paragraph corpus"; IRCoT retrieves open-domain from 139,416
paragraphs (arXiv:2212.10509v2, App. A), so the IRCoT margin also reflects the setting; the two
"structural factors" (hybrid recall, RRF) removed, since retrieval returns nearly every candidate
(support_hit@10 99.88%); dev/test differences 0.8–5.0 points (arXiv:2108.00573v3 Tables 4–5), not
"about one point"; EX(SA) is not the baseline Beam Retrieval improved on (SA 52.3, RoHTmix 63.6 in
arXiv:2308.08973v2 Table 4); per-hop breakdown stated (2-hop margin ~1.5 points), no per-template
breakdown exists. HotPotQA: top_k=5 (not §5.2.1's 20), per-question 10-paragraph store, n = 7,405
(3 errors), source cell `eval/hotpotqa/RESULTS-HOTPOTQA.md` (was `audits/`); "order of magnitude"
dev/test claim removed; FE2H is rank 4 on the leaderboard (read 2026-10-02). LoCoMo: 10 public
conversations of 19–32 sessions (not "10-session"), not a "dev" split; top_k=20 requested, scored
at 10; table cells without artifact corrected (single-hop 71.40/84.13 → 80.36/92.03; temporal
68.94/82.31 → 77.96/84.74; overall adjacency-2 87.10 → 87.44; `eval/locomo/RESULTS-LOCOMO.md`);
multi-hop evidence recall@10 51.59% added and the "easier than EverMemBench" comparison withdrawn
(no retrieval metric on EverMemBench); the verbosity-gap attribution and the Mem0 "closes this
gap" claim replaced (constrained prompt already in the push; Mem0 Table 1 F1 per category only,
arXiv:2504.19413v1); §5.3.3 "route to >=55% is orchestration" → not measured; §5.3 heading no
longer says "competitive". §5.4: "100+ conversation turns" (absent from arXiv:2602.01313v3) →
the paper's own description; MAP cross-reference → §5.1.9 (section-bypass). `[^mem0]` lists §5.3.2.

*Mirrors.* `abstract.md` §2, `arxiv-metadata.txt` and `publication/techrxiv-metadata.md` now carry
one abstract of 1,824 characters (arXiv limit 1,920) that condenses the manuscript abstract
without new claims. Supplement `supplement-wave2-and-cross-backbone.md`: same statements corrected
in place (S5.3.3, §5.4 copy, §5.7.2, §5.8.5, Table 2 and its footnote), listed in its part F
erratum. Number changes are listed in `noxmem-audit/NUMBER-PARITY-v103E-to-v103F.md`.

**(G) Tone, provenance and pre-specification pass, 2026-10-04** (the 17 findings confirmed in
`paper2-interventional/_sprint-2026-10-04/noxmem-audit/REVIEW-FABLE.md`, with the verifier's fix
where it differs from the reviewer's; report in `noxmem-audit/APPLY-REPORT-G.md`). No measured
result changed; numbers were only moved, reworded, or removed when unsupported.

*A1 — Mem0 re-execution removed.* §6.3.2 (a) reported a replay against the preserved Mem0 store
(2,375 of 2,482 queries with identical top-10, mean overlap 9.83 of 10, nDCG@10 0.4446 against the
recorded 0.4337). Neither the script nor the per-query output exists in the repository, in the
lastro backup or in the session scratchpad that produced it (the scratchpad was deleted; the
transcript only names `replay-confound-a.py` and `replay-full.json`). The three numbers and the
"+0.011 bounds replication noise" sentence are cut; the version and parameterisation argument,
which rests on versioned artifacts, stays. The 2026-09-14 entry above keeps the history.

*A2 — product and advocacy wording.* §5.7.4 (observability layer) and §5.8.4 (search-error
monitoring) moved verbatim to `publication/supplement-operational-appendices.md` (§S5.7.4,
§S5.8.4); §5.8.5/§5.8.6 renumbered §5.8.4/§5.8.5 and the five references updated. §5.8.3 is one
sentence ("silent killer … core differentiator" gone). §5.1.7 "Verdict: REJECT as default. Ship
opt-in" → "Default: off; available behind a flag"; the "all other workloads do not" claim is cut.
§5.7.2: ratio column ("effectively free", "~667× cheaper", the 769× revision note) removed; the
Mem0 column is labelled as modeled, with the $0.001/call rate attributed to the reading recorded in
`RESULTS-PRODUCTION-SOTA.json` on 2026-05-29, which mem0.ai/pricing (read 2026-10-04) does not show
(the reviewer's proposed "$0.001/call read from mem0.ai/pricing" was **not** applied). §6.8 is now
Table 2 plus one neutral paragraph. §6.9 keeps the run observations and the dated scope note; the
"deployability penalty" paragraph and its table, the EverMind-AI note, the "Honest bound" paragraph
and the closing paragraph with the bold slogan are cut. Also: §2.5 "contract that makes nox-mem
composable" cut; §3.2 Notion sync / git auto-commit / SESSION-STATE steps replaced by one sentence;
§5.7.1 "the case for the local KG path"; §5.7.3 sidecar sentence; §6.3 "while delivering the
operational profile"; §6.3.3 "measured by us, published by us" and "the whole reason §6.8 exists";
§6.3.4 "honest in the direction that hurts us least"; §8 dashboard sentences; §5.8.5 "is marketing"
→ "a vendor figure without a stated percentile". The four census sites anchored in the cut §6.9
sentences (`penalidade-1286`, `bound-68a`, `bound-68b`, `bound-final`) were removed from
`q4-corridas-census.json` with a note; L5 completeness still sweeps the manuscript.

*A3 — internal status labels.* Headline box from 18 bullets to 6, each pointing to its own
section. "Lab Q1", "Wave 2", "F10", "Q3", WIN / PASS / FAIL / NO-REPLICATE / DOCUMENTED_INSUFFICIENT
/ INDETERMINATE / CLEAN replaced by plain words (gates "met" / "not met"; "the IterB composition
test"; "standalone knobs"); §5.1.6 "7/9 sub-dimensions WIN" → "above MemOS on seven of the nine"
(the Phase H v2 "WIN labels dropped" of part E had missed it). Run names the text defines (Wave A,
Wave B/C, Phase D/G/H v2, IterB, IterC, rc4) are kept. The quoted `"breakthrough"` in §5.8.2 is
kept on purpose: it is a quoted overclaim with its retraction in the same sentence, and the
`RETRATACAO` exemption and its mutation case depend on it.

*A4 — revision history moved out of the body.* Kept as short errata, because a DOI-published
number changed: §5.7.1 (653 ms, v1.0.2) and §6.4 (category table, v1.0.3). Moved here and cut
from the body: §5.1.3 "769 entity files × 3 sections ~ 2,307 chunks" and the "v1 paper draft"
remark; §5.3.2 the withdrawn table ranking nox-mem fifth (Zep 50.40%, LangMem 50.21%); §5.5.2 the
withdrawn Fisher p = 0.48 (part F); §6.3.2 (a) "Two earlier revisions … got this wrong", "used to
declare", "previously denied" (see the 2026-09-14 entry); §6.3.1 "we state this because the
repository is public", "disclosed rather than left for the reader to discover", "kept, dated,
because …" (×2), "Zero failures … not read away"; §6.6 the earlier "p50 + p95 + p99 explicit"
bullet; §8 the 15× extraction-yield figure of an earlier draft; Appendices note "named here rather
than silently dropped"; `[^hipporag2]` the two caveats on its missing locator (until 2026-09-09) and
wrong author names (until 2026-09-10; 3 of 32 arXiv footnotes then had wrong surnames under a green
check); `[^nox-mem-rss]` the "~50 MB [estimated]" origin and "initially denied" remark;
`[^everos-stack]` the "silently updating it would misdate" narration (the HTTP 404 fact stays, in
one sentence); `[^lightrag-stack]` "which an earlier revision counted as two services". §7.2 F6
keeps the dated ~95k record of 2026-06-04 (a corpus fact, and the `populacao_check` mutation case
needs a second population to bite).

*M1 — "pre-registered" → "pre-specified".* The plan `specs/2026-05-23-Q4-comparison-execution-plan.md`
is an internal execution document committed to the public repository before the first run, not a
registry entry; it names version ranges, treats the all-Gemini run as "side experiment" (l.142),
and its success criterion was the go/no-go gate for GTM Phase 2 (l.6, l.23). Title of §6, abstract,
§6.1, §6.2, §6.7 (now "Pre-specification", which also states the gate use) and §8 changed; the
all-Gemini variant is "a planned side experiment". Mirrored in `abstract.md`, `arxiv-metadata.txt`
and `publication/techrxiv-metadata.md` ("pre-specified (plan committed publicly before the first
run)"; 1,902 characters, limit 1,920) and in the V103 block of
`publication/zenodo-paper1/deposit-v103.py`, which now also rewrites "pre-regist*" in the inherited
v1.0.2 description and stops if any occurrence survives. The appeal letter never said
"pre-registered"; its evidence table row was updated.

*M3 — boost composition.* §4.1 now defines `score = base × (1 + Σδ)`, δ = w − 1, section weights
w ∈ {2.0, 1.5, 0.8} (1.0 without a section), salience δ ∈ [−0.5, +0.5], checked against
`staged/1.7a/edits/search.ts` (header l.19–20; `boostSum` at l.408–421). §2.5 "additive section and
source-type boosts" → "boost weights, summed as deltas (§4.1)"; §5.1.3 "multipliers" → "weights";
§5.7 and §8 no longer write the stack as `section_boost × source_type_boost × salience`. The
supplement copy of that formula (`supplement-wave2-and-cross-backbone.md`, verbatim block) is not
changed.

*M4 — §6.4 provenance.* New `paper/measurement/recompute-rc4-categories.py` recomputes the table
and the ablation figures from `eval/q4-comparison/output/rc4{,-ablation}/*.json` with the declared
map, re-deriving each LoCoMo bucket from `cache/raw/locomo10.json` and checking that every stored
label equals the old map of the native category (join check), then asserting the §6.4 values;
output `paper/measurement/out/recompute-rc4-categories.json` (all 15 cells and the five n match).
§6.4 now cites it; `category_labeler.py` is not changed.

*M5.* §5.1.7: provenance of the paired intervals (per-batch values in `RESULTS-PATHB-FULL.md`,
`RESULTS-PHASEG-5BATCH.md`, `results/analysis-phase{D,3}-batch-*.txt`), superseding that file's
"CI excludes 0", which compared levels. *M6.* "third of four" → "ranks third, behind EverOS and
nox-mem and ahead of Mem0" (abstract, §6.3.4, §8). *M8.* Table 2 keeps services and mandatory keys;
competitor RAM, cold start and setup steps moved to the supplement (§S6.8) as author's estimates;
the "~10× less RSS" headline is withdrawn; nox-mem setup counted as 2 commands. *M9.*
`[^everos]`: "The only memory-OS peer … publishes its own benchmark" and "§3.4 is the direct
narrative counter to EvoAgent framing" removed. *M10.* §3.4 retitled "Write-Side Maintenance:
Rule-Based Mechanisms"; the opening no longer says "promotes self-evolution to a first-class
subsystem", and "four mechanisms" (there are five subsections) is gone; §3.5 title "the read side".
*L1.* §2.3 column "Count (workspace store, early snapshot; not current)". *L2.* "Every deployment
that enables embeddings supplies its own Gemini API key". *L3.* §5.1.2 now cites
`docs/audits/2026-05-19-salience-distribution-audit.md` for 99.7%, 90.67% and 99.76% (its l.105, l.26, l.79). *L5.* §2.5:
determinism restricted to `search` and the temporal filter; `answer` calls an LLM. *L7* (in A2) and
*L9* (in M8) applied.

Words: 28,623 → 26,091; reference density 2.061 → 2.261 per thousand (floor 2.06, ceiling 2.95).
`claims_check.py`: 21 guards pass; `claims_check_mutation_test.py`: 49 mutations bitten. The PDF
in `paper/build/` and the Zenodo draft 23130276 were **not** rebuilt or touched: they still carry
part F (MD5 `05335e7afc3819532cb86278752ef05f`).

*Mechanical check after (G), 2026-10-04* (independent check; wording, placement and formatting
only, no measured result changed). Two headings rendered as literal text because no blank line
preceded them (§5.2 and §7.2 F3; the check reports both as present since v1.0.2); the Zep
paragraph of §6.3.1 merged into the Letta bullet; §6.3.1 announced three gaps but listed two, so
the EverMind-AI bullet is restored, with the barrier text moved into it from the paragraph below;
§5.1.8 listed "adjacent-chunk inclusion" where the knob is the adaptive query classifier (AC);
a misplaced sentence at the end of §5.1.7 removed (§5.1.8 already points to §5.1.9); "(§S5.x.)"
→ "(§S5.x)." ×4; §5.4 column "Verdict" → "Position vs references"; "ship/reject", "autonomy
axis", "product-planning", "still a win but a different narrative", "overclaimed in print" and
the "honest" labels (§5 intro, §5.8, §5.8.4, §5.8.5, §6.3) reworded; bold removed from the §1
design-principle phrase and from a standalone line in §6.3.1; footnote heading "Operational-cost
table (Table 2) sources" → "Table 2 sources"; §6.4 no longer says "the three §6.3.1 gaps"; the
§5.3.2 row of the summary table drops "verbosity-constrained"; §5.1.10 cites §5.5.4–§5.5.6, not
–§5.5.8. The δ of §4.1 and §5.1.3 was silently dropped by the PDF font (7 "Missing character"
warnings); it is now written in math mode, and the build has 0 glyph warnings. `abstract.md`
checklist and `arxiv-metadata.txt` header brought in line (task-type ablation does not attribute
the lead to the architecture; 1,902 characters; 4 head-to-head + 1 non-run). Density 59 works /
26,096 words = 2.261. `claims_check.py`: 21 guards pass; mutation test: 49 bitten. PDF rebuilt
(73 pages, 318,365 B, MD5 `207e02545b3f5a4619789df11374aaf1`) and uploaded to the Zenodo draft
23130276 by `deposit-v103.py`, whose V103 block now summarizes parts A–G (readback OK, not
published).

*Scoped regression review of (G), 2026-10-04* (Codex, receipt
`.remember/adversary-receipt-codex-2026-10-04T175005-5803.txt`, exit 0; question limited to errors
introduced by (G)). Three confirmed and fixed, no measured result changed: (1) §2.5 said search and
the temporal filter are deterministic for a given store and query; ranking uses time-dependent
signals and hybrid search can call LLM query expansion, so only temporal filtering at a resolved
cutoff is deterministic; (2) §3.4.3 placed the salience delta "on top of RRF", contradicting the
new §4.1 definition and the code (`staged/1.7a/edits/search.ts`: `salienceDelta` enters each
layer's `boostSum` before fusion); (3) §6.1 and §6.7 dated the first run 2026-05-24, but §6.6
reports a capped smoke on 2026-05-23; the plan was first committed on 2026-05-21 (`git log
--follow`), so the text now gives both dates.

- Not yet done (author's action): publishing the Zenodo version under concept DOI
  `10.5281/zenodo.22649268`; README badge and `CITATION.cff` still point at v1.0.2 until
  that deposit exists.

## Roadmap rumo à v1.0.0 (evoluir-antes-de-publicar)

| rc | Incremento | O que agrega ao paper | ETA | Custo |
|---|---|---|---|---|
| ~~**rc2**~~ ✅ **DONE (2026-06-29)** | §6.4 per-category breakdown | ✅ preenchido pela run rc4 (full set categorizado → aggregate per-category). nox supera o mem0 nas 5 categorias. | — | feito junto do rc4 |
| **~~rc3~~ ❌ DROPPED** | ~~Claude backbone~~ | **Cortado 2026-06-28** (Toto: não pagar Anthropic; Max OAuth = policy violation, bloqueado — ev `RESULTS-BACKBONE-MATRIX.md:154-157`). Paper já tem 2 backbones (gpt-4.1-mini + Gemini-3-flash) → tese backbone-agnostic sustentada. Config `pipeline-backbone-claude.yaml` fica pronta caso reative com modelo **grátis** (OpenRouter free / local). | — | $0 (não roda) |
| ~~**rc4**~~ ✅ **DONE (2026-06-29/30)** | all-Gemini fair variant | ✅ ambos @ Gemini 3072d, full n=2.482. **Inverteu o split: nox supera o mem0 nos dois** (LME +0.119, LoCoMo +0.055). §6.3.2. 3 confounds residuais declarados; task-type **ablacionado e neutralizado** (06-30: nox genérico ainda ganha, −0.34 pp). | — | ~$2 Gemini prepaid |
| **v1.0.0** ← **próximo** | sweep claims + polish + submit | audita abstract-claims vs conteúdo, rebuild `.pdf`/`.docx`, submit arXiv | ½ dia | — |

> Recheck antes de rc2/rc4: confirmar se os resultados raw da canonical run 06-15 sobreviveram (pod dedicado já terminado) — se não, re-rodar n=100×2×3 do zero.

---

## Progresso — 2026-06-28 (prep paralela, pré-execução)

Recheck por evidência primária (filesystem + §6 do paper) + 3 agentes de prep em paralelo. **Prep das 3 rcs 100% pronta e validada; execução 100% bloqueada em compute (pod RunPod stopado, sem meu acesso ao RunPod).**

**Achados que mudam o plano:**
- **Raws 06-15 NÃO estão locais** (todo `cache/` é de 23-24 mai). Viviam no pod dedicado (terminado) → rc2/rc4 são **re-run**, não reprocessamento.
- **rc2 não era reprocessamento de qualquer forma:** §6 (linha 1121) confirma que a run 06-15 só produziu métricas **dataset-level**. Per-category exige labels novos + re-run.
- **rc3 NÃO é $0** (ver tabela acima). Max OAuth bloqueado; precisa API key paga.

**Prep entregue (commitada, validada py_compile/yaml/sh):**
- **rc2** — `lib/category_labeler.py` + `scripts/build_categorized_queries.py` + `docs/rc2-per-category-mapping.md`. Mapeamento dos campos NATIVOS (LoCoMo `category` 1-5; LME `question_type`) → 6 buckets §6.4. Distribuição medida. **3 células n/a legítimas** (LoCoMo×numeric, LME×open-domain, LME×numeric). 1 ambiguidade documentada (`knowledge-update`→adversarial — precisa footnote no paper). ⚠️ rodar **sem `--limit`** (full), senão sub-amostragem cria n/a falsos. Queries categorizadas geradas em `cache/queries-*-categorized.jsonl` (gitignored, reproduzíveis).
- **rc3** — `pipeline-backbone-claude.yaml` + `run-batch-backbone-claude.sh` + `RESULTS-BACKBONE-CLAUDE.md`. ⚠️ incerteza de endpoint: `api.anthropic.com/v1/chat/completions` + `Authorization: Bearer` (OpenAI SDK) pode não ser compat — fazer curl smoke antes do 5-batch (fallback OpenRouter no yaml).
- **rc4** — `docs/rc4-all-gemini-plan.md` + `lib/all_gemini_config.py`. nox+mem0 dão; **agentmemory NÃO** (embedder server-side → vira limitação documentada no §6). ⚠️ eval usa **768d**, prod usa 3072d — rc4 é fair inter-sistemas mas não fiel ao prod (caveat pro paper). Custo re-ingest ~$0,60.

**Pivot 2026-06-28 (decidido com Toto):** rc3 **dropado** (sem custo $0 possível). rc2+rc4 vão rodar **local no Mac, sem pod** — recheck mostrou que são retrieval leve (CPU + API Gemini), n=100; o pod 06-15 era só anti-CPU-steal da VPS. Setup local em andamento:
- ✅ `mem0ai` + `chromadb` instalados na venv py3.14 (wheels nativos cp314 — risco descartado).
- ✅ nox-mem DB local existe (`cache/nox-mem-eval.db`).
- ⏳ **bloqueador atual: `GEMINI_API_KEY`** não está no ambiente do Mac (pra re-query/re-ingest de embeddings). Aguardando Toto fornecer via `.env.local` gitignored (eu nunca vejo nem comito o valor).
- ⏳ agentmemory (só pro rc2 completo, 3 sistemas): precisa subir daemon npm iii-engine (:3111). rc4 (nox+mem0) não precisa.
