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

---

## Roadmap rumo à v1.0.0 (evoluir-antes-de-publicar)

| rc | Incremento | O que agrega ao paper | ETA | Custo |
|---|---|---|---|---|
| **rc2** | §6.4 per-category breakdown | preenche a tabela §6.4 (hoje 100% `[deferred]`); mostra onde nox vence/perde por tipo de query | ½–1 dia | re-run pod (raws 06-15 provavelmente perdidos) |
| **rc3** | Claude Sonnet 4.6 / Opus 4.7 backbone | 3ª coluna na matriz de backbone (gpt-4.1-mini → Gemini-3-flash → **Claude**); tese de robustez backbone-agnostic | 1 dia | **~$42 Sonnet / ~$200 Opus (PAGO).** ⚠️ Max OAuth NÃO serve: bench automatizado via token Max = violação de policy, já bloqueado pelo classifier (ev: `eval/evermembench/RESULTS-BACKBONE-MATRIX.md:154-157`). Requer `ANTHROPIC_API_KEY` de billing. |
| **rc4** | all-Gemini fair variant | controla o confound de embedding no §6 (hoje nox=Gemini 3072d vs Mem0=OpenAI 1536d) — comparação mais limpa | 1 dia | re-ingest. ⚠️ risco: pode reverter o split |
| **v1.0.0** | sweep claims + polish + submit | audita abstract-claims vs conteúdo, rebuild `.pdf`/`.docx`, submit arXiv | ½ dia | — |

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

**Bloqueio único de execução:** todas as 3 precisam do **pod RunPod de volta** (rc2/rc4 = Q4; rc3 = EverMemBench). Sem isso, nada roda. Decisões pendentes do Toto: (1) subir pod + me dar acesso; (2) autorizar gasto rc3 (~$42 Sonnet) e qual modelo; (3) aceitar caveat 768d do rc4.
