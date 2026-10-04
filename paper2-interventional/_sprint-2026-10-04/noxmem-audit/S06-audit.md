# S06 audit — §5.2 / §5.3 / §5.4 (paper-tecnico-nox-mem.md, lines 654–767)

Data: 2026-10-04. Escopo: §5.2 MuSiQue/HotPotQA, §5.3 LoCoMo, §5.4 F_MH paradox. Contexto lido: Abstract.
Sem git, sem Zenodo, sem contato.

## Fontes abertas
- eval/musique/RESULTS-MUSIQUE.md (+ adapter_nox_mem.py linhas 6-18: corpus POR PERGUNTA de 20 parágrafos; top_k=20)
- eval/hotpotqa/RESULTS-HOTPOTQA.md / .json ("top_k": 5) + adapter_nox_mem.py (linha 5: distractor 10 parágrafos/pergunta; linha 83 DEFAULT_TOP_K = 5)
- eval/locomo/RESULTS-LOCOMO.md (linhas 189-201: hit@10 strict/adj), RESULTS-LOCOMO-SOTA-PUSH.md
- eval/evermembench/RESULTS-BACKBONE-MATRIX.json (F_MH gpt-4.1-mini 3.21; gemini-3-flash 6.02)
- paper/publication/supplement-wave2-and-cross-backbone.md §S5.3.3
- arXiv 2602.01313v3 HTML (EverMemBench Table 4), 2504.19413v1 HTML (Mem0 Tables 1-2),
  2402.17753 abs (LoCoMo), 1809.09600 HTML (HotpotQA), 2007.01282 HTML (FiD), 2004.04906 abs (DPR),
  2308.08973 abs v2 (Beam Retrieval; só abstract — Tables 4/5 NÃO reabertas, ficam "não reverificadas").

## Achados (resumo)
H1 MuSiQue: corpus é por pergunta (20 parágrafos) e top_k=20 => recupera tudo; texto diz "full paragraph corpus" e atribui ganho a recall/RRF.
H2 HotPotQA: artefato usa top_k=5 sobre 10 parágrafos/pergunta; texto diz "same config as §5.2.1" (top_k=20) e "full corpus".
H3 LoCoMo: 66.88% do Mem0 é LLM-as-a-Judge J overall (Mem0 Table 2), não F1; Mem0g 68.44 é maior. Zep 50.40 / LangMem 50.21 não aparecem no Mem0 paper (que não reporta F1 overall); paper os rotula "replication / internal measurement", artefato os atribui a Chhikara 2025. Linhas ~60/~55/~52 sem artefato.
H4 LoCoMo retrieval table: single-hop 71.40/84.13, temporal 68.94/82.31, overall adj-2 87.10 não batem com artefato (80.36/92.03, 77.96/84.74, 87.44). Nenhum arquivo do repo contém 71.40/68.94 (grep).
M1 "+2.8 pp date-normalization": artefato mostra normalizer OFF no full run; ganho temporal +15.94 pp veio de session-date injection; normalizer ON piorou temporal -3.07 pp no smoke.
M2 "gap ... is the verbosity gap" + "Mem0's fact-extraction prompts close this gap": artefato diz que composição também é gargalo; 66.88 é J.
M3 §5.4 tabela: 3 linhas com 5 células em tabela de 6 colunas (desalinhadas); "Mem0 answer-F1" errado.
M4 §5.4 gap F_MH mistura backbones: Gemini-3-Flash mesma coluna MemOS = 10.84% (Zep 6.02, Mem0 5.62); nox 6.02 => -4.82 pp same-backbone.
M5 §5.4 título "resolved" vs "refined rather than dissolved"; frase final "still largely a structural property ... × all-or-nothing scoring" contradiz hedge e oráculo (Table 5 aponta retrieval, não scoring).
M6 DPR/FiD não avaliam HotPotQA (FiD: NQ, TriviaQA, SQuAD); faixa 65-72% sem fonte.
M7 Baseline HotpotQA 2018 não é BERT: reimplementação de Clark & Gardner (2017); dev distractor ans F1 58.28.
M8 §5.3.3: rota ">=55% F1" sem medição LoCoMo; suplemento apoia-se em §5.1.9 (EverMemBench).
M9 LoCoMo: "10-session dialogues" (é até 35 sessões, ~300 turnos; 10 conversas); "dev corpus" (locomo10.json não é split dev).
L1 "readers published with the benchmark" inclui IRCoT (2023, outro paper).
L2 "Per-hop and per-type breakdowns ... gain is broad": artefato só tem per-hop; 4hop3 47.84% < EX(SA) 49.70.
L3 §5.3.1 "ceiling ... at top_k=10" mas geração usou top_k=20; "structurally easier than on EverMemBench" compara métricas diferentes.
L4 Jargão: "Lab Q1 knob series", "MAP (bypass-entity)" (§5.1.9 chama MAP de "section bypass"), "Q3 IterB/IterC", "(2026-05-31)".

## Não verificável / não reverificado
- Beam Retrieval Table 4 (69.20), Table 5 (85.04), dev retrieval 77.37/79.31, "49.0 → 69.2": só abstract v2 aberto ("nearly 50% improvement").
- FE2H 84.44 (leaderboard) não reaberto. EverMemBench Table 5 (2.41 → 97.99) não reaberto nesta passada (round anterior citou v3); 2.41 coincide com Full Context GPT-4.1-mini F_MH de Table 4.
- "100+ conversation turns" para F_MH: não encontrado na consulta ao v3.
- "Dev/test variance ~1 point" no MuSiQue: sem fonte.
