# 7b — Brief action probe: does the injected brief change what agents do?

Status: **v2 for review** (2026-10-14). ROADMAP v6 item 7(b). v1 was challenged by Kimi
(`adversary-receipt-kimi-2026-10-14T194124-93966.txt`) and Grok
(`adversary-receipt-grok-2026-10-14T194125-94087.txt`); §10 maps each finding to its disposition.
Decisions by Toto (2026-10-14): add an underspecified-request stratum; one sham (other-agent memory,
filtered), framed as right vs wrong memory.

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
prompts, not turns. Hence three strata, analysed separately:

| stratum | units | cluster | source |
|---|---|---|---|
| **C** (scheduled work) | real cron/boot turns, **at most 8 per prompt**, spread evenly over the window so each instance sees a different brief | the cron prompt | transcripts |
| **R** (real human) | the 13 human Discord turns to forge | the turn | transcripts |
| **H** (underspecified requests) | **40** human-style requests that leave a needed argument unstated | the source task | written per §2.1 |

Expected units: C ≈ 75, R = 13, H = 40. Exact lists are frozen in a manifest (unit id, stratum,
cluster, agent, t, sha256 of the input) before any run.

### 2.1 Authoring stratum H without seeing the briefs

- The **task catalog** is the 18 cron prompts, the 13 Discord turns and each agent's `SOUL.md` role
  section. Nothing from `brief_log`, `chunks` or any `MEMORY.md` enters it.
