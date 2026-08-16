# External references — where the things this package points at actually live

This directory is deposited as a self-contained package. Several documents cite
artifacts that live **outside** it. A reader who follows those citations inside
the deposit finds nothing, which reads as a broken promise rather than as a
deliberate boundary. This file resolves each one.

Repository: `https://github.com/totobusnello/memoria-nox`, directory
`paper2-interventional/`. Paths below are relative to the repository root.

## Deliberately not deposited — production data

These files are real production verdicts and episodes. They are the study's raw
material and they are **not** deposited: they contain the contents of actions
executed by live agents. What *is* deposited is the code that produces and
consumes them, the seeds that determine every sample, and the hashes.

| Cited as | Where it lives | Cited in |
|---|---|---|
| `universo-extensao.jsonl` | `~/.paper2-verdicts/` (operator host) | `EXTENSION-2-SEED-2026-08-14.md` |
| `verdicts-extensao-full-v2.jsonl` | `~/.paper2-verdicts/` | `SIZING-2026-08-14.md` |
| `extensao-pass1.jsonl` | `~/.paper2-verdicts/` | `STABILITY-TEST.md` |
| `extensao-moonshot-ainda-restante.jsonl` | `~/.paper2-verdicts/` | `STABILITY-TEST.md` |
| `universo-combinado.jsonl`, `verdicts-combinado-v2.jsonl`, `estrato-b-ids.txt` | `~/.paper2-verdicts/` | `SIZING-2026-08-14-v2.md` §2 |

Reproducibility without them: the seeds are declared in `CALIBRATION-SEED.md`,
`EXTENSION-SEED-2026-08-11.md` and `EXTENSION-2-SEED-2026-08-14.md`, each naming
a `drand` round committed **before that round existed**; the corpus state is
frozen by hash in `CORPUS-FREEZE.md` and `corpus-manifest-20260729T094609Z.txt`;
and `extract_episodes.py` is deterministic and hash-locked. A third party with
access to an equivalent action archive reproduces the sampling exactly. A third
party without one can verify every seed, every hash and every computation, but
cannot re-derive the verdicts — that limitation is real and is stated here rather
than implied.

## Host configuration — pinned by hash, not by file

The production policy is pinned to the systemd drop-in the running service reads,
not to a repository commit, because a commit hash would not catch a drift between
repository and host (`PREREG-DRAFT.md` §2).

| Cited as | What it is | SHA-256 |
|---|---|---|
| `d2-brief-diversity-active.conf` | control policy `NOX_BRIEF_DIVERSITY=active`, LOCKED 2026-07-29 | `76726519559ffbe65283610b9d4efe4c17a0d74933363c235e3859ef28af267c` |
| `p2s1-shadow.conf` | companion carrying `NOX_EPOCH_SNAPSHOT` | `3d27b98d…` |

## Elsewhere in the same repository

| Cited as | Cited in |
|---|---|
| `specs/2026-07-25-P2S1-serving-side-snapshot.md` — the serving-side snapshot mechanism (§0) | `PREREG-DRAFT.md`, `PLAN-2-TRILHAS.md` |
| `docs/INCIDENTS.md` — the operational incident log | `CONCEPT-NOTE.md`, `METHODOLOGY.md`, `REVIEWS.md` |
| `docs/DECISIONS.md` | `RELATED-WORK.md` |
| `docs/STANFORD-OUTREACH.md` | `NEXT-STEPS.md` |

`specs/2026-07-25-P2S1-serving-side-snapshot.md` is the one closest to
load-bearing — §0's frozen-corpus mechanism rests on that engineering work — and
it is deliberately **not** deposited. Two reasons, both stated rather than
implied: it is an internal engineering specification written in Portuguese, and
it carries open engineering debts unrelated to this study, which would enter the
scientific record as noise. What the pre-registration actually asserts about the
mechanism it asserts **inline and with measured numbers** (§0: `VACUUM INTO` at
9.8 s bare / 17.8 s with manifest over a 1.6 GB database, sliding retention of 3
snapshots at ~4.8 GB = 1.8% of free space, kill criterion K1 passing); the spec
corroborates those numbers, it does not carry them. The rest of the table is
context, and a reader who wants any of it can follow the repository.
