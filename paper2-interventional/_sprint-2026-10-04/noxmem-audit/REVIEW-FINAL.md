# REVIEW-FINAL — verificação das vozes Kimi e Codex sobre o manuscript v1.0.3 (2026-10-04)

Alvo: `paper/paper-tecnico-nox-mem.md` (1.487 linhas, working tree). Nada foi editado.

## Validade das vozes
| voz | recibo | exit | duração | output_bytes | válida |
|---|---|---|---|---|---|
| Kimi k3 | `paper/.remember/adversary-receipt-kimi-2026-10-04T070949-6334.txt` | 0 | 881 s | 108.009 | sim |
| Codex gpt-6-astra | `paper/.remember/adversary-receipt-codex-2026-10-04T070938-5934.txt` | 0 | 569 s | 628.780 | sim (recibo), mas 4 dos 7 achados "altos" caem no grep ou no artefato |

## Confirmados (12), por severidade
1. **MEDIUM — §6.7 × §8 contradizem-se** (Kimi 1 + Codex 21). L1183: "We therefore do not report the criterion as passed"; L1316: "is met, but weakly". Fix: alinhar o §8 ao §6.7.
2. **MEDIUM — "+2.8 pp" da date-normalization sem artefato** (Codex 13). L731. `eval/locomo/RESULTS-LOCOMO-SOTA-PUSH.md` L29/L34/L41-42/L77: o que entrou foi session-date injection (temporal 28,27→44,21%, +15,94 pp; overall +1,47 pp); o normalizer foi REJEITADO (smoke temporal: 51,54% com norm ON contra 54,61% com OFF). Nenhum "2.8 pp" em `eval/locomo/*.md` nem em `audits/`. Fix: trocar pelos números medidos e atribuir o ganho à injeção.
3. **LOW-MEDIUM — LightRAG "2 (Neo4j + vector DB)" está errado** (Codex 7, só a parte do LightRAG). L1198 + nota L1371. `raw.githubusercontent.com/HKUDS/LightRAG/main/lightrag/lightrag.py` L696-705: defaults `JsonKVStorage`, `NanoVectorDBStorage`, `NetworkXStorage`, `JsonDocStatusStorage`, todos in-process. A parte sobre o Mem0 não foi verificada.
4. **LOW-MEDIUM — cobertura do `withOpAudit()` contraditória** (Codex 16). L412: consolidation "is not currently wrapped in `withOpAudit()`"; L1257: o wrapper "targets destructive bulk operations (reindex, consolidate, crystallize)". Fix: tirar consolidate da L1257.
5. **LOW — o veredito "2/4" do IterC não se reconstrói pela tabela** (Kimi 2). L766-777. A 4ª gate é a de latência: `eval/evermembench/RESULTS-Q3-ITERC-POC.md` L31, "Latency p95 ≤ 5000ms | 3688ms | PASS". Fix: rotular a linha de custo/latência "(gate ≤ 5,000 ms: PASS)".
6. **LOW — significância do IterB** (Kimi 3 + Codex 9, juntos). L785: o CI pareado por batch [0.25, 3.76] exclui zero e o texto não trata disso; além disso, "20 vs 15 correct of 249" são as mesmas 249 perguntas, então o Fisher exact trata dado pareado como independente (o certo seria McNemar). Não recalculei: precisa das respostas por pergunta.
7. **LOW — sobrou "D73"** (Kimi 4). L781 "(decision D73, …)", enquanto o CHANGELOG L176 diz "all of them are gone". Fix: descrever a decisão sem o código.
8. **VERY LOW — linha MAP standalone** (Kimi 5). L621: 7.22% com +4.02 pp contra a baseline de 3.21%, que dá 4,01. O artefato `RESULTS-PHASEMAP-5BATCH.md` L40 usa baseline 3.20%. Fix: nota de arredondamento.
9. **LOW — "ceiling" do retrieval@10** (Codex 12). L714/L725: hit da evidência anotada@10 não é teto do token-F1, porque a resposta pode vir de evidência não anotada. Fix: "observed annotated-evidence hit rate@10".
10. **LOW — "zero marginal retrieval cost"** (Codex 18). A L874 afirma isso incondicionalmente e, no mesmo parágrafo, dá o custo do hybrid em $0.0000015/query. Fix: restringir ao KG path.
11. **LOW — MemoryBank "applied uniformly"** (Codex 15). L164-165. O abstract em arxiv.org/abs/2305.10250 diz "forget and reinforce memory based on time elapsed and the relative significance of the memory", ou seja, por item. Fix: reformular o contraste.
12. **VERY LOW — "machine-independent terms (latency percentiles, resident set size…)"** (Codex 21, parte). L13-14: latência em ms e RSS dependem do hardware. Fix: "hardware-relative".

## Rejeitados (14)
- **Kimi 6:** "which is the case for the local KG path" (L863) é o idioma "the case for" (= argumento a favor). É questão de estilo.
- **Codex 3:** o 0.6455 do EverOS vem de `eval/q4-comparison/output-2026-09-10/_aggregate.json` (overall ndcg@k = 0.64553667642804). O 0.6375 que o Codex cita é o `score` de um chunk recuperado (`evermind.json` L71687), não uma métrica de benchmark.
- **Codex 4:** a citação "55.74" não aparece no manuscript (0 ocorrências).
- **Codex 2:** a citação "v0.1.114" não aparece no manuscript (0 ocorrências).
- **Codex 6:** o +9.13 pp tem margem de 7 pp sobre o limite inferior do CI, e a diferença de população (2.733 × 2.400) já está declarada na L650. O que sobra é wording.
- **Codex 1, 5, 8, 10, 19, 20:** vagos ou sem citação localizável ("unchanged" não aparece no sentido alegado). O próprio Codex diz que o rc4 sobrevive ao bootstrap por conversa.
- **Codex 11:** a premissa "remover documentos" está errada; a ablação troca só o task type (L1048).
- **Codex 14:** a atribuição do hypergraph ao EverOS (L68) não foi verificada em fonte primária, logo não é verificável aqui.
- **Codex 17:** os ~16 min/query do Letta (L1006/L1228) não foram verificados contra artefato, logo não são verificáveis aqui. Fica a sugestão de checar se esse número existe em algum artefato.
- **Codex 21, partes:** "2,482" para o LoCoMo não aparece (o LoCoMo usa 1,982: L1037/L1065/L1088). A observação sobre o cross-encoder é vaga.

## Veredito
Nada bloqueia. O veto do Codex não se sustenta: 4 dos 7 achados "altos" caem no grep ou no artefato. Restam 12 correções pontuais, e as duas médias (§6.7×§8 e o +2.8 pp sem artefato) têm de entrar antes de congelar.
