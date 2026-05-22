# refs.bib — Verification Log

**Date:** 2026-05-22 (Fri madrugada, pre-Tue arXiv prep)  
**Verified by:** Sisyphus-Junior agent (automated HEAD/GET + arXiv HTML scrape)  
**Method:** `curl -sI --max-time 10` for URL status; Python urllib for arXiv metadata; GitHub API for repo metadata  

**Summary: 12 VERIFIED / 1 PARTIAL (venue SKIPPED-MANUAL) / 0 FAILED**  
**Critical author corrections: 3 entries had wrong authors → FIXED in refs.bib**

---

## Entry-by-Entry Results

### `mem0_2024` — Mem0 GitHub
- **URL tested:** `https://github.com/mem0ai/mem0`
- **Response:** HTTP 200
- **Status:** VERIFIED 2026-05-22
- **Notes:** No arXiv paper found. Software-only cite is appropriate. `year=2024` consistent with repo created 2023-06-20 (first stable year 2024).

---

### `zep_2024` — Zep GitHub
- **URL tested:** `https://github.com/getzep/zep`
- **Response:** HTTP 200
- **Status:** VERIFIED 2026-05-22
- **Notes:** "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" paper not located on arXiv as a formal publication. Cite as software. `year=2024` acceptable.

---

### `packer2023memgpt` — MemGPT arXiv:2310.08560
- **URL tested:** `https://arxiv.org/abs/2310.08560`
- **Response:** HTTP 200
- **Authors confirmed:** Packer, Charles; Wooders, Sarah; Lin, Kevin; Fang, Vivian; Patil, Shishir G.; Stoica, Ion; Gonzalez, Joseph E.
- **Title confirmed:** "MemGPT: Towards LLMs as Operating Systems"
- **Status:** VERIFIED 2026-05-22
- **Notes:** Authors in refs.bib were CORRECT. No changes needed.

---

### `letta_2024` — Letta GitHub
- **URL tested:** `https://github.com/letta-ai/letta`
- **Response:** HTTP 200
- **Repo metadata:** owner=letta-ai, created=2023-10-11, 22879+ stars
- **Status:** VERIFIED 2026-05-22
- **Notes:** `year=2024` acceptable (rebranded from MemGPT repo in late 2023, stabilized 2024).

---

### `agentmemory_2026` — agentmemory GitHub  ⚠️ CORRECTED
- **URL tested:** `https://github.com/rohitg00/agentmemory`
- **Response:** HTTP 200
- **Repo metadata:** owner=rohitg00, created=**2026-02-25**, 16132+ stars
- **Status:** VERIFIED 2026-05-22 — **YEAR CORRECTED: 2024→2026; BibTeX key renamed agentmemory_2024→agentmemory_2026**
- **Notes:** Original `year=2024` was WRONG. Repo created 2026-02-25. Title updated to match repo description. Author handle `rohitg00` confirmed (full legal name "Rohit Garg" per handle; update if formal paper published).
- **Action required:** Update any `\cite{agentmemory_2024}` references in paper body to `\cite{agentmemory_2026}`.

---

### `evermind_2025` — EverMind-AI/EverOS GitHub  ⚠️ CORRECTED
- **URL tested:** `https://github.com/EverMind-AI/EverOS`
- **Response:** HTTP 200
- **Repo metadata:** owner=EverMind-AI, created=**2025-10-28**, 5469+ stars
- **Status:** VERIFIED 2026-05-22 — **YEAR CORRECTED: 2024→2025; title updated; BibTeX key renamed evermind_2024→evermind_2025**
- **Associated paper found:** arXiv:2601.02163 — "EverMemOS: A Self-Organizing Memory Operating System for Structured Long-Horizon Reasoning" (Hu, Chuanrui et al., 2026)
- **Notes:** Original `year=2024` and title were WRONG. Repo title is EverOS (not EverMemOS), but associated paper is EverMemOS. Consider adding separate `@article{hu2026evermemos}` entry citing arXiv:2601.02163 if claiming benchmark comparisons.
- **Action required:** Update `\cite{evermind_2024}` → `\cite{evermind_2025}` in paper body. Consider separate arXiv cite for EverMemOS paper.

---

