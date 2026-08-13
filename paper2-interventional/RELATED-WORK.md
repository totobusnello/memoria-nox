# Related Work — Paper 2 (Interventional Memory)

> **Status:** v0.1, opened 2026-08-13. **Sections 1, 2, 5 and 6 are written against a source read in full** (Huang et al., TMLR 07/2026). **Sections 3 and 4 are a working table, not prose**: every row marked `TODO — requires reading` names a work known only through the survey's own tables or through our project notes. Nothing in this file may be lifted into a manuscript while a `TODO` remains on the row it depends on.
>
> Prior to this file, the Paper 2 workspace contained **no external citation of any kind** — this is the first.

---

## 1. Positioning against the canonical taxonomy

Huang et al., *A Survey of Agent Memory in the Second Half: Towards Self-Evolving and Long-Horizon Agents* (TMLR 07/2026; arXiv:2602.06052v4) surveys 218 papers and organises foundation-agent memory along three orthogonal axes. Stating our coordinates in their frame is the cheapest way to let a reviewer locate this work:

| Axis (survey §) | Their categories | Where nox-mem / Paper 2 sits |
|---|---|---|
| **Memory substrate** (§3.1) | internal (weights, latent state, KV cache) vs. external (vector index, text record, structural store, hierarchical store) | **External**, specifically *structural store* — SQLite + FTS5 + sqlite-vec + a typed knowledge graph. We hold **no** internal-memory component, deliberately (see §5). |
| **Cognitive mechanism** (§3.2) | sensory, working, episodic, semantic, procedural | **Episodic + semantic**, with procedural present but underdeveloped (`crystallize`). The intervention under test operates on *episodic* records weighted by adjudicated outcome. |
| **Memory subject** (§3.3) | user-centric vs. agent-centric | **Agent-centric.** The unit of study is a fleet of production agents accumulating their own experience, not a user profile being personalised. |

The survey's Figure 3 shows agent-centric work (146 papers) having overtaken user-centric (72) during 2025. Our position is on the growing side of that split, which is worth one sentence in the manuscript and no more.

---

## 2. What the field measures — and the cell that is empty

The survey's **Table 3** enumerates the metrics in use across foundation-agent memory evaluation and partitions them exhaustively into three families:

- **accuracy-based** — Accuracy/Memory Accuracy, F1, Recall@K, MAP, NDCG@K, Success Rate / Goal Completion, Pass@K / Resolved Rate, Memory Integrity, False Memory Rate;
- **similarity-based** — ROUGE, BLEU, Distinct-*n*, BERTScore, FactScore, Perplexity;
- **LLM-as-a-judge** — Response Correctness, Faithfulness/Groundedness, Preference Following.

Every one of these scores either **what was retrieved** (Recall@K, MAP, NDCG@K), **what was written** (Memory Integrity, False Memory Rate), or **what was said** (the similarity and judge families). **None measures whether the retrieved memory changed the agent's decision or action** — which is the quantity this paper randomises over. This is the gap statement, and it can now be made by citation rather than by assertion.

Two further admissions in the survey sharpen it:

- **Table 4** marks *Compression & Summarization* (CS) and *Forgetting & Retention* (FR) as "comparatively under-evaluated" across the user-centric benchmark set, and notes that *Abstain & Boundary Handling* (AB) is "inconsistently required", with only a few benchmarks explicitly rewarding abstention.
- **§9.6** independently proposes, as future work, the design this study pre-registers: closed-loop, longitudinal, execution-grounded evaluation comparing *"memory-augmented agents and memory-free baselines under identical conditions"*, with provenance metadata, versioned and rollback-able persistent state, MCP-style tool mediation for reproducible logging and replay, and explicit resource–utility accounting.

**Verified by string search over the extracted text of the survey (2026-08-13):** `pre-registration` / `preregistration` — **0 occurrences** in 54 pages; `interventional` — 1 (in passing, §5); `counterfactual` — 1, in §9.6, as a suggested future direction. These are claims about strings in one document, which is what makes them checkable; they are *not* a claim that no one has ever pre-registered a memory experiment.

---

## 3. Adjacent benchmarks — working table `⚠️ TODO`

