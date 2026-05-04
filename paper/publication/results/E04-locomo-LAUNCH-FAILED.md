# E04 — LOCOMO Evaluation: Launch Failed

**Date:** 2026-05-04  
**Sprint:** W2  
**Paper section:** §5.2 Table 5 — Conversational long-context memory benchmark

---

## Failure Reason

`snap-stanford/locomo` is **inaccessible** on HuggingFace Hub as of 2026-05-04.

```
HTTP 401 Unauthorized
Dataset 'snap-stanford/locomo' doesn't exist on the Hub or cannot be accessed.
```

The dataset was referenced in Maharana et al. (2024) arXiv:2402.17753 and cited in the LOCOMO-ADAPTER-SPEC as the canonical source, but it has been deleted or made private/gated since the paper was written.

---

## Evidence

Checks performed from VPS (100.87.8.44):

| Endpoint | Result |
|---|---|
| `https://huggingface.co/datasets/snap-stanford/locomo` | HTTP 401 |
| `https://huggingface.co/api/datasets/snap-stanford/locomo` | `{"id": null, "private": null, "gated": null}` — dataset not found |
| `https://datasets-server.huggingface.co/splits?dataset=snap-stanford/locomo` | `{"error": "does not exist or not accessible without authentication"}` |
| `https://github.com/snap-stanford/locomo` | HTTP 404 |
| `https://github.com/snap-stanford/LOCoMo` | HTTP 404 |
| snap-stanford org public datasets (20 listed) | locomo not among them |

**Alternative mirrors checked:**

- `adymaharana/locomo` — public, but EmptyDatasetError (no data files in repo)
- `Aman279/Locomo` — public, has 35 rows but wrong schema: only `{dialogue_id, turns}`, no QA pairs/evidence spans

---

## What Was Not Fabricated

No results were generated. No metrics were estimated or imputed. The eval was aborted at Stage 1 (download).

The VPS environment was otherwise ready:

- Load avg at launch: 1.53 (5min), well under 3.5 threshold
- BEIR `beir-trec` tmux session running without interference
- `/root/locomo-baselines/locomo_adapter.py` deployed
- Python venv `/tmp/locomo-venv` with `datasets>=2.19` installed
- nox-mem HTTP API healthy at `:18802` (vectorCoverage: 61253/61258)

---

## Alternative Strategies

1. **HuggingFace authentication**: If the dataset became gated (requires approved access), apply at `https://huggingface.co/datasets/snap-stanford/locomo` with account credentials. Once access granted, set `HF_TOKEN` in VPS `.env` and re-run the adapter.

2. **Author direct contact**: Email Adyasha Maharana (adymaharana@cs.stanford.edu) requesting the data. The first author's HF account (`adymaharana`) exists but the dataset repo has no data files.

3. **Paper supplementary**: The arXiv paper (2402.17753) may have a data release link in its updated versions or supplementary materials.

4. **Alternative conversational benchmark**: Replace LOCOMO with another public episodic memory benchmark for §5.2:
   - **MemoryBank** (Zhong et al., 2023) — conversational memory, publicly available
   - **MuSiQue** (Trivedi et al., 2022) — multi-hop, public
   - **QMSum** (Zhong et al., 2021) — query-based meeting summarization with retrieval
   - **FRAMES** (Google DeepMind, 2024) — long-context factual retrieval, HF public

5. **Synthetic LOCOMO-style data**: Generate 100 synthetic QA pairs over nox-mem's own conversation corpus (real sessions in `memory/entities/person/`) following the LOCOMO schema. Would not be citable as LOCOMO but valid as internal ablation.

---

## Recommendation for Paper §5.2

Two options:

**Option A (preferred):** Replace LOCOMO with MemoryBank or FRAMES (both public) and relabel Table 5 as "Episodic memory benchmark." The nox-mem adapter requires only minor schema changes.

**Option B:** Acknowledge LOCOMO unavailability in footnote: *"LOCOMO dataset (Maharana et al., 2024) was inaccessible at evaluation time (HF 401). Table 5 reports results on [alternative]."* Proceed with the alternative.

Do not omit §5.2 entirely — the conversational memory angle is a key differentiator from BEIR.

---

## BEIR Status (for context)

`beir-trec` tmux session was running at eval time (Phase 4 e5 embed). No interference occurred. Load avg remained stable at ~1.5–2.0.
