# Related Work — Paper 2 (Interventional Memory)

> **Status:** v0.2, 2026-08-13. Sections 1, 2, 5 and 6 are written against a source **read in full** (Huang et al., TMLR 07/2026). Sections 3 and 4 are written against **abstracts and metadata read directly from arXiv**, plus each work's row in the survey's own tables — **not against the full papers**. Every claim below is at abstract granularity and is marked as such; before any of it enters a manuscript, the papers marked ⚠️ must be read in full, because the manuscript's positioning depends on them.
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

## 4. ⚠️ Direct prior art — MemoryArena, and what it costs us

**MemoryArena** — arXiv:2602.16313 (He, Wang, Zhi, Hu, …, McAuley, Choi, Pentland; 18 Feb 2026). Abstract, verbatim in the load-bearing part:

> "Existing evaluations of agents with memory typically assess memorization and action in isolation. One class of benchmarks evaluates memorization by testing recall of past conversations or text **but fails to capture how memory is used to guide future decisions**. Another class focuses on agents acting in single-session tasks without the need for long-term memory. However, in realistic settings, memorization and action are tightly coupled…"

**This must be confronted, not buried.** MemoryArena states the gap this paper opens with — *retrieval metrics do not capture how memory guides decisions* — and states it first, in February 2026. Two consequences, both mandatory:

1. **The novelty claim must move.** Our contribution is **not** the observation that the field measures representation instead of decision; that observation is published prior art with a strong author list. Our contribution is the **method**: a pre-registered, randomised crossover on a live production fleet, with adjudicated outcomes and a declared seed — an *experiment*, where MemoryArena builds a *benchmark*. Benchmarks establish comparability under researcher-chosen tasks; randomisation establishes an effect estimate under the traffic the system actually receives. Both are needed; they are not the same claim.
2. **Any framing that implies we noticed it first is now false** and would be caught by any reviewer who knows this literature — plausibly including the survey authors, since Julian McAuley and Yu Wang appear on both MemoryArena and the survey.

⚠️ **MemoryArena must be read in full before the manuscript is drafted.** Its design decisions constrain how we position: if it already contrasts memory-augmented against memory-free conditions, the distinguishing axis narrows to live-traffic randomisation and pre-registration alone — still a real axis, but a narrower one that must be claimed precisely.

**"hypotree"** — carried in our project notes as prior art; the actual citation was never resolved and it is not cited in the survey. Either resolve it to a real work or drop it from our notes; an unresolvable reference is worse than none.

---

## 5. What we adopt, and what we refuse

**Adopted** — the survey's vocabulary (substrate / cognitive mechanism / subject), because it is now the coordinate system reviewers will use, and its framing of memory as *the substrate of agent self-evolution* rather than passive storage.

**Refused, deliberately** — the direction §9.3 points to: parametric/latent memory and memory controllers trained by reinforcement learning (MEM1, Mem-α). Three reasons, in order of weight: (i) it requires training, which breaks the "runs locally, costs nothing" property that is our stated autonomy pillar; (ii) it makes memory non-inspectable by the user, contradicting the §9.4 desideratum of user-controllable inspection, editing and revocation that we do satisfy; (iii) the research cost does not fit our capacity. Registered in `docs/DECISIONS.md` **NÃO FAZEMOS #30** so the omission reads as a decision rather than an oversight.

---

## 6. Positioning, one sentence

The observation that memory evaluation scores representation rather than decision is established (MemoryArena, Feb 2026; Evo-Memory, Nov 2025); what is not established is an **effect estimate** — this paper randomises memory composition across epochs on a live agent fleet, under a pre-registered protocol with adjudicated outcomes, to measure whether the policy changes what agents *do* under the traffic they actually receive.

---

## Open before manuscript

1. ⚠️ Read **MemoryArena** (2602.16313) in full — the positioning in §4 depends on its design.
2. ⚠️ Read **Evo-Memory** (2511.20857) in full — nearest neighbour on the test-time-learning axis.
3. Read InterruptBench (2604.00892) — the only non-stationary neighbour.
4. Resolve or drop "hypotree".
5. Decide whether HaluMem's MI/FMR are adopted as KG-health instruments (roadmap S1) — an engineering decision, separate from this paper.

## Provenance

- Survey read in full 2026-08-13; string counts reproduced via `pdftotext` over `2602.06052v4`. arXiv IDs for §3 extracted from the survey's own bibliography, then confirmed against arXiv.
- §3 and §4 written from arXiv abstracts and metadata, **not** from full papers.
- Analysis and the Stanford-authorship finding: memory `[[project_agent_memory_survey_tmlr_2602_06052]]`.
- Gap statement also recorded, dated, in `PREREG-DRAFT.md` §1 as a declared non-substantive addition.
