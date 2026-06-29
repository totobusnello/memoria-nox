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

- **§6.3.2 nova — controlled-embedding:** ambos os sistemas em `gemini-embedding-001` @ **3072d** (não 768d — preflight refutou a premissa do plano original, commit `a6e7e4d`; medido nox=3072 / mem0=3072 com a key real). **nox-mem lidera os dois**: LongMemEval 0.5255 vs 0.4061 (+0.119); **LoCoMo 0.4952 vs 0.4407 (+0.055) — inverte** o split as-configured do §6.3. Overall 0.5013 vs 0.4337.
- **§6.4 per-category preenchido** (era 100% `[deferred]`): nox-mem lidera as 5 categorias representadas; maiores margens em **adversarial** (+0.142) e **temporal** (+0.118), menor em single-hop (+0.006); `numeric` = n/a (n<10). Consistente com a tese §5 (vantagem vem da fusão multi-sinal, não só do embedding).
- **Confounds residuais declarados** (§6.3.2, per §6.6): (a) mem0 mudou de 0.1.x→2.0.10 entre a canonical e o rc4 (exigiu fix de compat na API `search`/`get_all`) → 0.4337 ≠ o mem0 0.4686 do §6.3; (b) task_type assimétrico a favor do nox (nox usa `RETRIEVAL_*`, mem0 não). rc4 ≠ isolamento de arquitetura puro.
- **Abstract `[Q4 NUMBERS]` preenchidos** (split as-configured + controlled) em `abstract.md` e `arxiv-submission-ready.md`.
- **Tese atualizada (não substituída):** §6.3 mantém o split honesto as-configured; §6.3.2 mostra que sob embedding controlado a vantagem do nox é robusta (lidera ambos). As duas leituras coexistem — mais defensável que apagar o split.
- **Infra — 4 bloqueadores de execução corrigidos:** `_self_check` 768→3072 (import quebrado), `google-genai` faltante (mem0 embedder), `runner_rc4.py` criado, mem0 2.0.10 `search`/`get_all` API. Smoke validado (dims 3072=3072, gold-match 100% nos dois datasets, billing path exercitado). Raws: `eval/q4-comparison/output/rc4/_aggregate.{json,md}`.

---

## Roadmap rumo à v1.0.0 (evoluir-antes-de-publicar)

| rc | Incremento | O que agrega ao paper | ETA | Custo |
|---|---|---|---|---|
| ~~**rc2**~~ ✅ **DONE (2026-06-29)** | §6.4 per-category breakdown | ✅ preenchido pela run rc4 (full set categorizado → aggregate per-category). nox lidera as 5 categorias. | — | feito junto do rc4 |
| **~~rc3~~ ❌ DROPPED** | ~~Claude backbone~~ | **Cortado 2026-06-28** (Toto: não pagar Anthropic; Max OAuth = policy violation, bloqueado — ev `RESULTS-BACKBONE-MATRIX.md:154-157`). Paper já tem 2 backbones (gpt-4.1-mini + Gemini-3-flash) → tese backbone-agnostic sustentada. Config `pipeline-backbone-claude.yaml` fica pronta caso reative com modelo **grátis** (OpenRouter free / local). | — | $0 (não roda) |
| ~~**rc4**~~ ✅ **DONE (2026-06-29)** | all-Gemini fair variant | ✅ ambos @ Gemini 3072d, full n=2.482. **Inverteu o split: nox lidera ambos** (LME +0.119, LoCoMo +0.055). §6.3.2. Confounds residuais (versão mem0, task_type) declarados. | — | ~$2 Gemini prepaid |
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
