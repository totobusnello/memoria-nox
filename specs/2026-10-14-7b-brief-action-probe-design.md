# 7b — Brief action probe: does the injected brief change what agents do?

Status: **v3.2** (2026-10-14; v3.1 approved by Toto, v3.2 amendment §3/§4.1 approved by Toto after the render gate failed). ROADMAP v6 item 7(b).
v1 challenged by Kimi (`adversary-receipt-kimi-2026-10-14T194124-93966.txt`) and Grok
(`adversary-receipt-grok-2026-10-14T194125-94087.txt`); v2 reviewed by Kimi
(`…kimi-2026-10-14T195904-11351.txt`, NO-GO, 5 MÉDIO) and Grok (`…grok-2026-10-14T195909-11431.txt`,
NO-GO, 3 ALTO / 6 MÉDIO / 3 BAIXO). §11 maps every finding to its disposition.
Decisions by Toto (2026-10-14), not reopened: an underspecified-request stratum; one sham
(other-agent memory, filtered), framed as right vs wrong memory; `claude -p` with a deny-all hook.

## 1. Question and why

nox-mem reaches the VPS agents only through the **brief**: a cron (`nox-mem-brief-refresh.sh`, every
15 min) writes `agents/<p>/brief/MEMORY.md`, the OpenClaw hook `bootstrap-extra-files` injects it, and
the Claude CLI backend appends it to the system prompt on every run (`--append-system-prompt-file`).
Agents never search nox-mem (0 `nox_mem_search` calls since 2026-09-01).

7(a) (`audits/2026-10-14-brief-usage.md`) found **0 of 9,398** exposed (brief item × reply) pairs with
a textual trace of use, with a positive control that fired. That rules out *visible* use only.

**7(b) asks:** holding everything else fixed, does the brief change the agent's **first action**
(presence effect), does *its content* change it relative to wrong-agent memory (content effect), and
is the change for the better? Every conclusion is scoped to **the first assistant message** under
**today's scaffold**; a null here does not close item 7.

The harness is selection-agnostic: any brief (D2 today, R1 at the 2026-10-21 checkpoint) is an arm.

Related: Mem2ActBench (Shen et al., ACL 2026): memory matters when it grounds the arguments of a tool
call from an *underspecified* instruction. DolphinBench (Mem0) is on the 2026-10-13 reading list.

## 2. Units, strata and clusters

Census of non-heartbeat input turns, 2026-09-21 → 2026-10-14, tool results and task notifications
excluded: **156 turns from only 18 distinct prompts** (agent × normalized prefix); five prompts carry
112 turns (`relatorio-eod` 24, `end-of-day` 24, `x-digest-tarde-discord` 24,
`memory-cron-failure-feedback` 22, `ai-daily-digest-manha` 18). The effective N is the number of
clusters, not turns. Three strata, analysed separately:

| stratum | main units | cluster | source |
|---|---|---|---|
| **C** (scheduled work) | Σ min(turns, 8) over the 17 non-Discord prompts = **71** (2026-10-14 census), instances spread evenly over the window so each sees a different brief | the cron prompt | transcripts |
| **R** (real human) | the **13** human Discord turns to forge | the turn | transcripts |
| **H** (underspecified requests) | **40** | the source task | authored per §2.1 |

Main: 124 units. **Pilot** (§5, excluded from every decision): 20 C instances drawn from the surplus of
the five large prompts (not in the main sample) and 10 H requests authored separately (§2.1). All lists
are frozen in a manifest (unit id, stratum, cluster, agent, t, sha256 of the input) before any run.

### 2.1 Authoring stratum H blind to the briefs

- The **task catalog** is the 18 cron prompts, the 13 Discord turns and each agent's `SOUL.md` role
  section. Nothing from `brief_log`, `chunks` or any `MEMORY.md` enters it.
