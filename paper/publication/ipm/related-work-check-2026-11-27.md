# Related-work citation check, Sections 2.1–2.4 of `manuscript.md` (2026-11-27)

Scope: every reference dated 2025 or 2026 that Sections 2.1–2.4 cite (31 papers). For each, the paper text was
fetched on 2026-11-27: arXiv metadata and abstract from `export.arxiv.org/api/query`, and the full PDF from
`arxiv.org/pdf/<id>` (latest version), converted with `pdftotext`. Venue claims not visible on arXiv were checked
by web search (ACL Anthology, ACM DL, project repository). Quotes are verbatim from those texts; where `pdftotext`
interleaves two columns, only one column's contiguous words are quoted and `[...]` marks a cut. No verdict
below is from memory.

Verdict scale: SUPPORTED · PARTLY (with the overreaching words and a minimal correction) · NOT SUPPORTED ·
COULD NOT READ.

---

## 2.1 Memory systems for LLM agents

### 1. Zhang et al. (2025a), *A Survey on the Memory Mechanism of Large Language Model based Agents* — arXiv:2404.13501

**Manuscript:** "Surveys organize agent memory by what is stored and how it is written, read and managed (Zhang et al., 2025a)"

**Paper (Section 1, Introduction):** "For the memory design, we discuss previous works from three dimensions, that is,
memory sources, memory forms, and memory operations."
**Paper (Section 5.3):** "including memory writing, memory management, and memory reading." (Table of contents:
"5.3.1 Memory Writing", "5.3.2 Memory Management", "5.3.3 Memory Reading".)

**Verdict: SUPPORTED.** Sources/forms = what is stored; the three operations = written, managed, read.

**Reference entry:** title, first author (Zeyu Zhang), arXiv id match (arXiv v1 2024-04-21). The TOIS version exists
(ACM DL, doi:10.1145/3748302); its title is hyphenated "Large Language Model-based Agents". Consider adding the DOI
and using the ACM title.

### 2. Gao et al. (2026), *A Survey of Self-Evolving Agents* — arXiv:2507.21046

**Manuscript:** "and self-evolving agents by what, when, how and where they adapt (Gao et al., 2026)."

**Paper (title):** "A Survey of Self-Evolving Agents: What, When, How, and Where to Evolve on the Path to Artificial
Super Intelligence".
**Paper (Section 1):** "We organize our analysis around three foundational questions — what, when, and how to evolve
— and provide a structured framework for understanding each." The taxonomy figure has a fourth branch, "Where to
Evolve", split into "General Domain" and "Specialized Domain".

**Verdict: SUPPORTED.** (The body calls what/when/how the three foundational questions; "where" is the
application-domain branch of the title and taxonomy. Wording is accurate.)

**Reference entry:** title, first author (Huan-ang Gao), arXiv id match; arXiv comment: "Transactions on Machine
Learning Research (01/2026)". OK.

### 3. Chhikara et al. (2025), *Mem0* — arXiv:2504.19413

**Manuscript:** "Vector stores with a metadata layer, such as Mem0 (Chhikara et al., 2025), extract facts from
dialogue with an LLM and index them."

**Paper (Section 2.1, extraction phase):** "[...] for an extraction function ϕ implemented via an LLM. The function
ϕ(P) then extracts a set of salient memories Ω = {ω1 , ω2 , ..., ωn } specifically from the new exchange [...]
resulting in candidate facts for potential inclusion in the knowledge base."
**Paper (Section 2.1):** "The vector database employs dense embeddings to facilitate efficient similarity search
during the update phase."

**Verdict: SUPPORTED.** (Mem0 also has a graph variant, Mem0^g; the sentence describes the base system.)

**Reference entry:** matches.

### 4. Rasmussen et al. (2025), *Zep* — arXiv:2501.13956

**Manuscript:** "Temporal and graph services, such as Zep (Rasmussen et al., 2025), build a knowledge graph with
validity intervals over the conversation."

