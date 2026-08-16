# Action-corpus freeze — 2026-07-29T09:46:09Z

> Closes the open item declared in `CALIBRATION-SEED.md`: *"declaring the seed is
> not enough — a seed orders a set, and the set moves."* This document freezes
> the set.

---

## The problem this solves

The episode corpus is derived from a live archive that grows by **~330 episodes
per day**. Between the pre-registration (2026-07-26) and the sampling
(2026-07-29) it went from 4,560 to 5,547 episodes, and the taxonomy derived from
`sig()` moved with it: **72 → 74** primary signatures, **162 → 168** fine. Any
number published over that corpus expires on its own between writing and
submission.

The beacon seed makes the **sampling** reproducible. Without freezing the set
being sampled, it orders something that no longer exists.

## What is frozen

| Artefact | SHA-256 |
|---|---|
| **Snapshot** `action-archive-20260729T094609Z.tar.gz` (107 MB) | `ba5fcc81f43cede6e40572236be984bc0cc5e450325b115e2b994f5a24cdf382` |
| **Manifest** `corpus-manifest-20260729T094609Z.txt` (3,860 lines) | `2fe8ba2b6a545a84c3a3ee09efe061126c74ee93c5d458eb3209076ade6c5638` |
| `extract_episodes.py` — canonical implementation of `sig()` | `e860357bd9f1fc0690ec8a817b7f6d23ac0c237882152d3a8714f7c0af7748b2` |
| `adjudication_prompt.md` (the file) | `3767fdb50e31ce41e3de8484501c056a48ccdfa3cc3e283f59e64a8d2c339bd7` |
| **Prompt sent** to the panelists (extracted body) | `5b22f02c1a557417fe874b98cdf8a3ad6441cada74d69ace8e54f82b3438b03e` |
| Commit freezing `sig()` | `c0abe143df1ab6452cf83556b2bc442ec87319a0` (2026-07-26T16:27:28-03:00) |

⚠️ The two prompt hashes are **not the same object** and both matter:
`carregar_prompt()` extracts only the body between the header and the first HTML
comment, and it is that body which goes to the panelists. The file hash versions
the artefact; the body hash versions what was actually sent.

⚠️ **The files in this table are hash-locked and must never be edited — including
for translation.** `extract_episodes.py` and `adjudication_prompt.md` are
therefore the only artefacts in this deposit still written in Portuguese; an
English rendering of the prompt is provided as a *separate* file
(`adjudication_prompt.en.md`) which is documentation only and was never sent to
any panelist.

**Corpus state at freeze time:** 3,860 `.jsonl` files, 409 MB uncompressed,
spread across 9 agent directories.

## How a third party verifies

The manifest lives **in this repository** precisely so that verification does not
require downloading 107 MB. It lists the SHA-256 of each of the 3,860 files:

```bash
# from the snapshot
tar xzf action-archive-20260729T094609Z.tar.gz
sha256sum -c corpus-manifest-20260729T094609Z.txt      # 3,860 OK expected

# and the snapshot against itself
sha256sum action-archive-20260729T094609Z.tar.gz
```

The snapshot lives in `/var/backups/nox-mem/paper2-corpus/` with mode `0400`
(read-only, even for the owner) and is not covered by automatic rotation.

## What this freeze does NOT solve

1. **It does not freeze retroactively.** The pre-registration numbers written on
   2026-07-26 (4,560 episodes, 72/162 signatures) describe a corpus that no
   longer exists. Anyone reproducing from this snapshot obtains **5,547 episodes
   and 74/168 signatures**, and that divergence is expected, not an error. The
   §4.1 numbers were updated to those of this snapshot.
2. **It does not make the archive immutable at the source.**
   `/var/lib/nox-mem/action-archive` keeps growing. Future freezes need a new
   snapshot and a new hash — this document is dated deliberately.
3. ~~**It does not settle the provenance of the `-tmp` episodes.**~~ ✅ **VERIFIED
   AND CLOSED on 2026-07-29.** The 1,615 files (41.8%) under `-tmp` contribute
   **no episodes at all**: a sweep of 400 of them found **zero `tool_use`**. They
   are memory-compaction sessions (`queue-operation`, a *"maximum
   non-destructive compression"* prompt), with no executed action.

   Two hypotheses were tested and refuted. **(a) Contamination by the panel:**
   `run_panel.py` invokes the CLIs with `cwd="/tmp"`, and ~1,700 calls against
   1,615 files is a coincidence that demanded checking. Refuted by the temporal
   distribution — the `-tmp` files are uniform at **~145/day since 2026-07-18**,
   not concentrated on 07-28 when the panel ran. **(b) A construct problem:** it
   does not exist, because a file without `tool_use` never becomes an episode.
   The 5,547-episode corpus comes entirely from the nine named agent
   directories.

   What remains: the snapshot's **file** count (3,860) far exceeds the count of
   files that **produce episodes**. The two numbers measure different things and
   must not be cited for one another.

## Provenance

The archive is fed by `nox-archive-transcripts.sh` (cron `40 3,9,15,21`), which
mirrors `/root/.claude/projects/` with `rsync` **without** `--delete` — which is
why it preserves episodes that the 04:23 `prune-claude-sessions.sh` deletes at
the source. On 2026-07-27 that mechanism rescued 311 files that today exist only
in the archive. The snapshot above inherits that property.
