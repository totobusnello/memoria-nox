# Path A2 — Gemini Flash chunk summarizer (Q4 capped@500 + full corpus)

**Verdict:** `NEGATIVE`

**Template:** `A` (atomic-fact extraction, mem0-style)

**Generated:** 2026-05-24 (Sat, BRT)

---

## Headline numbers

| Run | n_chunks | nDCG@10 | MRR | R@10 | hit_rate | p50 (ms) | p95 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline hybrid **full** (PR #338) | 6,830 | **0.4509** | — | — | — | — | — |
| Baseline hybrid **cap=500** (Sat closure) | 500 | 0.0918 | — | — | — | — | — |
| **mem0 cap=500** (gap target)     | 500   | **0.1315** | — | — | — | — | — |
| A2 (template A) **cap=500** | 500 | **0.0645** | 0.0383 | 0.1500 | 0.15 | 511.4 | 1126.4 |
| A2 (template A) **full** | 6,822 | **0.2973** | 0.3100 | 0.4208 | 0.55 | 479.7 | 1105.1 |

### Gap closure (vs cap=500)

| Δ | Value |
|---|---:|
| Gap to close (mem0@500 − hybrid@500) | **+0.0397** |
| A2@500 lift over hybrid@500 | **-0.0273** |
| Gap closure | **-69%** (A2 made gap worse) |
| A2@500 vs mem0@500 | **-0.0670** |

### Regression analysis (full corpus)

| Δ | Value |
|---|---:|
| A2 full vs baseline hybrid full (PR #338) | **-0.1536** |
| Regression | **-34%** of baseline nDCG@10 |

---

## Verdict

**NEGATIVE on the main claim.** Ingest-side fact extraction via Gemini Flash
Lite **does not close the gap vs mem0@500**. In fact, it makes retrieval
**worse** than the raw-text hybrid baseline:

- **Cap=500 (LoCoMo turns):** A2 nDCG@10 = 0.0645, hybrid = 0.0918 → **-30%**
- **Full corpus (LoCoMo + LongMemEval sessions):** A2 = 0.2973, hybrid = 0.4509 → **-34%**

Decision: **do not merge**. This is the third query/ingest concentration path
that has failed to beat the raw-text hybrid baseline (PRs #337 query rewrite,
#339 E+F+H combo, and now A2 chunk summarizer).

---

## Why it failed — root cause analysis

### Mechanism 1: LoCoMo turns are TOO SHORT to summarize

The cap=500 corpus is purely the first 500 LoCoMo turns (canonical ingest
order). Mean raw turn length: **144 chars**. Template A's fact-extraction
prompt produces either:

- "No facts found." / "There are no facts in the provided passage." for
  conversational filler (≈40% of turns); or
- A truncated fact that drops the **conversational signal** needed for
  retrieval (e.g. turn embedding context, speaker affect).

Example:
```
RAW (107c):    "Caroline: That's awesome, Mel! I'd love to hear more about
                them. Tell me more about what you saw."
A2 (29c):      "Caroline is Melanie's friend."
```
The raw turn has lexical overlap with queries about Caroline's reactions,
emotions, conversational context. The summary strips ALL of that.

### Mechanism 2: LongMemEval session compression loses retrieval-relevant detail

LongMemEval sessions are **2,000-17,000 chars**, summarized to **100-700 chars**
(95-99% reduction). Compression looks impressive but specific tokens get lost:

- **Adversarial queries** ("How many Italian restaurants?" when only Korean
  mentioned): A2 nDCG@10 = **0.0** across the board. The summary strips
  context that would let the retriever fail-loudly.
- **Single-session-preference / single-session-user** queries: A2 = 0.0.
  Need verbatim quotes ("I like X better") that get normalized in summaries.
- **Adversarial loss is structural** — when the model condenses to facts,
  it commits to a positive assertion and drops the absence-of-evidence
  signal that adversarial questions rely on.

### Mechanism 3: Dense embeddings lose semantic spread on short summaries

3072-dim Gemini embeddings on **identical-looking** fact bullets ("The user
bought a silver Honda Civic"; "The user's car is a silver Honda Civic")
cluster too tightly. Cosine similarity stops discriminating between sessions
that share entities but differ on the relevant detail.

### Why mem0 ≠ A2 at cap=500

mem0's cap=500 = **500 EXTRACTED FACTS** (one fact per chunk, distilled from
~10× more raw conversation). A2's cap=500 = **500 SUMMARIES OF RAW TURNS**
(many "no facts" duds). mem0 effectively does **first the summarization, then
the cap**; A2 caps before the corpus offers anything to concentrate from.

Replicating mem0 honestly would require summarizing each conversation
**before** the cap protocol — but then "cap=500" would mean 500 conversations
worth of facts, **not 500 source chunks**. Apples-to-apples breaks.

---

## Full-corpus subset breakdown (A2 vs intuition)

Even where A2 lost overall, the per-subset breakdown reveals where ingest-side
concentration **does** help vs where it actively hurts.

### Where A2 (full corpus) helped

| Subset | n | A2 nDCG@10 | Hit rate | Notes |
|---|---:|---:|---:|---|
| multi-hop | 2 | **0.7500** | 1.00 | Fact extraction chains entities across hops |
| temporal-reasoning | 2 | **0.6186** | 1.00 | Dates / numbers preserved cleanly |
| single-session-assistant | 1 | **0.6309** | 1.00 | Assistant turns are factual already |
| open-domain | 2 | **0.5000** | 1.00 | Lots of entity types — facts help |
| knowledge-update | 2 | **0.3066** | 0.50 | Update tracking benefits from consolidation |

### Where A2 (full corpus) lost

| Subset | n | A2 nDCG@10 | Hit rate | Notes |
|---|---:|---:|---:|---|
| adversarial | 2 | **0.0000** | 0.00 | Absence-of-evidence stripped by summarization |
| single-session-preference | 1 | **0.0000** | 0.00 | Verbatim preferences normalized away |
| single-session-user | 2 | **0.0000** | 0.00 | Specific user quotes lost |
| temporal | 2 | **0.0755** | 0.50 | Date math survives, but query phrasing drift hurts |
| multi-session | 2 | **0.1847** | 0.50 | Need cross-session detail that's flattened |
| single-hop | 2 | **0.2221** | 0.50 | Some single-fact lookups still work |

### Cap=500 subset breakdown (all LoCoMo)

| Subset | n | A2 nDCG@10 | Hit rate |
|---|---:|---:|---:|
| open-domain | 2 | 0.3945 | 1.00 |
| multi-hop | 2 | 0.2500 | 0.50 |
| single-hop / temporal / adversarial / knowledge-update / multi-session / single-session-* | 11 | 0.00 | 0.00 |

Only 2 of 13 LoCoMo subsets register any hit at cap=500.

---

## Cost

| Metric | Value |
|---|---:|
| Summarizer total cost | **$0.3042** |
| Input tokens | 3,631,011 |
| Output tokens | 106,092 |
| Embeddings (3072d, all 6,822 chunks) | included in nox-mem hybrid pipeline (free tier) |
| Model | `gemini-2.5-flash-lite` |
| Hard cap | $5 (well under) |

Total wall-clock: **~18 min summarize + ~44 min embed + ingest** = ~1h end-to-end.

---

## What we learned (value of the negative)

This is the **third** failed concentration path. The three failures together
paint a consistent picture:

1. **PR #337 (query rewrite, -11.8%)** — query-side concentration adds lexical
   noise without helping fusion.
2. **PR #339 (E+F+H combo, +2.4%)** — partial query-side tweaks recover some
   but don't close the gap.
3. **PR A2 (ingest-side summarization, -30% capped / -34% full)** —
   ingest-side concentration destroys retrieval-relevant tokens.

**Conclusion for the ship narrative:** the mem0 cap=500 advantage is NOT
something nox-mem can replicate at parity using the same protocol. mem0
trades **coverage** for **concentration**, and at the same chunk budget the
two are structurally different objects.

The honest framing is the one already in the memory chain
([[honest-cross-system-framing]]): mem0 nDCG@10 is high **because** of the
concentration design — but their corpus coverage is ~45% vs nox-mem's ~87%.
The right Q4 GTM Phase 2 gate is the **two-metric gate** (nDCG@10 ≥ +15%
AND coverage ≥ 80%), not the single-metric chase.

### New design intel for the Lab Q1 docket

Per-subset evidence that **ingest-side concentration is a different design
point**, not a strict improvement:

- For **multi-hop**, **temporal-reasoning**, **assistant-side** queries, the
  fact-extracted corpus actively beats raw hybrid (multi-hop +0.75 vs raw
  full corpus baseline subset breakdown).
- For **adversarial**, **user-preference**, **single-session-user** queries,
  fact extraction is structurally fatal because it converts open-ended
  conversational signal into closed positive assertions.

This suggests a future **hybrid-of-hybrids** design: keep both the raw and
the summarized corpus indexed; route queries by detected intent (factual /
multi-hop → summarized; adversarial / preference → raw). That's a Lab Q1/Q2
parking-lot item now backed by real numbers.

---

## Recommendations

1. **Do NOT merge A2 into prod.** Document as the third closed concentration
   path. Draft PR opens for archive.
2. **Update the ship narrative** with the per-subset wins (multi-hop 0.75,
   temporal-reasoning 0.62) as evidence that ingest-side concentration is
   not categorically bad — it's a different design point that hurts more
   than it helps on the LongMemEval gold-set composition.
3. **Lab Q1 P1** (concentration vs coverage) gets concrete evidence: three
   failed attempts; design point lives on the other axis. New Q1/Q2 idea:
   **hybrid-of-hybrids** corpus routing.
4. **Q4 Phase 2 gate**: stick with the two-metric gate (nDCG@10 + coverage)
   already documented in `[[honest-cross-system-framing]]`. A2 closes this
   line of investigation.

---

## Artifacts

- `eval/q4-comparison/lib/chunk_summarizer.py` — Gemini Flash Lite summarizer
  (3 templates, parallel/serial, cost tracking, $5 hard cap, resumable cache).
- `eval/q4-comparison/adapters/nox_mem_a2.py` — adapter ingesting the
  summarized JSONL with the same hybrid pipeline as PR #338.
- `eval/q4-comparison/run-a2-summarizer.sh` — end-to-end runner script.
- `eval/q4-comparison/run-a2-benchmark.py` — capped/full benchmark + report
  generator.
- `eval/q4-comparison/cache/summarized-A.jsonl` — 6,830 summarized chunks
  (gitignored; reproducible via the runner).
- `eval/q4-comparison/cache/summarized-A-cost.jsonl` — per-batch cost log.

---

## References

- Baseline #338 hybrid: PR #338 (Sat 2026-05-24).
- mem0@500 ref: PR #306 Sat closure (nDCG@10 = 0.1315).
- Prior failed concentration paths:
  - PR #337 query rewrite (-11.8%)
  - PR #339 E+F+H combo (+2.4%, gap persists)
- Memory consolidation:
  - `[[concentration-vs-coverage]]`
  - `[[honest-cross-system-framing]]`
  - `[[shared-loader-canonical-pattern]]`
  - `[[adapter-response-shape-validation]]`
