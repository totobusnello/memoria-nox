# S03 — §1.5 Related Work (audit, 2026-10-04)

Fonte: paper/paper-tecnico-nox-mem.md (linhas 79–218 = §1.5; footnotes 1362–1475).
Pedido do Toto: rápido. Escopo efetivamente coberto abaixo; o que não foi aberto está declarado.

## Fontes externas abertas
- WebCoach arXiv:2511.12997v2 (abs) — "enabling ... continual learning without retraining"; Coach "retrieves relevant experiences based on similarity and recency, and decides whether to inject task-specific advice". Sem componente treinado.
- ReasoningBank arXiv:2509.25140v2 (abs) — memória destilada de experiências auto-julgadas; recuperada em test time; sem treino. Comments: "Accepted to ICLR 2026" (venue do footnote confere).
- Generative Agents arXiv:2304.03442v2 (PDF) — "score = a_recency·recency + a_importance·importance + a_relevance·relevance ... all [alphas] set to 1". Soma ponderada, não produto.
- LongMemEval arXiv:2410.10813v2 (HTML §2) — MSC (Xu et al. 2022a) aparece só como benchmark anterior na tabela comparativa; nada diz que LongMemEval deriva do setup do MSC.

## Artefatos internos lidos
- staged/1.7a/edits/salience.ts:45-78 — DEFAULT_RETENTION_BY_TYPE feedback:0, person:0; NULL na coluna -> default do tipo; never-decay = retention_days <= 0.
- Paper §2.3 (l.276) — só taxonomia; sem retenção, sem entity files.
- Paper §3.4 (l.369-407) — "four cooperating mechanisms"; §3.4.4 reflect = batch nightly synthesis que ESCREVE chunks; §3.4.5 consolidate noturno roda reflect e crystallize.
- Paper §3.5 (l.411) — "The mechanisms above are write-side".
- Paper §7.1 (l.1255-1290) — nenhuma menção a ~100k; a menção está em §7.2 (l.1314), como limiar NÃO atingido (67.724 chunks).
- Paper §5.4 (l.745-767) — atribui F_MH a task setup como "leading account"; não mede o custo do KG path.

## Achados
1. [medium] §7.1 -> §7.2 e "binding constraint" exagera (§7.2 diz limiar não atingido). Footnote hnsw repete "§7.1".
2. [high] WebCoach: "advice is produced by a trained component" — fonte diz "without retraining".
3. [medium] "Self-evolution: ... without a training loop" + "rather than triggered by a trained policy": ReasoningBank também é training-free; o contraste só vale para RMM (retrospective RL).
4. [medium] reflect "(§3.4.2)" -> §3.4.4; e "read-side ... synchronous call over already ranked chunks" contradiz §3.4.4 (batch noturno que escreve chunk) e §3.5 (write-side).
5. [medium] "crystallize is invoked by the operator" contradiz §3.4.5 (consolidate noturno roda crystallize).
6. [medium] "self-evolution limited to two operator-invoked primitives (§3.4)" contradiz §3.4 (quatro mecanismos, nightly).
7. [medium] "Nothing here adapts" / "pain is assigned by the operator" contradiz §3.4.2 (pain drifts upward implicitly) e access_score (peso 0.20, §3.4.3).
8. [low] "no learned component anywhere in the loop" — consolidação usa Ollama llama3.2:3b (§3.2), crystallize/reflect usam Gemini (§3.4.1/§3.4.4). O que falta é componente TREINADO para a tarefa.
9. [medium] "§5.4 quantifies that price" — §5.4 não atribui F_MH ao KG path.
10. [medium] footnote genagents "recency × importance × relevance" — GA é soma ponderada (PDF v2).
11. [low] "typed retention windows per chunk_type (§2.3), with NULL meaning never-decay" — §2.3 sem retenção; código/footnote: never-decay = 0, NULL = default do tipo.
12. [low] "entity files (§2.3)" — §2.3 não descreve entity files; formato aparece em §5.1.3.
13. [low] LongMemEval "descend from" MSC — não suportado pela fonte.

## Não verificado (declarado)
Venues de memsurvey (TOIS 2025), selfevolsurvey (TMLR 2026), MemAgent (ICLR 2026), MemSearcher (ACL 2026), HippoRAG 2 (ICML 2025), LightRAG (EMNLP 2025); descrições de Mem-α, Memory-R1, MEM1, Memory as Action, ACON, MIRIX, treemem, MemoryBank, Mallen et al. — não reabertas nesta passada (pedido de rapidez). Nenhum veredito emitido sobre eles.
