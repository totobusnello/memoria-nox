# Neither cause explains it alone: the window and the prompt interact — 2026-10-27

**What this corrects.** Two readings were published today and both were wrong in the same way.
The morning's audit called the see-once rule the mechanism; the afternoon's called the extraction
criterion the mechanism and the window a product concern. Measured together, **each explains 8.7% of
the gap and the two together explain 45.7%.** There is no single mechanism. There is an interaction,
and the earlier framings each attributed to one cause an effect that needs both.

## The A/B — one paragraph of prompt, everything else fixed

`DISTILL_SYSTEM_V2` is the builder's own prompt with a single paragraph inserted, requiring every
identifier in the conversation to be copied letter for letter — file name, path, command, table or
column name, config key, port, URL, channel, version, numeric value — and stating that a memory
without the identifier is not worth extracting. Blocking, model, temperature, `responseMimeType`, the
`importance >= 0.5` filter and the **10-item ceiling** are untouched. The ceiling is a candidate of
its own and stays fixed so that whatever moves is attributable to the paragraph.

| arm | input / prompt | correct | silent | contradicts |
|---|---|---|---|---|
| A — oracle *(control)* | raw window / — | 88.9% | 0.0% | 17.2% |
| **B — the real memory** | visible / OLD | **42.4%** | 49.5% | 7.1% |
| C_visible — my re-implementation | visible / OLD | **42.4%** | 47.5% | 7.1% |
| D_visible | visible / **NEW** | 46.5% | 39.4% | 13.1% |
| C_all | whole / OLD | 46.5% | 39.4% | 17.2% |
| **D_full** | whole / **NEW** | **63.6%** | 25.3% | 12.1% |
| D_iso — D_full at B's budget | whole / NEW | 48.5% | 43.4% | 7.1% |
| bm25_iso — naive RAG at B's budget | raw chunks | 63.6% | 24.2% | 15.2% |

## The interaction is superadditive, and that is the finding

| what is changed | correct | recovers | share of the 46.5 pp gap |
|---|---|---|---|
| the window alone (C_all) | 46.5% | +4.0 pp | 8.7% |
| the prompt alone (D_visible) | 46.5% | +4.0 pp | 8.7% |
| **both (D_full)** | **63.6%** | **+21.2 pp** | **45.7%** |

4.0 + 4.0 = 8.0, and together they give 21.2. **An interaction of 13.2 pp**, which is larger than
either main effect. The mechanism is legible: an instruction to carry the identifier can only act on
an identifier that is in the block the builder is shown, and a block that contains the identifier is
no use if the criterion discards it. Each fix is nearly inert without the other.

🔑 **And it closes the net-value claim.** Against naive RAG at 63.6%:

| memory arm | net value |
|---|---|
| B, as built | **−21.2 pp** |
| D_iso — both fixes, B's context budget | −15.2 pp |
| **D_full — both fixes, the 2.4× context the fixed builder would produce** | **0.0 pp** |

The negative net value measured this morning is **not a property of agent memory**. It is a property
of this construction, and two changes — neither of which is a new idea — bring it level with naive
RAG over the raw text.

⚠️ **D_full receives 2.41× arm B's characters**, because a builder that returns produces more memory;
arm B likewise received all of its own units. At a strictly equal budget the figure is **48.5%**, net
value −15.2 pp. Quote whichever matches the claim, and never the 0.0 pp without the 2.4×.

## `context` was the cell this was written for, and it moved

| category | n | A | B | D_visible | C_all | **D_full** | bm25_iso |
|---|---|---|---|---|---|---|---|
| **`context`** | 42 | 90.5% | 26.2% | 28.6% | 26.2% | **52.4%** | 66.7% |
| `decision` | 29 | 82.8% | 48.3% | 51.7% | 48.3% | **65.5%** | 55.2% |
| `lesson` | 28 | 92.9% | 60.7% | 67.9% | 75.0% | **78.6%** | 67.9% |

`context` **doubles**, from 26.2% to 52.4%, and `decision` passes naive RAG. `context` still trails
retrieval over the raw text by 14 pp, so the criterion is better and not solved.

| final prose | n | A | B | D_visible | **D_full** | bm25_iso |
|---|---|---|---|---|---|---|
| < 50k | 52 | 90.4% | 53.8% | 57.7% | 59.6% | 63.5% |
| 50–200k | 7 | 71.4% | 42.9% | **14.3%** | 71.4% | 71.4% |
| **200k–1M** | 40 | 90.0% | **27.5%** | 37.5% | **67.5%** | 62.5% |

In the band where see-once bites, the memory goes from 27.5% to **67.5%** and overtakes naive RAG.

## Controls

| control | result |
|---|---|
| **fidelity, now on accuracy** — same prompt, same input as the real builder | C_visible = **42.4%** correct and **7.1%** contradicting: arm B's figures **exactly**. This is what makes C and D readable at all; the earlier run could only show volume (ratio 1.17) |
| **mechanical, no judge** — do identifiers survive verbatim? | visible **10.1% → 16.5%**, whole **6.6% → 12.9%**. The prompt's claim is a string-matching claim and was tested as one, before any model was asked |
| volume did not collapse | units +8.5% (997→1082 visible, 2141→2361 whole), chars per unit +8% |
| d_iso budget | aggregate **0.991**, 0 pairs over |
| distillation failures | **0 of 563** |
| damage | D_full contradicts at 12.1%, below arm A's 17.2% false-positive floor — **fourth day without asserting damage** |

