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

    paper/build/paper-tecnico-nox-mem.pdf   — 73 páginas, 318 KB (318.365 B), xelatex via pandoc (v1.0.3, MD5 207e02545b3f5a4619789df11374aaf1)
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

⚠️ **Histórico.** O bloco que foi ao arXiv em 2026-06-30 afirmava *"architecture is the
leading explanation"*, *"not **yet** significant"* e omitia a comparação em que nox-mem
**perde**. Desde a v1.0.3 parte F (2026-10-04) o `paper/arxiv-metadata.txt` (local,
gitignored) traz o mesmo bloco de baixo, que condensa o abstract do manuscrito sem
alegação nova e cabe no limite de 1.920 caracteres do arXiv.

**O bloco abaixo é o `paper/abstract.md` §2, palavra por palavra** (desde 2026-09-29;
reescrito em 2026-10-04 para caber em 1.920 caracteres) — é o texto que o `claims_check.py` confere
(contagens de sistemas). Editar lá e copiar para cá, nunca o contrário. Ver
`../publication/sota-retraction-patch-2026-09-03.md` para a classe de defeito.

    We introduce nox-mem, a persistent memory system for LLM agents. Retrieval and
    retention use an additive salience score in which pain, an operator-assignable
    severity in [0.1, 1.0] otherwise set at ingest by a keyword rule, is a first-class
    signal; ranking changes pass a mandatory shadow phase. Each store is one SQLite
    file, with swappable embeddings, event-driven writeback, per-type retention,
    chunk-level provenance and a pre-snapshot before destructive operations (MIT
    license). In production since March 2026, it serves six agents at KG-path p50 2.5
    ms, $0 per KG-path query and a 399 MB resident set. Our central result is a
    pre-specified (plan committed publicly before the first run), same-corpus comparison
    against five memory systems: four (Mem0, agentmemory, EverOS, Zep) produce
    head-to-head quality numbers; one (Letta) is a documented deployment non-run. Under
    native embedders nox-mem and Mem0 split: Mem0 wins LoCoMo (nDCG@10 0.469 vs 0.426),
    nox-mem wins LongMemEval. An embedding-matched variant run as a planned side
    experiment (both Gemini 3072-d, n=2,482), an embedding match rather than an
    architecture isolation, inverts the split: nox-mem leads on both datasets
    (LongMemEval 0.526 vs 0.406; LoCoMo 0.495 vs 0.441) and in all five represented
    categories, with four residual confounds declared. EverOS outperforms nox-mem on
    both (overall 0.646 vs 0.501), with a cross-encoder stage nox-mem lacks, whose share
    of the gap is unmeasured; Zep ranks third, ahead of Mem0. On EverMemBench nox-mem
    reaches 63.28% Overall with Gemini-3-flash, 4.01 pp above the published MemOS figure
    on that backbone and below its 72.61% full-context baseline, so this is not a
    state-of-the-art claim. Against our headline: pain's isolated effect is directional,
    not significant; section-aware ranking is the dominant driver; and multi-hop F_MH is
    6.02%, against 10.84% for MemOS on the same backbone.

⚠️ **Nenhum limite de tamanho de abstract está estabelecido nas páginas oficiais do
TechRxiv** (o 150–250 palavras que se encontra por aí é de *journals* IEEE, não do
repositório). O bloco acima tem 1.902 caracteres (v1.0.3 parte G), dentro do limite de 1.920 do arXiv. Os
limitadores **não** são candidatos a corte.

## Keywords sugeridas

    agent memory, hybrid retrieval, reciprocal rank fusion, SQLite, retrieval-augmented
    generation, salience ranking, self-hosted, cross-system benchmark

## Declaração de estado do manuscrito

Inédito e não submetido a *peer review* em nenhum veículo no momento. O TechRxiv é para
pesquisa **inédita e pré-revisão** e **não** aceita versão final de artigo já publicado —
este manuscrito satisfaz as duas condições.