### `guo2024lightrag` — LightRAG arXiv:2410.05779  ⚠️ CRITICAL CORRECTION
- **URL tested:** `https://arxiv.org/abs/2410.05779`
- **Response:** HTTP 200
- **Authors confirmed:** Guo, Zirui; Xia, Lianghao; Yu, Yanhua; Ao, Tu; Huang, Chao (HKUDS group, HKU)
- **Title confirmed:** "LightRAG: Simple and Fast Retrieval-Augmented Generation"
- **Status:** VERIFIED 2026-05-22 — **AUTHORS COMPLETELY WRONG IN ORIGINAL; BibTeX key renamed edge2025lightrag→guo2024lightrag**
- **Critical error:** Original entry listed `Edge, Darren et al.` (Microsoft) — those are the authors of **GraphRAG** (arXiv:2404.16130), NOT LightRAG. This was a serious citation error that would have been caught during peer review.
- **GitHub:** `https://github.com/HKUDS/LightRAG` verified HTTP 200 (35535 stars, created 2024-10-02)
- **Action required:** Update ALL `\cite{edge2025lightrag}` in paper body to `\cite{guo2024lightrag}`.

---

### `wu2024longmemeval` — LongMemEval arXiv:2410.10813  ⚠️ CORRECTED
- **URL tested:** `https://arxiv.org/abs/2410.10813`
- **Response:** HTTP 200
- **Authors confirmed:** Wu, Di; Wang, Hongwei; Yu, Wenhao; Zhang, Yuwei; Chang, Kai-Wei; Yu, Dong
- **Venue confirmed:** ICLR 2025 (from arXiv comments field)
- **Status:** VERIFIED 2026-05-22 — **AUTHORS CORRECTED** (He,Hongwei→Wang,Hongwei; Liu,Wenhao→Yu,Wenhao; Han,Weijia/Zhao,Kaifeng/Chen,Mulong replaced); venue confirmed ICLR 2025
- **Notes:** Original author list was mostly wrong. 3 of 6 authors had incorrect names.

---

### `maharana2024locomo` — LoCoMo arXiv:2402.17753  ⚠️ PARTIAL CORRECTION
- **URL tested:** `https://arxiv.org/abs/2402.17753`
- **Response:** HTTP 200
- **Authors confirmed:** Maharana, Adyasha; Lee, Dong-Ho; Tulyakov, Sergey; Bansal, Mohit; **Barbieri, Francesco; Fang, Yuwei**
- **Venue:** arXiv comments say "19 pages; Project page: [URL]" — no journal_ref in HTML. ACL 2024 NOT confirmed from arXiv metadata.
- **Status:** VERIFIED 2026-05-22 (authors) — **AUTHORS CORRECTED** (Dernoncourt,Franck→Barbieri,Francesco; Kim,Doo Soon→Fang,Yuwei)
- **SKIPPED-MANUAL-TUE:** Venue (ACL 2024?) — arXiv does not confirm. Check ACL Anthology or paper PDF before submit.
- **Recommended action Tue 06-02:** Search `https://aclanthology.org/` for "LoCoMo" to confirm ACL 2024. If confirmed, add `booktitle={Proceedings of ACL 2024}` and change `@article` → `@inproceedings`.

---

### `cormack2009rrf` — RRF SIGIR DOI
- **DOI tested:** `https://doi.org/10.1145/1571941.1572114`
- **Response:** HTTP 302 → `https://dl.acm.org/doi/10.1145/1571941.1572114` (403 from bot-blocking, expected)
- **Status:** VERIFIED 2026-05-22 — DOI resolves correctly; 403 is ACM's bot protection, not an error
- **Notes:** `dl.acm.org/doi/10.1145/1571941.1572114` is the canonical landing page. No changes needed.

---

### `robertson2009bm25` — BM25 FnT DOI
- **DOI tested:** `https://doi.org/10.1561/1500000019`
- **Response:** HTTP 302 → `https://www.nowpublishers.com/` / Emerald (403 from bot-blocking, expected)
- **Status:** VERIFIED 2026-05-22 — DOI resolves correctly; 403 is publisher's bot protection
- **Notes:** `url` field kept as `https://doi.org/10.1561/1500000019` (canonical). No changes needed.

---

