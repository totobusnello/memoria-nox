# Related Work — Paper 2 (Interventional Memory)

> **Status:** v0.4, 2026-08-15.
>
> Sections 1, 2, 4, 4.1, 5 and 6 are written against three sources **read in full**: Huang et al. (TMLR 07/2026), MemoryArena (2602.16313) and Evo-Memory (2511.20857).
>
> §4.2 (InterruptBench) is at abstract level, and that is sufficient — the point there is a *distinction*, not an overlap. §4.3 closes a reference that had been dangling in our notes for weeks.
>
> Section 3 remains at **abstract-and-metadata granularity**. Two of its rows are superseded by later sections: Evo-Memory by §4.1 and InterruptBench by §4.2. They are left in place because §3 is the map of the neighbourhood; §4 is where the confrontation happens.
>
> Prior to this file the Paper 2 workspace contained **no external citation of any kind** — this is the first.

---

## 1. Positioning against the canonical taxonomy

Huang et al., *A Survey of Agent Memory in the Second Half: Towards Self-Evolving and Long-Horizon Agents* (TMLR 07/2026; arXiv:2602.06052v4) surveys 218 papers and organises foundation-agent memory along three orthogonal axes. Stating our coordinates in their frame is the cheapest way to let a reviewer locate this work:

| Axis (survey §) | Their categories | Where nox-mem / Paper 2 sits |
|---|---|---|
| **Memory substrate** (§3.1) | internal (weights, latent state, KV cache) vs. external (vector index, text record, structural store, hierarchical store) | **External**, specifically *structural store* — SQLite + FTS5 + sqlite-vec + a typed knowledge graph. We hold **no** internal-memory component, deliberately (§5). |
| **Cognitive mechanism** (§3.2) | sensory, working, episodic, semantic, procedural | **Episodic + semantic**, with procedural present but underdeveloped (`crystallize`). The intervention under test operates on *episodic* records weighted by adjudicated outcome. |
| **Memory subject** (§3.3) | user-centric vs. agent-centric | **Agent-centric.** The unit of study is a fleet of production agents accumulating their own experience, not a user profile being personalised. |

The survey's Figure 3 shows agent-centric work (146 papers) having overtaken user-centric (72) during 2025. We sit on the growing side of that split — worth one sentence in the manuscript, no more.

---

## 2. What the field measures — and the cell that is empty

The survey's **Table 3** enumerates the metrics in use across foundation-agent memory evaluation and partitions them into three families:

- **accuracy-based** — Accuracy/Memory Accuracy, F1, Recall@K, MAP, NDCG@K, Success Rate / Goal Completion, Pass@K / Resolved Rate, Memory Integrity, False Memory Rate;
- **similarity-based** — ROUGE, BLEU, Distinct-*n*, BERTScore, FactScore, Perplexity;
- **LLM-as-a-judge** — Response Correctness, Faithfulness/Groundedness, Preference Following.

Each scores either **what was retrieved** (Recall@K, MAP, NDCG@K), **what was written** (Memory Integrity, False Memory Rate), or **what was said** (similarity and judge families). None scores **whether the retrieved memory changed the agent's decision**, as an effect estimated against a counterfactual.

Two further admissions sharpen the picture:

- **Table 4** marks *Compression & Summarization* and *Forgetting & Retention* as "comparatively under-evaluated" across user-centric benchmarks, and notes *Abstain & Boundary Handling* is "inconsistently required", with few benchmarks rewarding abstention.
- **§9.6** independently proposes, as future work, the design this study pre-registers: closed-loop, longitudinal, execution-grounded evaluation comparing *"memory-augmented agents and memory-free baselines under identical conditions"*, with provenance metadata, versioned and rollback-able persistent state, MCP-style tool mediation for reproducible logging and replay, and explicit resource–utility accounting.

**Verified by string search over the extracted text (2026-08-13):** `pre-registration` / `preregistration` — **0 occurrences** in 54 pages; `interventional` — 1 (in passing, §5); `counterfactual` — 1, in §9.6, as a suggested future direction. These are claims about strings in one document, which is what makes them checkable. They are **not** a claim that no one has ever pre-registered a memory experiment.

---

## 3. Adjacent benchmarks