**Paper (Abstract):** "Zep addresses this fundamental limitation through its core component Graphiti -- a
temporally-aware knowledge graph engine that dynamically synthesizes both unstructured conversational data and
structured business data while maintaining historical relationships."
**Paper (Section 2.2.3, Temporal Extraction and Edge Invalidation):** "the system tracks four timestamps: t′created
and t′expired ∈ T′ monitor when facts are created or invalidated in the system, while tvalid and tinvalid ∈ T track
the temporal range during which facts held true."

**Verdict: SUPPORTED.**

**Reference entry:** matches.

### 5. Hu et al. (2026a), *EverMemOS* — arXiv:2601.02163

**Manuscript:** "Memory operating systems, such as EverMemOS (Hu et al., 2026a) and MemOS (Li et al., 2025), organize
memory into managed units with their own lifecycle and, in EverOS's case, add a mandatory cross-encoder re-ranker."

**Paper (Abstract):** "We introduce EverMemOS, a self-organizing memory operating system that implements an
engram-inspired lifecycle for computational memory. Episodic Trace Formation converts dialogue streams into MemCells
[...]"
**Paper (implementation details, retrieval configuration):** "[...] and sparse retrieval (BM25) via Reciprocal Rank
Fusion (RRF), followed by episode re-ranking (Qwen3-Reranker-4B (Zhang et al., 2025)). Unless otherwise specified, we
retrieve the top-10 [...]"

**Verdict: PARTLY.** "Managed units with their own lifecycle" is supported. The paper describes a re-ranking stage
with Qwen3-Reranker-4B in its default retrieval configuration, but neither the word "mandatory" nor "cross-encoder"
comes from the paper. "Mandatory" is the manuscript's own observation of the `everos` 1.3.1 release (Table in §4.2,
"`Qwen3-Reranker-4B` (mandatory)"), so the sentence attributes a deployment fact to the citation.

**Proposed wording:** "...organize memory into managed units with their own lifecycle; EverMemOS also re-ranks
retrieved episodes with a 4B re-ranker model (Hu et al., 2026a), which the EverOS release we ran requires
(Section 4.2)."

**Reference entry:** title, first author (Chuanrui Hu), arXiv id match.

### 6. Li et al. (2025), *MemOS: A Memory OS for AI System* — arXiv:2507.03724

**Manuscript:** same sentence as item 5 ("organize memory into managed units with their own lifecycle").

**Paper (Abstract):** "As the basic unit, a MemCube encapsulates both memory content and metadata such as provenance
and versioning."
**Paper (Section 1):** "It builds a modular architecture around the memory lifecycle—including generation,
activation, fusion, archiving, and expiration—supported by components such as MemReader, MemScheduler, MemLifecycle,
and MemOperator [...]"

**Verdict: SUPPORTED.**

**Reference entry:** matches.

### 7. Gutiérrez et al. (2025), *From RAG to Memory* (HippoRAG 2) — arXiv:2502.14802

**Manuscript:** "Graph-based retrieval for RAG, such as HippoRAG (Gutiérrez et al., 2024), HippoRAG 2 (Gutiérrez et
al., 2025) and LightRAG (Guo et al., 2025), spends an LLM call per chunk to build the graph"

**Paper (Figure 2 caption):** "HippoRAG 2 methodology. For offline indexing, we use an LLM to extract open KG triples
from passages, with synonym detection applied to phrase nodes."

**Verdict: SUPPORTED.**

**Reference entry:** matches; arXiv comment "ICML 2025".

### 8. Guo et al. (2025), *LightRAG* — arXiv:2410.05779

**Manuscript:** same sentence as item 7.

**Paper (Section 3, complexity analysis):** "During this phase, we use the large language model (LLM) to extract
entities and relationships from each chunk of text. As a result, the LLM needs to be called total tokens / chunk size
times."

**Verdict: SUPPORTED.**

**Reference entry:** title and authors match; ACL Anthology lists it as Findings of EMNLP 2025
(aclanthology.org/2025.findings-emnlp.568). The page range 10746–10761 was not checked in this pass.

