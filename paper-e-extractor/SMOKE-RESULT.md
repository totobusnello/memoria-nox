# Paper E cost smoke (2026-11-08)

Paper E asks whether the advantage of writing criterion C2 over the deployed C0 (+24.8 to +27.3 pp
in the Paper 3 confirmatory run, extractor `gemini-2.5-flash-lite`) shrinks when the extractor is
stronger. The strong extractor is `gemini-2.5-pro`, so that strength changes and the model family
does not. This smoke measures what that extractor costs per block. It computes no outcome.

Run: `runs/smoke-2026-11-08/` (`e-smoke.py`, sha256 `e51637fc…`). 40 blocks drawn with a fixed
seed from the haystacks of the 200 spent stage-1 instances, excluding every block that also occurs
in the 242 confirmatory haystacks. No reader, judge or question ran. The files keep token and
unit counts only, no block or memory text. Spend: **US$ 1.92** for 280 calls, plus US$ 0.09 for
the shape probe below.

## Criterion P

`e_prompts.py` fixes the third criterion, P ("purpose only"), before any call that used it. P keeps
C0's header, output format, importance scale, ceiling of 10 items and the >= 0.5 filter. It drops
every rule about what to keep (C0's category list and ignore list) and states instead what the
memories will be used for. sha256: C0 `72208f90…`, C2 `325342a3…` (identical to Paper 3), P
`9e7668b2…`.

## Per call

| model, thinking | criterion | input tokens | output tokens | thinking tokens | parse failures / 40 | US$ per call |
|---|---|---|---|---|---|---|
| 2.5-pro, default | C0 | 535 | 129 | 942 | 13 | 0.0114 |
| 2.5-pro, default | C2 | 860 | 186 | 1,009 | 13 | 0.0130 |
| 2.5-pro, default | P | 505 | 274 | 1,034 | 2 | 0.0137 |
| 2.5-pro, budget 128 | C0 | 535 | 100 | 71 | 25 | 0.0024 |
| 2.5-pro, budget 128 | C2 | 860 | 177 | 66 | 14 | 0.0035 |
| 2.5-pro, budget 128 | P | 505 | 261 | 70 | 1 | 0.0039 |
| 2.5-flash-lite | P | 505 | 202 | 0 | 0 | 0.00013 |

Prices: Gemini Developer API list price, standard tier, read 2026-11-08: 2.5-pro US$ 1.25 in and
US$ 10 out per million tokens (thinking billed as output); flash-lite US$ 0.10 and 0.40. The Batch
API is listed at half price.

## The parse failures are a format, not a failure

The Paper 3 parser reads `{"memories": [...]}` and serves an empty block for anything else.
`e-shape-probe.py` re-ran the first 24 failed calls that had more than one output token and kept
only the JSON shape:

| shape | calls |
|---|---|
| object with key `memories` (parses on the re-run) | 11 |
| top-level list of memory objects | 11 |
| top-level empty list | 2 |

The calls with one output token were a bare `[]`, which is what the prompt asks for when nothing
is relevant ("Retorne [] se não houver nada relevante"). `gemini-2.5-pro` often answers in the
list form; flash-lite almost never does (87 of 155,506 Paper 3 blocks failed for any reason,
0.056%). Under the Paper 3 parser, the strong extractor would lose memories to a format choice.
Paper E's parser therefore accepts both forms: an object's `memories` list, or a top-level list.
On flash-lite this can change at most the 0.056% of blocks that failed in Paper 3.

## Projected cost

Distinct blocks per criterion (median of 5 random subsets of the 242) times the per-call means
above, three criteria on the strong extractor:

| instances | distinct blocks | default thinking, batch | budget 128, batch | flash-lite P | reader and judges |
|---|---|---|---|---|---|
| 100 | 31,241 | US$ 595 | US$ 153 | US$ 4 | about US$ 12 |
| 160 | 48,399 | US$ 922 | US$ 238 | US$ 6 | about US$ 19 |
| 242 | 70,067 | US$ 1,335 | US$ 344 | US$ 9 | about US$ 29 |

Standard (non-batch) calls cost twice the batch column.

## Power for the interaction

From the 242 confirmatory rows, the weak extractor's per-instance difference d = Y(11) − Y(10) has
mean +0.248 and variance 0.228 (judge 1; judge 2: +0.273, 0.240). Assuming the strong extractor's
difference has the same variance and correlation ρ with the weak one, a paired test at α = 0.05
two-sided and 80% power needs:

| shrinkage of the C2 advantage | ρ = 0 | ρ = 0.2 | ρ = 0.4 |
|---|---|---|---|
| 10 pp | 358 | 287 | 215 |
| 15 pp | 159 | 128 | 96 |
| 20 pp | 90 | 72 | 54 |

Only 242 instances exist, so a 10 pp shrinkage is detectable only with positive correlation and
the full sample. With 100 instances the design detects a shrinkage of about 15 to 20 pp, that is,
an advantage cut by more than half.

## Second smoke: `gemini-2.5-flash`, thinking off

The pro arms priced the design above what the study is worth, so a second set (`e-smoke.py --set
flash`, run `runs/smoke-flash-2026-11-08/`) priced the middle model of the same generation:
`gemini-2.5-flash` with `thinkingBudget: 0`, on the same 40 blocks. Its request differs from the
flash-lite one only by the model name and that thinking setting. List price US$ 0.30 in and
US$ 2.50 out per million tokens, read 2026-11-08. Spend: US$ 0.08.

| criterion | input tokens | output tokens | parse failures / 40 | units kept per block | US$ per call |
|---|---|---|---|---|---|
| C0 | 535 | 137 | 0 | 2.42 | 0.00050 |
| C2 | 860 | 139 | 0 | 2.98 | 0.00061 |
| P | 505 | 258 | 0 | 4.30 | 0.00080 |

All 120 answers used the `{"memories": [...]}` form. With 70,067 distinct blocks on all 242
instances, the three criteria cost about US$ 133 at the standard price and US$ 67 in batch, plus
US$ 9 for flash-lite on P and about US$ 29 for reader and judges. The step from flash-lite to
flash is smaller than the step to pro, so a null interaction here would not rule out one at a
larger step.