⚠️ **Two cells where my re-implementation is not faithful, stated rather than smoothed:** C_visible
matches B on the aggregate and on contradiction exactly, but gives 16.7% on `context` against B's
26.2%, and D_visible drops to 14.3% in the 50–200k band against B's 42.9% (n=7, so three cases). The
missing embedding dedup is the likely cause. **Per-cell differences of that size are inside this
instrument; the aggregate and the 200k–1M band are not.**

## What this changes

- **The paper's claim changes shape, and gets stronger.** Not "agent memory has negative net value"
  but "this construction does, the cause is an interaction of window and criterion, and fixing both
  brings it level". That is a result with a mechanism and a remedy, measured on production data.
- **Ship both or neither.** Each fix alone buys 4 pp and would read as a failed intervention.
  Shipping the prompt without fixing see-once is the likely way to conclude, wrongly, that the prompt
  does not work.
- **`context` is improved, not solved** — 52.4% against retrieval's 66.7%. The 10-item ceiling and
  the no-overlap blocking are still untested as causes, and are the next candidates.
- **The two earlier framings from today are superseded**, not the numbers: every figure in
  `2026-10-27-net-value-and-see-once.md` and `-the-gap-is-extraction-not-the-window.md` stands. What
  changes is the attribution, which neither of them could see without the other arm.

**Cost.** Distillation US$ 0.2436 (1,462,899 in / 243,246 out, from the provider's counts), judging
US$ 0.0316. The answer calls were not instrumented in this script; the equivalent run in arm C cost
US$ 0.1082 for 99 pairs over 2 arms, so 4 arms is ~US$ 0.20 — an estimate, anchored on a measurement,
and labelled as one. **~US$ 0.48.**

**Artifacts.** `audits/2026-10-27-arm-d-verbatim-identifiers-{build,answer}.py`. Units, answers and
judge keys stay on the host (`/root/medicoes/2026-10-26-memory-tax/`).

---

## Correction, same day — the window factor has no variance in most of the sample

Found while writing the pre-registration code rather than the plan, which is the only reason it was
found before a DOI existed. `audits/2026-10-27-window-variance-correction.py`, free, no API calls.

**The window factor is the fraction of the session the builder saw. On 182 of the 194 eligible
sessions that fraction is ≥ 0.95** — the builder saw essentially everything, so W0 and W1 are the
same arm and the factor is inestimable there by construction. In this sample, 43 of the 99 pairs sit
in that condition and were averaged in regardless.

That cuts both ways, and the limit is the more important half.

**The limit.** The figures above rest on fewer sessions than the pair counts suggest:

| figure | pairs | **sessions** |
|---|---|---|
| the headline, all arms | 99 | **17** |
| `<50k` band | 52 | 11 |
| `50-200k` band | 7 | **1** |
| `200k-1M` band | 40 | **5** |
| **the interaction** — needs the window to vary | 56 | **8** |

The audits said "20 sessions, 99 questions". The interaction rests on **eight**, the 50–200k row on
**one**, and the unit of inference is the session, not the question. That is the same defect class as
a severity stratum resting on one panel family, and it was not declared.

**The bias, in the other direction.** 43 pairs could not show a window effect at all. Restricted to
the 56 pairs where the window varies:

| | published (all 99) | **window varies (56 pairs, 8 sessions)** |
|---|---|---|
| oracle | 88.9% | 89.3% |
| **memory as built** | 42.4% | **30.4%** |
| gap to close | 46.5 pp | **58.9 pp** |
| window alone | +4.0 pp = 8.7% | **+10.7 pp = 18.2%** |
| criterion alone | +4.0 pp = 8.7% | +3.6 pp = 6.1% |
| **both** | +21.2 pp = 45.7% | **+35.7 pp = 60.6%** |
| **interaction** | +13.2 pp | **+21.4 pp** |
| D_full against bm25_iso | 63.6% vs 63.6% (level) | **66.1% vs 60.7% (memory ahead)** |

So every published figure **understated** the effect, by averaging in a condition where one factor
could not act. The interaction is 21.4 pp where it can occur, not 13.2 pp.

⚠️ **This recomputation is post-hoc on data already seen and is not confirmation.** It is the correct
reading of the sample we have, with n=8 sessions, and it is reported because the published numbers
were wrong in a stated direction — not because the larger figure is preferred.

**The control that makes the partition readable, and it passes.** Where the window is flat the window
factor cannot act, so the two window levels must coincide:

| | visible | whole | verdict |
|---|---|---|---|
| old criterion | 55.8% | 53.5% | 2.3 pp — ok |
| new criterion | 62.8% | 60.5% | 2.3 pp — ok |

Had these diverged, the partition would have been tracking something other than the window.

## And it makes the pre-registration plan as drafted unexecutable

`paper3-construction/PREREGISTRATION-DRAFT.md` asks for 60 sessions, 15 per stratum. Available:

| stratum | eligible sessions | already used |
|---|---|---|
| `<50k` | 185 | 14 |
| `50-200k` | **3** | 2 |
| `200k-1M` | **6** | 4 |
| `>1M` | **0** | — |
| **window varies at all (<95% seen)** | **12** | **8** |

The band where the effect lives holds **nine sessions in the whole corpus**, and the exploratory run
already consumed most of them. A confirmatory factorial on this corpus would re-use the same sessions,
which is not confirmation. **The plan cannot be deposited as written**, and the fix is a design
decision, not an amendment: see the plan's own status note.