- A **fresh model run** (Gemini, no tools, input = catalog only) writes 40 requests a person would
  plausibly send these agents, each leaving one argument implicit ("redo the digest like last time but
  skip the long threads"), with owner agent and source task.
- The requests are frozen (sha256 in the manifest) **before** any brief is reconstructed. Each gets a
  timestamp t drawn uniformly from the window; its B1 is the owner agent's brief at t.
- Whether any brief item is relevant to a request is not controlled: the stratum measures whether the
  real brief helps on realistic requests, including the case where it carries nothing relevant.

## 3. Arms

Each unit runs **three arms × two replicas** (temperature cannot be set in `claude -p`; replicas
provide the noise floor):

| arm | brief block in the system prompt |
|---|---|
| **B0** | none (block removed) |
| **B1** | the brief the agent had at t: latest `brief_id` for that agent with `served_at` < t in `brief_log`, rendered from its chunk ids by the production formatter |
| **BS** | wrong-agent memory: another agent's brief from `brief_log` within ±3 days of t, filtered (below) |

**BS filter:** only chunks with `created_at ≤ t`; drop items whose chunk id appears in B1 or whose
distinctive-token overlap with any B1 item exceeds 0.3 (7a token definition); refill from the next
candidate brief; match item count exactly and total tokens within ±10%. A unit whose BS cannot be
built under the filter is dropped and counted. BS is **not** a neutral placebo: B1 vs BS contrasts
right with wrong memory, and BS worse than B0 is never evidence that B1 helps.

## 4. Execution

- **Scaffold:** the OpenClaw-appended template captured in
  `/tmp/openclaw/openclaw-cli-system-prompt-*/system-prompt.md` (forge, 2026-09-30) with the owner
  agent's **current** bootstrap files, identical across arms, plus the arm's brief block.
- **Arm-file check:** an automated diff asserts the arm files of a unit differ only inside the brief
  block; the unit fails otherwise. sha256 of each arm file, CLI version and flags are logged per run.
- **Run:** `claude -p --model claude-sonnet-5 --append-system-prompt-file <arm file> --max-turns 1`,
  with the owner agent's MCP configuration so tool schemas match production.
- **Nothing executes:** a `PreToolUse` hook records **every** tool call of the first assistant message
  (name + input) and denies it. First plan task: a smoke test proving capture and that nothing ran (a
  tool whose execution would leave a trace).
- **Block scheduling:** the six runs of a unit execute back-to-back in random order (same date line,
  no drift within a unit); units are shuffled.
- **Account isolation:** a separate `CLAUDE_CONFIG_DIR` on an account other than the agents'
  (`claude-nuvini-team`), verified before running.
- **Failures:** a failed or retried run is re-run once; the per-arm failure rate is reported and
  tested for difference before any metric is read.
- **Data handling:** inputs and outputs contain session content and stay on the VPS
  (`/root/medicoes/`). The memoria-nox repo is public: only scripts, the frozen non-content parameters
  and aggregates are committed.

### 4.1 Fidelity checks (reported, some gating)

- **B1 render fidelity:** the 2026-09-30 22:31 captured prompt contains the brief generated at 22:22;
  the harness renders that `brief_id` and compares byte-for-byte. A mismatch is fixed before running.
- **Scaffold leakage:** distinctive-token overlap between each B1 and today's bootstrap files; units
  where any B1 item overlaps > 0.5 are flagged and analysed with and without them.

## 5. Pilot (excluded from every decision)

20 units from stratum C (instances not in the main sample) and 5 from H, B1 only, **four replicas**.
The pilot freezes, before the main run:

1. **Canonicalizer** (executable, versioned): action string = tool name + arguments, Bash parsed to
   argv with flags sorted, a closed regex set masking dates, times, uuids, hashes and temp paths; JSON
   arguments compared structurally. If the first message has no tool call, its text is the action.
2. **Divergence** `d(x, y) = 1 − token-set Jaccard` of canonical action strings over the whole first
   message (all tool calls in order, then text). Continuous, one comparator for every pair.
3. **Validity ceiling:** if the pilot A/A divergence of a stratum exceeds **0.5**, the mechanical
   primary for that stratum is declared **invalid** (not null) and only §6.2 is read.
4. **MDE:** minimum detectable Δ by simulation under the pilot A/A distribution with the §6.1 cluster
   bootstrap; written into the frozen parameters.

## 6. Metrics and pre-registered decision rules

### 6.1 Primary (mechanical, no judge), per stratum

Per unit, with replicas r1, r2:

- `AA = mean of d(Xr1, Xr2)` over the three arms (noise floor).
- `D(X, Y) = mean of d(Xri, Yrj)` over the four replica cross-pairs.
- **Presence** `Δp = D(B1, B0) − AA`; **content** `Δc = D(B1, BS) − AA`.

Stratum estimate = mean over clusters of the cluster mean (each cron prompt weighs once). CI by
**cluster bootstrap** (resample clusters, 10,000 draws). The four decisions (Δp, Δc in strata C and H)
are Holm-corrected at family α = 0.05; stratum R (13 units) is descriptive only.

- **Presence effect** iff the corrected CI of Δp lies above 0.
- **Content effect** iff the corrected CI of Δc lies above 0.
- A CI containing 0 excludes only effects larger than the stratum's frozen MDE.

### 6.2 Secondary (judged): is the change for the better?

- **Rubric:** per unit, written **from the input alone** by a fresh Gemini run before any arm runs
  (what a correct first action must and must not do); frozen in the manifest. Where an external outcome
  exists independently of the agent's text (cron exit code, a file the prompt names), it is added as a
  fact. Nothing produced under the real brief (final messages, later turns) is shown.
- **Judge:** Gemini, blind to arm, A/B order randomized; sees input, rubric, two candidates (replica
  r1); outputs A / B / tie + one-line reason.
- **Pairs:** B1×B0, B1×BS, B0×BS, and B1r1×B1r2 (gate).
- **Win rate** with ties counted as 0.5; CI by the §6.1 cluster bootstrap.
- **"The brief helps"** iff CI(win B1 over B0) > 50% **and** CI(win B1 over BS) > 50% (the direct
  contrast; no comparison of significance levels). B0×BS is diagnostic only.

**Judge validity gates** (§6.2 is reported as invalid if either fails):

- **Position/form:** B1r1×B1r2 win rate equivalent to 50% by TOST with margin ±5pp.
- **Known answer:** 20 pairs of a real B1 run against a copy corrupted to violate its rubric (wrong
  path, wrong tool, missing required argument); the judge must prefer the original in ≥ 17/20.

## 7. Positive control

20 scenarios on real cron prompts. The fact is planted by **substitution** (it replaces one B1 item;
item count unchanged), and the scenario is such that the fact changes an argument of the first action.

- 10 **decisive** facts (salient, specific, e.g. a moved output directory) and 10 **typical** facts
  written in the vague register of real brief items.
- Arms: B1 with the substitution vs B1, two replicas each.
- **Hit** = the planted value appears in the first message's actions **and** the superseded value does
  not; the planted token must be absent from the input turn and from every B1-arm run.
- **Pass** iff decisive hits ≥ 7/10 with B1-arm false hits ≤ 1/10. Typical-fact hits are the
  sensitivity estimate, reported without a threshold.
- **Symmetric reading:** a failed control means the probe is insensitive, so §6 nulls are uninformative
  while §6 positives are still reported; a passed control shows the probe *can* see an effect, not that
  typical brief content would produce one. Scenarios are frozen before any run.

## 8. Threats and limits (declared)

- First assistant message only; influence that emerges after tool feedback is invisible by
  construction.
- Scaffold is today's (one captured template, current bootstrap files); the estimand is "the brief
  block under today's scaffold", not the historical runs.
- B1 is re-rendered from `brief_log` ids, verified once byte-for-byte (§4.1), not snapshotted per run.
- The observed turns happened with the brief present; the corpus is a selected stratum.
- Stratum H is synthetic; its realism rests on the catalog and on being authored blind to the briefs.

## 9. Cost, sequence, deliverables

- Runs: pilot ≈ 100; main ≈ 128 units × 6 = 768; control 20 × 2 arms × 2 = 80; ≈ 950 CLI runs on the
  subscription, spread over one to two days. Gemini: 40 H requests + ≈ 128 rubrics + ≈ 530 judgments
  (cents).
- Sequence: smoke test → manifest + H authoring + rubrics frozen → pilot → frozen parameters committed
  → main run + control → analysis exactly as §6–7 → `audits/<date>-7b-action-probe.md`.
- Code in `eval/brief-action-probe/`; raw data on the VPS only.

## 10. Review dispositions (v1 → v2)

| finding (voice) | disposition |
|---|---|
| Primary ignores the sham; presence ≠ content (Kimi A1, Grok) | Δp and Δc both primary (§6.1) |
| Retrospect leaks the D2 trajectory to the judge (both) | retrospect removed; input-only rubric (§6.2) |
| Turn-level bootstrap anti-conservative; 18 prompts (both) | strata, clusters, cluster bootstrap, cap 8 per prompt (§2, §6.1) |
| "Significant vs not significant" in the helps rule (both) | direct B1×BS contrast (§6.2) |
| Positive control: echo, guessable, no threshold, too salient (both) | substitution, baseline exclusion, threshold, typical facts (§7) |
| Divergence near 1 by construction; one-line masker; Jaccard 0.5 (both) | pilot-frozen canonicalizer, continuous d, validity ceiling (§5) |
| Temperature not fixed (both) | not settable in `claude -p`; replicas + A/A floor (§3) |
| Cron corpus biased to null; memory matters when underspecified (Kimi A4) | stratum H (§2.1), Toto's decision |
| Sham is wrong memory, not neutral; future/overlapping items (Kimi A5, Grok) | filtered BS, framed as right vs wrong memory (§3), Toto's decision |
| First action only; null used to close 7b (both) | all tool calls of the first message; scoped claims (§1, §4, §8) |
| Reconstruction not only external validity (Grok) | render fidelity and scaffold-leakage checks (§4.1) |
| Judge gate too weak (both) | TOST ±5pp + known-answer gate (§6.2) |
| No MDE for the primary; no multiplicity policy (both) | pilot MDE; Holm over four decisions (§5, §6.1) |
| Cache/clock between interleaved runs (Grok) | six runs of a unit back-to-back (§4) |
