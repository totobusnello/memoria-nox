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
(§6.3.4, #534); confounds 3 → 4 and the density guard (#535); TMLR template and
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

### v1.0.3 — 2026-10-03 (generative-AI disclosure; product framing removed)

Prepared for the arXiv appeal of `submit/7771319`. Form and framing only: no result,
measurement, citation or scientific claim changed.

- **Added: "Disclosure of Generative AI Use"**, an unnumbered section after the
  Conclusion. arXiv's moderation policy asks authors to report significant use of
  text-to-text generative AI; v1.0.2 had no such statement. It ends with an author
  confirmation marker that must be resolved before deposit.
- **Product/roadmap framing removed (pacote b1):** the D43 "approval gate" and
  "GTM Phase 2" language in §6.1, §6.6, §6.7, §7.2 F1/F6/F7/F8 and the Conclusion; the
  gate annotation labels (D43, D48, D51, D67, D68, D69) in §5.7.4. The pre-registered
  criterion itself (top-3 on >=2 of the 4 key metrics) stays, in §6.1, §6.7 and the
  Conclusion, now named as a success criterion. F8 is retitled "Feedback from use
  outside the author's deployment".
- **Abstract (b2):** tagline sentence and "no vendor lock-in" removed; MIT license and the
  production envelope (since March 14, 2026, six agents, 2.5 ms, $0, 399 MB) kept.
- **Labels (b3):** §6 heading "Q4 COMPARISON" → "Cross-System Comparison
  (Pre-registered)"; §5.1.3 "is the moat" → "accounts for 99.85% of the gain"; §6.8
  "Autonomy quantified" and every "Autonomy pillar" / "Q/A/P" reference neutralised; the
  `[^q-a-p-pivot]` footnote removed (it was `evidencia`, not `obra`: 55 works and the
  density are unchanged; `bibitem-census.json` updated). File paths containing `q4`
  are unchanged.
- **Form defect (b4):** the empty duplicate "### 6.8 Operational cost" heading removed.
- **Scope (b5):** §1.3 no longer lists the agents' names (they remain in the §2 data
  table); the third Conclusion paragraph rewritten without "institutional learning" /
  "agent organization" phrasing, pointing at §4.3.
- **Number parity, v1.0.2 → v1.0.3 (multiset of numerals in the `.md`):** removed only
  the version/date (1.0.2, 2026-09-29), the internal labels D43 ×6, D48/D51/D67/D68/D69,
  "Q4" ×4, "rc4" ×1 (F8), "Phase 2" ×7, the gate restatement in F8 (top-3 / 2 / 4 /
  nDCG@10 / R@10), the footnote date 2026-05-17, and the duplicate "6.8"; added only
  1.0.3, 2026-10-03 and the cross-references §6.7 ×2 and §4.3. Spelled-out numbers:
  "three" (footnote) and "zero" (L2, "zero vendor lock-in") removed; "two" ×2 added
  (disclosure). In the PDF, footnote numbering shifts by one after the removed footnote.
- `claims_check.py`: 21 guards green; `claims_check_mutation_test.py`: 48 mutations bitten.
- Not yet done (author's action): Zenodo version under concept DOI
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
