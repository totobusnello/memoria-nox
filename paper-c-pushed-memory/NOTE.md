---
title: "Delivered, not quoted: no textual trace of a pushed memory brief in agent replies"
author: "Luiz Antonio Busnello"
---

Status: working draft, not deposited, not peer reviewed. A data note, dated: every measurement
below covers 2026-09-21 to 2026-10-23 on one deployment. Every number has an entry in
`PROVENANCE.json`.

## Abstract

A memory system for a group of software agents pushed a short brief of ten memory items into each
agent's system prompt on every turn. We asked whether the agents' replies show any trace of what
the brief contained. Three measurements answered no, each within its own limits. Across 1,524
assistant messages from six agents, none of 12,782 exposed (message, brief item) pairs carried a
strict or fuzzy textual trace of the item, while a control built from items that entered the brief
later matched 57 times. A second measurement, on 574 messages, compared what was served with what a
recency-ordered brief would have served: zero traces in both arms, with a detector that fired on
95.7% to 100.0% of injected items. A behavioural probe that planted a salient fact in the brief and
watched the agent's first action failed its own positive control (0 of 10 decisive scenarios
against a gate of 7), so its main phase was not run. We state the result narrowly: in these
protocols we did not detect a textual trace of the pushed brief, nor a change in the first action.
This is not evidence that the agents do not use memory. On the pull side, the agents almost never
searched the memory on their own, but when one was given a task that required it, it did.

## 1. Setting

The memory system (nox-mem) serves a brief: ten items chosen by salience, refreshed by a scheduled
job, written to a file per agent, and appended to the agent's system prompt on every turn. The
agents are long-running assistants that act on schedules and on messages. The brief is the only
channel by which memory reaches them without the agent asking; the other channel is a search tool
the agent may call.

The question this note answers is narrow: when the brief is in the prompt, do the agent's replies
show it?

## 2. Measurement 1: textual trace in replies

Unit and arms. One assistant message, with the items of the brief that was in the prompt when
the message was written (the exposed arm). Two controls use the same agent's briefs at other
moments of the window: items that had left the brief before the message (past), and items that
entered it later (future). The future control is the check that the detector can see overlap at
all, because a conversation can push its own material into a later brief.

Detectors. Strict: the item's one-line summary (at least 25 characters) verbatim, or a
distinctive file stem on word boundaries. Fuzzy: at least 60% of the item's distinctive tokens. A
first version matched stems as substrings and counted dictionary words, and produced eight strict
"hits", all false on inspection; it is kept in the audit as a lesson and not used.

Result. Over 2026-09-21 to 2026-10-15, reading all three places where transcripts are kept:
1,524 messages, 12,782 exposed pairs, zero strict and zero fuzzy hits. The future control produced
57 fuzzy hits. In the first run, the hits of that control were read by hand: they were summaries
derived from the same conversations that entered the brief afterwards, and so: the detector sees real overlap when it exists, and the exposed zero is not a
blind instrument.

The base was understated at first. The first run read one of three transcript roots and
reported 1,120 messages. Transcripts are kept in two live directories and an archive, and one of
the live directories is pruned on a seven-day clock, so a rerun of the same script later reaches
fewer messages than it did. Reading all three roots raised the base by 36%. The verdict did not
change: the exposed arm stayed at zero while the positive control scaled with the base.

## 3. Measurement 2: served brief against a recency-ordered brief

From 2026-10-14 the brief server also logged, on every refresh and without changing what the agent
received, what a recency-ordered brief would have contained. Over 574 messages in the following
week, the served arm (the only one that could be copied from the prompt) and the counterfactual
recency arm were measured on the same message with the same detectors. Both had zero strict and
zero fuzzy hits, and no message was discordant, so the paired comparison carried no information.

A positive control injected brief items into message text and re-ran the detector. It fired on
95.7% of injected one-line summaries and on 100.0% of summaries with their file stem, and 99.6% of
the items in the window were detectable by construction. If an agent had quoted an item, the
detector would have seen it.

## 4. Measurement 3: the first action, behaviourally

Influence without textual trace is possible: an agent can be steered by a brief item and never
reuse its wording. A behavioural probe tried to measure this. It froze 20 scheduled scenarios,
replaced one brief item with a planted fact, and checked whether the agent's first action used the
planted value. By the rule fixed before the run, the main phase would run only if the planted fact
was picked up in at least 7 of 10 decisive scenarios.

It was picked up in 0 of 10, so the main phase did not run, and its nulls would have been
uninformative. The fact did reach the prompt: restricted to the 28 runs whose first message was a
real action, the planted value appeared in 3, all in decisive scenarios, and never without the
plant (0 of 27). It did not displace the old value, which appeared at about the same rate with and
without the plant (13 of 28 and 12 of 27). The first action followed the scheduled prompt and the
workspace instructions, not the brief.

## 5. The pull side

The brief is the push channel. The pull channel is a search tool, and through 2026-10-21, 337 of
382 searches recorded by the memory server were its own 30-minute canary probe; none came from an
agent. On 2026-10-23, an agent was given a recurring task whose answer depended on the corpus (a
weekly sweep for contract deadlines, where an exhaustive query finds the candidates and the agent
checks whether each was later amended). The prompt did not name the search tool. In two production
runs it searched 11 and 6 times on its own. The audit's reading: zero traffic was never evidence
that retrieval is unwanted; it was evidence that the questions being asked of the corpus were
censuses.

## 6. What this note claims, and what it does not

It claims: in these three protocols, on this deployment and in this window, we did not detect a
textual trace of the pushed brief in the agents' replies, nor a change in the first action of
scheduled runs.

It does not claim that the agents do not use memory, that the brief has no effect later in a
session or in free conversation, or that a different brief would also go unused. The behavioural
probe failed its positive control and measured only the first action. The textual detectors see
quotation and close paraphrase, not influence.

## 7. Two things that transfer

A measurement over transcripts is a measurement over a substrate someone else prunes. The same
script, run a week apart, read different data, because a cleanup job deletes old sessions daily and
only an archive keeps them. The base of the first measurement was understated by 36% for this
reason. Both scripts now read all three roots and print the roots and the directory count, so the
base can be checked from the output.

A null needs a positive control, and the control has to pass. Measurements 1 and 2 carry one
that passes, so their zeros are facts about the agents. Measurement 3 carried one that failed, so
its silence is a fact about the probe, and this note reports it that way.

## 8. Data availability

The transcripts and the brief items are private and are not released. The detectors, the positive
controls and the audits that report each number are in the public repository; raw outputs that
contain agent text stay on the host. Every number in this note has an entry in `PROVENANCE.json`
naming its audit, a locator string that must occur in it, and the commit that holds it.