### 9. Quek et al. (2026), *MeMo: Memory as a Model* — arXiv:2605.15156

**Manuscript:** "MeMo (Quek et al., 2026) encodes new knowledge into a separately trained memory model, the opposite
of an inspectable store."

**Paper (Abstract):** "we introduce MeMo (Memory as a Model), a modular framework that encodes new knowledge into a
dedicated memory model while keeping the LLM parameters unchanged."
**Paper (arXiv comment):** "MeMo augments any LLM with up-to-date or domain-specific knowledge via a trained memory
model [...]"

**Verdict: SUPPORTED.** ("the opposite of an inspectable store" is the manuscript's framing, not a claim about the
paper.)

**Reference entry:** matches.

---

## 2.2 Scoring and forgetting

### 10. Wang et al. (2025), *Mem-α* — arXiv:2509.25911

**Manuscript:** "A recent line of work learns the memory policy instead of fixing it: what to write (Mem-α; Wang et al.,
2025)"

**Paper (Abstract):** "language models may lack the ability to determine which information to store, how to structure
it, and when to update it [...] we propose Mem-alpha, a reinforcement learning framework that trains agents to
effectively manage complex memory systems [...] Empirical evaluation demonstrates that Mem-alpha achieves significant
improvements over existing memory-augmented agent baselines."

**Verdict: SUPPORTED.** **Reference entry:** matches.

### 11. Yan et al. (2025), *Memory-R1* — arXiv:2508.19828

**Manuscript:** "which management operation to apply (Memory-R1; Yan et al., 2025)"

**Paper (Abstract):** "a Memory Manager that learns structured operations, including ADD, UPDATE, DELETE, and NOOP
[...] With only 152 training QA pairs, Memory-R1 outperforms strong baselines [...]"

**Verdict: SUPPORTED.** **Reference entry:** matches.

### 12. Zhang et al. (2025b), *Memory as Action* — arXiv:2510.12635

**Manuscript:** "when to curate context (Memory as Action; Zhang et al., 2025b)"

**Paper (Section 1):** "Unlike external memory systems that operate via fixed heuristics, MemAct enables the policy to
autonomously learn when and how to curate its working memory using the Prune&Write operator [...]"
**Paper (Abstract):** "MemAct-RL-14B matches the accuracy of models 16× larger while reducing average context length by
51%".

**Verdict: SUPPORTED.** **Reference entry:** matches.

### 13. Zhou et al. (2025), *MEM1* — arXiv:2506.15841

**Manuscript:** "how to keep a constant-size state across turns (MEM1; Zhou et al., 2025 ...)"

**Paper (Abstract):** "We introduce MEM1, an end-to-end reinforcement learning framework that enables agents to operate
with constant memory across long multi-turn tasks. At each turn, MEM1 updates a compact shared internal state [...]"

**Verdict: SUPPORTED.** **Reference entry:** matches.

### 14. Yu et al. (2026), *MemAgent* — arXiv:2507.02259

**Manuscript:** "...MemAgent, Yu et al., 2026). Each replaces a hand-written rule with a trained one and reports gains
from doing so."

**Paper (Section 1):** "we propose a novel use of Reinforcement Learning (RL) to equip LLMs with a dynamically updated
fixed-length 'memory'".
**Paper (Abstract):** "able to extrapolate from an 8K context trained on 32K text to a 3.5M QA task with performance
loss < 5% and achieves 95%+ in 512K RULER test."

**Verdict: SUPPORTED.** **Reference entry:** matches; arXiv comment "Accepted to ICLR 2026 as an Oral presentation".

---

## 2.3 Raw history against constructed memory

### 15. Zhou et al. (2026a), *Do Conversational Agents Need Explicit Memory?* — arXiv:2610.24671

**Manuscript:** "Zhou et al. (2026a) compared six explicit memory systems with retrieval over the raw history and found
localized gains but no consistent advantage over a strong raw-history baseline."

