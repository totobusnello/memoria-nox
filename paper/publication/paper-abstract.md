# Abstract — The Pain Diary and Shadow Discipline

> arXiv submission: 2026-05-19
> Word count target: 150–250 words
> Style: NeurIPS-style structured abstract

---

Persistent memory for autonomous AI agents is widely treated as a retrieval problem, yet production deployments reveal a more fundamental failure mode: silent architectural degradation that no embedding model can prevent. Existing systems — including GraphRAG, MemGPT, Mem0, and A-MEM — model structure and recency but none encodes incident severity as a retrieval signal, and none enforces ranking change validation before production activation. We present NOX-Supermem, a memory system whose architecture is shaped by its own operational failures: each production incident became a schema constraint, and each hard-won lesson a reproducible feature. We make three concrete contributions. First, pain-weighted salience (salience = recency × pain × importance, pain ∈ [0.1, 1.0]) treats incident severity as a first-class retrieval dimension, allowing a six-month-old prod-outage lesson to outrank yesterday's trivial note — as human memory does. Second, shadow discipline enforces a minimum seven-day shadow-mode gate before any ranking change activates, implemented as an architectural constraint via cron and /api/health rather than an optional best practice. Third, shared-canonical multi-agent context serves six specialized agents from a single corpus without federation, synchronization, or merge overhead. On a 64,180-chunk production corpus, hybrid retrieval (FTS5 + Gemini 3072d embeddings + RRF) achieves nDCG@10 = 0.714 versus 0.000 for BM25-only, confirming hybrid as a structural requirement rather than an optimization. Knowledge-graph edge-type coverage improved from 14% to 56% (4× gain) after defensive prompt engineering. Against seven published alternatives, NOX-Supermem scores 5/5 on a five-dimension architectural parity rubric (knowledge graph, hybrid retrieval, eval harness, multi-agent, shadow discipline) versus a mean of 1.6/5; no competitor implements shadow discipline. The full corpus, eval harness, incident log, and schema history (v1–v12) are publicly available, enabling complete reproduction and refutation. Operational discipline, not embedding sophistication, is the binding constraint in production agent memory.

---

**Word count:** 277 words (trim note below)

> **Trim note for arXiv submission:** If the venue enforces 250 words strictly, remove the parenthetical "(salience = recency × pain × importance, pain ∈ [0.1, 1.0])" and the clause "as human memory does" — saves ~20 words, preserving all claims. Alternatively, collapse the three contributions into two sentences and cut the BM25 baseline sentence to reach ~250 cleanly.