Read at abstract granularity 2026-08-13. The common structure: **all are benchmarks** — curated task suites executed against a fixed corpus, with the researcher choosing the tasks. None randomises a memory policy over live traffic, and none reports a pre-registered effect estimate. That is the axis on which this paper differs, and it is a difference of *method*, not of *problem statement* (see §4).

### 3.1 Agent-centric, test-time learning — the nearest neighbours

| Work | ID | What it does (abstract-level) | Relation to us |
|---|---|---|---|
| **Evo-Memory** | arXiv:2511.20857 (Wei et al., Nov 2025; v2 May 2026) | Argues existing evaluation "mostly focus[es] on static conversational settings, where memory is passively retrieved from dialogue to answer queries, overlooking the dynamic ability to accumulate and reuse experience across evolving task streams." Benchmarks self-evolving memory over continuous task streams. | **Same diagnosis, different instrument.** They fix it with a task-stream benchmark; we fix it with randomisation on a live fleet. Note the first author is also a core contributor to the survey. |
| **LifelongAgentBench** | arXiv:2505.11942 (Zheng et al., May 2025) | "First unified benchmark to systematically assess the lifelong learning ability of LLM agents": skill-grounded interdependent tasks across Database, OS and Knowledge Graph environments, with automatic label verification. | Interdependence across tasks is the shared concern. Their environments are curated and verifiable by construction; our outcome must be **adjudicated**, which is why the panel and its κ exist. |
| **OdysseyBench** | arXiv:2508.09124 (Aug 2025) | Long-horizon office-application workflows; argues existing benchmarks "predominantly focus on atomic tasks that are self-contained and independent, failing to capture the long-term contextual dependencies and multi-interaction coordination required in realistic scenarios." | Same complaint about atomicity, applied to office workflows. Simulated environment; no memory-policy contrast. |
| **InterruptBench** | arXiv:2604.00892 (Zou et al., Apr 2026) | "First systematic study of interruptible agents in long-horizon, environmentally grounded web navigation tasks, where actions induce persistent" state — users adding requirements or revising goals mid-execution. | The closest thing to a *non-stationary* setting in this list, and the survey cites it in §9.6 as relaxing the reset-centric assumption. Authors overlap heavily with the survey team (Huang, Yu). |

### 3.2 User-centric, offline

| Work | ID | Note |
|---|---|---|
| **HaluMem** | arXiv:2511.03506 (v3 Jan 2026) | "Evaluating Hallucinations in Memory Systems of Agents" — fabrication, errors, conflicts and omissions during storage and retrieval; argues existing evaluation of memory hallucination is primarily end-to-end. **Source of the Memory Integrity / False Memory Rate metrics.** Relevant to us as an *instrument* (roadmap S1, KG health), not as a competitor. |
| LoCoMo, LongMemEval, PersonaMem, MemBench, ConvoMem, PrefEval | survey Table 4 | Long-context recall, question-typed memory abilities, evolving preference, capacity/efficiency, preference adherence. Offline and user-centric; the survey itself notes LoCoMo "implicitly assume[s] stationary user intent and unambiguous ground truth" and that PersonaMem "does not assess memory update or refresh" (§9.6). Not read; characterised from the survey only. |

---

## 4. Direct prior art — MemoryArena, read in full (2026-08-15)

**MemoryArena** — arXiv:2602.16313 (He, Wang, Zhi, Hu, …, McAuley, Choi, Pentland; 18 Feb 2026). It states the gap this paper opens with — *retrieval metrics do not capture how memory guides decisions* — and states it first.

**Design, as read.** 766 human-crafted tasks over four environments (bundled web shopping, group travel planning, progressive web search, formal math/physics reasoning), averaging 6.9 interdependent subtasks and 57 action steps. Each subtask runs in its own session; the trace is inaccessible once the session ends, which is what forces the persistent-memory dependency. Formalised as a Memory-Agent-Environment loop with `Retrieve` and `Update`, and interpreted as a POMDP where external memory approximates belief-state estimation. Metrics: Task Success Rate, Progress Score, and SR@*k* by subtask depth. Task agent held fixed (GPT-5.1-mini) while the memory system varies across long-context buffers, four external memory systems (MemGPT, Mem0, Mem0-g, ReasoningBank) and four RAG variants.