**Paper (Abstract):** "This study compares six state-of-the-art explicit memory systems with raw-history RAG on
LongMemEval-S and BEAM-100K under original and controlled retrieval settings. We find only localized gains for
particular question types and tight run-time context budgets, with no consistent advantage over strong raw-history RAG
baselines."

**Verdict: SUPPORTED.** **Reference entry:** matches.

### 16. Fang et al. (2025), *LightMem* — arXiv:2510.18866

**Manuscript:** "Their reproduction of LightMem (Fang et al., 2025) found..."

**Paper (Abstract):** "we introduce a new memory system called LightMem [...] organizes memory into three complementary
stages." Zhou et al. (2026b) confirm it is the system reproduced ("In this study, we reproduce LightMem").

**Verdict: SUPPORTED** (identification only). **Reference entry:** matches; arXiv comment "ICLR 2026".

### 17. Zhou et al. (2026b), *Reproducing LightMem* — arXiv:2607.29104

**Manuscript:** "Their reproduction of LightMem (Fang et al., 2025) found that changing only the retriever over a fixed
constructed store moved answer accuracy more than construction did, and that retrieval over constructed memory did not
consistently beat retrieval over raw turns (Zhou et al., 2026b)."

**Paper (Abstract):** "find that retriever choice substantially affects answer accuracy: changing only the retriever
over a fixed LightMem store shifts answer accuracy from 58.1% to 75.5%. Retrieval over constructed memory also does
not consistently outperform raw-turn retrieval."
**Paper (Section 4.2, RQ1 results):** "In our runs, (𝑟 =0.6, 𝑡ℎ=768) and (𝑟 =0.8, 𝑡ℎ=1024) achieve 68.2% and 70.7%
accuracy, respectively, exceeding Full-context at 60.8% and Naive RAG at 67.3%. By contrast, (𝑟 =0.4, 𝑡ℎ=768) reaches
57.0% and underperforms both baselines."
**Paper (RQ3, Finding 2):** "At the smallest budget, LightMem outperforms Naive RAG for most retrievers, with an
average advantage of 5.5 accuracy points."

**Verdict: PARTLY.** The second clause is verbatim-supported. "moved answer accuracy more than construction did" is
not a finding the paper states; it is an inference. The numbers allow it (17.4 points across retrievers vs. 13.7
across the three construction configurations, and ≤5.5 points between LightMem and Naive RAG), but the paper never
makes that comparison, so it reads as the authors' claim.

**Proposed wording:** "...found that changing only the retriever over a fixed constructed store moved answer accuracy
from 58.1% to 75.5%, and that retrieval over constructed memory did not consistently beat retrieval over raw turns
(Zhou et al., 2026b)." (If the comparison is kept, mark it as ours: "a wider spread than across its three
construction configurations, 57.0% to 70.7%".)

**Reference entry:** matches; arXiv comment "Accepted at SIGIR-AP 2026".

### 18. Bao et al. (2026), *Is Complex Agentic Memory Always Needed?* — arXiv:2610.30755

**Manuscript:** "Bao et al. (2026) ranked naive retrieval over raw turns first among the compared memory systems,
EverMemOS, MemOS and Mem0 among them, in most of their benchmark and model settings"

**Paper (Abstract):** "We study Raw-RAG, a naive RAG baseline using dense retrieval and reranking over raw history
[...] Across LoCoMo, LongMemEval, MEME, and MemoryAgentBench, Raw-RAG ranks first among the compared memory systems in
six of seven benchmark-model settings".
**Paper (Section 4.1):** "Baselines include EverMemOS [10], MemOS [21], EMem [59], SimpleMem [23], MemU [31],
MemMachine [49], Mem0 [4], Memora [53], Nemori [30], MemoryOS [16], A-MEM [54], and RecMem [5], alongside
Full-context."
**Paper (Section 4.2):** "Raw-RAG achieves the highest score among the compared memory systems in six of seven
benchmark–model settings, excluding Full-context."

