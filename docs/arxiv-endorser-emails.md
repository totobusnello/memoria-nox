# arXiv Endorsement Email Templates

**Prep for P0 submission Mon 2026-06-01**

Context: cs.IR first-time submitter requires endorsement. Candidates identified from paper refs (§3 RRF, §5 benchmarks). Sending order: Cormack (most foundational) → Wu (2-3h later) → Maharana (2-3h after Wu).

---

## Template 1: Gordon V. Cormack — RRF Founder

**Candidate Profile:**
- **Name:** Gordon V. Cormack
- **Affiliation:** University of Waterloo, David R. Cheriton School of Computer Science
- **Key Work:** "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods" (SIGIR 2009, ACM DL 10.1145/1571941.1572114)
- **Email:** (likely public as gvcormack@uwaterloo.ca based on institutional affiliation)
- **arXiv endorser ID:** (Toto will generate from arXiv form)

**Email Draft:**

```
Subject: arXiv endorsement request — nox-mem hybrid memory system (cs.IR)

Dear Dr. Cormack,

I hope this message finds you well. I am writing to request your endorsement for an arXiv submission in cs.IR on behalf of an open-source project I am developing.

My work, *nox-mem: Pain-Weighted Hybrid Memory for LLM Agents*, applies your Reciprocal Rank Fusion (RRF) framework to multi-stage LLM agent memory retrieval. Specifically, we combine FTS5 keyword ranking (BM25) with Gemini dense semantic embeddings, fusing results via RRF with k=60 following your established convention. Your foundational insight — that rank fusion is more robust than learned aggregation — proved critical when tuning interaction between section-boosting and source-type-boosting at scale (69k+ chunks).

The work introduces a pain-weighted salience formula (`salience = recency × pain × importance × access_count`) where `pain` encodes incident severity (0.1–1.0 continuous), enabling memory systems to surface high-stakes contexts even when recency is low. We report ablation studies (G3–G10d) on LongMemEval and LoCoMo, benchmarking against five production systems, with a novel Conditional Hard Mutex protocol that recovers multi-hop accuracy (+1.58% nDCG@10) without sacrificing single-hop precision.

**Submission details:**
- **Title:** nox-mem: Pain-Weighted Hybrid Memory for LLM Agents
- **Primary category:** cs.IR
- **Cross-list:** cs.LG, cs.AI
- **Expected submission date:** Tuesday, June 2, 2026 (9h ET)
- **Code:** https://github.com/totobusnello/memoria-nox (MIT license, open-source)
- **Abstract:** ~280 words (included below)

We pre-registered our methodology and release all evaluation harnesses and raw results alongside code, enabling reproduction against competitors.

**arXiv endorsement code:** [Toto will insert after generation]

---

**Abstract:**

Memory systems for LLM agents typically optimize for developer ergonomics, sacrificing retrieval quality or imposing vendor lock-in. Standardized cross-system benchmarks are scarce, making per-system accuracy claims difficult to reproduce or compare.

We present **nox-mem**, an open-source hybrid memory layer that combines FTS5 keyword retrieval, sqlite-vec dense retrieval, and Reciprocal Rank Fusion (RRF) over a zero-dependency SQLite database. We introduce a *pain-weighted salience* formula — `salience = recency × pain × importance × access_count` — where `pain` encodes incident severity on a continuous scale (0.1 trivial → 1.0 production outage), enabling retrieval to surface high-stakes memories even when recency is low. We further propose a **Conditional Hard Mutex** (G10d), which gates section and source-type boosts on query entity count (threshold τ=2), recovering multi-hop retrieval accuracy (+1.58% nDCG@10, +3.04% MRR on adversarial queries) without sacrificing single-hop precision.

We pre-register our methodology and report ten ablation studies (G3 through G10d) on LongMemEval (n=100) and LoCoMo, benchmarking against five production-grade memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI). Per-category breakdowns expose tradeoffs across multi-hop, temporal, and adversarial query types. All evaluation harnesses and raw results are published alongside the code.

**Contributions:** (i) pain-weighted salience formula that incorporates incident severity into memory scoring; (ii) Conditional Hard Mutex ablation protocol for boost interaction; (iii) open benchmark methodology reproducible against five competitors; (iv) production-stable single-file deployment (SQLite + FTS5 + sqlite-vec, zero external services).

---

I would greatly appreciate your endorsement. If you have any questions about the work or methodology, I am happy to discuss further.

Thank you for your time and for your foundational contributions to retrieval science.

Best regards,

**Luiz Antonio Busnello**  
Independent Researcher  
lab@nuvini.com.br  
https://github.com/totobusnello/memoria-nox
```

---

## Template 2: Di Wu et al. — LongMemEval Lead

**Candidate Profile:**
- **Name:** Di Wu (corresponding/lead author)
- **Affiliation:** MSRA (Microsoft Research Asia) or comparable institutional affiliation per ICLR 2025 proceedings
- **Key Work:** "LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory" (arXiv:2410.10813, ICLR 2025)
- **Email:** (likely public via institutional directory or ICLR proceedings metadata)
- **arXiv endorser ID:** (Toto will generate from arXiv form)

