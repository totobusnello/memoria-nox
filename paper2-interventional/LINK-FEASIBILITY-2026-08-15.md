# `linked` — what can actually be built, measured

> **2026-08-15.** Exploratory, pre-treatment, read-only. Changes no locked
> number. Script: `link_feasibility.mjs`. It exists because the dose measurement
> (`dose_reach.mjs`) exposed that §2's `linked` term had never been defined.

## 1. There is no join key — and it is not a recoverable oversight

| | |
|---|---|
| distinct sessions across the episodes | 789 |
| session UUIDs in chunk `source_file` | 48 |
| **intersection** | **0** |
| chunks originating from the action archive | **0** |
| chunks carrying `episode` in `metadata` | **0** |

The episodes' session UUIDs come from the **Claude CLI**
(`/root/.claude/projects`); the chunks' come from **OpenClaw**
(`sessions/<agent>/…`). Disjoint namespaces. There is no latent link waiting to
be found: the link has to be **constructed**, and how it is constructed decides
which chunks receive the boost — that is, it decides the treatment itself.

## 2. The three constructions, and why two fail

**A — match existing chunks by signature (`sig()`), textually.**
Rejected, on the argument this document already makes elsewhere: chunks carry no
signature, so the match would be FTS over the signature's tokens. That scores
**topical adjacency, not episodic linkage** — precisely the defect for which the
`pain` column is forbidden as a wiring (`Do not wire this to the existing pain
column`, §9-4). Worse, it would make the matching heuristic a free parameter of
the treatment.

**C — change the salience weights for episode chunks** (e.g. exempting them from
the `access_count` penalty). Rejected: the control arm *is* the production brief
policy. Altering the formula so the study can work contaminates the control and
destroys the comparison the whole design exists to make.

**B — write the memory from the adjudicated episode**, carrying `episode_id` in
`metadata`, and apply `W_OUTCOME × severity` to it. The link becomes one of
**construction**: auditable, no heuristic, no invented key. It is the only one
left — and it is also the one that matches the paper's thesis (memory of
failures avoids repeating them), whereas re-weighting pre-existing chunks that
were never about the episodes transmits no failure information at all.

## 3. Does B work? Measured

Chunk written as `chunk_type='lesson'` → importance **0.90**
(`IMPORTANCE_BY_TYPE`), `access_count = 0`, `pain` = severity.

| cut | value |
|---|---|
| slot 10 of the main pool | **0.8524** |
| coverage slot 2 (`freshSlots = 2`) | **0.7342** |

| sev | share of failures | base | w=0.5 | w=1.0 | w=2.0 | enters? | minimum `w` |
|---|---|---|---|---|---|---|---|
| **S1** | **69.73%** | 0.6700 | 0.6754 | 0.6808 | 0.6915 | never | **6.0** |
| **S2** | **29.62%** | 0.6950 | 0.7058 | 0.7165 | **0.7380** | only at `w=2.0` | 1.8 |
| S3 | 0.58% | 0.7200 | **0.7361** | 0.7522 | 0.7845 | from `w=0.5` | 0.4 |
| S4 | 0.08% | 0.7450 | — | — | — | already, unboosted | 0 |

**Three readings, in this order of importance:**

1. **The main slot is unreachable for new content at any locked dose.** The best
   case falls 0.0214 short of the cut. The entire treatment acts through the
   **2 coverage slots**, never the 8 primary ones.
2. **The dose decides, and it decides where the mass is.** At S2 — 29.62% of
   failures — only `w = 2.0` gets in. That is a real dose–response gradient,
   with 30% of the corpus as the effective treated population. The `w` arm is
   not a label.
3. **The modal failure is out of reach.** S1 is 69.73% of failures and would
   need `w ≈ 6.0` — three times the top of the locked band
   `{0.5 · 1.0 · 2.0}`. Widening it would be an **amendment**, not an escape
   clause: `w` was locked on 2026-07-29 with that band stated explicitly.

## 4. What this forces us to declare

- The **effective treated population is ~30% of failures** (S2 and above), not
  all of them. This tightens the detectable effect further and belongs in the
  abstract, not in a limitations section.
- The effect of `w` is a **threshold at the coverage-slot boundary** for S2, not
  a continuum. The pre-committed dose–response reading rule in §3 has to be
  rewritten in those terms.
- `w ≈ 6.0` as what reaching S1 would require is **recorded now**, before any
  arm data exists, so that widening the band later is visibly an amendment
  rather than a refinement.

## 5. What remains open

Construction B still needs decisions that are **not** measurement: which
component writes the chunk (the adjudication pipeline being the natural home),
when (end of epoch? immediately?), with what text, and whether the write happens
in **both** arms with only the boost differing — which is the only way for the
contrast to isolate weighting rather than confounding writing with weighting.
That last one matters most and is a design decision, not a number.
