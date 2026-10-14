I'll run the parity check and its self-test to confirm the binding machinery actually passes, and glance at the figure.

# Review: `datanote-telemetry/DATA-NOTE.md` (rc2, 2026-10-13)

**How I checked.** I read the note, the dataset README, `analysis.py`, `parity.py`, `figure.py` and `numbers.json` in full; ran `parity.py numbers.json DATA-NOTE.md` (72 bindings, 5 conditions, 0 errors) and its self-test (10/10 mutations caught); fetched the actual Zenodo deposit 10.5281/zenodo.23130191 with `analysis.py --fetch` — checksums passed and the recomputed metrics are **byte-identical to `numbers.json`**; verified timestamp monotonicity and the two >32-min gaps directly against the raw CSV; and inspected `figure1.png` (3 construction days above 10 milli-USD, panel totals 0.0753/0.0412/0.0187, shading 2026-08-25 → 2026-09-06, migration line 2026-08-23 — all match the text).

## HIGH — none found

Every number in the note matches `numbers.json` (which recomputes exactly from the deposit) or a README statement, at the note's stated rounding. I checked Tables 1–3 cell by cell, both amortization columns of Table 2 (including "in block 2 the construction cost is the same in both columns": 32.923 µUSD × 740 = 61.214 µUSD × 398), all percentages, all dates, all counts. No false or unsupported claim found.

## MEDIUM — one finding

**M1. The headline "55×" per-call cost ratio silently uses the contaminated query set.**
Abstract: "one construction call costs about 55 times as much as one query call" (line 17–18); §3: "A construction call costs USD 0.000673 on average and a query call USD 0.0000123, a ratio of about 55" (line 121–122). Both per-call averages are computed on the **raw** rows — the same rows of which the note says, one sentence later in the abstract, "62.8% of query calls match a monitoring or probe signature, so the call counts cannot be read as agent demand." Recomputing on the note's own unflagged set (1,437 rows): construction USD 0.000683/call, query USD 0.0000274/call — a ratio of **≈25, not ≈55**. The query average is doubled by removing the 17-token canary probes. Table 1 commendably gives raw and unflagged side by side for shares, but the per-call paragraph and the abstract headline give only the raw figure, and the note nowhere reports that its signature number more than halves under its own contamination filter. A data-journal reviewer will ask for exactly this. The printed value is arithmetically correct; the omission is what misleads.

## LOW

- **L1. Denominator mismatch that would pass parity (latent).** `analysis.py:97` hardcodes `m["usd_per_day"] = raw["cost"] / 32`, but `parity.py:148–150` binds the note's "per day over the 32 days" to `days_with_rows`, not to 32. If a window day ever had no rows, the note would read "over the 31 days" while the value still divides by 32, and parity would pass. Harmless today (`days_with_rows` = 32, and the README mandates the /32 convention), but the binding is to the wrong quantity.
- **L2. parity.py does not census most spelled-out numbers.** `WORDS` (parity.py:36) covers only {zero, one, two, three, six, thirteen}, and the docstring (line 26–27) admits unbound spelled-out numbers are not censused. "Three rules flag rows" (line 97), "five-hour night window" (line 98), and "seven-day blocks" (line 146) are unchecked — "six-hour night window" would pass. All three are currently correct (canary + aug10 + smoke; [01:00Z, 06:00Z); blocks 1–4), so this is a robustness gap, not a wrong value.
- **L3. Hedges dropped relative to the README.** "LLM knowledge-graph extraction is scheduled weekly" (line 204) — README D8 attributes this: "*Project records* schedule the LLM graph build weekly." "those stores have no telemetry table (D13)" (line 77–78) — README D13 qualifies: "operator measurement from 2026-09-07, *not re-measured for this deposit*." Both statements are supported in substance, but the note states them more flatly than its own source.
- **L4. Tense inconsistency.** Status block: "not peer reviewed and *not yet deposited*" (line 3) vs. Data availability: "the code for this note … *is deposited* with this note" (line 242–243). Only true after deposit; mildly confusing in a pre-deposit draft.
- **L5. parity.py rounding mode.** `same()` (parity.py:218) uses Python's banker's `round()`; a metric landing exactly on a half at the text's precision could pass/fail opposite to round-half-up. No current metric triggers this.

## Category 2 — numbers disagreeing with numbers.json or the README: none found

(See verification summary above; the recompute-from-Zenodo was exact, not approximate.)

## Category 3 — statements about [1] (Omri et al., arXiv:2606.06448): unverifiable from the files

Not judged; listed per instructions:

1. "Characterization studies of agent memory find that building memory costs more than querying it, but they measure benchmark runs, not deployments" (line 12–13) — echoed with citation [1] at line 44–45 ("measure controlled workloads [1]").
2. "Phase labels adapt the construction / retrieval split of [1] … the table adds a maintenance phase … that the benchmark decomposition does not have" (line 47–49); also "This adapts [1], where construction and retrieval are two of three phases. The third, generation, is not observable here" (line 88–90) and "The decomposition in [1] has no maintenance phase" (line 140). The README asserts the same adaptation, but the README is by the same author, so this is one source, not corroboration.
3. "These numbers agree in direction with [1], where the structure-augmented and agentic systems (their Paradigms III and IV) shift most end-to-end energy into construction" and "the cost measure (list price here, energy and wall time there)" (line 169–172) — the paradigm numbering and the energy/wall-time characterization are unverifiable here.
4. The reference itself (line 254–256): author list, title, arXiv identifier.

## Category 4 — errors in analysis.py / parity.py that compute a wrong value or let one pass

No wrong computations: the full pipeline (fetch → checksums → recompute → parity) passes end-to-end, and the parity self-test catches all 10 seeded mutations, including value-swap and rounding-truncation cases. The code-level weaknesses found are latent, all listed above as LOW: L1 (parity binds the day-count to `days_with_rows` while analysis divides by a hardcoded 32), L2 (spelled-out numbers outside bindings escape the census), L5 (banker's rounding). One further robustness note: `analysis.py:231` computes gaps between consecutive rows in file order; I verified timestamps are strictly monotonic in `id` order for this deposit, so the "no gap … exceeds 32 minutes except two" claim (line 212–213) is sound — the two gaps are 45.8 min after the smoke test and 222.5 min at the migration, matching README D9.

## Category 5 — what a data-journal reviewer would object to

- **M1 above is the main one**: the abstract's two headline quantities sit oddly together — "55× per-call cost" (raw rows) immediately followed by "query counts cannot be read as agent demand" — without the unflagged counterpart (~25×) anywhere in the note.
- Everything else a reviewer typically probes is already disclosed in the text: per-panel y-scales in Figure 1 (caption, line 137), block 5 being four days (caption, line 161), the tiny absolute scale and the shares-not-absolutes framing (line 163–167), signature-vs-verified-provenance flags (line 100–103), NOT-MEASURED items (D5, D8, D9, D11), and the version mismatch between reference [2] and the README's citation (line 259–261). Precision of per-call USD figures (e.g. USD 0.0000123 on estimated tokens, D4/D5) mirrors the README and is defensible, but a reviewer may suggest an uncertainty remark.

**Bottom line:** the note is unusually well verified — no HIGH findings, no numeric disagreements, and the deposit recomputes exactly. The one substantive defect worth fixing before deposit is M1: report the unflagged per-call cost ratio alongside the raw one, or explicitly state that the 55× figure includes the monitoring traffic the note itself discounts.