**Email Draft:**

```
Subject: arXiv endorsement request — nox-mem + LongMemEval benchmark (cs.IR)

Dear Dr. Wu,

I hope this message finds you well. I am reaching out with a request for arXiv endorsement for an open-source memory system paper that directly benchmarks against the evaluation methodology your team established.

My work, *nox-mem: Pain-Weighted Hybrid Memory for LLM Agents*, uses **LongMemEval** (your arXiv:2410.10813) as a primary evaluation harness to measure retrieval accuracy and multi-turn reasoning capability. Your benchmark proved invaluable in exposing a fundamental interaction between retrieval boost mechanics — specifically, how section-level boosts (entity-file frontmatter, compiled sections, timelines) compound with source-type boosts, leading to precision loss on multi-hop queries.

We report ten ablation studies (G3–G10d) on LongMemEval (n=100 golden dataset), with per-query-type breakdowns (single-hop, multi-hop, temporal, adversarial, open-domain). Our Conditional Hard Mutex (G10d) — a query-entity-count threshold that gates boost application — recovers +1.58% nDCG@10 and +3.04% MRR on adversarial queries without sacrificing single-hop precision (which remains the primary signal in production).

**Submission details:**
- **Title:** nox-mem: Pain-Weighted Hybrid Memory for LLM Agents
- **Primary category:** cs.IR
- **Cross-list:** cs.LG, cs.AI
- **Expected submission date:** Tuesday, June 2, 2026 (9h ET)
- **Code:** https://github.com/totobusnello/memoria-nox (MIT license)
- **LongMemEval results:** [Q4 numbers to be added pre-submission Sat 2026-05-24]
- **Abstract:** ~280 words (included below)

We benchmark against five production memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI) and publish all evaluation harnesses, golden datasets, and raw results for community reproduction.

**arXiv endorsement code:** [Toto will insert after generation]

---

**Abstract:**

Memory systems for LLM agents typically optimize for developer ergonomics, sacrificing retrieval quality or imposing vendor lock-in. Standardized cross-system benchmarks are scarce, making per-system accuracy claims difficult to reproduce or compare.

We present **nox-mem**, an open-source hybrid memory layer that combines FTS5 keyword retrieval, sqlite-vec dense retrieval, and Reciprocal Rank Fusion (RRF) over a zero-dependency SQLite database. We introduce a *pain-weighted salience* formula — `salience = recency × pain × importance × access_count` — where `pain` encodes incident severity on a continuous scale (0.1 trivial → 1.0 production outage), enabling retrieval to surface high-stakes memories even when recency is low. We further propose a **Conditional Hard Mutex** (G10d), which gates section and source-type boosts on query entity count (threshold τ=2), recovering multi-hop retrieval accuracy (+1.58% nDCG@10, +3.04% MRR on adversarial queries) without sacrificing single-hop precision.

We pre-register our methodology and report ten ablation studies (G3 through G10d) on LongMemEval (n=100) and LoCoMo, benchmarking against five production-grade memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI). Per-category breakdowns expose tradeoffs across multi-hop, temporal, and adversarial query types. All evaluation harnesses and raw results are published alongside the code.

**Contributions:** (i) pain-weighted salience formula that incorporates incident severity into memory scoring; (ii) Conditional Hard Mutex ablation protocol for boost interaction; (iii) open benchmark methodology reproducible against five competitors; (iv) production-stable single-file deployment (SQLite + FTS5 + sqlite-vec, zero external services).

---

Thank you for your pioneering work in memory benchmarking. I would be grateful for your endorsement. If you wish to discuss the methodology or results in more detail, I am available.

Best regards,

**Luiz Antonio Busnello**  
Independent Researcher  
lab@nuvini.com.br  
https://github.com/totobusnello/memoria-nox
```

---

## Template 3: Adyasha Maharana et al. — LoCoMo Dataset Lead

**Candidate Profile:**
- **Name:** Adyasha Maharana (corresponding/lead author)
- **Affiliation:** University of Michigan or institutional affiliation per ICLR/ACL proceedings
- **Key Work:** "Evaluating Very Long-Term Conversational Memory of LLM Agents" (arXiv:2402.17753, LoCoMo dataset)
- **Email:** (likely public via institutional directory or conference proceedings)
- **arXiv endorser ID:** (Toto will generate from arXiv form)

**Email Draft:**