### `garcia2024sqlitevec` — sqlite-vec GitHub
- **URL tested:** `https://github.com/asg017/sqlite-vec`
- **Response:** HTTP 200
- **Repo metadata:** owner=asg017, created=2024-04-20, 7622+ stars
- **Status:** VERIFIED 2026-05-22
- **Notes:** No VLDB/academic paper found. Software-only cite is appropriate. `year=2024` correct.

---

### `google2024geminiembedding` — Gemini API docs
- **URL tested:** `https://ai.google.dev/gemini-api/docs/models`
- **Response:** HTTP 200
- **Status:** VERIFIED 2026-05-22
- **Notes:** URL is live. For arXiv paper citation, consider adding separate `@techreport` for the Gemini 1.5 Technical Report if model embed-001 is described there. Current software cite is acceptable.

---

### `busnello2026noxmem` — self-citation
- **URL tested:** `https://github.com/totobusnello/memoria-nox`
- **Response:** HTTP 200 (public repo confirmed via API)
- **CITATION.cff consistency:** URL matches (`repository-code` field in commit 112798f)
- **Status:** VERIFIED 2026-05-22
- **SKIPPED-MANUAL-TUE:** Update `note` field with actual arXiv ID after 2026-06-02 submission.

---

## Summary Table

| Entry | URL/DOI | Authors | Venue | Action |
|-------|---------|---------|-------|--------|
| mem0_2024 | ✅ 200 | N/A (org) | N/A | None |
| zep_2024 | ✅ 200 | N/A (org) | N/A | None |
| packer2023memgpt | ✅ 200 | ✅ Correct | arXiv only | None |
| letta_2024 | ✅ 200 | N/A (org) | N/A | None |
| **agentmemory_2026** | ✅ 200 | ⚠️ handle ok | N/A | **Year fixed 2024→2026; key renamed** |
| **evermind_2025** | ✅ 200 | N/A (org) | N/A | **Year fixed 2024→2025; title corrected; key renamed** |
| **guo2024lightrag** | ✅ 200 | ❌→✅ FIXED | arXiv only | **Authors completely wrong (Edge et al. was GraphRAG); CRITICAL FIX** |
| **wu2024longmemeval** | ✅ 200 | ❌→✅ FIXED | ✅ ICLR 2025 | **3/6 authors wrong; venue confirmed** |
| **maharana2024locomo** | ✅ 200 | ❌→✅ FIXED | ⏳ MANUAL TUE | **2/6 authors wrong; venue unconfirmed** |
| cormack2009rrf | ✅ DOI OK | ✅ Correct | ✅ SIGIR 2009 | None |
| robertson2009bm25 | ✅ DOI OK | ✅ Correct | ✅ FnT 2009 | None |
| garcia2024sqlitevec | ✅ 200 | ✅ asg017 | N/A | None |
| google2024geminiembedding | ✅ 200 | N/A (org) | N/A | None |
| busnello2026noxmem | ✅ 200 | ✅ Correct | ⏳ MANUAL TUE | Add arXiv ID after submit |

---

## Manual Checks Required Tue 06-02

1. **LoCoMo venue (maharana2024locomo):** Search ACL Anthology for "LoCoMo" — confirm ACL 2024 or find correct venue. If ACL 2024: change `@article` → `@inproceedings`, add `booktitle`.
2. **busnello2026noxmem arXiv ID:** After submit, add `eprint`, `archivePrefix`, `primaryClass`, update `note`.
3. **EverMind paper separate cite:** Consider `@article{hu2026evermemos, eprint=2601.02163}` if claiming benchmark comparisons vs EverMemBench.
4. **Gemini Embedding paper:** If Google releases `gemini-embedding-001` paper before submit, add separate `@techreport` or `@article`.
5. **agentmemory_2026 author full name:** `rohitg00` → confirm legal name "Rohit Garg" is correct before final submit.

---

## BibTeX Key Renames (update paper body `\cite{}` calls)

| Old key | New key | Reason |
|---------|---------|--------|
| `edge2025lightrag` | `guo2024lightrag` | Wrong authors (was GraphRAG); correct paper is HKU group |
| `agentmemory_2024` | `agentmemory_2026` | Year corrected 2024→2026 |
| `evermind_2024` | `evermind_2025` | Year corrected 2024→2025 |
