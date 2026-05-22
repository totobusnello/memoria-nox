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

Memory systems for LLM agents typically optimize for developer ergonomics, sacrificing retrieval quality or imposing vendor lock-in. Standardized cross-system benchmarks are scarce, making per-system accuracy claims difficult to reproduce or compare.

We present **nox-mem**, an open-source hybrid memory layer that combines FTS5 keyword retrieval, sqlite-vec dense retrieval, and Reciprocal Rank Fusion (RRF) over a zero-dependency SQLite database. We introduce a *pain-weighted salience* formula — `salience = recency × pain × importance × access_count` — where `pain` encodes incident severity on a continuous scale (0.1 trivial → 1.0 production outage), enabling retrieval to surface high-stakes memories even when recency is low. We further propose a **Conditional Hard Mutex** (G10d), which gates section and source-type boosts on query entity count (threshold τ=2), recovering multi-hop retrieval accuracy (+1.58% nDCG@10, +3.04% MRR on adversarial queries) without sacrificing single-hop precision.

We pre-register our methodology and report ten ablation studies (G3 through G10d) on LongMemEval (n=100) and LoCoMo, benchmarking against five production-grade memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI). On LongMemEval: [Q4 NUMBERS]. On LoCoMo: [Q4 NUMBERS]. Per-category breakdowns expose tradeoffs across multi-hop, temporal, and adversarial query types. All evaluation harnesses and raw results are published alongside the code.

Contributions: (i) pain-weighted salience formula that incorporates incident severity into memory scoring; (ii) Conditional Hard Mutex ablation protocol for boost interaction; (iii) open benchmark methodology reproducible against five competitors; (iv) production-stable single-file deployment (SQLite + FTS5 + sqlite-vec, zero external services). Code (MIT) and full evaluation harness: https://github.com/totobusnello/memoria-nox.

---

## §3 Campos do formulário arXiv

| Campo | Valor |
|---|---|
| **Title** | nox-mem: Pain-Weighted Hybrid Memory for LLM Agents |
| **Authors** | Luiz Antonio Busnello |
| **Affiliation** | Independent Researcher |
| **Email** | lab@nuvini.com.br |
| **Primary category** | cs.IR — Information Retrieval |
| **Cross-list** | cs.LG — Machine Learning; cs.AI — Artificial Intelligence |
| **Comments field** | Code: https://github.com/totobusnello/memoria-nox · MIT license |
| **License** | CC BY 4.0 (paper); MIT (code) |
| **Report number** | (deixar em branco) |

---

## §4 Contagem de palavras

> Rodar após geração: `wc -w paper/abstract.md`
>
> Contagem do §2 isolado: ~280 palavras (dentro do limite ≤300).

---

## §5 Checklist — submissão arXiv terça-feira manhã (~6h BRT = 9h ET)

- [ ] Conta arXiv ativa + endorsement cs.IR obtido (first-time submitter precisa de endorser)
- [ ] Título copiado do §3 acima → campo "Title" no formulário
- [ ] Abstract copiado do §2 acima → campo "Abstract" (verificar ≤1920 chars)
- [ ] Categorias selecionadas: cs.IR primary, cs.LG + cs.AI cross-list
- [ ] Arquivos fonte enviados (`.tex` via `scripts/build-paper.sh --tex-only`)
- [ ] `refs.bib` incluído junto com os fontes
- [ ] Licença selecionada: CC BY 4.0
- [ ] Campo Comments preenchido: `Code: https://github.com/totobusnello/memoria-nox · MIT license`
- [ ] Preview de compilação final revisado (checar fórmulas, tabelas, referências)
- [ ] **[Q4 NUMBERS] preenchidos** antes de submeter (dados chegam sab 24/05)
- [ ] Submeter
