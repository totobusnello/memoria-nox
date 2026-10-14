# Review of rc2: Grok and Codex, 2026-10-13

Full read of `DATA-NOTE.md` with `analysis.py`, `parity.py`, `numbers.json`, `figure.py` and the dataset README.

| voice | receipt | exit | attach |
|---|---|---|---|
| Grok (`grok-4.7`) | `adversary-receipt-grok-2026-10-13T205256-75144.txt` | 0 | 51,056 B |
| Codex | `adversary-receipt-codex-2026-10-13T205256-75260.txt` | 0 | harness (reads the checkout) |

Both receipts verified with `verify-adversary-receipt.sh`; both ran in the checkout of this branch.
Neither voice found a number that disagrees with `numbers.json` or the README.

## Disposition

| # | finding | voices | status | action |
|---|---|---|---|---|
| 1 | `parity.py` accepts any value from any key; the "every number" rule is false | both | confirmed: the 4 Codex mutations passed | `parity.py` rewritten: 72 bindings tie each number to its metric or README statement, 5 word conditions, unbound numbers fail, decimals need 2 significant digits; `--selftest` catches 10/10 mutations |
| 1a | "1.0" in version strings would make parity fail | Grok | false in effect: it passed by matching unrelated keys | moot after the rewrite (versions are bound) |
| 1b | facts stated but not computed (485, 474/114, gaps, failure dates, top-3 caller, phase rule) | both | confirmed | computed in `analysis.py`; all reproduce the README |
| 2 | "Most query calls come from the monitor" | both | confirmed: canary is 45.2%, flags are signature matches | heading and abstract say "match a monitoring signature"; counts "cannot be read as agent demand" |
| 3 | "clean"; transferability; "absolute cost carries no information" | both | confirmed | "unflagged"; transferability "not tested here" |
| 4 | "13 days without writes" asserts inactivity | Codex | confirmed (D9) | "no recorded construction or maintenance call" |
| 5 | Table 2 ratio "moves with construction timing, not query volume" | Codex | confirmed by block 2 | rewritten: depends on both terms |
| 6 | "no information about people" broader than the check | Codex | confirmed | states the closed-vocabulary check only |
| 7 | all 588 rows described as probe-like | Grok | confirmed (474 + 114) | split stated |
| 8 | "most of the ratio is input size" (tokens 67x vs cost 55x) | Grok | confirmed | both ratios given, model and price mix named |
| 9 | "Tokens are stored raw" | Grok | confirmed | estimates disclosed (D4) |
| 10 | "follow [1], so can be compared" vs README "adapt" | Grok | confirmed | "adapt", "coarse comparison" |
| 11 | "prune or forget" quote next to maintenance | Grok | quote is correct (checked in [1] §4.7); its use implied compaction = pruning | quote removed; maintenance defined as compaction and consolidation, not pruning |
| 12 | spec row "every code path" ignores D7, D9 | Grok | confirmed | gaps named |
| 13 | smoke 0.1%; per-day ignores partial first day | Grok | confirmed | 0.060%; first day 13.3 h stated |
| 14 | [2] v1.0.6 vs README v1.0.2 | Grok | judgment | kept v1.0.6 (author's decision); README version noted |
| 15 | title and "two readings" read as a results paper | both | judgment | kept (author's decision); conclusions trimmed to what the data support |
| 16 | statements about [1] unverifiable from the attached files | both | checked against arXiv:2606.06448 v2: §4.2 "Construction Dominates the Agent Lifecycle", Paradigm III/IV energy in construction, §4.7 "None of the evaluated systems prune or forget by default" | no change needed beyond item 11 |

One number written during the fixes was wrong before it was computed: the canary share inside the
13-day stretch was first written as 92.0% and is 96.3%. It was corrected from `analysis.py`
before the census ran.
