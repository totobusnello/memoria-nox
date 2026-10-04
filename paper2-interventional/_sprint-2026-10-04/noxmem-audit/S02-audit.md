# S02 audit — §1.1–§1.4 (paper-tecnico-nox-mem.md v1.0.3, lines 22–77)

Fast pass (o usuário pediu rapidez). Fontes abertas listadas por achado.

## Achados

1. HIGH — linha 53: "§6 explains why only two of them (Mem0 and agentmemory) could be brought to a same-corpus comparison at all".
   - agentmemory não é um dos "other six systems" da Tabela 1 (mem0, Letta, Zep, EverOS, LightRAG, MeMo).
   - Linha 1279 (§7) e abstract (linha 18): EverOS e Zep "both swept over the full n=2,482 set on 2026-09-10 … reported in §6.3.3". Logo, da tabela, três (mem0, Zep, EverOS) chegaram a comparação same-corpus.
2. HIGH — [^memo] (linha 1370) + §1.4: arXiv 2605.15156v2 aberto em https://arxiv.org/abs/2605.15156v2 → título "MeMo: Memory as a Model", Quek et al. (9 autores); abstract: "encodes new knowledge into a dedicated memory model while keeping the LLM parameters unchanged". O footnote dá outro título ("Towards Language Models with Associative Memory Mechanisms") e o texto diz "folds reflections into model weights via continued pretraining" — nada de reflections nem de pesos do LLM. Footnote também diz "§1.4, abstract": o abstract não cita MeMo (grep).
3. MEDIUM — linha 43: "spans roughly three families" seguido de (i)–(iv) = quatro.
4. MEDIUM — linha 43: "**memanto**" sem footnote/locator; grep em paper e refs.bib: só esta ocorrência. Referência irresolvível.
5. MEDIUM — linha 43: EverOS "the only memory OS in this space that publishes its own benchmark dataset (EverMemBench) and reports threshold numbers". Letta (cuja paper MemGPT se apresenta como "LLMs as Operating Systems") publica Context-Bench (https://www.letta.com/blog/context-bench/, leaderboard.letta.com). "threshold numbers" = jargão indefinido. EverMemBench = arXiv:2602.01313 (Hu et al.), divulgado por EverMind (LinkedIn ai-evermind) — atribuição em si ok.
6. MEDIUM — linha 73: provenance "(§3.3)" — §3.3 é Deduplication (linhas 361–367), sem chunk_id/source_file/ops_audit. Provenance fields estão em §2.5 (Primitive 1) e withOpAudit/ops_audit em §3.4.1 (linha 375).
7. LOW — linha 43: Reflexion → "reflection artefacts our `crystallize` path persists (§2.5)". §2.5 só lista crystallize como verbo; crystallize (§3.4.1) promove pending→lesson; reflexão é o reflect pipeline (§3.4.4).
8. LOW — linha 43 e [^lightrag]: "EMNLP 2025". ACL Anthology 2025.findings-emnlp.568 → Findings of ACL: EMNLP 2025.

## Verificado sem defeito
- §1.3 "6 AI agents … 4 vCPUs and 8GB RAM" = preâmbulo (linhas 8–9).
- 2-second debounce: §3.1 linha 332.
- §3.4.3 cobre retention_days → recency no salience (linhas 381–398).
- Lost in the Middle, Reflexion, A-Mem, HaluMem: descrições compatíveis com títulos/locators dos footnotes (não reabri os PDFs).
- Células da Tabela 1 para sistemas terceiros: NÃO verificadas célula a célula (fora do tempo); a tabela já se declara "as documented".
