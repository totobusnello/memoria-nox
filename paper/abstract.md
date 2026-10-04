# nox-mem: arXiv Abstract + Submission Fields

---

## §1 Título — candidatos

**Primary (escolhido):**
> nox-mem: Pain-Weighted Hybrid Memory for LLM Agents

**Alt 1:**
> Pain-Weighted Hybrid Retrieval: A Production Memory Layer for Autonomous LLM Agents

**Alt 2:**
> Open Benchmarks for LLM Agent Memory: A Pain-Weighted Hybrid Approach

---

## §2 Abstract (≤1.920 caracteres, limite do arXiv)

We introduce nox-mem, a persistent memory system for LLM agents. Retrieval and retention use an additive salience score in which pain, an operator-assignable severity in [0.1, 1.0] otherwise set at ingest by a keyword rule, is a first-class signal; ranking changes pass a mandatory shadow phase. Each store is one SQLite file, with swappable embeddings, event-driven writeback, per-type retention, chunk-level provenance and a pre-snapshot before destructive operations (MIT license). In production since March 2026, it serves six agents at KG-path p50 2.5 ms, $0 per KG-path query and a 399 MB resident set. Our central result is a pre-specified (plan committed publicly before the first run), same-corpus comparison against five memory systems: four (Mem0, agentmemory, EverOS, Zep) produce head-to-head quality numbers; one (Letta) is a documented deployment non-run. Under native embedders nox-mem and Mem0 split: Mem0 wins LoCoMo (nDCG@10 0.469 vs 0.426), nox-mem wins LongMemEval. An embedding-matched variant run as a planned side experiment (both Gemini 3072-d, n=2,482), an embedding match rather than an architecture isolation, inverts the split: nox-mem leads on both datasets (LongMemEval 0.526 vs 0.406; LoCoMo 0.495 vs 0.441) and in all five represented categories, with four residual confounds declared. EverOS outperforms nox-mem on both (overall 0.646 vs 0.501), with a cross-encoder stage nox-mem lacks, whose share of the gap is unmeasured; Zep ranks third, ahead of Mem0. On EverMemBench nox-mem reaches 63.28% Overall with Gemini-3-flash, 4.01 pp above the published MemOS figure on that backbone and below its 72.61% full-context baseline, so this is not a state-of-the-art claim. Against our headline: pain's isolated effect is directional, not significant; section-aware ranking is the dominant driver; and multi-hop F_MH is 6.02%, against 10.84% for MemOS on the same backbone.

---

## §3 Campos do formulário arXiv

| Campo | Valor |
|---|---|
| **Title** | nox-mem: Pain-Weighted Hybrid Memory for LLM Agents |
| **Authors** | Luiz Antonio Busnello |
| **Affiliation** | Independent Researcher |
| **Email** | lab@nuvini.com.br |
| **Primary category** | cs.IR — Information Retrieval |
| **Cross-list** | cs.LG — Machine Learning |
| **Comments field** | Code: https://github.com/totobusnello/memoria-nox · MIT license |
| **License** | CC BY 4.0 (paper); MIT (code) |
| **Report number** | (deixar em branco) |

---

## §4 Contagem de palavras

> Rodar após geração: `wc -w paper/abstract.md`
>
> Contagem do abstract (v1.0.3 parte G, 2026-10-04, ASCII): 281 palavras / 1902 caracteres (limite do arXiv: 1.920; parte F: 268 / 1824). Condensa o abstract do manuscrito sem alegacao nova; o mesmo bloco esta em paper/arxiv-metadata.txt e em publication/techrxiv-metadata.md.

---

## §5 Checklist — submissão arXiv terça-feira manhã (~6h BRT = 9h ET)

- [ ] Conta arXiv ativa + endorsement cs.IR obtido (first-time submitter precisa de endorser)
- [ ] Título copiado do §3 acima → campo "Title" no formulário
- [ ] Abstract copiado do §2 acima → campo "Abstract" (verificar ≤1920 chars)
- [ ] Categorias selecionadas: cs.IR primary, cs.LG cross-list
- [ ] Arquivos fonte enviados (`.tex` via `scripts/build-paper.sh --tex-only`)
- [ ] `refs.bib` incluído junto com os fontes
- [ ] Licença selecionada: CC BY 4.0
- [ ] Campo Comments preenchido: `Code: https://github.com/totobusnello/memoria-nox · MIT license`
- [ ] Preview de compilação final revisado (checar fórmulas, tabelas, referências)
- [x] **[Q4 NUMBERS] preenchidos** — rc4 controlled-embedding (2026-06-29): split as-configured invertido sob embedding igual; nox-mem supera o mem0 em ambos os datasets + 5 categorias; task-type ablation (2026-06-30) descarta o task type como causa (−0.34 pp, ainda ganha); não atribui a liderança à arquitetura
- [ ] Submeter