**Verdict: SUPPORTED.** Advisory: the paper's "naive" baseline includes a re-ranker ("dense retrieval and
cross-encoder reranking", Section 1). Since the manuscript attributes EverOS's lead to its re-ranker, "naive retrieval
with re-ranking over raw turns" would be more exact and avoids a reader assuming plain dense retrieval.

**Reference entry:** matches.

### 19. He et al. (2026), *Memory Tax* — arXiv:2610.34073

**Manuscript:** "He et al. (2026) reached the same direction on a different set of systems."

**Paper (Abstract):** "Through a large-scale evaluation across multiple benchmarks and model backbones, we find many
dedicated memory systems underperform naive RAG in many cases, indicating a negative net value."
**Paper (Section 3.1):** "We evaluate on LongMemEval-s (Wu et al., 2025), PersonaMem-v2 (Jiang et al., 2025b), and
MINT-Eval (Lee et al., 2026)."
**Paper (Table 1, method rows):** A-Mem, MemOS, SimpleMem, MemoryOS, LightMem, OpenViking, HippoRAG2, MAGMA, PlugMem,
Mem-T, Memory-R2.

**Verdict: PARTLY.** "Same direction" is supported. "A different set of systems" overreaches: four of He et al.'s
eleven systems (MemOS, SimpleMem, MemoryOS, A-Mem) are also in Bao et al.'s baseline list. What differs is most of the
set (no EverMemOS or Mem0; LightMem, HippoRAG 2 and trained policies added) and two of three benchmarks.

**Proposed wording:** "He et al. (2026) reached the same direction on a partly overlapping set of systems (LightMem
and HippoRAG 2 among them) and different benchmarks."

**Reference entry:** matches (11 authors on arXiv; first eight as listed).

### 20. Yuan et al. (2026), *Diagnosing Retrieval vs. Utilization Bottlenecks* — arXiv:2603.02473

**Manuscript:** "Yuan et al. (2026) crossed three write strategies (raw chunks, extracted facts, summaries) with three
retrieval methods and found retrieval to matter more than write-time sophistication." Also §2.3 ¶2: "The finding of
Yuan et al. (2026) that the retrieval method dominates..."

**Paper (Abstract):** "a 3x3 study crossing three write strategies (raw chunks, Mem0-style fact extraction,
MemGPT-style summarization) with three retrieval methods (cosine, BM25, hybrid reranking). On LoCoMo, retrieval method
is the dominant factor: average accuracy spans 20 points across retrieval methods (57.1% to 77.2%) but only 3-8 points
across write strategies. [...] We argue that, under current retrieval practices, improving retrieval quality yields
larger gains than increasing write-time sophistication."

**Verdict: SUPPORTED.** **Reference entry:** matches; arXiv comment "Accepted at the MemAgents Workshop, ICLR 2026".

### 21. Sharma & Lall (2026), *When Does Selection Replace Extraction?* — arXiv:2609.34227

**Manuscript:** "In a pre-registered test, Sharma and Lall (2026) found raw turns selected by a typed decision model
non-inferior to an LLM-extraction memory."

**Paper (Abstract):** "At a tight budget on LoCoMo, raw turns selected by a single call to Jev, a typed decision model,
are non-inferior to an LLM-extraction memory (one-sided 95% bound -3.0 points against a -5-point margin). [...] At
generous budgets it adds 1.5 and 1.1, and extraction systems are more accurate."
**Paper (Section 3, primary test):** "The primary test H1 compares Turns + Jev with engram v2 question by question."

**Verdict: PARTLY.** The sentence drops the condition the result is tied to (tight budget, LoCoMo) and omits that
extraction was more accurate at generous budgets, which cuts against the direction of the paragraph.

**Proposed wording:** "In a pre-registered test, Sharma and Lall (2026) found raw turns selected by a typed decision
model non-inferior to an LLM-extraction memory at a tight context budget on LoCoMo, while extraction was more accurate
at generous budgets."

**Reference entry:** matches.