**What the full read settles — the distinguishing axis did not narrow.** The worry in the previous version of this section was that MemoryArena might already contrast memory-augmented against memory-free conditions in a way that leaves us only pre-registration. It does contrast them, but **observationally**: every system is run over the same fixed task suite and the systems are compared to each other. There is **no randomisation, no assignment mechanism, and no counterfactual estimand** — the paper does not claim one, and its framing (an "evaluation gym") does not require one. The comparison is between *systems*, holding tasks fixed; ours is between *policies*, holding the system fixed and randomising over traffic the researcher did not choose.

**A finding of theirs that our design is built to test causally.** Under the heading *"External Memory and RAG Systems Are Not Universally Beneficial"*, they report that augmenting the agent with external memory or RAG does **not** consistently beat the model's own long-context history, and attribute it to representation mismatch and training mismatch. This is exactly the kind of claim that an observational comparison can surface but not identify: it is confounded with which tasks were curated, with the fixed backbone, and with each system's tuning. Our contribution is not to notice this — they noticed it — but to make it an **estimand**.

Two consequences for the manuscript, both unchanged and both mandatory:

1. **The novelty claim sits on the method.** Not the observation that the field measures representation instead of decision — that is published prior art with a strong author list. The method: a pre-registered, randomised crossover on a live production fleet, with adjudicated outcomes and a seed declared before the beacon round existed.
2. **Any framing that implies we noticed it first is false** and would be caught by any reviewer who knows this literature — plausibly including the survey authors, since Julian McAuley and Yu Wang appear on both MemoryArena and the survey.

### 4.1 Evo-Memory, read in full (2026-08-15) — and the opening it leaves

**Evo-Memory** — arXiv:2511.20857 (Wei, Sachdeva, Coleman, …, Chi, Wang, Pereira, Kang, Cheng; Nov 2025, v2 May 2026; Google Research + UIUC). Restructures ten static datasets into streaming task sequences under a unified `search → synthesis → evolve` loop, benchmarks ten-plus memory modules on Gemini-2.5 and Claude backbones, and proposes ExpRAG and ReMem. API cost reported on the order of tens of thousands of USD.

**The load-bearing sentence for us**, verbatim from §A.2:

> "Across all experiments, we maintain a **unified task sequence ordering** within each dataset, ensuring consistent memory evolution dynamics for all models."

Order is **held fixed**, and fixing it is presented — correctly, for their purpose — as a fairness measure: every system sees the same stream. But their own §4.2.3 then measures how much order matters, comparing Easy→Hard against Hard→Easy, and finds swings of up to **12 points** of average success (ExpRAG 0.57 vs 0.69) with the same system on the same tasks. They conclude by highlighting *"the importance of task sequence design for fair evaluation and effective learning"*, and they list "Sequence robustness" among their four metric dimensions — evaluated across **two chosen orders**, not sampled ones.

**This is the clearest opening in the literature for a randomised design, and it is one the authors themselves point at.** Order of experience is a first-order determinant of measured memory performance; the field's response so far has been to *hold it constant and disclose that*, which controls it for comparability across systems but leaves the effect of any one policy entangled with the particular order chosen. Randomisation is the standard answer to precisely this problem, and no one in this literature applies it.

Note also that the first author is a core contributor to the Huang et al. survey, and that MemoryArena's Table 1 marks Evo-Memory as having no enforced cross-session dependency — the two nearest neighbours already disagree about each other's coverage, which is worth one sentence as evidence that the evaluation question is unsettled.

### 4.2 InterruptBench — the other non-stationarity, and it is not ours

**InterruptBench** — arXiv:2604.00892 (Zou et al., Apr 2026). Derived from WebArena-Lite, it formalises three interruption types (addition, revision, retraction) and evaluates six backbones on whether agents adapt when the *user changes their mind* mid-task.

Read at abstract granularity, and that suffices for our purpose, because the relevant point is a **distinction, not an overlap**. Both works are about non-stationarity, but of different objects:

- **Theirs:** the *user's intent* changes during execution. The environment and the agent's memory are stable; the target moves.
- **Ours:** the *memory itself* changes because it accumulates. Intent is whatever production traffic brings, and the thing that drifts is the stock of eligible signatures — which we measured growing from 0 to 64 across the pilot corpus without saturating (`PREREG-DRAFT.md`, Appendix B note).

Neither subsumes the other, and conflating them would be a mistake: an agent could be perfectly interruptible and still have a memory whose composition never changes what it does. Worth one sentence in the manuscript as the nearest work on the non-stationary axis, with the distinction stated.

