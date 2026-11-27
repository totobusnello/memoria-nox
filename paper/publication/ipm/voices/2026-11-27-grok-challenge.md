llm-call [info]: anexei 2 ficheiro(s) citado(s) ao prompt (rota HTTP, o conteudo vai inline): paper/publication/ipm/manuscript.md, paper/publication/ipm/supplement/S1-technical-report.md. Isto nao e erro.
{
  "schema": "findings.v1",
  "findings": [
    {
      "severity": "alta",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 61,
      "section": "2.3 e 6.1",
      "question": "1",
      "claim": "O manuscrito trata o embedder como causa da inversão Mem0/nox-mem, o que o relatório recusa isolar.",
      "manuscript_quote": "in Section 4 the embedder alone was enough to reorder two systems.",
      "manuscript_quote_2": "Highlights: The ordering of nox-mem and Mem0 flips when the embedder is matched.",
      "manuscript_quote_3": "First, retrieval comparisons of memory systems should be reported under matched embedders as well as native defaults, because the embedder is large enough to reorder systems.",
      "report_quote": "§6.3.2: This does not attribute the §6.3 Mem0 win to the embedder, nor the rc4 nox-mem lead to the retrieval architecture: the run also changed the Mem0 version, its vector backend, the query sample and corpus retention (confounds (a)–(c) and (e) below), and nothing here separates their effects.",
      "evidence": "O §4.5 do manuscrito declara os mesmos (a)–(d) e diz que nada separa os efeitos; o resumo, o highlight e a conclusão prática de §6.1 apagam isso e reintroduzem causalidade. Linha 61 é contagem do texto anexado."
    },
    {
      "severity": "alta",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 33,
      "section": "contribuição 1, highlight e 2.4",
      "question": "1",
      "claim": "A comparação é vendida como seis sistemas, nativo e emparelhado, sobre 2.482 queries; o relatório não correu isso.",
      "manuscript_quote": "A pre-specified, same-corpus retrieval comparison of six memory systems (Section 4), reported under each system's native embedder and under a matched embedder ... a third system, with a mandatory 4 B cross-encoder, leads both.",
      "manuscript_quote_2": "Pre-specified comparison with five memory systems over 2,482 queries",
      "manuscript_quote_3": "We found no study that compares Mem0, Zep, EverOS and Letta on a retrieval metric over one corpus, under both native and matched embedders, and with the deployment failures reported; that is the gap Section 4 fills.",
      "report_quote": "Resumo S1: four produced head-to-head quality numbers (two in the 2026-06-15 canonical run, and EverOS and Zep in later runs over the same corpus and the full n = 2,482 query set of the embedding-matched variant) and one was a documented deployment non-run. §6.4: Only nox-mem and Mem0 participate ... Letta produced no number, and the 2026-09-10 EverOS and Zep runs were not broken down by category. §6.3.2: o braço emparelhado é só nox-mem vs Mem0.",
      "evidence": "Letta não tem número. agentmemory só entra no canónico n=100. Zep ficou em text-embedding-3-small. EverOS não foi corrido nos dois settings; 'leads both' retoma 'the two settings'. O gap de §2.4 não é o que a Secção 4 entrega."
    },
    {
      "severity": "alta",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 39,
      "section": "1, último parágrafo da introdução",
      "question": "1",
      "claim": "A introdução diz que o full-context supera os dois sistemas de memória no EverMemBench; no relatório isso só vale no Gemini-3-flash.",
      "manuscript_quote": "on EverMemBench the full-context baseline outperforms both memory systems we compare.",
      "report_quote": "§5.8.4: GPT-4.1-mini has the weakest full-context baseline in Table 4 (37.44%); on it MemOS (+5.11 pp) and Zep (+2.52 pp) beat full context. §5.1.6: nox-mem Overall 51.68% vs MemOS 42.55% nesse backbone. §5.1.10: full-context 72.61% acima de ambos só na coluna Gemini-3-flash.",
      "evidence": "51.68 e 42.55 estão ambos acima de 37.44. O §5.2 do manuscrito restringe o 72.61% a 'that backbone'; a introdução não. O abstract (6.02% / +4.01 pp) está no contexto Gemini e não cai neste achado."
    },
    {
      "severity": "alta",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 282,
      "section": "5.2",
      "question": "1",
      "claim": "MuSiQue/HotPotQA é usado para dizer que a composição multi-hop não é onde o pipeline falha, contra as ressalvas do relatório.",
      "manuscript_quote": "On classical multi-hop QA, where each question brings its own candidate paragraphs, the same pipeline reaches answer F1 58.62% on MuSiQue-Ans dev ... and 73.37% on HotPotQA distractor dev ..., above the conventional reference readers and 10.58 and 11.67 points below Beam Retrieval ..., so multi-hop composition as such is not where it fails.",
      "report_quote": "§5.2.1: support_hit@20 99.96%; support_hit@10 99.88%; this result measures the reader over the per-question candidate set; it does not test hybrid retrieval recall or RRF fusion. Splits differ in the top row (Beam Retrieval no test; nox-mem no dev); no split-matched answer figure is published. the comparison confounds retrieval design with three years of backbone progress, and we do not claim the delta measures the former. §5.2.3: the EverMemBench F_MH gap cannot be attributed to task structure alone on the strength of these two results.",
      "evidence": "HotPotQA é top_k=5 sobre 10 parágrafos (§5.2.2), não o mesmo tecto que MuSiQue; o manuscrito funde os dois e trata gaps cross-split como diferença do mesmo pipeline. Linha aproximada (contagem do anexo)."
    },
    {
      "severity": "média",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 49,
      "section": "2.1",
      "question": "1",
      "claim": "O caminho de grafo é dado como a razão da fraqueza multi-hop; o relatório diz que esse preço não foi isolado.",
      "manuscript_quote": "nox-mem's graph path is a SQL and regular-expression walk over extracted relations with no LLM call at query time, which is why it is cheap and why it is less expressive on multi-hop questions.",
      "report_quote": "§1.5: It buys latency and cost at the price of multi-hop expressiveness; that price is not isolated here, and §5.4 offers task setup, not the KG path, as the leading account of the F_MH gap.",
      "evidence": "Leitura caridosa: contraste de desenho com HippoRAG, não o F_MH. Ainda assim o 'why it is' afirma o que o relatório marca como não isolado. A comparação de nDCG é híbrida (RRF), não o caminho de grafo isolado (§6.3.3)."
    },
    {
      "severity": "média",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 7,
      "section": "Abstract e contribuição 3",
      "question": "1",
      "claim": "Abstract e contribuição 3 atribuem quase todo o ganho da ablação ao section ranking, apagando a ressalva G3 e o conjunto não documentado.",
      "manuscript_quote": "section-aware ranking carries nearly all of the ablation gain",
      "manuscript_quote_2": "An ablation and a cross-benchmark evaluation (Section 5) that locate where the ranking gains come from. They come from section-aware ranking over structured entity files, not from the severity signal the system was first built around.",
      "report_quote": "§5.1.1: Section-aware ranking accounts for nearly all of the full stack's gain over unboosted hybrid retrieval within G5 V3 (0.5126), though not for most of the +78.8% over G3. No record documents how the 100 queries were selected. run records disagree on whether the G5 V3 run searched a ~69k-chunk clone ... or the 500-chunk entity-eval.db.",
      "evidence": "O §5.1 do manuscrito recupera a distinção (+78.8% vem de sair do G3; dentro do G5 o stack soma +21.7% e a secção carrega isso) e os dois limites do golden set. Abstract, contribuição 3 e §6.2 ('nearly all of the measured gain') voltam à formulação que o relatório rejeita. O golden set não é o corpus da comparação."
    },
    {
      "severity": "média",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 61,
      "section": "2.3",
      "question": "1",
      "claim": "'Única construção' é a extração noturna; o relatório e o §3.1 também têm grafo extraído por LLM.",
      "manuscript_quote": "its only construction step, the nightly extraction into topic files (Section 3.2), adds passages without replacing their sources.",
      "report_quote": "§2.2 e §3.2: kg_entities/kg_relations extraídos por LLM, com confidence e TTL; consolidação noturna é outro passo. §8: The LLM-powered knowledge graph extracts typed entities and relations that the earlier regex path did not.",
      "evidence": "O próprio manuscrito §3.1 lista 'Entities and typed relations extracted by an LLM'. 'Adds without replacing sources' pode valer para o job noturno; 'only' não."
    },
    {
      "severity": "alta",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 313,
      "section": "6.1–6.2",
      "question": "1",
      "claim": "A discussão converte stacks documentados, não medidos, num limite do que serviços extra compram na tarefa de retrieval.",
      "manuscript_quote": "operational requirements differ widely across systems of comparable retrieval quality, from one process and no key to five services and up to three keys (Table 8)",
      "manuscript_quote_2": "ranked second of four on every quality metric over the full query set, ahead of two systems that run on separate databases. ... it bounds what the extra services and model calls of the alternatives buy on this retrieval task.",
      "report_quote": "§6.8: The EverOS row describes its 2026-06-15 configuration, not the library measured in §6.3.3. Only the nox-mem row is measured ... neither column says anything about retrieval quality. §6.3.3: pip install everos resolves to a local-first library (v1.3.1) that needs no HTTP service and no mandatory OpenRouter credential. §6.3.2(b): canonical Mem0 used faiss; rc4 Mem0 uses Chroma.",
      "evidence": "Os cinco serviços são o docker-compose de 2026-06-15, não o EverOS que fez 0.6455. Mem0 medido não é Postgres+Qdrant. Zep teve summarizer, entity e intent extractors desligados (§6.3.4). O relatório não autoriza o 'bounds'."
    },
    {
      "severity": "média",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 341,
      "section": "7",
      "question": "1",
      "claim": "A conclusão ata o segundo lugar à ausência opcional de chave; a corrida que rankeia usou Gemini e não houve ablação keyless.",
      "manuscript_quote": "nox-mem ranked second of four over the full query set while needing one process and, optionally, no third-party key.",
      "report_quote": "§8: which used Gemini in every configuration measured here; FTS5-only retrieval is a valid keyless degraded mode (§4). ... no FTS5-only or dense-only ablation was run on the canonical LoCoMo/LongMemEval sets.",
      "evidence": "'Optionally' descreve um modo não avaliado. O §6.4 do manuscrito diz o fallback lexical; a conclusão volta a colá-lo ao número da Tabela 6. Linha aproximada."
    },
    {
      "severity": "alta",
      "file": "paper/publication/ipm/manuscript.md",
      "line": 7,
      "section": "título, 4 e 6",
      "question": "2",
      "claim": "O primeiro ataque IP&M é a não-identificação da comparação (confounds e justiça), não novidade; o texto declara e não responde.",
      "manuscript_quote": "Our main contribution is a comparison against five memory systems whose execution plan was committed to a public repository before the first run.",
      "report_quote": "§6.7: plano não registado externamente; version ranges em vez de pins; critério de sucesso vazio por construção no canónico (só três sistemas com número). §6.3.2: quatro confounds residuais não separados. §6.3.3: quota do re-ranker 4B não medida. §6.3.4: extractors do Zep desligados; fan-out a 510 sessões. §6.3: outputs do 2026-06-15 perdidos com o pod.",
      "evidence": "Atacaria primeiro o desenho: embedder não isolado de versão 0.1.114 vs 2.0.10, faiss vs Chroma, n=100 vs 2.482, retenção 6.822 vs 6.826, task type, datas junho–setembro, filtro k=30 pós-hoc que sobe LoCoMo de 0.4173 para 0.4263, Zep sem o pipeline que o define, EverOS com re-ranker obrigatório e candidatos cortados a 50, Letta sem número, autor único. Novidade e reprodutibilidade vêm depois: o texto já admite stack convencional e pain nulo; links estão retidos para revisão. Responde por declaração em §§4.1, 4.5, 4.6 e 6.3, e no primeiro parágrafo de §6.1. Não responde: título 'pre-specified', §2.4 ('gap Section 4 fills'), §6.1 ('embedder is large enough'; 'pre-specified rules forced all of them' — o all-Gemini era side experiment opcional, §6.5 princípio 5) e §6.2 (bounds). Incerteza: não há o ficheiro do plano no anexo, só o que os dois textos dizem dele."
    }
  ]
}