### 22. Ma et al. (2025), *What Deserves Memory* (Nemori) — arXiv:2508.03341

**Manuscript:** "Constructed-memory systems continue to report strong results on the same benchmarks (Ma et al., 2025,
among others: ...)"

**Paper (Abstract):** "Extensive experiments confirm that NEMORI achieves strong performance, efficiency, and storage
reduction."
**Paper (Section 4.7, Scalability Analysis):** "We evaluate on LongMemEvalS (105K), an order of magnitude longer than
LoCoMo (9K). As shown in Table 8, NEMORI outperforms Full Context by +16.7% on gpt-4o-mini and +13.7% on gpt-4.1-mini,
a substantial increase from the marginal gains on LoCoMo (+1.0% and +0.2%)."

**Verdict: SUPPORTED** (evaluated on LoCoMo and LongMemEval-S).

**Reference entry:** arXiv v4 lists four authors (adds Yize Chen); the ACL 2026 Anthology entry
(2026.acl-long.1607; dblp: ACL (1) 2026: 34789–34812) lists three: Wenquan Ma, Jiayan Nan, WenLong Wu. The entry
cites the arXiv author list but says "Published in ACL 2026". Pick one version: either cite the ACL paper with three
authors and year 2026, or the arXiv preprint with four authors and no venue. In-text year is 2025.

### 23. Liu et al. (2026), *SimpleMem* — arXiv:2601.02553

**Manuscript:** "(... SimpleMem, Liu et al., 2026; ...)" in the same sentence as item 22.