### 4.3 "hypotree" — resolved 2026-08-15, and it was not a paper

Carried in our notes as prior art with an unresolvable citation. It resolves to an **MCP server** (`mcpservers.org/servers/tygryso/hypotree`, published 2026-07-31), not to an academic work — which is why it never appeared in the survey's 218 references and why the citation could not be found.

It is worth knowing about anyway, because it occupies the same cell we do. Its own description — *"Current agent memory is passive: vector stores and scratchpads accumulate facts but never revise them"* — is the same complaint the systems-characterisation paper makes in its Recommendation 9, and it implements the same answer we do: a hypothesis DAG over SQLite-WAL that retracts dependent beliefs when a premise collapses, tagged *"memory that forgets"*.

**Cite as a related system, never as prior art for the claim.** It makes no measurement claim, runs no experiment, and reports no effect. The pending note in our records is closed: it was neither a paper nor a competitor, and carrying it as an unresolved reference for weeks was worse than either.

---

## 5. What we adopt, and what we refuse

**Adopted** — the survey's vocabulary (substrate / cognitive mechanism / subject), because it is now the coordinate system reviewers will use, and its framing of memory as *the substrate of agent self-evolution* rather than passive storage.

**Refused, deliberately** — the direction §9.3 points to: parametric/latent memory and memory controllers trained by reinforcement learning (MEM1, Mem-α). Three reasons, in order of weight: (i) it requires training, which breaks the "runs locally, costs nothing" property that is our stated autonomy pillar; (ii) it makes memory non-inspectable by the user, contradicting the §9.4 desideratum of user-controllable inspection, editing and revocation that we do satisfy; (iii) the research cost does not fit our capacity. Registered in `docs/DECISIONS.md` **NÃO FAZEMOS #30** so the omission reads as a decision rather than an oversight.

---

## 6. Positioning, one sentence

The observation that memory evaluation scores representation rather than decision is established (MemoryArena, Feb 2026; Evo-Memory, Nov 2025), and that the *order* in which experience arrives moves measured memory performance by double-digit margins is established too (Evo-Memory §4.2.3) — what is not established is an **effect estimate under randomised order**: this paper randomises memory composition across epochs on a live agent fleet, under a pre-registered protocol with adjudicated outcomes, to measure whether the policy changes what agents *do* under the traffic they actually receive.

The three sit in a clean progression, and the manuscript should say so plainly: MemoryArena fixes the *tasks* and varies the *system*; Evo-Memory fixes the *order* and varies the *system*; we fix the *system* and randomise the *policy over unchosen traffic*. Each controls what the previous left free. None of the three subsumes another.

---

## Open before manuscript

1. ✅ **MemoryArena** (2602.16313) read in full 2026-08-15 — §4 rewritten. The distinguishing axis did **not** narrow: their comparison is observational, between systems on fixed tasks.
2. ✅ **Evo-Memory** (2511.20857) read in full 2026-08-15 — §4.1 added. They hold task order fixed by design and separately measure that order is worth up to 12 points; they recommend care in sequence design, which is the problem randomisation solves.
3. ✅ **InterruptBench** (2604.00892) read at abstract level 2026-08-15 — §4.2. Their non-stationarity is the *user's intent*; ours is the *memory stock*. Distinct, and the manuscript must say so.
4. ✅ **"hypotree" resolved 2026-08-15** — §4.3. It is an **MCP server**, not a paper; that is why the citation was never findable. Cite as a related system, never as prior art.
5. Decide whether HaluMem's MI/FMR are adopted as KG-health instruments (roadmap S1) — an engineering decision, separate from this paper.

## Provenance

- Survey read in full 2026-08-13; string counts reproduced via `pdftotext` over `2602.06052v4`. arXiv IDs for §3 extracted from the survey's own bibliography, then confirmed against arXiv.
- §3 written from arXiv abstracts and metadata, **not** from full papers.
- §4 and §4.1 written from the full texts of 2602.16313 and 2511.20857, read 2026-08-15. Quotations verified against the arXiv HTML.
- Analysis and the Stanford-authorship finding: memory `[[project_agent_memory_survey_tmlr_2602_06052]]`.
- Gap statement also recorded, dated, in `PREREG-DRAFT.md` §1 as a declared non-substantive addition.
