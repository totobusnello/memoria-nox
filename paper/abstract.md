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

## §2 Abstract (≤300 palavras)

LLM-agent memory systems often trade retrieval quality or portability for developer ergonomics, and cross-system benchmarks remain scarce. We present nox-mem, an open-source hybrid memory layer combining FTS5 keyword retrieval, sqlite-vec dense retrieval, and Reciprocal Rank Fusion over a single-file SQLite store; the default embedding layer is a swappable cloud provider, with an FTS5-only offline fallback. Its pain-weighted salience score, W_IMPORTANCE*importance + W_RECENCY*recency + W_PAIN*pain + W_ACCESS*access_score (weights 0.55 / 0.15 / 0.10 / 0.20), adds incident severity as a retrieval signal. Pain-weighting is a design signal whose isolated effect is directional and not yet significant; section-aware ranking is the empirical driver (99.85% of the ablated gain). We also introduce a Conditional Hard Mutex (G10d) that gates section and source-type boosts when a query names at most two entities, recovering multi-hop (+1.58% nDCG@10) and adversarial (+3.04% nDCG@10, +6.25% MRR) regressions. We pre-register methodology, report nine ablation generations (G3-G10d) on an n=100 golden set, and benchmark five memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI): two (Mem0, agentmemory) produce head-to-head quality numbers on LongMemEval and LoCoMo; three are documented deployment non-runs. Native embedders split the two leaders; under controlled embedding (both Gemini-3072d, n=2,482) nox-mem beats Mem0 on LongMemEval (nDCG@10 0.526 vs 0.406) and LoCoMo (0.495 vs 0.441) and on all five populated query categories. A task-type ablation rules out task-type asymmetry; architecture is the leading explanation, residual confounds declared. Contributions: pain-weighted salience, the Conditional Hard Mutex boost-interaction ablation, an open five-system benchmark, and single-file self-hosted deployment. Code (MIT) and evaluation harness: https://github.com/totobusnello/memoria-nox.

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
> Contagem do abstract (versao arXiv, ASCII): 254 palavras / 1909 chars (dentro do limite <=1920). Espelha exatamente o bloco de paper/arxiv-metadata.txt.

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
- [x] **[Q4 NUMBERS] preenchidos** — rc4 controlled-embedding (2026-06-29): split as-configured invertido sob embedding igual; nox-mem supera o mem0 em ambos os datasets + 5 categorias; task-type ablation (2026-06-30) confirma vitória arquitetural (−0.34 pp, ainda ganha)
- [ ] Submeter