**Paper (Section 4, Benchmark Dataset):** "We evaluate performance on the LoCoMo (Maharana et al., 2024) and
LongMemEval-S (Wu [...]".
**Paper (Abstract):** "achieving an average F1 improvement of 26.4% in LoCoMo while reducing inference-time token
consumption by up to 30-fold".

**Verdict: SUPPORTED.**

**Reference entry:** title, authors, arXiv id match. Venue: the arXiv v3 PDF header reads "Preprint. January 30,
2026." and the arXiv comment is empty; the only ICML 2026 evidence found is the project repository title "[ICML'26]
SimpleMem" (github.com/aiming-lab/SimpleMem). Confirm against the ICML 2026 proceedings before submission, or drop the
venue.

### 24. Dai et al. (2026), *RecMem* — arXiv:2605.16045

**Manuscript:** "(... RecMem, Dai et al., 2026; ...)"

**Paper (Abstract):** "Experiments show that RecMem reduces the memory construction token cost of three SOTA memory
systems by up to 87% while exceeding their accuracy."
**Paper (Section 4.2):** "despite large reductions in construction tokens, RecMem attains the best overall score on
LongMemEval-S." (Table 2: "Results on the LongMemEval-S benchmark"; LoCoMo is the other benchmark.)

**Verdict: SUPPORTED.** **Reference entry:** matches; arXiv comment "Accepted to ACL 2026 Findings".

### 25. Li et al. (2026), *TiMem* — arXiv:2601.02845

**Manuscript:** "(... TiMem, Li et al., 2026)"

**Paper (Abstract):** "Under a consistent evaluation setup, TiMem achieves state-of-the-art accuracy on both
benchmarks, reaching 75.30% on LoCoMo and 76.88% on LongMemEval-S."

**Verdict: SUPPORTED.** **Reference entry:** matches; arXiv comment "ACL 2026 Findings".

---

## 2.4 Comparing memory systems

### 26. Wu et al. (2025), *LongMemEval* — arXiv:2410.10813

**Manuscript:** "LoCoMo (Maharana et al., 2024) and LongMemEval (Wu et al., 2025) provide gold evidence per question,
which allows a retrieval metric"

**Paper (Section 3, benchmark construction):** "manually decompose the answer into one or more evidence statements
with optional timestamps." Figure caption: "(b) Then, the evidence sessions are LLM-simulated and human-edited."
**Paper (Section 1):** "further expanding the keys with extracted user facts improves both memory recall (9.4% higher
recall@k) and downstream question answering (5.4% higher accuracy)."

**Verdict: SUPPORTED.** **Reference entry:** matches; arXiv comment "ICLR 2025".

### 27. Hu et al. (2026b), *EverMemBench* — arXiv:2602.01313

**Manuscript:** "EverMemBench (Hu et al., 2026b) targets multi-party, long-horizon collaboration and reports LLM-judged
accuracy per category."

**Paper (Abstract):** "we introduce EverMemBench, the first benchmark designed for long-horizon collaborative memory,
built from multi-party, multi-group conversations [...] using 2400 QA pairs across three dimensions [...]: fine-grained
recall, memory awareness, and user profile understanding."
**Paper (Section 3):** "we pose (1) multiple-choice queries for high-precision diagnosis and (2) open-ended queries
judged by an LLM for semantic equivalence".
**Paper (Section 4, Evaluation Metrics):** "For Fine-Grained Recall, [...] we use LLM-as-a-judge [43] to assess
equivalence. For Memory Awareness and Profile Understanding, [...] we use multiple-choice questions with carefully
constructed distractors [...]"

**Verdict: PARTLY.** The first clause is supported. "LLM-judged accuracy per category" overreaches: only the
fine-grained-recall dimension is LLM-judged; the other two are scored as multiple choice.

**Proposed wording:** "...and reports accuracy per category, LLM-judged for open-ended recall questions and
multiple-choice for memory awareness and profile understanding."

**Reference entry:** title, first author (Chuanrui Hu), arXiv id match.

### 28. Chen et al. (2025), *HaluMem* — arXiv:2511.03506

**Manuscript:** "HaluMem (Chen et al., 2025) measures hallucination in memory systems, a dimension we do not evaluate."

**Paper (Abstract):** "we introduce the Hallucination in Memory Benchmark (HaluMem), the first operation level
hallucination evaluation benchmark tailored to memory systems."

**Verdict: SUPPORTED.** **Reference entry:** matches.

### 29. Hu, Wang & McAuley (2026c), *MemoryAgentBench* — arXiv:2507.05257

**Manuscript:** "MemoryAgentBench (Hu et al., 2026c) defines four competencies and finds that no method masters all of
them"

**Paper (Abstract):** "we identify four core competencies essential for memory agents: accurate retrieval, test-time
learning, long-range understanding, and selective forgetting. [...] Empirical results reveal that current methods fall
short of mastering all four competencies".

**Verdict: SUPPORTED.** **Reference entry:** matches; PDF header "Published as a conference paper at ICLR 2026".

### 30. Wu et al. (2026), *Memory in the LLM Era* — arXiv:2604.01707

**Manuscript:** "Wu et al. (2026) re-implement existing methods as modules of one framework"

**Paper (Section 4, Experimental setup):** "we collect and reimplement 12 representative methods within the unified
framework described in Section 3"; "Implementation. We implement all methods in Python under the proposed unified
framework, ensuring faithful and consistent reimplementation based on original papers and publicly available code."
**Paper (Section 1, contributions):** "We propose a unified framework that decomposes representative agent memory
methods into four core memory modules".

**Verdict: SUPPORTED.** (Benchmarks, unconfirmed in the sweep notes, are LOCOMO, LONGMEMEVAL and MemoryArena per
Section 1.) **Reference entry:** matches.

### 31. Shao et al. (2026), *When Stored Evidence Stops Being Usable* — arXiv:2605.07313

**Manuscript:** "Shao et al. (2026) show that reliability loss with scale is not a single phenomenon."

**Paper (Abstract):** "Applied to LongMemEval and LoCoMo across flat, planar, and hierarchical memory interfaces, the
protocol shows reliability loss is not a single phenomenon."

**Verdict: SUPPORTED.** **Reference entry:** matches; arXiv comment "Accepted at NeurIPS 2026, Evaluations and Datasets
Track".

---

## Summary table

| # | Citation | arXiv | Verdict | Issue |
|---|---|---|---|---|
| 1 | Zhang et al. 2025a (survey) | 2404.13501 | SUPPORTED | ref: add TOIS DOI 10.1145/3748302 |
| 2 | Gao et al. 2026 | 2507.21046 | SUPPORTED | — |
| 3 | Chhikara et al. 2025 (Mem0) | 2504.19413 | SUPPORTED | — |
| 4 | Rasmussen et al. 2025 (Zep) | 2501.13956 | SUPPORTED | — |
| 5 | Hu et al. 2026a (EverMemOS) | 2601.02163 | PARTLY | "mandatory cross-encoder" not in paper; is a deployment fact |
| 6 | Li et al. 2025 (MemOS) | 2507.03724 | SUPPORTED | — |
| 7 | Gutiérrez et al. 2025 (HippoRAG 2) | 2502.14802 | SUPPORTED | — |
| 8 | Guo et al. 2025 (LightRAG) | 2410.05779 | SUPPORTED | page range unchecked |
| 9 | Quek et al. 2026 (MeMo) | 2605.15156 | SUPPORTED | — |
| 10 | Wang et al. 2025 (Mem-α) | 2509.25911 | SUPPORTED | — |
| 11 | Yan et al. 2025 (Memory-R1) | 2508.19828 | SUPPORTED | — |
| 12 | Zhang et al. 2025b (MemAct) | 2510.12635 | SUPPORTED | — |
| 13 | Zhou et al. 2025 (MEM1) | 2506.15841 | SUPPORTED | — |
| 14 | Yu et al. 2026 (MemAgent) | 2507.02259 | SUPPORTED | — |
| 15 | Zhou et al. 2026a | 2610.24671 | SUPPORTED | — |
| 16 | Fang et al. 2025 (LightMem) | 2510.18866 | SUPPORTED | — |
| 17 | Zhou et al. 2026b | 2607.29104 | PARTLY | "more than construction did" is an inference, not stated |
| 18 | Bao et al. 2026 | 2610.30755 | SUPPORTED | advisory: their "naive" RAG includes a re-ranker |
| 19 | He et al. 2026 (Memory Tax) | 2610.34073 | PARTLY | set of systems partly overlaps Bao's, not "different" |
| 20 | Yuan et al. 2026 | 2603.02473 | SUPPORTED | — |
| 21 | Sharma & Lall 2026 | 2609.34227 | PARTLY | drops "tight budget, LoCoMo"; extraction wins at generous budgets |
| 22 | Ma et al. 2025 (Nemori) | 2508.03341 | SUPPORTED | ref: author list (arXiv 4) vs ACL 2026 (3); year mismatch |
| 23 | Liu et al. 2026 (SimpleMem) | 2601.02553 | SUPPORTED | ref: ICML 2026 only via repo title; arXiv says "Preprint" |
| 24 | Dai et al. 2026 (RecMem) | 2605.16045 | SUPPORTED | — |
| 25 | Li et al. 2026 (TiMem) | 2601.02845 | SUPPORTED | — |
| 26 | Wu et al. 2025 (LongMemEval) | 2410.10813 | SUPPORTED | — |
| 27 | Hu et al. 2026b (EverMemBench) | 2602.01313 | PARTLY | only one of three dimensions is LLM-judged |
| 28 | Chen et al. 2025 (HaluMem) | 2511.03506 | SUPPORTED | — |
| 29 | Hu, Wang & McAuley 2026c (MemoryAgentBench) | 2507.05257 | SUPPORTED | — |
| 30 | Wu et al. 2026 | 2604.01707 | SUPPORTED | — |
| 31 | Shao et al. 2026 | 2605.07313 | SUPPORTED | — |

**Counts:** SUPPORTED 26 · PARTLY 5 · NOT SUPPORTED 0 · COULD NOT READ 0.

All 31 reference entries match the fetched papers on title, first author and arXiv id. Year in the entry agrees with
the venue year or arXiv year in every case except the Nemori mixed form noted in item 22.