The hypothesis to be tested against each row is: *these are reset-centric or offline, and none randomises over live traffic.* **Not yet verified for any row.**

### 3.1 User-centric, offline (survey Table 4)

| Work | Known from | Claimed distinction | Status |
|---|---|---|---|
| LoCoMo | Survey Table 4; our own Q4 harness | Long-context retrieval accuracy; survey itself notes it "implicitly assume[s] stationary user intent and unambiguous ground truth" (§9.6) | `TODO — requires reading` |
| LongMemEval | Survey Table 4 (JUDGE, Recall@K, NDCG@K) | Categorises questions by memory ability; still offline | `TODO — requires reading` |
| HaluMem | Survey Table 4 (MA, MI, FMR) | **Source of the FMR/MI metrics we may adopt for KG health (roadmap S1)** — relevant as instrument, not as competitor | `TODO — requires reading` |
| PersonaMem | Survey Table 4 + §9.6 | Targets evolving preference; survey notes it "does not assess memory update or refresh" | `TODO — requires reading` |
| MemBench, ConvoMem, MemoryBench, PrefEval | Survey Table 4 | Capacity/efficiency and preference adherence | `TODO — requires reading` |

### 3.2 Agent-centric with test-time learning (survey Table 5, `TTL` tag)

These are the closest neighbours — the only benchmarks in the survey tagged for experience accumulation across episodes.

| Work | Size / env (per Table 5) | Claimed distinction | Status |
|---|---|---|---|
| Evo-Memory | ~3,700 · TEXT · QA/MT · SIM | Simulated, reset-centric | `TODO — requires reading` |
| LifelongAgentBench | 1,396 · APP/OS · API/MT · MIX | Lifelong across episodes, but curated environment | `TODO — requires reading` |
| OdysseyBench | 602 · APP · GUI/MT · MIX | Long-horizon app workflows | `TODO — requires reading` |
| InterruptBench | Cited in survey §9.6 (Zou et al., 2026) | Augments WebArena-Lite with mid-task additions, revisions, retractions | `TODO — requires reading` |

---

## 4. Direct prior art — `⚠️ TODO`

| Work | Known from | Why it matters | Status |
|---|---|---|---|
| MemoryArena (arXiv:2602.16313) | Our own project notes | Nearest prior art identified before the survey existed | `TODO — requires reading` |
| "hypotree" | Our own project notes | Same | `TODO — requires reading, including resolving the actual citation` |

**Note worth keeping:** neither is cited anywhere in the survey (verified by string search). That cuts both ways — it may mean they are peripheral, or it may mean the survey missed them. Do not use their absence as evidence of anything until both are read.

---

## 5. What we adopt, and what we refuse

**Adopted** — the survey's vocabulary (substrate / cognitive mechanism / subject), because it is now the coordinate system reviewers will use, and its framing of memory as *the substrate of agent self-evolution* rather than passive storage.

**Refused, deliberately** — the direction §9.3 points to: parametric/latent memory and memory controllers trained by reinforcement learning (MEM1, Mem-α). Three reasons, in order of weight: (i) it requires training, which breaks the "runs locally, costs nothing" property that is our stated autonomy pillar; (ii) it makes the memory non-inspectable by the user, contradicting the §9.4 desideratum of user-controllable inspection, editing and revocation that we do satisfy; (iii) the research cost does not fit our capacity. This refusal is registered in `docs/DECISIONS.md` under **NÃO FAZEMOS** so that the omission reads as a decision rather than an oversight.

---

## 6. Positioning, one sentence

The field evaluates memory by what it retrieves and what it says; this paper randomises memory composition on a live agent fleet and measures whether it changes what the agent *does* — the design the canonical survey of the area names as open, and does not report anyone having run.

---

## Provenance

- Survey read in full 2026-08-13; string counts reproduced via `pdftotext` over `2602.06052v4`.
- Analysis and the Stanford-authorship finding: memory `[[project_agent_memory_survey_tmlr_2602_06052]]`.
- Gap statement also recorded, dated, in `PREREG-DRAFT.md` §1 as a declared non-substantive addition.
