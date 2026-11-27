# Related work added for the IP&M version (2025–2026)

Swept 2026-11-27 for Section 2.3–2.4 of `manuscript.md`. Every arXiv id below was checked against
`export.arxiv.org/api/query?id_list=<id>` (title, authors, date, comment). The one-line findings come
from the abstracts as returned by a fetch summarizer, not from reading the PDFs: **before submission,
re-read each abstract and the cited result in the PDF** (tracked in `SUBMISSION-CHECKLIST.md`).

## A. Raw history against constructed memory

| short cite | arXiv | venue | finding used in §2.3 | LoCoMo / LongMemEval |
|---|---|---|---|---|
| Zhou, Wang, Koopman & Zuccon (2026a), *Do Conversational Agents Need Explicit Memory? A Controlled Comparison with Raw-History Retrieval* | 2610.24671 | preprint | six explicit memory systems show localized gains and no consistent advantage over strong raw-history RAG | LongMemEval-S (and BEAM-100K) |
| Zhou, Wang, Koopman & Zuccon (2026b), *Reproducing LightMem: When Does Memory Construction Help Over Raw-Turn Retrieval?* | 2607.29104 | SIGIR-AP 2026 (arXiv comment) | changing only the retriever over a fixed LightMem store moves answer accuracy a lot; constructed memory does not consistently beat raw-turn retrieval | LongMemEval-S |
| Bao, Zhang, Zhang, Lou, Wen & Luo (2026), *Is Complex Agentic Memory Always Needed? Naive RAG Is Stronger Than We Thought* | 2610.30755 | preprint | raw-turn RAG ranks first among compared memory systems in most benchmark–model settings (EverMemOS, MemOS, SimpleMem, Mem0, Nemori, A-MEM, RecMem among them; not Zep or Letta) | both |
| He, Zhoubian, Yang, … , Han & Zhai (2026), *Memory Tax: Dissecting the Net Value of Agent Memory* | 2610.34073 | preprint | many dedicated memory systems underperform naive RAG | LongMemEval-S |
| Yuan, Su & Yao (2026), *Diagnosing Retrieval vs. Utilization Bottlenecks in LLM Agent Memory* | 2603.02473 | MemAgents Workshop, ICLR 2026 (arXiv comment) | in a write-strategy × retrieval-method design, retrieval method matters more than write-time sophistication | LoCoMo |
| Sharma & Lall (2026), *When Does Selection Replace Extraction? A Pre-Registered Test of Agent Memory with a Typed Decision Model* | 2609.34227 | preprint | raw turns selected by a typed decision model are non-inferior to an LLM-extraction memory (pre-registered) | both |
| Ma, Nan & Wu (2026), *What Deserves Memory: Adaptive Memory Distillation for LLM Agents* (Nemori) | 2508.03341 | ACL 2026 (Anthology lists three authors; arXiv v4 lists four, adding Yize Chen) | constructed-memory system; strong on both benchmarks | both |

## B. Several memory systems under one protocol

| short cite | arXiv | venue | note |
|---|---|---|---|
| Hu, Wang & McAuley (2026c), *Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions* (MemoryAgentBench) | 2507.05257 | ICLR 2026 | four competencies; no method masters all four |
| Wu, Lin, Zhou, … & Fang (2026), *Memory in the LLM Era: Modular Architectures and Strategies in a Unified Framework* | 2604.01707 | preprint | re-implements existing methods as modules in one framework |
| Shao, Lu, Zhang & Luo (2026), *When Stored Evidence Stops Being Usable: Scale-Conditioned Evaluation of Agent Memory* | 2605.07313 | NeurIPS 2026 E&D (arXiv comment) | reliability loss with scale is not one phenomenon |

No formal re-run study of Mem0 or Zep under a shared protocol was found.

## C. Lightweight systems (named only)

SimpleMem (Liu et al., 2026; arXiv:2601.02553; ICML 2026), LightMem (Fang et al., 2025; arXiv:2510.18866;
ICLR 2026), RecMem (Dai et al., 2026; arXiv:2605.16045; Findings of ACL 2026), TiMem (Li et al., 2026;
arXiv:2601.02845; Findings of ACL 2026).

## Not confirmed (do not cite these details)

Benchmark names in 2604.01707; LongMemEval for SimpleMem; benchmarks in RecMem's abstract; the query
count of Sharma & Lall; TiMem's accuracy figures.