- A **fresh GPT run** (`OPENAI_API_KEY`, no tools, input = catalog only) writes **50** requests a
  person would plausibly send these agents, each leaving one argument implicit ("redo the digest like
  last time but skip the long threads"), with owner agent and source task. A seeded draw assigns 10 to
  the pilot and 40 to the main set. GPT authors H and the rubrics (§6.2); Gemini judges, so no single
  model family defines the request, the standard and the verdict.
- Requests are frozen (sha256) **before** any brief is reconstructed. Each gets a timestamp t drawn
  uniformly from the window by a frozen seed; if the owner agent has no brief before t, t is redrawn
  with the next seed value (count reported).
- Relevance is not controlled: H measures whether the real brief helps on realistic requests, including
  when it carries nothing relevant. **Diagnostic** (reported, not a decision input): after B1 is
  reconstructed, a blind Gemini pass sees each request and its B1 items (no runs) and marks whether the
  implicit argument is present in some item; the rate separates "brief irrelevant" from "brief ignored".

## 3. Arms

Each unit runs **three arms × two replicas** (temperature cannot be set in `claude -p`; replicas give
the noise floor):

| arm | brief block in the system prompt |
|---|---|
| **B0** | none (block removed) |
| **B1** | the brief **as served**: the latest git-archived snapshot of the owner's `brief/MEMORY.md` whose header `generated_at` ≤ t, byte for byte (§4.1 explains why not `brief_log`) |
| **BS** | wrong-agent memory, built by the frozen procedure below from other agents' archived snapshots |

**BS procedure (reproducible):**

1. The manifest freezes, per unit and before filtering, an **ordered candidate list**: other agents in
   a seeded order (for owners `main` and `nox`, both are excluded: their briefs share the `nox` content);
   for each, its archived snapshots with `generated_at` in [t − 3 days, t], nearest first. Only snapshots
   served **before** t are eligible, so no future information can enter.
2. Flatten the list into one item sequence: candidate snapshots in list order, item lines in served
   order. Remove items whose `chk` id is in B1 and items whose distinctive-token overlap with any B1 item
   exceeds 0.3 (7a token definition); keep each `chk` id once.
3. Slide a window of |B1| consecutive items over that filtered sequence, starting at position 0. Build
   the block exactly as served (auto-generated comment, header line with the owner's agent label and
   B1's `generated_at`, then the item lines as archived); accept the first window whose block is within
   ±10% of B1's length in characters; otherwise advance the window by one item. If the sequence is
   exhausted, the unit is dropped.
4. Drop rate is reported per stratum; if it exceeds 20% of a stratum, that stratum's Δc is flagged as
   estimated on a selected subset.

BS is **not** a neutral placebo: B1 vs BS contrasts right with wrong memory, and BS worse than B0 is
never evidence that B1 helps.

## 4. Execution

- **Scaffold:** the OpenClaw-appended template, persisted from tmpfs to
  `/root/medicoes/7b-scaffold/forge-2026-09-30T2231.system-prompt.md`
  (sha256 `7b4b0820009bc170d178e0ce8bf16af5780a9d394e90bf678b2addee0dffb75c`), with the owner agent's
  **current** bootstrap files, identical across arms, plus the arm's brief block. The run aborts if the
  hash differs.
- **Arm-file check:** an automated diff asserts the arm files of a unit differ only inside the brief
  block; the unit fails otherwise. sha256 of each arm file, CLI version and flags are logged per run.
- **One isolated config dir** (`CLAUDE_CONFIG_DIR`), on an account other than the agents'
  (`claude-nuvini-team`), holds: the `PreToolUse` deny-all hook, and the owner agent's MCP configuration
  with **schemas only** (no write credentials). An MCP server is included only if the smoke test shows
  that connecting to it has no side effect; otherwise it is excluded for every arm and listed in the
  manifest.
- **Run:** `claude -p --model claude-sonnet-5 --append-system-prompt-file <arm file> --max-turns 1` in
  that dir. The hook records **every** tool call of the first assistant message (name + input) and
  denies it.
- **Smoke test, first task, same dir:** a tool whose execution would leave a trace; pass iff the call is
  recorded and no trace exists. No unit runs before it passes.
- **Block scheduling:** the six runs of a unit execute back-to-back in random order (same date line, no
  drift within a unit); units are shuffled.
- **Failures:** a failed run is retried once. Per stratum and per arm, failures after retry are compared
  with the other two arms pooled by a 2×2 Fisher exact test; every contrast that involves an arm with
  p < 0.05 is **inconclusive** for that stratum (its p is set to 1 in §6.1 and its Δ is not read);
  contrasts not involving such an arm are read normally.
- **Data handling:** inputs and outputs contain session content and stay on the VPS
  (`/root/medicoes/`). The memoria-nox repo is public: only scripts, frozen non-content parameters and
  aggregates are committed.

### 4.1 Fidelity (amended in v3.2)

**Why the brief is not rebuilt from `brief_log`.** The v3.1 gate re-rendered every git-archived served
brief of the window from `brief_log` chunk ids: **0 of 525 matched**, and 524 failed because at least one
chunk no longer exists. Until the write-path fix of 2026-10-14 14:34 UTC, re-ingesting a file replaced its
chunk ids; the daily `lessons` re-ingest therefore removed one served item of nearly every brief (e.g.
chunks 313690–313695, served 2026-10-08/09, gone). `brief_log` cannot reproduce any brief of the window.

**What is used instead.** Each agent's `MEMORY.md` is committed to the workspace git (71 snapshots per
agent in the window, mostly around 02:00). B1 is the latest snapshot with `generated_at` ≤ t, verbatim:
exactly a text that was served, not a reconstruction. The cost is timing: the brief at t is approximated
by the last archived one. **Reported, not gated:** the distribution of t − `generated_at` per stratum,
and the item turnover between consecutive snapshots of the same agent (share of `chk` ids that change),
which bounds how far the snapshot can be from the brief at t.

- **Scaffold leakage (reported):** distinctive-token overlap between each B1 and today's bootstrap
  files; units where any B1 item overlaps > 0.5 are flagged and the primaries are reported with and
  without them.

## 5. Pilot (excluded from every decision)

30 units (20 C, 10 H), B1 only, **four replicas**. It freezes, before the main run:

1. **Canonical serialization** (executable, versioned): the first message becomes one token sequence:
   each tool call in order as `tool_name` followed by its arguments, JSON keys sorted, Bash parsed to
   argv with flags sorted; then the message text. A closed regex set masks dates, times, uuids, hashes
   and temp paths. Tokenization is fixed (split on whitespace and punctuation).
2. **Divergence** `d(x, y)` = normalized Levenshtein distance between the two token sequences
   (edit distance ÷ length of the longer), in [0, 1]. Order-aware; one comparator for every pair.
3. **Validity ceiling:** if a stratum's pilot A/A mean divergence (pairs of distinct replicas) exceeds
   **0.5**, the mechanical primary for that stratum is **invalid** (not null).
4. **MDE:** simulate the §6.1 estimator per stratum. Each simulated unit takes a pilot unit as its
   base; the replicas of every arm are drawn without replacement from that unit's four pilot replicas
   (so A/A is real run-to-run noise). Under the alternative with parameter q, for each simulated unit
   with probability q, the comparison arm's replicas are drawn instead from a different pilot unit of
   the same stratum. Clusters follow the main set's structure. For each q on a grid, compute the
   power of the one-sided bootstrap test at α = 0.0125 (the strictest Holm step, 0.05/4, which makes the
   MDE conservative without simulating the other three tests) and E[Δ | q]. MDE = the smallest E[Δ | q]
   with power ≥ 80%. Frozen per stratum.

Frozen parameters are committed (no content) before the main run.

## 6. Metrics and pre-registered decision rules

### 6.1 Primary (mechanical, no judge), strata C and H

Per unit, replicas r1, r2:

- `AA = mean of d(Xr1, Xr2)` over the three arms (noise floor).
- `D(X, Y) = mean of d(Xri, Yrj)` over the four replica cross-pairs.
- **Presence** `Δp = D(B1, B0) − AA`; **content** `Δc = D(B1, BS) − AA`.

Stratum estimate = mean over clusters of the cluster mean (each cluster of §2 weighs once).
**Cluster bootstrap**, 10,000 draws resampling clusters within the stratum.

- **Test:** one-sided bootstrap p = (1 + #draws with Δ ≤ 0) / (1 + 10,000).
- **Multiplicity:** Holm over the four p values (Δp, Δc × C, H); an effect is declared iff its
  Holm-adjusted p < 0.05. If a stratum is invalid (§5.3), its two p values are set to 1; if a contrast is
  inconclusive (§4), its p value is set to 1; the family stays at four.
- **Reporting:** unadjusted 95% percentile CIs alongside.
- **Null reading** (only when no effect is declared): effects outside the CI are excluded. If the CI
  contains 0 and its upper bound is below the stratum's frozen MDE, effects ≥ MDE are excluded; if the
  CI contains 0 and its upper bound is ≥ MDE, the stratum is reported as underpowered for effects of
  that size.
- **Invalid stratum** (§5.3): no Δ, no CI, no null reading for its mechanical primaries; only §6.2 is
  read for it, and if §6.2 also fails a gate the stratum is inconclusive.
- Stratum R (13 units) is descriptive only.

### 6.2 Secondary (judged): is the change for the better? Strata C and H (R judged, descriptive)

- **Rubric:** per unit, written **from the input alone** by the GPT authoring run before any arm runs
  (what a correct first action must and must not do), frozen in the manifest. External facts enter only
  if they are in the input or describe state before t, and are marked as such. Nothing from the
  historical run (messages, exit codes, artefacts) is used.
- **Judge:** Gemini, blind to arm, A/B order randomized; sees input, rubric and two candidates (replica
  r1); outputs A / B / tie + one-line reason.
- **Pairs:** B1×B0, B1×BS, B0×BS (diagnostic), B1r1×B1r2.
- **Unit score** for a contrast: 1 if the first-named arm wins, 0.5 tie, 0 loss. Stratum score = mean
  over clusters of cluster means; 95% percentile CI by the §6.1 cluster bootstrap.
- **"The brief helps"** in a stratum iff the **lower bound** of that CI exceeds 0.5 for **both** B1×B0
  and B1×BS. Secondary, not Holm-adjusted.

**Judge validity gates** (if either fails, §6.2 is invalid for every stratum):

- **Position:** over all non-tie judgments of the main set (≈ 500), the share choosing the slot shown
  as A must be equivalent to 0.5 by TOST, α = 0.05, margin ±0.10. The B1r1×B1r2 tie rate and win rate
  are reported, not gated (randomized order makes that win rate 0.5 by symmetry).
- **Known answer:** 20 B1r1 runs with a tool call, drawn by seed from C and H, each paired with a copy
  corrupted by a fixed script cycling three operators: (i) the first path argument replaced by a
  non-existent sibling path; (ii) the tool name replaced by another tool from the same schema set;
  (iii) the argument the rubric marks required removed. The judge must prefer the original in ≥ 17/20.

**If the primary is invalid and §6.2 fails a gate** for a stratum, the stratum is **inconclusive**, and
that is the reported result.

## 7. Positive control

20 scenarios on real cron prompts, frozen before any run and never substituted afterwards. The fact is
planted by **substitution** (it replaces one B1 item; item count unchanged), and the scenario is such
that the fact changes an argument of the first action.

- 10 **decisive** facts (salient, specific, e.g. a moved output directory) and 10 **typical** facts in
  the vague register of real brief items.
- Arms: B1 with the substitution vs B1, two replicas each. The planted token must be absent from the
  input turn (checked at freeze time).
- **Scenario hit** = in **both** replicas of the planted arm, the planted value appears in the first
  message's actions and the superseded value does not. **False hit** = the planted value appears in
  either replica of the B1 arm (counted after the runs).
- **Pass** iff decisive hits ≥ 7/10 **and** false hits ≤ 1/10 decisive scenarios.
- **Reading:** §6 nulls are informative only if the control passes **and** typical hits ≥ 3/10. If the
  decisive control passes but typical hits < 3/10, nulls are read as "the probe sees salient facts but
  not facts in the brief's register". If the control fails, nulls are uninformative; positives are
  always reported.

## 8. Threats and limits (declared)

- First assistant message only; influence that emerges after tool feedback is invisible by
  construction.
- The scaffold is today's (one captured template, current bootstrap files); the estimand is "the brief
  block under today's scaffold", not the historical runs.
- B1 is the last archived served snapshot before t, not the brief at t (§4.1 reports the gap and the
  turnover).
- The observed turns happened with the brief present; the corpus is a selected stratum.
- Stratum H is synthetic; its realism rests on the catalog and on blind authoring by a model family
  other than the judge's. Rubric author and H author are the same family (GPT).
- MCP servers excluded for side effects (§4) shrink the tool surface equally in every arm.

## 9. Cost, sequence, deliverables

- CLI runs on the subscription: smoke test; pilot 30 × 4 = 120; main 124 × 6 = 744; control 20 × 2
  arms × 2 = 80 ⇒ ≈ 950, spread over one to two days.
- GPT: 50 H requests + 124 + 30 rubrics. Gemini: 40 relevance diagnostics + ≈ 500 judgments + 20
  known-answer. Cents.
- Sequence: scaffold hash check → smoke test → snapshot index and §4.1 fidelity report → manifest (C, R, H, BS
  candidate lists, rubrics, control scenarios) frozen → pilot → frozen parameters committed → main run +
  control → analysis exactly as §6–7 → `audits/<date>-7b-action-probe.md`.
- Code in `eval/brief-action-probe/`; raw data on the VPS only.

## 10. Glossary of frozen artefacts

manifest (units, seeds, candidate lists, rubrics, scenarios) · canonical serializer + mask regex ·
validity ceiling per stratum · MDE per stratum · config dir hash (hook + MCP schemas) · scaffold sha256.

## 11. Review dispositions

### v1 → v2 (challenge)

| finding (voice) | disposition |
|---|---|
| Primary ignores the sham; presence ≠ content (Kimi A1, Grok) | Δp and Δc both primary (§6.1) |
| Retrospect leaks the D2 trajectory to the judge (both) | retrospect removed; input-only rubric (§6.2) |
| Turn-level bootstrap anti-conservative; 18 prompts (both) | strata, clusters, cluster bootstrap, cap 8 per prompt (§2, §6.1) |
| "Significant vs not significant" in the helps rule (both) | direct B1×BS contrast (§6.2) |
| Positive control: echo, guessable, no threshold, too salient (both) | substitution, baseline check, threshold, typical facts (§7) |
| Divergence near 1 by construction; one-line masker; Jaccard 0.5 (both) | pilot-frozen serializer, continuous d, validity ceiling (§5) |
| Temperature not fixed (both) | not settable in `claude -p`; replicas + A/A floor (§3) |
| Cron corpus biased to null (Kimi A4) | stratum H (§2.1), Toto's decision |
| Sham is wrong memory, not neutral (Kimi A5, Grok) | filtered BS, right vs wrong memory (§3), Toto's decision |
| First action only; null used to close 7b (both) | all tool calls of the first message; scoped claims (§1, §4, §8) |
| Reconstruction not only external validity (Grok) | fidelity and leakage checks (§4.1) |
| Judge gate too weak (both) | position gate + known-answer gate (§6.2) |
| No MDE; no multiplicity policy (both) | pilot MDE; Holm (§5, §6.1) |
| Cache/clock between interleaved runs (Grok) | six runs of a unit back-to-back (§4) |

### v2 → v3 (review)

| finding (voice, severity) | disposition |
|---|---|
| H count impossible with a pilot excluded from decisions (Kimi M1, Grok ALTO) | author 50: 10 pilot, 40 main; C derived as 71; main 124 (§2, §2.1, §9) |
| TOST on B1r1×B1r2 measures no position bias and cannot pass at this N (Grok ALTO) | position gate on share of slot A over ≈ 500 judgments, margin ±0.10; B1r1×B1r2 reported only (§6.2) |
| Null/MDE sentence false; MDE not executable (Kimi M3, Grok ALTO) | null reading rewritten; MDE simulates the exact estimator under a stated alternative (§5.4, §6.1) |
| "Corrected CI" undefined; family when a stratum is invalid (Kimi M2, Grok) | one-sided bootstrap p, Holm on p, p = 1 for invalid strata (§6.1) |
| Helps rule: level, bound, stratum scope (Kimi M4, Grok) | lower bound of 95% CI > 0.5, per stratum C and H, unit score 1/0.5/0 (§6.2) |
| Control: false-hit rule contradicts exclusion; replicas; typical unused (Kimi M5, Grok) | hit = both replicas; false hits counted post-run; no substitution; typical ≥ 3/10 gates null reading (§7) |
| Divergence: token-set Jaccard vs "in order"/structural (Grok) | one serialization, normalized Levenshtein on token sequence (§5.1–5.2) |
| BS not reproducible; formatter; drop bias (Grok) | frozen ordered candidate list, production render, ±10% rendered, drop-rate flag (§3) |
| Cron exit code re-enters the rubric (Grok) | historical exit codes and artefacts excluded (§6.2) |
| Render fidelity checked once (Kimi, Grok) | gate over ≈ 71 git-archived served briefs per agent, ≥ 95% exact, files never edited (§4.1) |
| Hook not bound to the isolated config dir; MCP side effects on connect (Grok) | single config dir with hook + schema-only MCP, side-effect check, smoke test in it (§4) |
| Failure-rate test has no branch (Kimi B3, Grok) | Fisher exact per stratum ⇒ contrast inconclusive (§4) |
| Judge gates underspecified (Kimi B2) | α, margin, seed and corruption operators fixed (§6.2) |
| Same family authors H, rubric and verdict (Kimi B4) | GPT authors H and rubrics; Gemini judges (§2.1, §8) |
| H unit with no brief before t (Kimi B5) | seeded redraw, count reported (§2.1) |
| H relevance not measured (Grok BAIXO) | blind relevance diagnostic (§2.1) |
| "each cron prompt weighs once" wrong for H/R (Grok BAIXO) | "each cluster of §2 weighs once" (§6.1) |
| Scaffold on a tmpfs glob (Grok BAIXO) | persisted copy + sha256, abort on mismatch (§4) |
| C ≈ 75 not derivable (Kimi B1) | C = Σ min(turns, 8) = 71 (§2) |

### v3 → v3.1 (Grok diff-only pass, `…grok-2026-10-14T201848-45207.txt`: 16 RESOLVED, 3 FALSE, 2 new)

| finding | disposition |
|---|---|
| Null reading: "otherwise" also fires when the CI excludes 0 (FALSE) | null reading only when no effect is declared; underpowered branch requires CI ∋ 0 (§6.1) |
| MDE: base sequence undefined; Holm not simulated (FALSE) | base pilot unit per simulated unit; power at α = 0.0125, the strictest Holm step (§5.4) |
| BS walk not a function: item order, "continue the walk" (FALSE) | flattened ordered sequence, sliding window of |B1| items (§3) |
| Invalid stratum could still get CI and null reading (new) | invalid stratum has no Δ, CI or null reading (§6.1) |
| Fisher across three arms names no arm (new) | 2×2 per arm vs the other two pooled; p = 1 only for contrasts touching it (§4, §6.1) |

### v3.1 → v3.2 (execution finding, Toto's decision)

| finding | disposition |
|---|---|
| §4.1 gate: 0/525 archived briefs reproducible from `brief_log` (ids rotated by daily re-ingest before the 2026-10-14 write-path fix) | B1 and BS come from git-archived served snapshots (§3); gate replaced by a reported gap/turnover measure (§4.1) |