```
Subject: arXiv endorsement request — nox-mem memory system (cs.IR) + LoCoMo evaluation

Dear Dr. Maharana,

I am writing to request your endorsement for an open-source memory system paper that extensively evaluates against your LoCoMo dataset.

My work, *nox-mem: Pain-Weighted Hybrid Memory for LLM Agents*, applies the long-term conversational memory evaluation framework your team developed (LoCoMo, arXiv:2402.17753) to stress-test retrieval robustness across extended conversations. Your dataset proved essential in identifying adversarial failure modes — specifically, how naive source-type boosts (prioritizing recent or topic-cohesive chunks) degrade accuracy when the user's intent spans multiple time windows or involves implicit context across domain boundaries.

We report per-category ablations (single-hop, multi-hop, temporal, adversarial, open-domain) on both LongMemEval and LoCoMo. Our Conditional Hard Mutex (G10d) — a threshold-based gating mechanism that conditionally disables section and source-type boosts when entity count ≤ τ — recovers +3.04% MRR on adversarial queries while preserving single-hop precision (the production baseline).

**Submission details:**
- **Title:** nox-mem: Pain-Weighted Hybrid Memory for LLM Agents
- **Primary category:** cs.IR
- **Cross-list:** cs.LG, cs.AI
- **Expected submission date:** Tuesday, June 2, 2026 (9h ET)
- **Code:** https://github.com/totobusnello/memoria-nox (MIT license, fully reproducible)
- **LoCoMo results:** [Q4 numbers to be added pre-submission Sat 2026-05-24]
- **Abstract:** ~280 words (included below)

We benchmark against five production systems and release all evaluation harnesses, datasets, and code for community verification.

**arXiv endorsement code:** [Toto will insert after generation]

---

**Abstract:**

Memory systems for LLM agents typically optimize for developer ergonomics, sacrificing retrieval quality or imposing vendor lock-in. Standardized cross-system benchmarks are scarce, making per-system accuracy claims difficult to reproduce or compare.

We present **nox-mem**, an open-source hybrid memory layer that combines FTS5 keyword retrieval, sqlite-vec dense retrieval, and Reciprocal Rank Fusion (RRF) over a zero-dependency SQLite database. We introduce a *pain-weighted salience* formula — `salience = recency × pain × importance × access_count` — where `pain` encodes incident severity on a continuous scale (0.1 trivial → 1.0 production outage), enabling retrieval to surface high-stakes memories even when recency is low. We further propose a **Conditional Hard Mutex** (G10d), which gates section and source-type boosts on query entity count (threshold τ=2), recovering multi-hop retrieval accuracy (+1.58% nDCG@10, +3.04% MRR on adversarial queries) without sacrificing single-hop precision.

We pre-register our methodology and report ten ablation studies (G3 through G10d) on LongMemEval (n=100) and LoCoMo, benchmarking against five production-grade memory systems (Mem0, Zep, Letta, agentmemory, EverMind-AI). Per-category breakdowns expose tradeoffs across multi-hop, temporal, and adversarial query types. All evaluation harnesses and raw results are published alongside the code.

**Contributions:** (i) pain-weighted salience formula that incorporates incident severity into memory scoring; (ii) Conditional Hard Mutex ablation protocol for boost interaction; (iii) open benchmark methodology reproducible against five competitors; (iv) production-stable single-file deployment (SQLite + FTS5 + sqlite-vec, zero external services).

---

I would greatly appreciate your endorsement. Thank you for establishing rigorous evaluation standards for conversational memory — this work would not be possible without your foundation.

Best regards,

**Luiz Antonio Busnello**  
Independent Researcher  
lab@nuvini.com.br  
https://github.com/totobusnello/memoria-nox
```

---

## Sending Checklist

| Candidate | Primary Affiliation | Send Time (BRT) | Status | Notes |
|---|---|---|---|---|
| **Cormack, Gordon V.** | University of Waterloo | Mon 09:00 | [ ] Send first | RRF most foundational; likely fastest endorser |
| **Wu, Di** | Microsoft Research Asia / ICLR 2025 | Mon 11:30 | [ ] Send second | 2-3h spacing; LongMemEval lead author |
| **Maharana, Adyasha** | University of Michigan / ACL | Mon 14:00 | [ ] Send third | 2-3h spacing; LoCoMo dataset lead author |

**Response tracking:** Create separate sheet (external to this repo) with actual email addresses once obtained from arXiv endorser API or institutional websites.

---

## Notes for Toto

1. **Email addresses:** Obtain from:
   - arXiv endorser search (arxiv.org/auth/show-endorsers, cs.IR category)
   - Google Scholar institutional pages (gvcormack, di.wu, adyasha.maharana)
   - ICLR 2025 proceedings (Wu et al.)
   - ACL proceedings (Maharana et al., if venue confirmed)

2. **Timing:** Send first email Mon morning (09:00 BRT = 06:00 ET). Each subsequent 2-3h apart to avoid appearing spammy.

3. **Endorsement code:** arXiv generates a unique code per endorsement request. Insert into `[Toto will insert after generation]` placeholder in each template before sending.

4. **Follow-up:** If no response after 48h, one gentle follow-up email. Do not escalate beyond 2 attempts per candidate.

5. **Contingency:** If primary candidate declines, fallback candidates from refs:
   - Robertson, Stephen (BM25 theory)
   - Guo, Zirui (LightRAG, KG dense retrieval)

6. **Pre-send checklist:**
   - [ ] Q4 numbers filled into abstract (data arrives Sat 2026-05-24)
   - [ ] Each email proofread for typos + technical accuracy
   - [ ] arXiv endorsement codes inserted
   - [ ] Email addresses verified correct before sending
