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
| **rc3** | Claude Sonnet 4.6 / Opus 4.7 backbone | 3ª coluna na matriz de backbone (gpt-4.1-mini → Gemini-3-flash → **Claude**); tese de robustez backbone-agnostic | 1 dia | **$0 via Max OAuth** |
| **rc4** | all-Gemini fair variant | controla o confound de embedding no §6 (hoje nox=Gemini 3072d vs Mem0=OpenAI 1536d) — comparação mais limpa | 1 dia | re-ingest. ⚠️ risco: pode reverter o split |
| **v1.0.0** | sweep claims + polish + submit | audita abstract-claims vs conteúdo, rebuild `.pdf`/`.docx`, submit arXiv | ½ dia | — |

> Recheck antes de rc2/rc4: confirmar se os resultados raw da canonical run 06-15 sobreviveram (pod dedicado já terminado) — se não, re-rodar n=100×2×3 do zero.
