# Brief usage by agents — ROADMAP v6 item 7(a), 2026-10-14

**Question.** The brief reaches every agent's system prompt (cron `nox-mem-brief-refresh.sh` →
`agents/<p>/brief/MEMORY.md` → OpenClaw hook `bootstrap-extra-files` → Claude CLI
`--append-system-prompt-file`, `systemPromptWhen: "always"`; verified on a leftover system prompt
of 2026-09-30). Do the agents' replies show any trace of the brief items?

**Design.** Unit: one assistant message (text blocks), 2026-09-21 → 2026-10-14 (after the Paper 2
trial, which manipulated the brief). Exposed arm: items of the brief that was in the prompt at that
moment (latest `brief_id` for the agent before the message). Controls: items in the same agent's
briefs at another moment of the window, split into *past* (left before) and *future* (enter later;
the conversation can push an item into a later brief). Items no longer in `chunks` are excluded.

Detectors: **strict** — the item's one-liner (≥ 25 chars, cut at 140 as `src/api/brief.ts` does)
verbatim, or a distinctive file stem (has `-`, `_` or a digit) on word boundaries; **fuzzy** — ≥ 60%
of the item's distinctive tokens (≥ 4 chars, present in < 5% of messages; min 4 tokens).

**v1 was wrong and is kept as a lesson:** stems were matched as substrings and plain dictionary
stems counted, so `EVOLUTION` matched "Marginal Revolution" in Boris's reading digests: 8 strict
"hits", all false (checked by hand). v2 below.

**Result (v2).**

```
assistant messages with text in window: 1120
by brief agent: {'nox': 426, 'boris': 549, 'forge': 103, 'cipher': 42}
briefs per agent: {'nox': 4568, 'atlas': 2284, 'boris': 2284, 'cipher': 2284, 'forge': 2284, 'lex': 2284}
distinct brief items: 974, resolvable in chunks: 623

== boris
  exposed      pairs=    4639  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_past    pairs=   52245  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_future  pairs=   94640  strict=    0 (  0.00/10k)  fuzzy=    2 (  0.21/10k)

== cipher
  exposed      pairs=     365  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_past    pairs=    1300  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_future  pairs=    3291  strict=    0 (  0.00/10k)  fuzzy=    1 (  3.04/10k)

== forge
  exposed      pairs=     847  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_past    pairs=    1471  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_future  pairs=    5510  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)

== nox
  exposed      pairs=    3547  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_past    pairs=   19331  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_future  pairs=   56358  strict=    0 (  0.00/10k)  fuzzy=   19 (  3.37/10k)

== ALL
  exposed      pairs=    9398  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_past    pairs=   74347  strict=    0 (  0.00/10k)  fuzzy=    0 (  0.00/10k)
  ctrl_future  pairs=  159799  strict=    0 (  0.00/10k)  fuzzy=   22 (  1.38/10k)

```

- **0 of 9,398 exposed pairs** carry a strict or fuzzy trace of the brief item, in 1,120 messages
  from four agents (atlas and lex had no turns).
- **Positive control:** the *future* arm has 22 fuzzy hits. By hand, they are chunks **derived from
  those same conversations** (session-distill summaries, end-of-day notes) that entered the brief
  later — reverse causation, as anticipated. The detector does see real overlap when it exists, so
  the exposed zero is not a blind instrument.
- **Not measured:** influence without textual trace (an agent that avoids a mistake because of the
  brief). That is item 7(b), the action probe.

**Reading.** The brief is delivered and not visibly used. Its items average 91–154 days old (April
incidents and reports at pain 1.0), while what the agents work on — their own recent sessions and
notes — only reaches the brief afterwards. Changing what the brief selects is a ranking change
(rule 5: `feat`, shadow first), and this measurement is the baseline to compare against.

Script: `audits/2026-10-14-brief-usage.py` (read-only; run on the production host). Per-hit samples
with session content stay on the host (`/root/medicoes/2026-10-14-brief-uso/`), not in this public
repo.

---

## 2026-10-22 — rerun: the base was understated by 36%, the verdict is not

The R1 audit of 2026-10-21 found that transcripts live under **two** roots and that it had read
one. This script had the same hole. Fixing it exposed a second, larger one.

**There are three roots, not two, and the live ones shrink daily.** `prune-claude-sessions.sh`
(cron 04:23) deletes every `.jsonl` older than 7 days from `/root/.claude/projects`, plus any
smaller than 50 KB older than 12 h. `nox-archive-transcripts.sh` (cron 03:40/09:40/15:40/21:40)
discovers every `$HOME/.claude*/projects` by glob and copies them to
`/var/lib/nox-mem/action-archive` — 1,543 files, 443 MB, reaching back to 2026-08-15. The archive
is where the pruned sessions survive, and no measurement had been reading it.

So the substrate of this audit is not stable: it is pruned on a 7-day clock. Rerunning the
published single-root configuration **today** reaches fewer messages than it did on 14/10, because
the window has since aged past the prune.

Same code, same window (2026-09-21 → 2026-10-15), roots varied via `PROJ_ROOTS`:

| configuration | dirs | messages | exposed pairs | strict | fuzzy (future control) |
|---|---|---|---|---|---|
| as published, 2026-10-14 | 5 | 1,120 | 9,398 | **0** | 22 |
| one root, rerun today | 5 | 1,029 | 8,683 | **0** | 20 |
| two roots, today | 12 | 1,079 | 9,108 | **0** | 25 |
| **three roots (with archive), today** | **19** | **1,524** | **12,782** | **0** | 57 |

**What was wrong.** The published base was understated by 36% (1,120 → 1,524), and the sentence
"atlas and lex had no turns" was false by the same mechanism — they have 7 and 11. `forge` goes
103 → 237, `cipher` 42 → 76.

**What holds.** Zero strict hits in 12,782 exposed pairs, against 57 fuzzy hits in the future
control — the positive control scales with the base and the exposed arm stays at zero. The reading
of this audit is unchanged, now on 36% more evidence.

🔑 **Transferable: a measurement over transcripts is a measurement over a substrate someone else
prunes.** Two jobs touch it on a schedule, one of them deleting on a 7-day clock, and the number a
script reports therefore depends on *when* it is run, not only on what it reads. Re-running an
audit later is not re-running the same audit. Both this script and the R1 one now default to all
three roots and print the roots and the directory count, so the base is auditable from the output.
The R1 audit was rerun the same way: 523 → 574 messages (+9.8%), verdict identical.

Reruns on the host in `/root/medicoes/2026-10-22-7a-refeito/`.
