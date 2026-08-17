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
| `paper2-interventional/PILOT-PROJECTION.md` — the pilot's projected quantities, superseded by `SIZING-2026-08-14-v2.md` and kept as the record of what was projected before it was measured | `PREREG-DRAFT.md`, both `EXTENSION-*-SEED` files |
| `paper2-interventional/REVIEWS-PREREG.md` — the full adversarial verdict on v0.1 (GLM-5.2: 5 FATAL / 7 GRAVE / 10 minor) | `PREREG-DRAFT.md` §9, version history |
| `paper2-interventional/tests/test_icc_ci.py` — confronts the pure-stdlib F implementation of `icc_bootstrap.py` against `scipy`; the only place `scipy` appears, and never on the canonical path | `SIZING-2026-08-14-v2.md` |
| `paper2-interventional/OSF-SUBMISSION.md` — the OSF submission checklist, in Portuguese, carrying the abstract that will be registered there. Not deposited because it is an operating checklist rather than a result, and because the abstract it carries is reproduced in the registration itself; cited here because `claims_check.py` names it as one of the files it sweeps, and because on 2026-08-17 it was found holding two stale claims and the wrong attachment version — the reason the sweep now covers Portuguese as well as English | `claims_check.py` |

**`REVIEWS-PREREG.md` deserves a word, because its absence reads worse than the
others.** This package argues that a registration should show the review that
shaped it, and §9 cites a verdict that a reader of the deposit alone cannot open.
It is not deposited because it is an internal working document in Portuguese,
covering v0.1 — a draft two locks and eleven versions behind this one — and
depositing a stale review beside a current registration invites reading the
former as commentary on the latter. Every fix it produced is recorded **inline**
in §9, each at the point it applies, with the reviewer's own text quoted in
block. The file is in the public repository for anyone who wants the unabridged
version.

## Operational scripts — on the production host only

These run the fleet. They are not in the repository: they are operator
infrastructure, not instruments of the study, and none of them computes anything
the analysis consumes. Each is cited only to say that a mechanism is **running**,
and every such claim is separately verifiable from the artifacts here.

| Cited as | What it does | Cited in | How the claim is checkable without it |
|---|---|---|---|
| `nox-epoch-boundary.sh` | `cron 0 6 * * *` — rotates the 24 h epoch at 06:00 BRT | `PREREG-DRAFT.md` §2 | the rotations it produced are in the frozen corpus; epoch ids are timestamps |
| `nox-archive-transcripts.sh` | `cron 40 3,9,15,21` — copies agent transcripts into the action archive before the daily prune | `PREREG-DRAFT.md` §3, `CORPUS-FREEZE.md` | `corpus-manifest-20260729T094609Z.txt` hashes exactly what the archive held |
| `prune-claude-sessions.sh` | `cron 04:23` — deletes CLI sessions; the archive above exists to outrun it | `CORPUS-FREEZE.md` | same manifest: what survived is what is hashed |
| `extensao-moonshot-loop.sh` | drove the Moonshot panelist's rate-limited extension pass | `STABILITY-TEST.md` | the verdicts it produced are counted and hashed in `STABILITY-TEST.md` |

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
