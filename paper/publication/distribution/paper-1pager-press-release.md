# [FOR REVIEW / PREPRINT]

## The Pain Diary and Shadow Discipline: A Memory System That Learns from Its Own Incidents

**arXiv preprint — 2026-05-19** | github.com/totobusnello/memoria-nox

---

### One-line summary

A production agent memory system where every operational incident becomes a schema constraint — achieving nDCG@10 = 0.5213 and 3.5× over a strong BM25 baseline, with zero federation across six agents.

---

### The problem

Agent memory systems fail silently. Not because embeddings are weak — because the architecture has no concept of operational discipline. Ranking changes deploy without validation gates. Incident severity never becomes a retrieval signal. Multiple specialized agents maintain isolated context pools that cannot learn from each other. After three months running six AI agents in production (64,000+ chunks, 3 months continuous), we observed all three failure modes, often in the same incident. The April 25th event is illustrative: a cron job ran `reindex` without dry-run at 22:03 and silently wiped section, retention, and section_boost from 183 entities. No error log. No alert. The database simply obeyed.

---

### Three contributions that do not exist in the literature

**1. Pain-weighted salience.** The formula `salience = recency × pain × importance` introduces incident severity as a first-class retrieval dimension. `pain ∈ [0.1, 1.0]` — from trivial note to production outage. GraphRAG, MemGPT, Mem0, A-MEM, HiRAG, and Cognee model structure and recency. None asks: *how much did this cost?* A six-month-old prod-outage lesson outranks yesterday's minor update — as human memory does. Post-incident queries (n=6) establish a baseline nDCG@10 = 0.2689, the hardest retrieval class in the corpus and the primary motivation for pain weighting. Zero prior papers encode incident severity as a retrieval signal.

**2. Shadow discipline.** `NOX_SALIENCE_MODE=shadow` is an architectural constraint enforced via cron and `/api/health` — not a documented best practice that a developer can skip. Any ranking change runs in shadow for a minimum of seven days, compared against prior behavior, before activating in production. The salience validation ran 7 days: 191 promotions, 16,608 revisions, 45,743 archives — then activated. Zero competitor systems implement this. Zero prior papers name it.

**3. Shared-canonical multi-agent context.** Six specialized agents — Atlas, Boris, Cipher, Forge, Lex, Nox — read from a single canonical corpus. Of 61,257 active chunks, 61,207 are shared: **99.92% sharing**, zero federation overhead. MemGPT/Mem0 isolation patterns yield 0% sharing by design. The architectural gap is 99.92 percentage points, not a decimal.

---

### Numbers

| Metric | Value |
|---|---|
| Hybrid nDCG@10 | **0.5213 ± 0.0004** (n=50, 3-run mean) |
| vs BM25 Pyserini (Anserini-tuned, n=60) | **3.5× better** |
| vs FTS5-vanilla baseline | **97.6% relative gap** |
| KG edge-type coverage gain | **14% → 56% (4× improvement)** |
| p95 search latency on 61K chunks | **< 1 second** |
| Schema migrations, zero downtime | **v1 → v12** |
| Architectural parity vs 7 alternatives | **5/5 vs mean 1.6/5** |

---

### Why this belongs in the literature

The community lacks vocabulary for *operational discipline as a methodological contribution*. This work names and formalizes three dimensions that existing systems ignore: severity as signal, shadow gates as architectural constraint, and reproducibility as a first-class deliverable. Six of seven analyzed alternatives publish no reproducible eval harness. This one does — full corpus, incident log, schema history, and golden queries are in the public repository. The reviewer can refute everything. That is the point.

---

### What is available now

- Public repo with full eval harness (nDCG, MRR, Recall@k)
- 50 internally-curated golden queries + 10 BEIR external cross-validation
- BM25 Pyserini and multilingual-e5-base adapter scripts
- 4 system architecture diagrams
- Complete incident log (April 25 + May 1 events documented verbatim)
- Schema history v1–v12 with migration scripts

---

### Author

Built solo by Toto, nerd entrepreneur in São Paulo. Three months, no funding, production infrastructure. Contact: lab@generantis.com.br

### Citation

```bibtex
@misc{nox-supermem-2026,
  title  = {The Pain Diary and Shadow Discipline: A Memory System
             That Learns from Its Own Incidents},
  author = {Toto},
  year   = {2026},
  note   = {arXiv preprint, forthcoming 2026-05-19},
  url    = {https://github.com/totobusnello/memoria-nox}
}
```

---

*The incidents are in the log. The log is in the schema. The schema is in the paper.*
