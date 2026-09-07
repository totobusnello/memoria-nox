# TechRxiv — bloco de metadados da submissão

> **Nada foi submetido.** Este arquivo é o pacote pronto para o Toto colar no formulário.
> Requisitos verificados em 2026-09-07 nas páginas oficiais IEEE/TechRxiv (ver
> `techrxiv-submission-runbook.md` §1); o que não estava estabelecido no oficial está
> marcado como **não verificado** em vez de preenchido por suposição.

## Título

    nox-mem: Pain-Weighted Hybrid Memory for LLM Agents

## Autor

    Luiz Antonio Busnello — Independent Researcher

## Licença

    CC BY 4.0   (paper)
    MIT         (código e harness de avaliação: https://github.com/totobusnello/memoria-nox)

## Arquivo

    paper/build/paper-tecnico-nox-mem.pdf   — 77 páginas, 345 KB, xelatex via pandoc
    Reconstruível com: ./scripts/build-paper.sh

## Categoria

Ciência da computação está no escopo. ⚠️ **O rótulo exato da subcategoria não está
exposto nas páginas oficiais** — confirmar na lista do formulário ao vivo. Alvo:
information retrieval / machine learning. Classe ACM usada no arXiv, se houver campo
equivalente: `H.3.3; I.2.7`.

## Abstract (metadados)

⚠️ **Este texto NÃO é o abstract do corpo do paper**, e a diferença é deliberada: um
campo de metadados é lido isolado, sem as seções que o qualificam, então cada limitador
tem de viajar dentro dele.

⚠️ **E ele NÃO é o bloco que foi ao arXiv.** O `paper/arxiv-metadata.txt` (local,
gitignored) afirma *"architecture is the leading explanation"*, enquanto o corpo do paper
diz o oposto — *"this is embedding-matching, **not** a clean architecture isolation"*
(§6.3.2). Aquele bloco também trazia *"not **yet** significant"* e omitia o número da
comparação em que nox-mem **perde**. As três coisas estão corrigidas abaixo. Ver
`../publication/sota-retraction-patch-2026-09-03.md` para a classe de defeito.

    LLM-agent memory systems often trade retrieval quality or portability for developer
    ergonomics, and cross-system benchmarks remain scarce. We present nox-mem, an
    open-source hybrid memory layer combining FTS5 keyword retrieval, sqlite-vec dense
    retrieval, and Reciprocal Rank Fusion over a single-file SQLite store; the default
    embedding layer is a swappable cloud provider, with an FTS5-only offline fallback.
    Its pain-weighted salience score adds incident severity as a retrieval signal
    (weights 0.55 importance / 0.15 recency / 0.10 pain / 0.20 access). Pain-weighting
    is a design signal whose isolated effect is directional and not statistically
    significant; section-aware ranking is the empirical driver. We also introduce a
    Conditional Hard Mutex (G10d) that gates section and source-type boosts when a query
    names at most two entities, recovering multi-hop (+1.58% nDCG@10) and adversarial
    (+3.04% nDCG@10, +6.25% MRR) regressions. We pre-register methodology, report nine
    ablation generations (G3-G10d) on an n=100 golden set, and benchmark five memory
    systems (Mem0, Zep, Letta, agentmemory, EverMind-AI): two (Mem0, agentmemory)
    produce head-to-head quality numbers on LongMemEval and LoCoMo; three are documented
    deployment non-runs. Under each system's native embedder the two leaders split --
    Mem0 wins LoCoMo (nDCG@10 0.469 vs 0.426), nox-mem wins LongMemEval. An
    embedding-matched variant (both Gemini 3072-d, n=2,482) inverts the split: nox-mem
    leads LongMemEval (0.526 vs 0.406) and LoCoMo (0.495 vs 0.441) and all five
    populated query categories. This is an embedding match rather than a clean
    architecture isolation, and three residual confounds are declared. On EverMemBench
    the F_MH multi-hop track sits at 3-7%, against 18.88% strict EM for the best
    published system on that track. Contributions: pain-weighted salience, the
    Conditional Hard Mutex boost-interaction ablation, an open five-system benchmark,
    and single-file self-hosted deployment. Code (MIT) and evaluation harness:
    https://github.com/totobusnello/memoria-nox

⚠️ **Nenhum limite de tamanho de abstract está estabelecido nas páginas oficiais do
TechRxiv** (o 150–250 palavras que se encontra por aí é de *journals* IEEE, não do
repositório). O bloco acima tem ~2.100 caracteres — o que foi ao arXiv tinha 1.909, então
está na mesma ordem. Se o formulário recusar, o corte a fazer primeiro é a frase do
Conditional Hard Mutex; os limitadores **não** são candidatos a corte.

## Keywords sugeridas

    agent memory, hybrid retrieval, reciprocal rank fusion, SQLite, retrieval-augmented
    generation, salience ranking, self-hosted, cross-system benchmark

## Declaração de estado do manuscrito

Inédito e não submetido a *peer review* em nenhum veículo no momento. O TechRxiv é para
pesquisa **inédita e pré-revisão** e **não** aceita versão final de artigo já publicado —
este manuscrito satisfaz as duas condições.
