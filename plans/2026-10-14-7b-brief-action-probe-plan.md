# 7b Brief Action Probe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run the offline replay probe that measures whether the injected nox-mem brief changes the first action of the VPS agents (presence and content effects), and whether the change is for the better.

**Architecture:** A stdlib-only Python package (`eval/brief-action-probe/probe/`) holds the pure logic (serialization, divergence, statistics, sham construction, scaffold assembly, transcript parsing, stream-json parsing, judging helpers), each unit-tested on the Mac and on the VPS. Thin scripts drive the VPS-side steps: a Node bridge renders briefs with the **production** formatter from `tools/nox-mem/dist/api/brief.js`; `claude -p` runs in an isolated `CLAUDE_CONFIG_DIR` whose `PreToolUse` hook records and denies every tool call; all session content stays under `/root/medicoes/7b/` on the VPS, and only code, frozen non-content parameters and aggregates are committed to this public repo.

**Tech Stack:** Python 3.12 (VPS) / 3.14 (Mac), stdlib only (`unittest`, `sqlite3`, `urllib`, `shlex`); Node 24 + `better-sqlite3` from the production nox-mem install; Claude Code CLI 2.1.293 on the VPS; OpenAI and Gemini REST APIs (keys in `/root/.openclaw/.env`).

**Spec:** `specs/2026-10-14-7b-brief-action-probe-design.md` (v3.1, approved by Toto 2026-10-14). Executors read the spec and this plan together; the spec's §-numbers are cited below.

## Global Constraints

- Window: 2026-09-21 00:00 UTC → 2026-10-15 00:00 UTC (spec §2).
- Stratum C: at most **8** turns per cron prompt, spread evenly; pilot C = **20** surplus instances of the five largest prompts (§2).
- Stratum H: **50** authored requests, **10** pilot, **40** main; authored by GPT from the catalog only (§2.1).
- Arms: **B0, B1, BS × 2 replicas**; pilot: **B1 × 4 replicas** (§3, §5).
- BS: candidates within **±3 days** of t, `created_at ≤ t`, Jaccard overlap with any B1 item **≤ 0.3**, rendered length within **±10%**; drop-rate flag above **20%** of a stratum (§3).
- Render-fidelity gate: **≥ 95%** exact over all git-archived served briefs in the window; archived files never edited (§4.1).
- Validity ceiling: pilot A/A mean divergence **> 0.5** ⇒ mechanical primary invalid for that stratum (§5.3).
- MDE: power **80%** at one-sided **α = 0.0125** (§5.4).
- Bootstrap: **10,000** cluster draws; one-sided p = (1 + #Δ≤0)/(1 + draws); Holm over **four** p values at **0.05** (§6.1).
- Judge gates: slot-A share TOST **α = 0.05, margin ±0.10**; known answer **≥ 17/20** (§6.2).
- Positive control: decisive hits **≥ 7/10**, false hits **≤ 1/10**, typical hits **≥ 3/10** for informative nulls (§7).
- Model under test: `claude-sonnet-5` via `claude -p`; production flags mirrored: `--output-format stream-json --verbose --setting-sources user --allowedTools mcp__openclaw__* --disallowedTools ScheduleWakeup,CronCreate,Bash(run_in_background:true),Monitor` (from `/usr/lib/node_modules/openclaw/dist/cli-backend-B4QtvgHC.js`).
- Raw inputs, outputs, manifest, rubrics, H requests and control scenarios live only under `/root/medicoes/7b/` on the VPS. Nothing with session content is committed. Research artefacts in English.
- Scaffold: `/root/medicoes/7b-scaffold/forge-2026-09-30T2231.system-prompt.md`, sha256 `7b4b0820009bc170d178e0ce8bf16af5780a9d394e90bf678b2addee0dffb75c`; abort on mismatch (§4).
- Repo rules: feature code goes through a PR with squash-merge; commits on the branch need `COMMIT_TO_NON_MAIN_OK=1`; never `sed -i` a `.db`; open the production DB read-only (`mode=ro`).

## Review Focus

1. **CLI prints no assistant message** (rate limit, auth error, crash): the run must count as a failure, never as an empty message (an empty-vs-empty pair has divergence 0 and would deflate A/A). Pinned in Task 6.
2. **Hook silently not loaded** (settings not read from the isolated dir): a tool would execute. Pinned by the smoke test (Task 7) and by a per-run cross-check that the hook log holds one entry per parsed tool call (Task 6).
3. **`brief_log` writes `agent=nox` for both `main` and `nox`** (the refresh script maps `main → agent_param=nox`): B1 for `main` must be the earlier of the pair, B1 for `nox` the later. Pinned in Task 4.
4. **Shell commands that `shlex` cannot parse** (heredocs with unbalanced quotes, `$'...'`): serialization must fall back deterministically, never raise. Pinned in Task 1.
5. **Chunks deleted since t** (compact incident of 2026-10-13): B1 cannot be reproduced; the unit must be dropped and counted, not rendered short. Pinned in Task 4.

---

## File Structure

All new files under `eval/brief-action-probe/` in memoria-nox:

| file | responsibility |
|---|---|
| `README.md` | what the probe is, where data lives, how to run each phase |
| `probe/__init__.py` | empty |
| `probe/canon.py` | §5.1–5.2 canonical serialization + normalized Levenshtein divergence |
| `probe/stats.py` | cluster bootstrap, one-sided p, CI, Holm, Fisher 2×2, binomial TOST, MDE simulation |
| `probe/sham.py` | §3 BS filter and sliding window |
| `probe/corpus.py` | transcript parsing, turn classification, template key, strata sampling |
| `probe/scaffold.py` | §4 template parsing, per-arm prompt assembly, only-brief-differs check |
| `probe/briefs.py` | read-only `brief_log` queries, main/nox pairing, Node bridge client |
| `probe/runner.py` | `claude -p` command, stream-json parsing, run with retry, hook cross-check |
| `probe/llm.py` | OpenAI and Gemini REST calls with model-identity preflight |
| `probe/judge.py` | judge prompt, A/B randomization, unit scores, known-answer corruption |
| `probe/control.py` | §7 substitution and hit detection |
| `render_brief.mjs` | Node bridge: chunk ids → `renderBriefText` output via production `dist/api/brief.js` |
| `runtime/deny_hook.py` | PreToolUse hook: log + deny |
| `runtime/stub_mcp.py` | stdio MCP server replaying captured tool names |
| `scripts/capture_surface.py` | observed `mcp__*` tool names → `surface.json` |
| `scripts/setup_config_dir.sh` | builds `/root/.claude-7b-probe` (hook + MCP config) |
| `scripts/smoke.sh` | §4 smoke test |
| `scripts/fidelity_gate.py` | §4.1 render-fidelity gate |
| `scripts/author_h.py` | §2.1 catalog + GPT authoring of 50 requests |
| `scripts/build_manifest.py` | strata, t, B1, BS, inputs, arm files, leakage flags |
| `scripts/author_rubrics.py` | §6.2 rubrics (GPT) + §2.1 relevance diagnostic (Gemini) |
| `scripts/run_phase.py` | runs pilot / main / control units, resumable |
| `scripts/freeze_params.py` | §5 pilot A/A, ceiling, MDE → `frozen/params.json` |
| `scripts/run_judge.py` | §6.2 judged pairs + known-answer pairs |
| `scripts/analyze.py` | §6–7 decisions → `out/aggregates.json` |
| `frozen/params.json` | committed after the pilot (no content) |
| `out/aggregates.json` | committed after analysis (no content) |
| `tests/test_*.py` | one test module per `probe/` module |

VPS layout (never committed): `/root/medicoes/7b/code/` (rsync of `eval/brief-action-probe/`), `/root/medicoes/7b/{inputs,arms,runs,control}/`, `manifest.jsonl`, `h_requests.jsonl`, `rubrics.jsonl`, `results-<phase>.jsonl`, `judgments.jsonl`.

Run tests from `eval/brief-action-probe/`: `python3 -m unittest discover -s tests -v`.

---

### Task 0: Branch, package skeleton, sync helper

**Files:**
- Create: `eval/brief-action-probe/README.md`, `eval/brief-action-probe/probe/__init__.py`, `eval/brief-action-probe/tests/__init__.py`, `eval/brief-action-probe/scripts/sync_to_vps.sh`

**Interfaces:**
- Produces: package import path `probe` when run from `eval/brief-action-probe/` (scripts insert their parent dir on `sys.path`); `scripts/sync_to_vps.sh` copies the package to `/root/medicoes/7b/code/`.

- [ ] **Step 1: Create the worktree and branch**

```bash
cd /Users/lab/Claude/Projetos/memoria-nox && git fetch -q origin
git worktree add ../wt-mn-7b-probe -b feat/7b-action-probe origin/main
cd ../wt-mn-7b-probe && mkdir -p eval/brief-action-probe/{probe,tests,runtime,scripts,frozen,out}
touch eval/brief-action-probe/probe/__init__.py eval/brief-action-probe/tests/__init__.py
```

- [ ] **Step 2: Write `README.md`**

```markdown
# 7b — brief action probe

Implements `specs/2026-10-14-7b-brief-action-probe-design.md` (plan: `plans/2026-10-14-7b-brief-action-probe-plan.md`).

Data never enters this repository: inputs, outputs, manifest, rubrics, authored requests and control
scenarios live on the VPS under `/root/medicoes/7b/`. Committed outputs are `frozen/params.json` and
`out/aggregates.json`, which hold no session content.

Tests: `python3 -m unittest discover -s tests -v` (stdlib only; Python ≥ 3.12).
Sync to the VPS: `scripts/sync_to_vps.sh` (needs `NOX_VPS`, e.g. `root@<host>`; the host is never written here).
```

- [ ] **Step 3: Write `scripts/sync_to_vps.sh`**

```bash
#!/usr/bin/env bash
# Copies the probe code to the VPS. Host comes from $NOX_VPS (public repo: never hard-code it).
set -euo pipefail
: "${NOX_VPS:?set NOX_VPS=root@<host>}"
here="$(cd "$(dirname "$0")/.." && pwd)"
ssh "$NOX_VPS" 'mkdir -p /root/medicoes/7b/code && chmod 700 /root/medicoes/7b'
rsync -a --delete --exclude out --exclude frozen --exclude __pycache__ "$here/" "$NOX_VPS:/root/medicoes/7b/code/"
echo "synced to $NOX_VPS:/root/medicoes/7b/code"
```

- [ ] **Step 4: Commit**

```bash
chmod +x eval/brief-action-probe/scripts/sync_to_vps.sh
git add eval/brief-action-probe
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): probe package skeleton and VPS sync helper"
```

---

### Task 1: Canonical serialization and divergence (§5.1–5.2)

**Files:**
- Create: `eval/brief-action-probe/probe/canon.py`
- Test: `eval/brief-action-probe/tests/test_canon.py`

**Interfaces:**
- Produces: `serialize(msg: dict) -> list[str]` where `msg = {"text": str, "tool_calls": [{"name": str, "input": dict}]}`; `divergence(a: list[str], b: list[str]) -> float` in [0, 1]; `CANON_VERSION: str`; `MAX_TOKENS: int`.

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from probe.canon import serialize, divergence, canon_bash, MAX_TOKENS


def msg(text="", calls=()):
    return {"text": text, "tool_calls": [{"name": n, "input": i} for n, i in calls]}


class CanonTest(unittest.TestCase):
    def test_identical_messages_have_zero_divergence(self):
        m = msg("hello", [("Bash", {"command": "ls -la /root"})])
        self.assertEqual(divergence(serialize(m), serialize(m)), 0.0)

    def test_both_empty_is_zero_and_one_empty_is_one(self):
        self.assertEqual(divergence([], []), 0.0)
        self.assertEqual(divergence(serialize(msg("x")), []), 1.0)

    def test_dates_times_uuids_hashes_and_tmp_paths_are_masked(self):
        a = msg("", [("Bash", {"command": "cat /tmp/abc.1/x 2026-10-14T23:00:05Z 12:30 0123456789abcdef 3f2a9c1e-1111-2222-3333-444455556666"})])
        b = msg("", [("Bash", {"command": "cat /tmp/zz9/y 2025-01-02 09:15 fedcba9876543210 00000000-aaaa-bbbb-cccc-dddddddddddd"})])
        self.assertEqual(serialize(a), serialize(b))

    def test_bash_option_order_is_canonical(self):
        self.assertEqual(canon_bash("grep -n -i foo file"), canon_bash("grep -i -n foo file"))
        self.assertNotEqual(canon_bash("cp a b"), canon_bash("cp b a"))

    def test_bash_description_is_ignored(self):
        a = msg("", [("Bash", {"command": "ls", "description": "list files"})])
        b = msg("", [("Bash", {"command": "ls", "description": "show me the directory"})])
        self.assertEqual(serialize(a), serialize(b))

    def test_unparseable_shell_falls_back_without_raising(self):
        out = canon_bash("cat <<'EOF'\nit's open\n")
        self.assertIsInstance(out, str)
        self.assertEqual(out, canon_bash("cat <<'EOF'\nit's open\n"))

    def test_json_arguments_are_key_order_insensitive(self):
        a = msg("", [("Read", {"file_path": "/x", "limit": 5})])
        b = msg("", [("Read", {"limit": 5, "file_path": "/x"})])
        self.assertEqual(serialize(a), serialize(b))

    def test_call_order_matters(self):
        a = msg("", [("Read", {"file_path": "/a"}), ("Read", {"file_path": "/b"})])
        b = msg("", [("Read", {"file_path": "/b"}), ("Read", {"file_path": "/a"})])
        self.assertGreater(divergence(serialize(a), serialize(b)), 0.0)

    def test_unicode_text_tokenizes(self):
        self.assertIn("ação", serialize(msg("Vou checar a ação agora")))

    def test_sequence_is_truncated(self):
        self.assertEqual(len(serialize(msg("w " * 5000))), MAX_TOKENS)

    def test_divergence_is_normalized_levenshtein(self):
        self.assertAlmostEqual(divergence(["a", "b", "c", "d"], ["a", "x", "c", "d"]), 0.25)
        self.assertEqual(divergence(["a"], ["b"]), 1.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd eval/brief-action-probe && python3 -m unittest tests.test_canon -v`
Expected: `ModuleNotFoundError: No module named 'probe.canon'`

- [ ] **Step 3: Implement `probe/canon.py`**

```python
"""Canonical serialization of a first assistant message, and divergence (spec §5.1–5.2).

Frozen by the pilot (§5): changing anything here after `frozen/params.json` exists invalidates the
main run. `freeze_params.py` records the sha256 of this file.
"""
import json
import re
import shlex

CANON_VERSION = "1"
MAX_TOKENS = 2000

# Closed mask set, applied in this order (§5.1).
MASKS = (
    (re.compile(r"/tmp/[\w.\-/]+"), "<TMP>"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<UUID>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"), "<DATE>"),
    (re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"), "<TIME>"),
    (re.compile(r"\b[0-9a-fA-F]{12,64}\b"), "<HASH>"),
)
TOKEN = re.compile(r"<[A-Z]+>|\w+|[^\w\s]")
SHELL_OPS = {"&&", "||", "|", ";", "&", "(", ")", ";;", "|&"}
# A Bash `description` is prose about the call, not an argument of the action.
BASH_DROP_KEYS = {"description"}


def mask(s: str) -> str:
    for rx, rep in MASKS:
        s = rx.sub(rep, s)
    return s


def tokens(s: str) -> list:
    return TOKEN.findall(mask(s))


def canon_bash(command: str) -> str:
    """argv with options sorted inside each simple command; raw string if unparseable."""
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        return command
    out, seg = [], []

    def flush():
        if seg:
            name, rest = seg[0], seg[1:]
            opts = sorted(t for t in rest if t.startswith("-") and len(t) > 1)
            pos = [t for t in rest if not (t.startswith("-") and len(t) > 1)]
            out.extend([name, *opts, *pos])
            seg.clear()

    for t in toks:
        if t in SHELL_OPS:
            flush()
            out.append(t)
        else:
            seg.append(t)
    flush()
    return " ".join(out)


def canon_call(name: str, inp) -> str:
    if name == "Bash" and isinstance(inp, dict) and isinstance(inp.get("command"), str):
        rest = {k: v for k, v in inp.items() if k != "command" and k not in BASH_DROP_KEYS}
        tail = (" " + json.dumps(rest, sort_keys=True, ensure_ascii=False)) if rest else ""
        return canon_bash(inp["command"]) + tail
    return json.dumps(inp, sort_keys=True, ensure_ascii=False)


def serialize(msg: dict) -> list:
    seq = []
    for call in msg.get("tool_calls") or []:
        seq += ["<CALL>", str(call.get("name"))] + tokens(canon_call(call.get("name"), call.get("input")))
    text = msg.get("text") or ""
    if text.strip():
        seq += ["<TEXT>"] + tokens(text)
    return seq[:MAX_TOKENS]


def divergence(a: list, b: list) -> float:
    """Normalized Levenshtein distance over token sequences (edit distance / longer length)."""
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1] / max(len(a), len(b))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd eval/brief-action-probe && python3 -m unittest tests.test_canon -v`
Expected: 11 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add eval/brief-action-probe/probe/canon.py eval/brief-action-probe/tests/test_canon.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): canonical serialization and normalized Levenshtein divergence"
```

---

### Task 2: Statistics (§5.4, §6.1, §6.2, §4)

**Files:**
- Create: `eval/brief-action-probe/probe/stats.py`
- Test: `eval/brief-action-probe/tests/test_stats.py`

**Interfaces:**
- Produces: `stratum_estimate(by_cluster: dict[str, list[float]]) -> float`; `cluster_bootstrap(by_cluster, n_draws=10000, seed=0) -> list[float]`; `one_sided_p(draws) -> float`; `percentile_ci(draws, level=0.95) -> tuple[float, float]`; `holm(pvals: dict[str, float]) -> dict[str, float]`; `fisher_2x2(a, b, c, d) -> float`; `tost_proportion(k, n, p0=0.5, margin=0.10, alpha=0.05) -> tuple[bool, float, float]`; `simulate_mde(pilot_units, dist, cluster_sizes, q_grid, n_sim=200, n_boot=1000, alpha=0.0125, seed=0) -> list[dict]`; `mde_from_curve(curve, power=0.8) -> float | None`.

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from probe.stats import (stratum_estimate, cluster_bootstrap, one_sided_p, percentile_ci, holm,
                         fisher_2x2, tost_proportion, simulate_mde, mde_from_curve)


class StatsTest(unittest.TestCase):
    def test_estimate_weighs_each_cluster_once(self):
        self.assertAlmostEqual(stratum_estimate({"a": [1.0, 1.0, 1.0, 1.0], "b": [0.0]}), 0.5)

    def test_bootstrap_is_seeded_and_bounded(self):
        d1 = cluster_bootstrap({"a": [0.2], "b": [0.4]}, 500, seed=7)
        self.assertEqual(d1, cluster_bootstrap({"a": [0.2], "b": [0.4]}, 500, seed=7))
        self.assertTrue(all(0.2 <= x <= 0.4 for x in d1))

    def test_one_sided_p(self):
        self.assertAlmostEqual(one_sided_p([1.0] * 99), 1 / 100)
        self.assertAlmostEqual(one_sided_p([-1.0] * 99), 1.0)

    def test_percentile_ci(self):
        lo, hi = percentile_ci([float(i) for i in range(101)])
        self.assertEqual((lo, hi), (2.0, 98.0))

    def test_holm_matches_hand_computation(self):
        adj = holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 1.0})
        self.assertAlmostEqual(adj["a"], 0.04)
        self.assertAlmostEqual(adj["c"], 0.09)
        self.assertAlmostEqual(adj["b"], 0.09)  # monotone: max(0.08, 0.09)
        self.assertAlmostEqual(adj["d"], 1.0)

    def test_fisher_two_sided_known_value(self):
        # Classic tea-tasting table [[3,1],[1,3]]: two-sided p = 0.4857
        self.assertAlmostEqual(fisher_2x2(3, 1, 1, 3), 0.4857, places=4)
        self.assertAlmostEqual(fisher_2x2(0, 10, 0, 10), 1.0)

    def test_tost(self):
        self.assertTrue(tost_proportion(250, 500)[0])
        self.assertFalse(tost_proportion(300, 500)[0])
        self.assertFalse(tost_proportion(10, 20)[0])

    def test_mde_simulation_moves_with_q(self):
        units = [[(u, r) for r in range(4)] for u in range(6)]
        dist = lambda x, y: 0.0 if x[0] == y[0] else 1.0
        curve = simulate_mde(units, dist, [3, 3, 3, 3], [0.0, 1.0], n_sim=40, n_boot=200, seed=1)
        self.assertAlmostEqual(curve[0]["mean_delta"], 0.0)
        self.assertLess(curve[0]["power"], 0.2)
        self.assertAlmostEqual(curve[1]["mean_delta"], 1.0)
        self.assertEqual(curve[1]["power"], 1.0)
        self.assertAlmostEqual(mde_from_curve(curve), 1.0)
        self.assertIsNone(mde_from_curve([{"q": 0, "mean_delta": 0.0, "power": 0.1}]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_stats -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `probe/stats.py`**

```python
"""Statistics for the 7b probe (spec §4, §5.4, §6). Stdlib only."""
import math
import random


def stratum_estimate(by_cluster):
    means = [sum(v) / len(v) for v in by_cluster.values() if v]
    return sum(means) / len(means)


def cluster_bootstrap(by_cluster, n_draws=10000, seed=0):
    """Resample clusters with replacement; each draw = mean of cluster means."""
    rng = random.Random(seed)
    means = [sum(v) / len(v) for v in by_cluster.values() if v]
    k = len(means)
    return [sum(means[rng.randrange(k)] for _ in range(k)) / k for _ in range(n_draws)]


def one_sided_p(draws):
    return (1 + sum(1 for d in draws if d <= 0)) / (1 + len(draws))


def percentile_ci(draws, level=0.95):
    s = sorted(draws)
    lo = (1 - level) / 2
    return s[int(math.floor(lo * (len(s) - 1)))], s[int(math.ceil((1 - lo) * (len(s) - 1)))]


def holm(pvals):
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def _hyper_pmf(a, r1, c1, n):
    return math.comb(c1, a) * math.comb(n - c1, r1 - a) / math.comb(n, r1)


def fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact test for [[a, b], [c, d]]."""
    r1, c1, n = a + b, a + c, a + b + c + d
    if n == 0:
        return 1.0
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    p_obs = _hyper_pmf(a, r1, c1, n)
    total = 0.0
    for x in range(lo, hi + 1):
        p = _hyper_pmf(x, r1, c1, n)
        if p <= p_obs * (1 + 1e-7):
            total += p
    return min(1.0, total)


def _binom_logpmf(k, n, p):
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log(1 - p))


def tost_proportion(k, n, p0=0.5, margin=0.10, alpha=0.05):
    """Exact binomial TOST: is the proportion k/n equivalent to p0 within ±margin?"""
    p_low = sum(math.exp(_binom_logpmf(x, n, p0 - margin)) for x in range(k, n + 1))
    p_high = sum(math.exp(_binom_logpmf(x, n, p0 + margin)) for x in range(0, k + 1))
    return (p_low < alpha and p_high < alpha), p_low, p_high


def simulate_mde(pilot_units, dist, cluster_sizes, q_grid, n_sim=200, n_boot=1000, alpha=0.0125, seed=0):
    """§5.4. pilot_units: list of replica-id lists (4 each) for one stratum; dist(i, j) -> divergence.

    Each simulated unit takes a random pilot unit as base; each arm's two replicas are drawn without
    replacement from the base's replicas. With probability q, the comparison arm's replicas come from a
    different pilot unit. Δ = D(B1, X) − mean A/A over the three arms, as in §6.1.
    """
    rng = random.Random(seed)
    curve = []
    for q in q_grid:
        deltas, hits = [], 0
        for _ in range(n_sim):
            by_cluster = {}
            for ci, size in enumerate(cluster_sizes):
                vals = []
                for _ in range(size):
                    u = rng.randrange(len(pilot_units))
                    b1 = rng.sample(pilot_units[u], 2)
                    third = rng.sample(pilot_units[u], 2)
                    if rng.random() < q:
                        v = rng.choice([x for x in range(len(pilot_units)) if x != u])
                        cmp_ = rng.sample(pilot_units[v], 2)
                    else:
                        cmp_ = rng.sample(pilot_units[u], 2)
                    aa = (dist(*b1) + dist(*cmp_) + dist(*third)) / 3
                    d = sum(dist(x, y) for x in b1 for y in cmp_) / 4
                    vals.append(d - aa)
                by_cluster[ci] = vals
            deltas.append(stratum_estimate(by_cluster))
            draws = cluster_bootstrap(by_cluster, n_boot, rng.randrange(2 ** 31))
            hits += one_sided_p(draws) < alpha
        curve.append({"q": q, "mean_delta": sum(deltas) / len(deltas), "power": hits / n_sim})
    return curve


def mde_from_curve(curve, power=0.8):
    ok = [c["mean_delta"] for c in curve if c["power"] >= power]
    return min(ok) if ok else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_stats -v` → 8 tests OK.

- [ ] **Step 5: Commit**

```bash
git add eval/brief-action-probe/probe/stats.py eval/brief-action-probe/tests/test_stats.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): cluster bootstrap, Holm, Fisher, TOST and MDE simulation"
```

---

### Task 3: Sham construction (§3)

**Files:**
- Create: `eval/brief-action-probe/probe/sham.py`
- Test: `eval/brief-action-probe/tests/test_sham.py`

**Interfaces:**
- Consumes: none.
- Produces: `item_tokens(text: str) -> set[str]`; `common_tokens(texts: list[str], share=0.05) -> set[str]`; `filter_candidates(cands, b1, t, common, max_overlap=0.3) -> list[dict]` (items are dicts `{"id": int, "created_at": "YYYY-MM-DD HH:MM:SS", "text": str}`, `text` = title + " " + one-liner); `build_sham(filtered, k, b1_len, render_len, tol=0.10) -> list[dict] | None`.

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from probe.sham import item_tokens, common_tokens, filter_candidates, build_sham


def it(i, text, created="2026-10-01 00:00:00"):
    return {"id": i, "created_at": created, "text": text}


class ShamTest(unittest.TestCase):
    T = "2026-10-05 12:00:00"

    def test_filters_future_b1_ids_overlap_and_duplicates(self):
        b1 = [it(1, "gateway restart drill procedure")]
        cands = [it(1, "same id as b1"), it(2, "future item text", "2026-10-06 00:00:00"),
                 it(3, "gateway restart drill procedure again"), it(4, "solar panel quotes"),
                 it(4, "solar panel quotes")]
        out = filter_candidates(cands, b1, self.T, set())
        self.assertEqual([c["id"] for c in out], [4])

    def test_common_tokens_are_excluded_from_overlap(self):
        texts = ["lessons something"] * 10 + ["unique words here"]
        common = common_tokens(texts, share=0.5)
        self.assertIn("lessons", common)
        b1 = [it(1, "lessons alpha")]
        out = filter_candidates([it(2, "lessons beta")], b1, self.T, common)
        self.assertEqual([c["id"] for c in out], [2])

    def test_sliding_window_accepts_first_within_tolerance(self):
        f = [it(i, "x") for i in range(5)]
        lens = {(0, 1): 50, (1, 2): 100, (2, 3): 102}
        render_len = lambda w: lens[(w[0]["id"], w[1]["id"])]
        w = build_sham(f, 2, 100, render_len)
        self.assertEqual([x["id"] for x in w], [1, 2])

    def test_exhausted_sequence_returns_none(self):
        f = [it(i, "x") for i in range(3)]
        self.assertIsNone(build_sham(f, 2, 100, lambda w: 10))
        self.assertIsNone(build_sham(f[:1], 2, 100, lambda w: 100))

    def test_item_tokens(self):
        toks = item_tokens("The CLI path: /usr/bin/bird ok")
        self.assertIn("path", toks)
        self.assertNotIn("the", toks)
        self.assertNotIn("ok", toks)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_sham -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `probe/sham.py`**

```python
"""BS (wrong-agent memory) construction, spec §3.

Overlap is Jaccard over distinctive tokens: tokens of >= 4 chars (7a definition) minus `common`, the
tokens present in >= 5% of all distinct brief items of the window (frozen in the manifest).
Repeated chunk ids in the candidate sequence are kept once (first occurrence).
"""
import re

TOK = re.compile(r"[^\w./]+")


def item_tokens(text):
    return {t for t in TOK.split(text.lower()) if len(t) >= 4}


def common_tokens(texts, share=0.05):
    df = {}
    for t in texts:
        for x in item_tokens(t):
            df[x] = df.get(x, 0) + 1
    n = max(1, len(texts))
    return {x for x, c in df.items() if c / n >= share}


def _jaccard(a, b):
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def filter_candidates(cands, b1, t, common, max_overlap=0.3):
    b1_ids = {x["id"] for x in b1}
    b1_toks = [item_tokens(x["text"]) - common for x in b1]
    out, seen = [], set()
    for c in cands:
        if c["id"] in b1_ids or c["id"] in seen or c["created_at"] > t:
            continue
        ct = item_tokens(c["text"]) - common
        if any(_jaccard(ct, bt) > max_overlap for bt in b1_toks):
            continue
        seen.add(c["id"])
        out.append(c)
    return out


def build_sham(filtered, k, b1_len, render_len, tol=0.10):
    """First window of k consecutive items whose rendered length is within ±tol of b1_len."""
    for start in range(0, len(filtered) - k + 1):
        window = filtered[start:start + k]
        if abs(render_len(window) - b1_len) <= tol * b1_len:
            return window
    return None
```

- [ ] **Step 4: Run tests** — `python3 -m unittest tests.test_sham -v` → 5 tests OK.

- [ ] **Step 5: Commit**

```bash
git add eval/brief-action-probe/probe/sham.py eval/brief-action-probe/tests/test_sham.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): BS filter and sliding-window construction"
```

---

### Task 4: Brief access, production render bridge, render-fidelity gate (§3 B1, §4.1)

**Files:**
- Create: `eval/brief-action-probe/probe/briefs.py`, `eval/brief-action-probe/render_brief.mjs`, `eval/brief-action-probe/scripts/fidelity_gate.py`
- Test: `eval/brief-action-probe/tests/test_briefs.py`

**Interfaces:**
- Produces: `db_agent(agent: str) -> str`; `brief_at(con, agent, t) -> dict | None` (`{"brief_id", "served_at"}`); `brief_by_generated_at(con, agent, gen_iso) -> str | None`; `brief_items(con, brief_id) -> list[int]`; `candidate_briefs(con, owner, t, seed, per_agent=20) -> list[str]`; `chunk_meta(con, ids) -> dict[int, dict]`; class `Bridge` with `render(chunk_ids, now_ms, agent, scope="global") -> dict` (`{"text", "items": [{"id","title","one_liner"}], "missing": [int]}`) and `close()`; `AUTO_HEADER: str`; `brief_block(render_text) -> str`; `iso_to_db(ts) -> "YYYY-MM-DD HH:MM:SS"`; `db_to_ms(s) -> int`.

- [ ] **Step 1: Write the failing tests (in-memory DB fixture, no VPS needed)**

```python
import sqlite3
import unittest
from probe.briefs import db_agent, brief_at, brief_by_generated_at, brief_items, candidate_briefs, iso_to_db


def fixture():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE brief_log (id INTEGER PRIMARY KEY, chunk_id INTEGER, scope TEXT, agent TEXT, served_at TEXT, brief_id TEXT)")
    rows = [
        # cycle 1 at 10:07 — refresh order: main (agent=nox), nox, boris
        ("nox", "2026-10-01 10:07:01", "m1", [1, 2]), ("nox", "2026-10-01 10:07:01", "n1", [3, 4]),
        ("boris", "2026-10-01 10:07:02", "b1", [5]),
        # cycle 2 at 10:22
        ("nox", "2026-10-01 10:22:01", "m2", [6]), ("nox", "2026-10-01 10:22:02", "n2", [7]),
        ("boris", "2026-10-01 10:22:02", "b2", [8]), ("forge", "2026-10-03 10:22:02", "f1", [9]),
    ]
    for agent, ts, bid, ids in rows:
        for cid in ids:
            con.execute("INSERT INTO brief_log (chunk_id, scope, agent, served_at, brief_id) VALUES (?,?,?,?,?)",
                        (cid, "global", agent, ts, bid))
    return con


class BriefsTest(unittest.TestCase):
    def test_main_maps_to_nox(self):
        self.assertEqual(db_agent("main"), "nox")
        self.assertEqual(db_agent("boris"), "boris")

    def test_main_gets_earlier_and_nox_later_of_the_pair(self):
        con = fixture()
        self.assertEqual(brief_at(con, "main", "2026-10-01 10:15:00")["brief_id"], "m1")
        self.assertEqual(brief_at(con, "nox", "2026-10-01 10:15:00")["brief_id"], "n1")
        self.assertEqual(brief_at(con, "boris", "2026-10-01 10:30:00")["brief_id"], "b2")
        self.assertIsNone(brief_at(con, "boris", "2026-10-01 09:00:00"))

    def test_items_keep_served_order(self):
        self.assertEqual(brief_items(fixture(), "m1"), [1, 2])

    def test_generated_at_lookup_pairs_main_and_nox(self):
        con = fixture()
        self.assertEqual(brief_by_generated_at(con, "main", "2026-10-01T10:22:01.400Z"), "m2")
        self.assertEqual(brief_by_generated_at(con, "nox", "2026-10-01T10:22:01.900Z"), "n2")

    def test_candidates_exclude_owner_and_respect_window(self):
        con = fixture()
        c = candidate_briefs(con, "boris", "2026-10-01 10:30:00", seed=1)
        self.assertNotIn("b1", c)
        self.assertNotIn("b2", c)
        self.assertIn("m2", c)
        self.assertIn("f1", c)  # 2 days later, inside ±3 d
        self.assertEqual(c, candidate_briefs(con, "boris", "2026-10-01 10:30:00", seed=1))

    def test_iso_to_db(self):
        self.assertEqual(iso_to_db("2026-10-01T10:22:01.400Z"), "2026-10-01 10:22:01")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_briefs -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `probe/briefs.py`**

```python
"""Read-only brief_log access and the production render bridge (spec §3, §4.1).

brief_log quirk: the refresh script requests the `main` brief with agent=nox, immediately before the
`nox` brief, so both are logged as agent='nox'. Within a refresh cycle the earlier brief_id (lower row
id) is main's and the later is nox's.
"""
import json
import os
import random
import subprocess
from datetime import datetime, timezone

NOX_MEM_DIR = os.environ.get("NOX_MEM_DIR", "/root/.openclaw/workspace/tools/nox-mem")
DB_PATH = os.environ.get("NOX_MEM_DB", f"{NOX_MEM_DIR}/nox-mem.db")
BRIDGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "render_brief.mjs")
AUTO_HEADER = (
    "<!-- AUTO-GERADO por nox-mem-brief-refresh.sh (cron */15) — NÃO EDITAR.\n"
    "     Session Priming Loop F3 — brief por salience do nox-mem.\n"
    "     Detalhe de qualquer item: nox_mem_search por id/título. -->\n\n"
)
PAIR_SECONDS = 60


def connect():
    import sqlite3
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def db_agent(agent):
    return "nox" if agent == "main" else agent


def iso_to_db(ts):
    return ts[:19].replace("T", " ")


def db_to_ms(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _secs(s):
    return db_to_ms(s) // 1000


def _briefs(con, agent, where, args, limit):
    return con.execute(
        "SELECT brief_id, MIN(id) AS r, MIN(served_at) AS s FROM brief_log "
        f"WHERE agent = ? AND brief_id IS NOT NULL AND {where} GROUP BY brief_id ORDER BY r DESC LIMIT ?",
        (db_agent(agent), *args, limit)).fetchall()


def _pick(agent, rows):
    """rows: newest first. For main/nox, split a same-cycle pair by row order."""
    if not rows:
        return None
    if agent in ("main", "nox") and len(rows) >= 2 and _secs(rows[0][2]) - _secs(rows[1][2]) <= PAIR_SECONDS:
        later, earlier = rows[0], rows[1]
        chosen = earlier if agent == "main" else later
    else:
        chosen = rows[0]
    return {"brief_id": chosen[0], "served_at": chosen[2]}


def brief_at(con, agent, t):
    return _pick(agent, _briefs(con, agent, "served_at < ?", (t,), 2))


def brief_by_generated_at(con, agent, gen_iso):
    s = _secs(iso_to_db(gen_iso))
    lo = datetime.fromtimestamp(s - 2, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    hi = datetime.fromtimestamp(s + 2, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = con.execute(
        "SELECT brief_id, MIN(id) AS r, MIN(served_at) AS s FROM brief_log WHERE agent = ? AND brief_id IS NOT NULL "
        "GROUP BY brief_id HAVING MIN(served_at) BETWEEN ? AND ? ORDER BY r", (db_agent(agent), lo, hi)).fetchall()
    if not rows:
        return None
    if agent in ("main", "nox") and len(rows) >= 2:
        return rows[0][0] if agent == "main" else rows[1][0]
    return rows[0][0]


def brief_items(con, brief_id):
    return [r[0] for r in con.execute("SELECT chunk_id FROM brief_log WHERE brief_id = ? ORDER BY id", (brief_id,))]


def candidate_briefs(con, owner, t, seed, per_agent=20):
    """§3 step 1: other agents in seeded order; for each, brief_ids within ±3 days of t, nearest first."""
    agents = sorted(r[0] for r in con.execute(
        "SELECT DISTINCT agent FROM brief_log WHERE agent IS NOT NULL AND agent != ?", (db_agent(owner),)))
    random.Random(seed).shuffle(agents)
    out = []
    for a in agents:
        rows = con.execute(
            "SELECT brief_id, MIN(served_at) AS s FROM brief_log WHERE agent = ? AND brief_id IS NOT NULL "
            "GROUP BY brief_id HAVING ABS(julianday(MIN(served_at)) - julianday(?)) <= 3 "
            "ORDER BY ABS(julianday(MIN(served_at)) - julianday(?)), MIN(id) LIMIT ?",
            (a, t, t, per_agent)).fetchall()
        out += [r[0] for r in rows]
    return out


def chunk_meta(con, ids):
    out = {}
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        q = f"SELECT id, created_at FROM chunks WHERE id IN ({','.join('?' * len(part))})"
        for cid, created in con.execute(q, part):
            out[cid] = {"id": cid, "created_at": created}
    return out


def brief_block(render_text):
    return AUTO_HEADER + render_text


class Bridge:
    """Long-lived `node render_brief.mjs` process; one JSON request per line."""

    def __init__(self):
        env = {**os.environ, "NOX_MEM_DIR": NOX_MEM_DIR, "NOX_MEM_DB": DB_PATH}
        self.p = subprocess.Popen(["node", BRIDGE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, env=env, bufsize=1)

    def render(self, chunk_ids, now_ms, agent, scope="global"):
        self.p.stdin.write(json.dumps({"chunk_ids": list(chunk_ids), "now_ms": now_ms,
                                       "agent": agent, "scope": scope}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("render bridge exited")
        return json.loads(line)

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)
```

- [ ] **Step 4: Run tests** — `python3 -m unittest tests.test_briefs -v` → 6 tests OK.

- [ ] **Step 5: Write `render_brief.mjs`**

```javascript
#!/usr/bin/env node
// Renders a brief from chunk ids with the PRODUCTION formatter (spec §3, §4.1).
// toItems() is not exported by src/api/brief.ts; the mapping below mirrors it, and the §4.1 gate
// (scripts/fidelity_gate.py) is what proves the mirror reproduces served briefs byte for byte.
import { createRequire } from "node:module";
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";

const dir = process.env.NOX_MEM_DIR;
if (!dir) { console.error("NOX_MEM_DIR is required"); process.exit(2); }
const require = createRequire(`${dir}/package.json`);
const Database = require("better-sqlite3");
const brief = await import(pathToFileURL(`${dir}/dist/api/brief.js`).href);
const db = new Database(process.env.NOX_MEM_DB ?? `${dir}/nox-mem.db`, { readonly: true, fileMustExist: true });
const get = db.prepare(
  "SELECT id, source_file, chunk_text, chunk_type, pain, source_date, created_at, updated_at FROM chunks WHERE id = ?",
);

for await (const line of createInterface({ input: process.stdin })) {
  if (!line.trim()) continue;
  const req = JSON.parse(line);
  const items = [];
  const missing = [];
  for (const id of req.chunk_ids) {
    const row = get.get(id);
    if (!row) { missing.push(id); continue; }
    const ref = row.source_date ?? row.created_at ?? row.updated_at;
    const refMs = ref ? brief.parseDbDateMs(ref) : NaN;
    items.push({
      id: row.id,
      title: brief.titleFromSourceFile(row.source_file),
      one_liner: brief.extractOneLiner(row.chunk_text),
      type: row.chunk_type,
      pain: row.pain ?? 0.2,
      salience: 0,
      age_days: Number.isFinite(refMs) ? Math.max(0, Math.floor((req.now_ms - refMs) / 86_400_000)) : 0,
    });
  }
  const result = {
    scope: req.scope ?? "global",
    ...(req.agent ? { agent: req.agent } : {}),
    generated_at: new Date(req.now_ms).toISOString(),
    items,
    token_estimate: 0,
  };
  process.stdout.write(JSON.stringify({
    text: brief.renderBriefText(result),
    items: items.map((i) => ({ id: i.id, title: i.title, one_liner: i.one_liner })),
    missing,
  }) + "\n");
}
```

- [ ] **Step 6: Write `scripts/fidelity_gate.py`**

```python
#!/usr/bin/env python3
"""§4.1 render-fidelity gate. Re-renders every git-archived served brief in the window and compares the
item lines byte for byte (header lines excluded). Read-only on git and on the DB. Exit 1 below 95%."""
import json
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.briefs import Bridge, brief_by_generated_at, brief_items, connect  # noqa: E402

WS = "/root/.openclaw/workspace"
SINCE, UNTIL = "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z"
FILES = {"main": "brief/MEMORY.md", **{a: f"agents/{a}/brief/MEMORY.md"
                                      for a in ("nox", "atlas", "boris", "cipher", "forge", "lex")}}
HDR = re.compile(r"^# nox-mem brief — scope=(\S+)(?: agent=(\S+))? — (\S+) — \d+ items$")
OUT = "/root/medicoes/7b/fidelity.json"


def git(*args):
    return subprocess.run(["git", "-C", WS, *args], capture_output=True, text=True, check=True).stdout


def main():
    con, bridge = connect(), Bridge()
    seen, res = set(), {"total": 0, "exact": 0, "no_brief_id": 0, "missing_chunks": 0, "mismatch": []}
    for persona, rel in FILES.items():
        for sha in git("log", f"--since={SINCE}", f"--until={UNTIL}", "--format=%H", "--", rel).split():
            content = git("show", f"{sha}:{rel}")
            lines = content.split("\n")
            hi = next((i for i, l in enumerate(lines) if HDR.match(l)), None)
            if hi is None:
                continue
            scope, agent, gen = HDR.match(lines[hi]).groups()
            if (persona, gen) in seen:
                continue
            seen.add((persona, gen))
            res["total"] += 1
            served = [l for l in lines[hi + 1:] if l.strip()]
            bid = brief_by_generated_at(con, persona, gen)
            if bid is None:
                res["no_brief_id"] += 1
                continue
            now_ms = int(datetime.fromisoformat(gen.replace("Z", "+00:00")).timestamp() * 1000)
            out = bridge.render(brief_items(con, bid), now_ms, agent, scope)
            if out["missing"]:
                res["missing_chunks"] += 1
                continue
            rendered = [l for l in out["text"].split("\n")[1:] if l.strip()]
            if rendered == served:
                res["exact"] += 1
            else:
                res["mismatch"].append({"persona": persona, "commit": sha[:10], "brief_id": bid,
                                        "first_diff": next(i for i, (a, b) in enumerate(
                                            zip(rendered + [""], served + [""])) if a != b)})
    bridge.close()
    res["rate"] = res["exact"] / res["total"] if res["total"] else 0.0
    res["pass"] = res["rate"] >= 0.95
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "mismatch"}), f"mismatches={len(res['mismatch'])}")
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Sync and run the gate on the VPS**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'cd /root/medicoes/7b/code && python3 -m unittest discover -s tests && python3 scripts/fidelity_gate.py'
```
Expected: tests OK on Python 3.12; gate prints `"pass": true` with `rate ≥ 0.95` and exits 0. If it exits 1: inspect `/root/medicoes/7b/fidelity.json` mismatches (first differing line index), fix the mirror in `render_brief.mjs` only if the cause is the mirror; if the cause is data (missing chunks, changed text), report the rate to Toto — the spec says the probe stops below the gate. Never edit archived files.

- [ ] **Step 8: Commit**

```bash
git add eval/brief-action-probe/probe/briefs.py eval/brief-action-probe/render_brief.mjs \
        eval/brief-action-probe/scripts/fidelity_gate.py eval/brief-action-probe/tests/test_briefs.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): brief_log access, production render bridge, render-fidelity gate"
```

---

### Task 5: Corpus extraction and scaffold assembly (§2, §4)

**Files:**
- Create: `eval/brief-action-probe/probe/corpus.py`, `eval/brief-action-probe/probe/scaffold.py`
- Test: `eval/brief-action-probe/tests/test_corpus.py`, `eval/brief-action-probe/tests/test_scaffold.py`

**Interfaces:**
- Produces (corpus): `classify(text) -> str` in {heartbeat, task-notification, auto, inter-agent, human, other}; `template_key(agent, text) -> str`; `load_turns(projects_dir, start_iso, end_iso) -> list[dict]` (`{"unit_id","agent","ts","text","kind","template","session"}`); `evenly(n, k) -> list[int]`; `build_strata(turns, cap=8, n_pilot=20, big=5, seed=0) -> {"C": [...], "R": [...], "pilot_C": [...]}`.
- Produces (scaffold): `parse_template(text) -> dict`; `build_prompt(tpl, agent, files: dict, brief_block: str | None, date: str, keep_conversation: bool) -> str`; `strip_brief(text, agent) -> str`; `assert_only_brief_differs(texts: dict[str, str], agent) -> None` (raises `AssertionError`); `agent_root(agent) -> str`; `read_bootstrap(agent) -> dict`.

- [ ] **Step 1: Write the failing corpus tests**

```python
import json
import os
import tempfile
import unittest
from probe.corpus import classify, template_key, load_turns, evenly, build_strata


def line(ts, content, typ="user", uuid=None):
    return json.dumps({"type": typ, "timestamp": ts, "uuid": uuid, "message": {"content": content}})


class CorpusTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("Read HEARTBEAT.md"), "heartbeat")
        self.assertEqual(classify("<task-notification> x"), "task-notification")
        self.assertEqual(classify("[cron:abc relatorio-eod] do it"), "auto")
        self.assertEqual(classify("[Inter-session message] sourceSession=..."), "inter-agent")
        self.assertEqual(classify('Conversation info: {"conversation_label":"#x"}'), "human")
        self.assertEqual(classify("plain"), "other")

    def test_template_key_ignores_dates_and_retry_prefix(self):
        a = template_key("main", "[Wed 2026-10-14 09:00 GMT-3] [cron:1 eod] run 2026-10-14 report 12345")
        b = template_key("main", "[Thu 2026-10-15 09:00 GMT-3] [Retry after the previous model attempt failed or timed out] [cron:1 eod] run 2026-10-15 report 99999")
        self.assertEqual(a, b)

    def test_load_turns_skips_tool_results_and_dedupes_retries(self):
        d = tempfile.mkdtemp()
        sub = os.path.join(d, "-root--openclaw-workspace-agents-boris")
        os.makedirs(sub)
        with open(os.path.join(sub, "s1.jsonl"), "w") as f:
            f.write(line("2026-10-01T10:00:00Z", "[cron:x digest] go", uuid="u1") + "\n")
            f.write(line("2026-10-01T10:00:05Z", [{"type": "tool_result", "content": "ok"}], uuid="u2") + "\n")
            f.write(line("2026-10-01T10:01:00Z", "[Retry after the previous model attempt failed or timed out] [cron:x digest] go", uuid="u3") + "\n")
            f.write(line("2026-10-01T10:02:00Z", [{"type": "text", "text": "Read HEARTBEAT.md"}], uuid="u4") + "\n")
            f.write("not json\n")
            f.write(line("2026-08-01T10:00:00Z", "[cron:old] out of window", uuid="u5") + "\n")
        turns = load_turns(d, "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z")
        self.assertEqual([(t["unit_id"], t["agent"], t["kind"]) for t in turns],
                         [("u1", "boris", "auto"), ("u4", "boris", "heartbeat")])

    def test_evenly(self):
        self.assertEqual(evenly(3, 8), [0, 1, 2])
        self.assertEqual(evenly(24, 8), [0, 3, 7, 10, 13, 16, 20, 23])

    def test_build_strata_caps_and_pilot_uses_surplus(self):
        turns = [{"unit_id": f"a{i}", "agent": "main", "ts": f"2026-10-{i + 1:02d}T00:00:00Z", "kind": "auto",
                  "template": "main|A", "text": "x"} for i in range(24)]
        turns += [{"unit_id": "h1", "agent": "forge", "ts": "2026-10-02T00:00:00Z", "kind": "human",
                   "template": "forge|H", "text": "y"}]
        s = build_strata(turns, cap=8, n_pilot=4, big=1, seed=3)
        self.assertEqual(len(s["C"]), 8)
        self.assertEqual([t["unit_id"] for t in s["R"]], ["h1"])
        self.assertEqual(len(s["pilot_C"]), 4)
        self.assertFalse({t["unit_id"] for t in s["pilot_C"]} & {t["unit_id"] for t in s["C"]})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Write the failing scaffold tests**

```python
import unittest
from probe.scaffold import parse_template, build_prompt, strip_brief, assert_only_brief_differs

TPL = "\n".join([
    "## Tooling", "x", "## Workspace", "Working directory: /root/.openclaw/workspace/agents/forge",
    "# Project Context",
    "## /root/.openclaw/workspace/agents/forge/AGENTS.md", "agents body", "## Rules",
    "## /root/.openclaw/workspace/agents/forge/brief/MEMORY.md", "old brief",
    "## /root/.openclaw/workspace/agents/forge/MEMORY.md", "memory body",
    "## Temporal Context", "Current date: 2026-09-30", "## Conversation Context", "discord stuff",
    "## Runtime", "Runtime: agent=forge | session=agent:forge:discord:channel:1 | sessionId=abc",
    "Current model identity: claude-cli/claude-sonnet-5.",
])


class ScaffoldTest(unittest.TestCase):
    def test_parse(self):
        t = parse_template(TPL)
        self.assertEqual([p.rsplit("/", 1)[-1] for p, _ in t["sections"]], ["AGENTS.md", "MEMORY.md", "MEMORY.md"])
        self.assertEqual(t["tail"][0], "## Temporal Context")

    def test_build_for_other_agent_and_date(self):
        t = parse_template(TPL)
        out = build_prompt(t, "boris", {"AGENTS.md": "B agents", "MEMORY.md": "B mem"}, "BRIEF", "2026-10-02", False)
        self.assertIn("Working directory: /root/.openclaw/workspace/agents/boris", out)
        self.assertIn("## /root/.openclaw/workspace/agents/boris/brief/MEMORY.md\nBRIEF", out)
        self.assertIn("Current date: 2026-10-02", out)
        self.assertNotIn("discord stuff", out)
        self.assertIn("Runtime: agent=boris | host=openclaw", out)
        self.assertNotIn("old brief", out)

    def test_main_uses_workspace_root(self):
        out = build_prompt(parse_template(TPL), "main", {"AGENTS.md": "M"}, None, "2026-10-02", False)
        self.assertIn("## /root/.openclaw/workspace/AGENTS.md\nM", out)
        self.assertNotIn("brief/MEMORY.md", out)

    def test_only_brief_differs(self):
        t = parse_template(TPL)
        files = {"AGENTS.md": "A", "MEMORY.md": "M"}
        arms = {a: build_prompt(t, "boris", files, b, "2026-10-02", False)
                for a, b in (("B0", None), ("B1", "real"), ("BS", "sham"))}
        assert_only_brief_differs(arms, "boris")
        arms["BS"] = arms["BS"].replace("M\n", "M changed\n")
        with self.assertRaises(AssertionError):
            assert_only_brief_differs(arms, "boris")

    def test_strip_brief_removes_only_that_section(self):
        out = build_prompt(parse_template(TPL), "boris", {"AGENTS.md": "A", "MEMORY.md": "M"}, "real", "2026-10-02", False)
        s = strip_brief(out, "boris")
        self.assertNotIn("real", s)
        self.assertIn("## /root/.openclaw/workspace/agents/boris/MEMORY.md\nM", s)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run both to verify failure** — `python3 -m unittest tests.test_corpus tests.test_scaffold -v` → `ModuleNotFoundError`.

- [ ] **Step 4: Implement `probe/corpus.py`**

```python
"""Transcript parsing and strata (spec §2). Transcripts: Claude CLI jsonl under
/root/.claude-nuvini-team/projects/-root--openclaw-workspace[-agents-<a>]/."""
import glob
import json
import os
import random
import re

HEARTBEAT = re.compile(r"HEARTBEAT|heartbeat")
AUTO = re.compile(r"\[cron|cron:|scheduled|BOOT\.md|Subagent Context", re.I)
HUMAN = re.compile(r"conversation_label|sender|whatsapp|discord|slack|webchat", re.I)
RETRY = "[Retry after the previous model attempt failed"
DIR_RE = re.compile(r"-root--openclaw-workspace(?:-agents-(\w+))?$")


def classify(text):
    head = text[:600]
    if HEARTBEAT.search(head):
        return "heartbeat"
    if "<task-notification>" in text[:100]:
        return "task-notification"
    if AUTO.search(head):
        return "auto"
    if "Inter-session message" in head:
        return "inter-agent"
    if HUMAN.search(head):
        return "human"
    return "other"


def _normalize(text):
    s = re.sub(r"\[(Mon|Tue|Wed|Thu|Fri|Sat|Sun) [^\]]*\]", "", text)
    s = re.sub(r"\[Retry after[^\]]*\]", "", s)
    s = re.sub(r"\d{4}-\d{2}-\d{2}[T ]?[\d:.]*Z?|\b\d{1,2}:\d{2}\b|[0-9a-f]{8}-[0-9a-f-]{27}|\b\d{3,}\b", "#", s)
    return re.sub(r"\s+", " ", s).strip()


def template_key(agent, text):
    return f"{agent}|{_normalize(text)[:120]}"


def _user_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in content):
            return None
        return " ".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
    return None


def load_turns(projects_dir, start_iso, end_iso):
    turns = []
    for d in sorted(glob.glob(os.path.join(projects_dir, "-root--openclaw-workspace*"))):
        m = DIR_RE.search(os.path.basename(d))
        if not m:
            continue
        agent = m.group(1) or "main"
        for path in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            last_key = None
            with open(path, errors="replace") as f:
                for n, raw in enumerate(f):
                    try:
                        o = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if o.get("type") != "user":
                        continue
                    ts = o.get("timestamp") or ""
                    if not (start_iso <= ts < end_iso):
                        continue
                    text = _user_text((o.get("message") or {}).get("content"))
                    if not text or not text.strip():
                        continue
                    key = template_key(agent, text)
                    if RETRY in text and key == last_key:
                        continue
                    last_key = key
                    turns.append({"unit_id": o.get("uuid") or f"{os.path.basename(path)}:{n}", "agent": agent,
                                  "ts": ts, "text": text, "kind": classify(text), "template": key,
                                  "session": os.path.basename(path)})
    return sorted(turns, key=lambda t: (t["ts"], t["unit_id"]))


def evenly(n, k):
    if n <= k:
        return list(range(n))
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def build_strata(turns, cap=8, n_pilot=20, big=5, seed=0):
    human = [t for t in turns if t["kind"] == "human"]
    rest = [t for t in turns if t["kind"] in ("auto", "inter-agent", "other")]
    by_tpl = {}
    for t in sorted(rest, key=lambda x: (x["ts"], x["unit_id"])):
        by_tpl.setdefault(t["template"], []).append(t)
    main_c, surplus = [], {}
    for tpl, ts in sorted(by_tpl.items()):
        idx = set(evenly(len(ts), cap))
        main_c += [x for i, x in enumerate(ts) if i in idx]
        surplus[tpl] = [x for i, x in enumerate(ts) if i not in idx]
    big_tpls = sorted(by_tpl, key=lambda k: (-len(by_tpl[k]), k))[:big]
    rng, pilot = random.Random(seed), []
    per = n_pilot // max(1, len(big_tpls))
    for tpl in big_tpls:
        pilot += rng.sample(surplus[tpl], min(per, len(surplus[tpl])))
    return {"C": main_c, "R": human, "pilot_C": pilot}
```

- [ ] **Step 5: Implement `probe/scaffold.py`**

```python
"""Per-arm system prompt assembly from the captured OpenClaw template (spec §4).

Rules (frozen; declared limits in spec §8): file sections are rebuilt in template order for the owner
agent; the brief section is the only arm-dependent part; in the generated tail, `Current date` is set to
the date of t, `Conversation Context` is kept only for stratum R (forge Discord, as captured), and the
`Runtime:` line is reduced to `agent=<owner> | host=openclaw` (session ids are per-run noise).
"""
import os
import re

WS = "/root/.openclaw/workspace"
FILE_HDR = re.compile(r"^## (/root/\.openclaw/workspace/\S+\.md)$")
TAIL_HDR = "## Temporal Context"
ORDER = ["AGENTS.md", "SOUL.md", "IDENTITY.md", "USER.md", "brief/MEMORY.md", "MEMORY.md"]
BOOTSTRAP = [n for n in ORDER if n != "brief/MEMORY.md"]


def agent_root(agent):
    return WS if agent == "main" else f"{WS}/agents/{agent}"


def parse_template(text):
    if text.count("\n" + TAIL_HDR + "\n") != 1:
        raise ValueError("template must contain exactly one tail header")
    head, sections, tail, cur, in_tail = [], [], [], None, False
    for ln in text.split("\n"):
        if in_tail:
            tail.append(ln)
            continue
        if ln == TAIL_HDR:
            in_tail = True
            tail.append(ln)
            continue
        m = FILE_HDR.match(ln)
        if m:
            cur = [m.group(1), []]
            sections.append(cur)
            continue
        (cur[1] if cur else head).append(ln)
    return {"head": head, "sections": [(p, "\n".join(c)) for p, c in sections], "tail": tail}


def _tail(lines, agent, date, keep_conversation):
    out, skip = [], False
    for ln in lines:
        if ln.startswith("## "):
            skip = ln == "## Conversation Context" and not keep_conversation
        if skip:
            continue
        if ln.startswith("Current date: "):
            ln = f"Current date: {date}"
        elif ln.startswith("Runtime: "):
            ln = f"Runtime: agent={agent} | host=openclaw"
        out.append(ln)
    return out


def build_prompt(tpl, agent, files, brief_block, date, keep_conversation):
    root = agent_root(agent)
    out = [f"Working directory: {root}" if l.startswith("Working directory: ") else l for l in tpl["head"]]
    for name in ORDER:
        if name == "brief/MEMORY.md":
            if brief_block is None:
                continue
            content = brief_block
        elif name in files:
            content = files[name]
        else:
            continue
        out += [f"## {root}/{name}", content.rstrip("\n")]
    out += _tail(tpl["tail"], agent, date, keep_conversation)
    return "\n".join(out)


def strip_brief(text, agent):
    root = agent_root(agent)
    out, skip = [], False
    for ln in text.split("\n"):
        if ln == f"## {root}/brief/MEMORY.md":
            skip = True
            continue
        if skip and (ln.startswith(f"## {root}/") or ln == TAIL_HDR):
            skip = False
        if not skip:
            out.append(ln)
    return "\n".join(out)


def assert_only_brief_differs(texts, agent):
    stripped = {arm: strip_brief(t, agent) for arm, t in texts.items()}
    first = next(iter(stripped.values()))
    for arm, s in stripped.items():
        assert s == first, f"arm {arm} differs outside the brief block"


def read_bootstrap(agent):
    root, files = agent_root(agent), {}
    for name in BOOTSTRAP:
        p = os.path.join(root, name)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                files[name] = f.read()
    return files
```

- [ ] **Step 6: Run tests** — `python3 -m unittest tests.test_corpus tests.test_scaffold -v` → 10 tests OK.

- [ ] **Step 7: Check the scaffold against the real capture on the VPS**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'cd /root/medicoes/7b/code && python3 - <<EOF
import hashlib, sys
sys.path.insert(0, ".")
from probe.scaffold import parse_template, build_prompt
p = "/root/medicoes/7b-scaffold/forge-2026-09-30T2231.system-prompt.md"
raw = open(p, encoding="utf-8").read()
assert hashlib.sha256(raw.encode()).hexdigest() == "7b4b0820009bc170d178e0ce8bf16af5780a9d394e90bf678b2addee0dffb75c"
t = parse_template(raw)
files = {s[0].split("/agents/forge/", 1)[1]: s[1] for s in t["sections"]}
brief = files.pop("brief/MEMORY.md")
out = build_prompt(t, "forge", files, brief, "2026-09-30", True)
diff = [(a, b) for a, b in zip(raw.split("\n"), out.split("\n")) if a != b]
print("sections", [s[0].rsplit("/", 2)[-2:] for s in t["sections"]], "lines_differ", len(diff), "len", len(raw.split("\n")), len(out.split("\n")))
for a, b in diff: print("-", a[:120]); print("+", b[:120])
EOF'
```
Expected: six sections (AGENTS, SOUL, IDENTITY, USER, brief/MEMORY, MEMORY), equal line counts, and exactly **one** differing line: the `Runtime:` line. Any other difference is a parser bug; fix before continuing.

- [ ] **Step 8: Commit**

```bash
git add eval/brief-action-probe/probe/corpus.py eval/brief-action-probe/probe/scaffold.py \
        eval/brief-action-probe/tests/test_corpus.py eval/brief-action-probe/tests/test_scaffold.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): transcript strata and per-arm scaffold assembly"
```

---

### Task 6: Runner — command, stream-json parsing, retry, hook cross-check (§4)

**Files:**
- Create: `eval/brief-action-probe/probe/runner.py`
- Test: `eval/brief-action-probe/tests/test_runner.py`

**Interfaces:**
- Consumes: none from earlier tasks.
- Produces: `PROBE_CONFIG_DIR = "/root/.claude-7b-probe"`; `MCP_CONFIG = "/root/.claude-7b-probe/mcp-config.json"`; `build_cmd(arm_file, model="claude-sonnet-5") -> list[str]`; `parse_first_message(stdout: str) -> dict | None` (`{"message_id","text","tool_calls"}`); `is_rate_limited(stdout, stderr) -> bool`; `run_arm(arm_file, input_text, cwd, run_dir, timeout=900) -> dict` (`{"ok", "returncode", "message", "hook_calls", "hook_mismatch", "rate_limited"}`); `run_unit(unit_id, arm_files: dict[str,str], input_text, cwd, run_root, reps, rng) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

```python
import json
import unittest
from probe.runner import build_cmd, parse_first_message, is_rate_limited, hook_mismatch


def ev(mid, blocks, typ="assistant"):
    return json.dumps({"type": typ, "message": {"id": mid, "content": blocks}})


class RunnerTest(unittest.TestCase):
    def test_cmd_mirrors_production_flags(self):
        c = build_cmd("/x/B1.md")
        for flag in ("-p", "--output-format", "stream-json", "--verbose", "--setting-sources", "user",
                     "--allowedTools", "mcp__openclaw__*", "--disallowedTools",
                     "ScheduleWakeup,CronCreate,Bash(run_in_background:true),Monitor",
                     "--append-system-prompt-file", "/x/B1.md", "--max-turns", "1", "--strict-mcp-config"):
            self.assertIn(flag, c)
        self.assertEqual(c[c.index("--model") + 1], "claude-sonnet-5")

    def test_parse_merges_blocks_of_first_message_only(self):
        out = "\n".join([
            json.dumps({"type": "system", "subtype": "init"}),
            ev("m1", [{"type": "thinking", "thinking": "hmm"}]),
            ev("m1", [{"type": "text", "text": "Vou olhar."}]),
            ev("m1", [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]),
            ev("m1", [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]),
            ev("m2", [{"type": "text", "text": "second message"}]),
        ])
        m = parse_first_message(out)
        self.assertEqual(m["text"], "Vou olhar.")
        self.assertEqual(m["tool_calls"], [{"name": "Bash", "input": {"command": "ls"}}])

    def test_no_assistant_message_is_none_not_empty(self):
        self.assertIsNone(parse_first_message(json.dumps({"type": "result", "is_error": True})))
        self.assertIsNone(parse_first_message(""))

    def test_rate_limit_detection(self):
        self.assertTrue(is_rate_limited("", "Claude AI usage limit reached|1760000000"))
        self.assertTrue(is_rate_limited('{"type":"result","result":"API Error: 429 rate_limit_error"}', ""))
        self.assertFalse(is_rate_limited("ok", ""))

    def test_hook_cross_check(self):
        msg = {"tool_calls": [{"name": "Bash", "input": {}}, {"name": "Read", "input": {}}]}
        self.assertFalse(hook_mismatch(msg, ["Bash", "Read"]))
        self.assertTrue(hook_mismatch(msg, ["Bash"]))
        self.assertTrue(hook_mismatch({"tool_calls": []}, ["Bash"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_runner -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `probe/runner.py`**

```python
"""`claude -p` execution for the probe (spec §4). Every tool call is denied by the PreToolUse hook in
PROBE_CONFIG_DIR; this module only parses the first assistant message and checks the hook saw it."""
import json
import os
import subprocess
import time

PROBE_CONFIG_DIR = "/root/.claude-7b-probe"
MCP_CONFIG = f"{PROBE_CONFIG_DIR}/mcp-config.json"
PROD_ARGS = ["-p", "--output-format", "stream-json", "--verbose", "--setting-sources", "user",
             "--allowedTools", "mcp__openclaw__*",
             "--disallowedTools", "ScheduleWakeup,CronCreate,Bash(run_in_background:true),Monitor"]
RATE_MARKERS = ("usage limit", "rate_limit", "rate limit", " 429")
RATE_PAUSE_S = 1800


def build_cmd(arm_file, model="claude-sonnet-5"):
    return ["claude", *PROD_ARGS, "--model", model, "--append-system-prompt-file", arm_file,
            "--mcp-config", MCP_CONFIG, "--strict-mcp-config", "--max-turns", "1"]


def parse_first_message(stdout):
    first, text, calls, seen = None, [], [], set()
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "assistant":
            continue
        msg = ev.get("message") or {}
        mid = msg.get("id")
        if first is None:
            first = mid
        if mid != first:
            break
        for b in msg.get("content") or []:
            key = (b.get("type"), b.get("id") or b.get("text"))
            if key in seen:
                continue
            seen.add(key)
            if b.get("type") == "text":
                text.append(b.get("text", ""))
            elif b.get("type") == "tool_use":
                calls.append({"name": b.get("name"), "input": b.get("input")})
    if first is None:
        return None
    return {"message_id": first, "text": "\n".join(text), "tool_calls": calls}


def is_rate_limited(stdout, stderr):
    blob = (stdout[-4000:] + stderr[-4000:]).lower()
    return any(m in blob for m in RATE_MARKERS)


def hook_mismatch(message, hook_names):
    return [c["name"] for c in message.get("tool_calls", [])] != list(hook_names)


def _read_hook(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l)["tool_name"] for l in f if l.strip()]


def run_arm(arm_file, input_text, cwd, run_dir, timeout=900):
    os.makedirs(run_dir, exist_ok=True)
    hook_log = os.path.join(run_dir, "hook.jsonl")
    if os.path.exists(hook_log):
        os.remove(hook_log)
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
    env.update(CLAUDE_CONFIG_DIR=PROBE_CONFIG_DIR, PROBE_HOOK_LOG=hook_log)
    try:
        p = subprocess.run(build_cmd(arm_file), input=input_text, capture_output=True, text=True,
                           cwd=cwd, env=env, timeout=timeout)
        out, err, rc = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = (e.stdout or ""), (e.stderr or "") + "\nTIMEOUT", -1
        out = out.decode() if isinstance(out, bytes) else out
        err = err.decode() if isinstance(err, bytes) else err
    with open(os.path.join(run_dir, "stdout.jsonl"), "w") as f:
        f.write(out)
    with open(os.path.join(run_dir, "stderr.txt"), "w") as f:
        f.write(err)
    msg = parse_first_message(out)
    hooks = _read_hook(hook_log)
    mismatch = msg is not None and hook_mismatch(msg, hooks)
    return {"ok": msg is not None and not mismatch, "returncode": rc, "message": msg, "hook_calls": hooks,
            "hook_mismatch": mismatch, "rate_limited": msg is None and is_rate_limited(out, err)}


def run_unit(unit_id, arm_files, input_text, cwd, run_root, reps, rng):
    """All runs of a unit back-to-back in random order (§4); one retry per failed run."""
    plan = [(arm, r) for arm in sorted(arm_files) for r in range(1, reps + 1)]
    rng.shuffle(plan)
    results = []
    for arm, r in plan:
        run_dir = os.path.join(run_root, unit_id, f"{arm}-r{r}")
        attempt, res = 0, None
        while True:
            res = run_arm(arm_files[arm], input_text, cwd, run_dir)
            if res["rate_limited"]:
                time.sleep(RATE_PAUSE_S)
                continue
            if res["ok"] or attempt == 1:
                break
            attempt += 1
        results.append({"unit_id": unit_id, "arm": arm, "rep": r, "attempts": attempt + 1,
                        "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **res})
    return results
```

- [ ] **Step 4: Run tests** — `python3 -m unittest tests.test_runner -v` → 5 tests OK.

- [ ] **Step 5: Commit**

```bash
git add eval/brief-action-probe/probe/runner.py eval/brief-action-probe/tests/test_runner.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): claude -p runner with stream-json parsing, retry and hook cross-check"
```

---

### Task 7: Isolated runtime — deny hook, stub MCP, config dir, smoke test (§4)

**Files:**
- Create: `eval/brief-action-probe/runtime/deny_hook.py`, `eval/brief-action-probe/runtime/stub_mcp.py`, `eval/brief-action-probe/scripts/capture_surface.py`, `eval/brief-action-probe/scripts/setup_config_dir.sh`, `eval/brief-action-probe/scripts/smoke.sh`
- Test: `eval/brief-action-probe/tests/test_runtime.py`

**Interfaces:**
- Consumes: `probe.runner.PROBE_CONFIG_DIR`, `MCP_CONFIG`, `parse_first_message`.
- Produces: `/root/.claude-7b-probe/{settings.json, mcp-config.json, surface.json}`; `/root/medicoes/7b/config-dir.sha256` (sha256 of settings.json + mcp-config.json + surface.json, concatenated in that order).

- [ ] **Step 1: Write the failing tests**

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RuntimeTest(unittest.TestCase):
    def test_deny_hook_logs_and_denies(self):
        log = os.path.join(tempfile.mkdtemp(), "hook.jsonl")
        ev = {"tool_name": "Bash", "tool_input": {"command": "touch /tmp/should-not-exist"}}
        p = subprocess.run([sys.executable, os.path.join(HERE, "runtime", "deny_hook.py")], input=json.dumps(ev),
                           capture_output=True, text=True, env={**os.environ, "PROBE_HOOK_LOG": log})
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(json.loads(open(log).read())["tool_name"], "Bash")

    def test_deny_hook_denies_even_on_garbage_input(self):
        p = subprocess.run([sys.executable, os.path.join(HERE, "runtime", "deny_hook.py")], input="not json",
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)

    def test_stub_mcp_lists_and_refuses(self):
        d = tempfile.mkdtemp()
        surface = os.path.join(d, "surface.json")
        json.dump({"openclaw": [{"name": "session_status", "description": "stub",
                                 "inputSchema": {"type": "object"}}]}, open(surface, "w"))
        reqs = "\n".join(json.dumps(r) for r in [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "session_status"}},
        ]) + "\n"
        p = subprocess.run([sys.executable, os.path.join(HERE, "runtime", "stub_mcp.py"), surface, "openclaw"],
                           input=reqs, capture_output=True, text=True, timeout=10)
        lines = [json.loads(l) for l in p.stdout.splitlines()]
        self.assertEqual([l["id"] for l in lines], [1, 2, 3])
        self.assertEqual(lines[1]["result"]["tools"][0]["name"], "session_status")
        self.assertTrue(lines[2]["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_runtime -v` → file-not-found failures.

- [ ] **Step 3: Implement `runtime/deny_hook.py`**

```python
#!/usr/bin/env python3
"""PreToolUse hook for the 7b probe: record the call, deny it. Nothing the agent asks for executes.
Exit 2 (block) when the event cannot be parsed, so a malformed event never lets a tool through."""
import json
import os
import sys
import time

try:
    ev = json.load(sys.stdin)
except Exception:
    print("7b probe: unparseable hook event; blocking", file=sys.stderr)
    sys.exit(2)
log = os.environ.get("PROBE_HOOK_LOG")
if log:
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "tool_name": ev.get("tool_name"),
                            "tool_input": ev.get("tool_input")}, ensure_ascii=False) + "\n")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                         "permissionDecisionReason": "7b probe: tools are not executed"}}))
```

- [ ] **Step 4: Implement `runtime/stub_mcp.py`**

```python
#!/usr/bin/env python3
"""Stdio MCP server that replays a captured tool list for one server name and refuses every call.
Usage: stub_mcp.py <surface.json> <server-name>. Tool schemas are permissive stubs (spec §8 limit)."""
import json
import sys

surface, server = sys.argv[1], sys.argv[2]
with open(surface) as f:
    TOOLS = json.load(f)[server]


def send(o):
    sys.stdout.write(json.dumps(o) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    if not line.strip():
        continue
    msg = json.loads(line)
    mid, method = msg.get("id"), msg.get("method")
    if mid is None:
        continue
    if method == "initialize":
        pv = (msg.get("params") or {}).get("protocolVersion", "2025-06-18")
        send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": pv, "capabilities": {"tools": {}},
                                                       "serverInfo": {"name": server, "version": "7b-stub"}}})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
    elif method == "tools/call":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": "7b probe stub: not executed"}], "isError": True}})
    else:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})
```

- [ ] **Step 5: Run tests** — `python3 -m unittest tests.test_runtime -v` → 3 tests OK.

- [ ] **Step 6: Implement `scripts/capture_surface.py`**

```python
#!/usr/bin/env python3
"""Tool surface for the stub MCP servers: every `mcp__<server>__<tool>` name the agents called between
2026-08-15 and 2026-10-15. Names only; schemas are permissive stubs, identical in every arm (spec §8)."""
import glob
import json
import sys

PROJ = "/root/.claude-nuvini-team/projects"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/root/.claude-7b-probe/surface.json"
names = set()
for path in glob.glob(f"{PROJ}/-root--openclaw-workspace*/*.jsonl"):
    with open(path, errors="replace") as f:
        for raw in f:
            if '"tool_use"' not in raw or "mcp__" not in raw:
                continue
            try:
                o = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not ("2026-08-15" <= (o.get("timestamp") or "") < "2026-10-15"):
                continue
            for b in (o.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and str(b.get("name", "")).startswith("mcp__"):
                    names.add(b["name"])
surface = {}
for n in sorted(names):
    _, server, tool = n.split("__", 2)
    surface.setdefault(server, []).append({"name": tool, "description": f"{server} tool {tool}",
                                           "inputSchema": {"type": "object", "additionalProperties": True}})
with open(OUT, "w") as f:
    json.dump(surface, f, indent=1, sort_keys=True)
print(json.dumps({s: len(t) for s, t in surface.items()}))
```

- [ ] **Step 7: Implement `scripts/setup_config_dir.sh`**

```bash
#!/usr/bin/env bash
# Builds the isolated CLAUDE_CONFIG_DIR for the probe (spec §4). Run on the VPS after the login step.
set -euo pipefail
D=/root/.claude-7b-probe
CODE=/root/medicoes/7b/code
test -f "$D/.credentials.json" || { echo "not logged in: run the login step first"; exit 1; }
python3 "$CODE/scripts/capture_surface.py" "$D/surface.json"
cat > "$D/settings.json" <<JSON
{"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command",
  "command": "python3 $CODE/runtime/deny_hook.py"}]}]}}
JSON
python3 - "$D" "$CODE" <<'PY'
import json, sys
d, code = sys.argv[1], sys.argv[2]
servers = json.load(open(f"{d}/surface.json"))
cfg = {"mcpServers": {s: {"command": "python3", "args": [f"{code}/runtime/stub_mcp.py", f"{d}/surface.json", s]}
                      for s in servers}}
json.dump(cfg, open(f"{d}/mcp-config.json", "w"), indent=1, sort_keys=True)
PY
cat "$D/settings.json" "$D/mcp-config.json" "$D/surface.json" | sha256sum | cut -d' ' -f1 > /root/medicoes/7b/config-dir.sha256
python3 - <<'PY'
import json
a = json.load(open("/root/.claude-7b-probe/.claude.json")).get("oauthAccount", {})
b = json.load(open("/root/.claude-nuvini-team/.claude.json")).get("oauthAccount", {})
same = a.get("accountUuid") == b.get("accountUuid")
print("probe account differs from agents' account:", not same)
raise SystemExit(1 if same or not a else 0)
PY
echo "config dir ready: $(cat /root/medicoes/7b/config-dir.sha256)"
```

- [ ] **Step 8: Implement `scripts/smoke.sh`**

```bash
#!/usr/bin/env bash
# §4 smoke test: the hook records the call and nothing runs. Must pass before any unit runs.
set -euo pipefail
CODE=/root/medicoes/7b/code
RUN=/root/medicoes/7b/runs/smoke/$(date -u +%Y%m%dT%H%M%SZ)
TRACE=/root/medicoes/7b/smoke-trace-$$
mkdir -p "$RUN"
printf 'You are a test agent.\n' > "$RUN/arm.md"
cd "$CODE"
python3 - "$RUN" "$TRACE" <<'PY'
import json, os, sys
sys.path.insert(0, ".")
from probe.runner import run_arm
run_dir, trace = sys.argv[1], sys.argv[2]
res = run_arm(f"{run_dir}/arm.md", f"Use the Bash tool to run exactly: touch {trace}", "/root/medicoes/7b", run_dir)
calls = (res["message"] or {}).get("tool_calls", [])
ok = (res["ok"] and any(c["name"] == "Bash" and trace in json.dumps(c["input"]) for c in calls)
      and res["hook_calls"] == ["Bash"] and not os.path.exists(trace))
print(json.dumps({"ok": ok, "calls": calls, "hook_calls": res["hook_calls"], "trace_exists": os.path.exists(trace)}))
raise SystemExit(0 if ok else 1)
PY
```

- [ ] **Step 9: Login (Toto's action) — STOP and ask**

The probe needs its own Claude login on the VPS, on an account other than the agents' (`claude-nuvini-team`). Ask Toto which account to use, then ask him to run in his terminal:

```
! ssh -t root@100.92.12.18 'mkdir -p /root/.claude-7b-probe && chmod 700 /root/.claude-7b-probe && CLAUDE_CONFIG_DIR=/root/.claude-7b-probe claude'
```
and complete `/login` there, then `/exit`.

- [ ] **Step 10: Build the config dir and run the smoke test**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'bash /root/medicoes/7b/code/scripts/setup_config_dir.sh && bash /root/medicoes/7b/code/scripts/smoke.sh'
```
Expected: `probe account differs from agents' account: True`, then `{"ok": true, ... "hook_calls": ["Bash"], "trace_exists": false}`. If `trace_exists` is true, a tool executed: stop everything, delete the trace, and report to Toto.

- [ ] **Step 11: Commit**

```bash
git add eval/brief-action-probe/runtime eval/brief-action-probe/scripts/capture_surface.py \
        eval/brief-action-probe/scripts/setup_config_dir.sh eval/brief-action-probe/scripts/smoke.sh \
        eval/brief-action-probe/tests/test_runtime.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): deny-all hook, stub MCP surface, isolated config dir and smoke test"
```

---

### Task 8: LLM clients and H authoring (§2.1)

**Files:**
- Create: `eval/brief-action-probe/probe/llm.py`, `eval/brief-action-probe/scripts/author_h.py`
- Test: `eval/brief-action-probe/tests/test_llm.py`

**Interfaces:**
- Produces: `openai_json(prompt, model=OPENAI_MODEL) -> dict`; `gemini_json(prompt, model=GEMINI_MODEL) -> dict`; `extract_json(text) -> dict | list`; `preflight() -> dict` (asserts returned model identities); `OPENAI_MODEL = "gpt-5.6-sol"`, `GEMINI_MODEL = "gemini-2.5-pro"`; file `/root/medicoes/7b/h_requests.jsonl` (50 lines: `{"h_id","request","owner_agent","source_task","implicit_argument","set": "pilot"|"main"}`).

- [ ] **Step 1: Write the failing tests (no network)**

```python
import unittest
from probe.llm import extract_json, build_catalog_guard


class LlmTest(unittest.TestCase):
    def test_extract_json_from_fenced_or_bare(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('text before [1, 2] after'), [1, 2])
        with self.assertRaises(ValueError):
            extract_json("no json here")

    def test_catalog_guard_rejects_brief_content(self):
        build_catalog_guard("cron prompt about the digest")
        for bad in ("item (chk 12345)", "# nox-mem brief — scope=global", "AUTO-GERADO por nox-mem-brief-refresh"):
            with self.assertRaises(AssertionError):
                build_catalog_guard(bad)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_llm -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `probe/llm.py`**

```python
"""OpenAI (authoring, rubrics) and Gemini (judge, relevance) REST clients, stdlib only.
Keys come from the environment (source /root/.openclaw/.env). The preflight records which model the
provider actually served: a provider can answer with a different model than requested."""
import json
import os
import re
import urllib.request

OPENAI_MODEL = "gpt-5.6-sol"
GEMINI_MODEL = "gemini-2.5-pro"
BRIEF_MARKERS = re.compile(r"\(chk \d+\)|# nox-mem brief|AUTO-GERADO por nox-mem-brief-refresh")


def _post(url, payload, headers, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def extract_json(text):
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    body = m.group(1) if m else text
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = body.find(opener), body.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(body[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON object in model output")


def openai_raw(prompt, model=OPENAI_MODEL):
    return _post("https://api.openai.com/v1/chat/completions",
                 {"model": model, "messages": [{"role": "user", "content": prompt}]},
                 {"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})


def gemini_raw(prompt, model=GEMINI_MODEL):
    return _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                 {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}},
                 {"x-goog-api-key": os.environ["GEMINI_API_KEY"]})


def openai_json(prompt, model=OPENAI_MODEL):
    r = openai_raw(prompt, model)
    return extract_json(r["choices"][0]["message"]["content"])


def gemini_json(prompt, model=GEMINI_MODEL):
    r = gemini_raw(prompt, model)
    return extract_json("".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"]))


def preflight():
    o = openai_raw('Reply with the JSON {"ok": true}')
    g = gemini_raw('Reply with the JSON {"ok": true}')
    served = {"openai": o.get("model"), "gemini": g.get("modelVersion")}
    assert str(served["openai"]).startswith(OPENAI_MODEL), served
    assert str(served["gemini"]).startswith(GEMINI_MODEL), served
    return served


def build_catalog_guard(text):
    assert not BRIEF_MARKERS.search(text), "catalog must not contain brief content (spec §2.1)"
```

- [ ] **Step 4: Run tests** — `python3 -m unittest tests.test_llm -v` → 2 tests OK.

- [ ] **Step 5: Implement `scripts/author_h.py`**

```python
#!/usr/bin/env python3
"""§2.1: build the task catalog (no brief content) and have GPT author 50 underspecified requests.
Writes /root/medicoes/7b/h_requests.jsonl and refuses to overwrite it (frozen once written)."""
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.corpus import build_strata, load_turns  # noqa: E402
from probe.llm import build_catalog_guard, openai_json, preflight  # noqa: E402
from probe.scaffold import agent_root  # noqa: E402

OUT = "/root/medicoes/7b/h_requests.jsonl"
AGENTS = ("main", "nox", "boris", "forge", "cipher", "atlas", "lex")
SEED = 20261014
PROMPT = """You are writing test requests for a team of AI agents. Below is a catalog of the tasks they do
(scheduled prompts, real human messages, and each agent's role). Write exactly 50 requests that a person
on this team would plausibly send to one of these agents. Each request must leave ONE argument implicit,
the way people do when they assume shared context (e.g. "redo the digest like last time but skip the long
threads" leaves implicit which digest and where it goes). Spread requests across agents in proportion to
the catalog. Return a JSON array of 50 objects with keys: request (Portuguese, as the team writes),
owner_agent (one of {agents}), source_task (short label of the catalog entry it derives from),
implicit_argument (what was left unstated).

CATALOG:
{catalog}
"""


def soul_role(agent):
    p = os.path.join(agent_root(agent), "SOUL.md")
    return "\n".join(open(p, encoding="utf-8").read().split("\n")[:60]) if os.path.isfile(p) else ""


def main():
    if os.path.exists(OUT):
        sys.exit(f"{OUT} exists: H requests are frozen")
    turns = load_turns("/root/.claude-nuvini-team/projects", "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z")
    strata = build_strata(turns)
    reps = {}
    for t in strata["C"]:
        reps.setdefault(t["template"], t)
    parts = [f"[scheduled prompt — {t['agent']}]\n{t['text'][:1500]}" for t in reps.values()]
    parts += [f"[human message — {t['agent']}]\n{t['text'][:1500]}" for t in strata["R"]]
    parts += [f"[role — {a}]\n{soul_role(a)}" for a in AGENTS if soul_role(a)]
    catalog = "\n\n---\n\n".join(parts)
    build_catalog_guard(catalog)
    served = preflight()
    reqs = openai_json(PROMPT.format(agents=", ".join(AGENTS), catalog=catalog))
    assert isinstance(reqs, list) and len(reqs) == 50, f"expected 50 requests, got {len(reqs)}"
    assert all(r.get("owner_agent") in AGENTS and r.get("request") for r in reqs)
    ids = list(range(50))
    random.Random(SEED).shuffle(ids)
    pilot = set(ids[:10])
    with open(OUT, "w", encoding="utf-8") as f:
        for i, r in enumerate(reqs):
            f.write(json.dumps({"h_id": f"H{i:02d}", **{k: r[k] for k in
                    ("request", "owner_agent", "source_task", "implicit_argument")},
                    "set": "pilot" if i in pilot else "main"}, ensure_ascii=False) + "\n")
    sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print(json.dumps({"served": served, "n": 50, "sha256": sha, "catalog_sha256": hashlib.sha256(catalog.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run on the VPS**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'set -a; . /root/.openclaw/.env; set +a; cd /root/medicoes/7b/code && python3 scripts/author_h.py'
```
Expected: one JSON line with `served.openai` starting `gpt-5.6-sol`, `served.gemini` starting `gemini-2.5-pro`, `n: 50`, and a sha256. If the preflight assertion fails, report the served model to Toto before choosing another (spec names the families, not exact ids). Record both sha256 values for Task 9.

- [ ] **Step 7: Commit**

```bash
git add eval/brief-action-probe/probe/llm.py eval/brief-action-probe/scripts/author_h.py eval/brief-action-probe/tests/test_llm.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): LLM clients with model preflight and blind H authoring"
```

---

### Task 9: Manifest, arm files, rubrics, relevance diagnostic (§2–§4, §6.2)

**Files:**
- Create: `eval/brief-action-probe/scripts/build_manifest.py`, `eval/brief-action-probe/scripts/author_rubrics.py`

**Interfaces:**
- Consumes: `probe.corpus.{load_turns, build_strata}`, `probe.briefs.{connect, brief_at, brief_items, candidate_briefs, chunk_meta, Bridge, brief_block, db_to_ms, iso_to_db}`, `probe.sham.{common_tokens, filter_candidates, build_sham}`, `probe.scaffold.{parse_template, build_prompt, read_bootstrap, assert_only_brief_differs, agent_root}`, `probe.llm.{openai_json, gemini_json}`.
- Produces: `/root/medicoes/7b/manifest.jsonl` — one line per unit: `{"unit_id","stratum": "C"|"R"|"H"|"pilot_C"|"pilot_H","cluster","agent","t","input_sha256","b1_brief_id","b1_ids","bs_ids","leak_flag","arm_sha256": {...}}`; `/root/medicoes/7b/inputs/<unit_id>.txt`; `/root/medicoes/7b/arms/<unit_id>/{B0,B1,BS}.md` (pilot units: `B1.md` only); `/root/medicoes/7b/manifest-summary.json` (counts, drops by reason, BS drop rate per stratum, common-token count); `/root/medicoes/7b/rubrics.jsonl` (`{"unit_id","must":[],"must_not":[],"required_args":[],"external_facts":[]}`); `/root/medicoes/7b/relevance.jsonl` (`{"unit_id","present": bool,"item_id": int|null}`).

- [ ] **Step 1: Implement `scripts/build_manifest.py`**

```python
#!/usr/bin/env python3
"""Freeze units, B1, BS and arm files (spec §2, §3, §4, §4.1 leakage). Refuses to overwrite."""
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.briefs import (Bridge, brief_at, brief_block, brief_items, candidate_briefs, chunk_meta,  # noqa: E402
                          connect, db_agent, db_to_ms, iso_to_db)
from probe.corpus import build_strata, load_turns  # noqa: E402
from probe.scaffold import assert_only_brief_differs, build_prompt, parse_template, read_bootstrap  # noqa: E402
from probe.sham import build_sham, common_tokens, filter_candidates, item_tokens  # noqa: E402

ROOT = "/root/medicoes/7b"
SCAFFOLD = "/root/medicoes/7b-scaffold/forge-2026-09-30T2231.system-prompt.md"
SCAFFOLD_SHA = "7b4b0820009bc170d178e0ce8bf16af5780a9d394e90bf678b2addee0dffb75c"
START, END = "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z"
SEED = 20261014
LEAK = 0.5


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def stable_seed(unit_id):
    # Python's hash() of str changes per process (PYTHONHASHSEED); seeds must be reproducible.
    return int(sha(f"{SEED}:{unit_id}")[:8], 16)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def draw_t(rng, con, agent):
    lo = datetime(2026, 9, 21, tzinfo=timezone.utc).timestamp()
    hi = datetime(2026, 10, 15, tzinfo=timezone.utc).timestamp()
    for redraw in range(100):
        t = datetime.fromtimestamp(rng.uniform(lo, hi), timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if brief_at(con, agent, t):
            return t, redraw
    raise RuntimeError(f"no brief for {agent} in window")


def main():
    if os.path.exists(f"{ROOT}/manifest.jsonl"):
        sys.exit("manifest exists: frozen")
    raw = open(SCAFFOLD, encoding="utf-8").read()
    assert sha(raw) == SCAFFOLD_SHA, "scaffold hash mismatch"
    tpl = parse_template(raw)
    con, bridge, rng = connect(), Bridge(), random.Random(SEED)
    turns = load_turns("/root/.claude-nuvini-team/projects", START, END)
    strata = build_strata(turns, seed=SEED)
    units = [dict(u, stratum=s, cluster=(u["unit_id"] if s == "R" else u["template"]),
                  t=iso_to_db(u["ts"]), input=u["text"]) for s in ("C", "R", "pilot_C") for u in strata[s]]
    redraws = 0
    for h in (json.loads(l) for l in open(f"{ROOT}/h_requests.jsonl", encoding="utf-8")):
        t, r = draw_t(rng, con, h["owner_agent"])
        redraws += r
        units.append({"unit_id": h["h_id"], "stratum": "H" if h["set"] == "main" else "pilot_H",
                      "cluster": h["source_task"], "agent": h["owner_agent"], "t": t, "input": h["request"]})
    # Frozen common-token set: tokens in >= 5% of distinct brief items in the window.
    all_ids = [r[0] for r in con.execute(
        "SELECT DISTINCT chunk_id FROM brief_log WHERE served_at BETWEEN ? AND ?", (iso_to_db(START), iso_to_db(END)))]
    texts = {}
    for i in range(0, len(all_ids), 200):
        out = bridge.render(all_ids[i:i + 200], db_to_ms("2026-10-15 00:00:00"), None)
        texts.update({x["id"]: f"{x['title']} {x['one_liner']}" for x in out["items"]})
    common = common_tokens(list(texts.values()))
    boot = {a: read_bootstrap(a) for a in {u["agent"] for u in units}}
    drops, bs_drops, kept = {}, {}, []
    for u in units:
        b = brief_at(con, u["agent"], u["t"])
        if b is None:
            drops["no_b1"] = drops.get("no_b1", 0) + 1
            continue
        now = db_to_ms(b["served_at"])
        b1_ids = brief_items(con, b["brief_id"])
        b1 = bridge.render(b1_ids, now, db_agent(u["agent"]))
        if b1["missing"]:
            drops["b1_missing_chunks"] = drops.get("b1_missing_chunks", 0) + 1
            continue
        arms = {"B1": brief_block(b1["text"])}
        bs_ids = None
        if not u["stratum"].startswith("pilot"):
            meta = chunk_meta(con, b1_ids)
            b1_items = [{"id": x["id"], "created_at": meta[x["id"]]["created_at"],
                         "text": f"{x['title']} {x['one_liner']}"} for x in b1["items"]]
            seq = []
            for bid in candidate_briefs(con, u["agent"], u["t"], seed=stable_seed(u["unit_id"])):
                ids = brief_items(con, bid)
                cm = chunk_meta(con, ids)
                r = bridge.render([i for i in ids if i in cm], now, None)
                seq += [{"id": x["id"], "created_at": cm[x["id"]]["created_at"],
                         "text": f"{x['title']} {x['one_liner']}"} for x in r["items"]]
            filt = filter_candidates(seq, b1_items, u["t"], common)
            b1_len = len(arms["B1"])
            render_len = lambda w: len(brief_block(bridge.render([x["id"] for x in w], now, db_agent(u["agent"]))["text"]))
            win = build_sham(filt, len(b1_items), b1_len, render_len)
            if win is None:
                bs_drops[u["stratum"]] = bs_drops.get(u["stratum"], 0) + 1
                continue
            bs_ids = [x["id"] for x in win]
            arms["BS"] = brief_block(bridge.render(bs_ids, now, db_agent(u["agent"]))["text"])
            arms["B0"] = None
        files = boot[u["agent"]]
        texts_by_arm = {a: build_prompt(tpl, u["agent"], files, blk, u["t"][:10], u["stratum"] == "R")
                        for a, blk in arms.items()}
        assert_only_brief_differs(texts_by_arm, u["agent"])
        boot_toks = item_tokens(" ".join(files.values())) - common
        leak = any(len((item_tokens(f"{x['title']} {x['one_liner']}") - common) & boot_toks)
                   / max(1, len(item_tokens(f"{x['title']} {x['one_liner']}") - common)) > LEAK for x in b1["items"])
        for a, text in texts_by_arm.items():
            write(f"{ROOT}/arms/{u['unit_id']}/{a}.md", text)
        write(f"{ROOT}/inputs/{u['unit_id']}.txt", u["input"])
        kept.append({"unit_id": u["unit_id"], "stratum": u["stratum"], "cluster": u["cluster"], "agent": u["agent"],
                     "t": u["t"], "input_sha256": sha(u["input"]), "b1_brief_id": b["brief_id"], "b1_ids": b1_ids,
                     "bs_ids": bs_ids, "leak_flag": leak,
                     "arm_sha256": {a: sha(x) for a, x in texts_by_arm.items()}})
    bridge.close()
    with open(f"{ROOT}/manifest.jsonl", "w") as f:
        for k in kept:
            f.write(json.dumps(k) + "\n")
    by = {}
    for k in kept:
        by[k["stratum"]] = by.get(k["stratum"], 0) + 1
    summary = {"units": by, "drops": drops, "bs_drops": bs_drops, "h_redraws": redraws,
               "bs_drop_rate": {s: bs_drops.get(s, 0) / (by.get(s, 0) + bs_drops.get(s, 0))
                                for s in ("C", "R", "H") if by.get(s, 0) + bs_drops.get(s, 0)},
               "common_tokens": len(common), "manifest_sha256": hashlib.sha256(open(f"{ROOT}/manifest.jsonl", "rb").read()).hexdigest()}
    json.dump(summary, open(f"{ROOT}/manifest-summary.json", "w"), indent=1)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run on the VPS and check the counts**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'cd /root/medicoes/7b/code && python3 scripts/build_manifest.py'
```
Expected: `units` ≈ `{"C": 71, "R": 13, "pilot_C": 20, "H": 40, "pilot_H": 10}` minus drops; every drop appears under `drops` or `bs_drops`; `bs_drop_rate` printed per stratum (a value above 0.20 is flagged in the report, not a stop). If C differs from 71 by more than drops, the corpus census changed: report it to Toto before going on.

- [ ] **Step 3: Implement `scripts/author_rubrics.py`**

```python
#!/usr/bin/env python3
"""§6.2 rubrics (GPT, from the input alone) and §2.1 relevance diagnostic (Gemini). Refuses to overwrite."""
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.briefs import Bridge, connect, db_agent, db_to_ms, brief_items  # noqa: E402
from probe.llm import gemini_json, openai_json  # noqa: E402

ROOT = "/root/medicoes/7b"
RUBRIC = """An AI agent ({agent}) receives the input below as its next turn. Without guessing hidden
context, state what a correct FIRST action must do and must not do, which tool arguments are required,
and any external fact stated in the input itself. Return JSON with keys: must (list of strings),
must_not (list), required_args (list of argument names), external_facts (list, only facts present in the
input). INPUT:
{input}"""
RELEVANCE = """A request leaves one argument implicit: "{arg}". Below are memory items the agent had.
Is the implicit argument present in any item? Return JSON {{"present": true|false, "item_id": <id or null>}}.
REQUEST: {request}
ITEMS:
{items}"""


def main():
    for p in ("rubrics.jsonl", "relevance.jsonl"):
        if os.path.exists(f"{ROOT}/{p}"):
            sys.exit(f"{p} exists: frozen")
    units = [json.loads(l) for l in open(f"{ROOT}/manifest.jsonl")]
    with open(f"{ROOT}/rubrics.jsonl", "w", encoding="utf-8") as f:
        for u in units:
            text = open(f"{ROOT}/inputs/{u['unit_id']}.txt", encoding="utf-8").read()
            r = openai_json(RUBRIC.format(agent=u["agent"], input=text[:6000]))
            f.write(json.dumps({"unit_id": u["unit_id"], **{k: r.get(k, []) for k in
                    ("must", "must_not", "required_args", "external_facts")}}, ensure_ascii=False) + "\n")
    hreq = {h["h_id"]: h for h in (json.loads(l) for l in open(f"{ROOT}/h_requests.jsonl", encoding="utf-8"))}
    con, bridge = connect(), Bridge()
    with open(f"{ROOT}/relevance.jsonl", "w", encoding="utf-8") as f:
        for u in units:
            if u["stratum"] != "H":
                continue
            b1 = bridge.render(brief_items(con, u["b1_brief_id"]), db_to_ms(u["t"]), db_agent(u["agent"]))
            items = "\n".join(f"[{x['id']}] {x['title']} — {x['one_liner']}" for x in b1["items"])
            h = hreq[u["unit_id"]]
            r = gemini_json(RELEVANCE.format(arg=h["implicit_argument"], request=h["request"], items=items))
            f.write(json.dumps({"unit_id": u["unit_id"], "present": bool(r.get("present")),
                                "item_id": r.get("item_id")}) + "\n")
    bridge.close()
    print("rubrics and relevance written")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run on the VPS**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'set -a; . /root/.openclaw/.env; set +a; cd /root/medicoes/7b/code && python3 scripts/author_rubrics.py && wc -l /root/medicoes/7b/rubrics.jsonl /root/medicoes/7b/relevance.jsonl'
```
Expected: one rubric per manifest unit; 40 relevance lines (main H only).

- [ ] **Step 5: Commit**

```bash
git add eval/brief-action-probe/scripts/build_manifest.py eval/brief-action-probe/scripts/author_rubrics.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): manifest with B1/BS/arm files, rubrics and relevance diagnostic"
```

---

### Task 10: Positive-control scenarios (§7) — frozen before any run

**Files:**
- Create: `eval/brief-action-probe/probe/control.py`
- Test: `eval/brief-action-probe/tests/test_control.py`

**Interfaces:**
- Consumes: `probe.briefs.brief_block`.
- Produces: `validate_scenario(s: dict, input_text: str, b1_lines: list[str]) -> None` (raises `AssertionError`); `plant(b1_text: str, index: int, line: str) -> str`; `actions_blob(msg) -> str`; `scenario_hit(planted_msgs, planted, superseded) -> bool`; `false_hit(b1_msgs, planted) -> bool`; file `/root/medicoes/7b/control/scenarios.jsonl` (`{"scenario_id","kind": "decisive"|"typical","unit_id","index","line","planted","superseded"}`).

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from probe.control import validate_scenario, plant, scenario_hit, false_hit

B1 = "# nox-mem brief — scope=global agent=boris — 2026-10-01T10:00:00.000Z — 2 items\n[lesson|pain 0.4|1d] a — b (chk 1)\n[team|pain 1.0|9d] c — d (chk 2)\n"
LINE = "[lesson|pain 0.4|2d] lessons — X digest output moved to /root/digests-v2/ (chk 900001)"


def m(*cmds):
    return {"text": "", "tool_calls": [{"name": "Bash", "input": {"command": c}} for c in cmds]}


class ControlTest(unittest.TestCase):
    def test_plant_replaces_one_item_keeping_count(self):
        out = plant(B1, 1, LINE)
        self.assertEqual(out.count("\n["), 2)
        self.assertIn(LINE, out)
        self.assertNotIn("(chk 2)", out)

    def test_validate_rejects_token_in_input_and_bad_format(self):
        s = {"kind": "decisive", "index": 0, "line": LINE, "planted": "/root/digests-v2/", "superseded": "/root/digests/"}
        validate_scenario(s, "run the digest into /root/digests/", B1.split("\n")[1:3])
        with self.assertRaises(AssertionError):
            validate_scenario(s, "write to /root/digests-v2/", B1.split("\n")[1:3])
        with self.assertRaises(AssertionError):
            validate_scenario(dict(s, line="free text"), "x", B1.split("\n")[1:3])

    def test_hit_requires_both_replicas_and_no_superseded(self):
        good = m("ls /root/digests-v2/")
        self.assertTrue(scenario_hit([good, good], "/root/digests-v2/", "/root/digests/"))
        self.assertFalse(scenario_hit([good, m("ls /root/digests/")], "/root/digests-v2/", "/root/digests/"))
        self.assertFalse(scenario_hit([m("ls /root/digests-v2/ /root/digests/")] * 2, "/root/digests-v2/", "/root/digests/"))

    def test_false_hit_is_any_b1_replica(self):
        self.assertTrue(false_hit([m("ls"), m("cat /root/digests-v2/x")], "/root/digests-v2/"))
        self.assertFalse(false_hit([m("ls"), {"text": "/root/digests-v2/", "tool_calls": []}], "/root/digests-v2/"))


if __name__ == "__main__":
    unittest.main()
```

Note on `test_hit_requires_both_replicas_and_no_superseded`: `/root/digests/` is a substring of `/root/digests-v2/`? It is not (`digests/` vs `digests-v2/`), so the third assertion tests the "superseded present" branch. Scenario authors must pick values where neither is a substring of the other; `validate_scenario` enforces it.

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_control -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `probe/control.py`**

```python
"""Positive control (spec §7): substitution planting and hit detection on tool-call arguments only."""
import json
import re

ITEM = re.compile(r"^\[[^|\]]+\|pain \d\.\d\|\d+d\] .+ — .+ \(chk \d+\)$")


def validate_scenario(s, input_text, b1_lines):
    assert s["kind"] in ("decisive", "typical")
    assert ITEM.match(s["line"]), "planted line must match the brief item format"
    assert 0 <= s["index"] < len(b1_lines)
    assert s["planted"] in s["line"]
    assert s["planted"] not in input_text, "planted token must be absent from the input turn"
    assert s["planted"] not in s["superseded"] and s["superseded"] not in s["planted"]


def plant(b1_text, index, line):
    lines = b1_text.split("\n")
    item_pos = [i for i, l in enumerate(lines) if l.startswith("[")]
    lines[item_pos[index]] = line
    return "\n".join(lines)


def actions_blob(msg):
    return "\n".join(f"{c.get('name')} {json.dumps(c.get('input'), ensure_ascii=False)}"
                     for c in (msg or {}).get("tool_calls") or [])


def scenario_hit(planted_msgs, planted, superseded):
    return all(planted in actions_blob(m) and superseded not in actions_blob(m) for m in planted_msgs)


def false_hit(b1_msgs, planted):
    return any(planted in actions_blob(m) for m in b1_msgs)
```

- [ ] **Step 4: Run tests** — `python3 -m unittest tests.test_control -v` → 4 tests OK.

- [ ] **Step 5: Author the 20 scenarios on the VPS (before any pilot/main run)**

Pick 20 C units from the **surplus** of the large prompts that are in neither the main nor the pilot set (read their inputs on the VPS). For each, write one JSON line into `/root/medicoes/7b/control/scenarios.jsonl`: 10 `decisive` (a specific, salient change to an argument the first action uses — directory, script name, channel, flag) and 10 `typical` (the same kind of change written in the vague register of real items, e.g. "lessons — digest pipeline: saída migrou (ver v2)" with the planted value still literal). Each line also carries `unit_id`, the B1 `index` to replace, and the `superseded` value present in the input. Add the control units to the manifest-side files with:

```bash
ssh root@100.92.12.18 'cd /root/medicoes/7b/code && python3 - <<EOF
import json, sys
sys.path.insert(0, ".")
from probe.briefs import Bridge, brief_at, brief_block, brief_items, connect, db_agent, db_to_ms
from probe.control import plant, validate_scenario
from probe.corpus import load_turns
from probe.scaffold import build_prompt, parse_template, read_bootstrap, assert_only_brief_differs
R = "/root/medicoes/7b"
turns = {t["unit_id"]: t for t in load_turns("/root/.claude-nuvini-team/projects", "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z")}
used = {json.loads(l)["unit_id"] for l in open(f"{R}/manifest.jsonl")}
tpl = parse_template(open("/root/medicoes/7b-scaffold/forge-2026-09-30T2231.system-prompt.md", encoding="utf-8").read())
con, br = connect(), Bridge()
sc = [json.loads(l) for l in open(f"{R}/control/scenarios.jsonl", encoding="utf-8")]
owners = open(f"{R}/control/owners.jsonl", "w")
assert len(sc) == 20 and sum(s["kind"] == "decisive" for s in sc) == 10
for s in sc:
    u = turns[s["unit_id"]]; assert s["unit_id"] not in used
    t = u["ts"][:19].replace("T", " "); b = brief_at(con, u["agent"], t)
    b1 = br.render(brief_items(con, b["brief_id"]), db_to_ms(b["served_at"]), db_agent(u["agent"]))
    assert not b1["missing"]
    validate_scenario(s, u["text"], [l for l in b1["text"].split("\n") if l.startswith("[")])
    files = read_bootstrap(u["agent"])
    arms = {"B1": brief_block(b1["text"]), "BP": brief_block(plant(b1["text"], s["index"], s["line"]))}
    texts = {a: build_prompt(tpl, u["agent"], files, x, t[:10], False) for a, x in arms.items()}
    assert_only_brief_differs(texts, u["agent"])
    for a, x in texts.items():
        p = f"{R}/control/arms/{s['scenario_id']}/{a}.md"
        import os; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w", encoding="utf-8").write(x)
    open(f"{R}/control/inputs-{s['scenario_id']}.txt", "w", encoding="utf-8").write(u["text"])
    owners.write(json.dumps({"scenario_id": s["scenario_id"], "agent": u["agent"]}) + "\n")
owners.close(); br.close(); print("20 control scenarios validated and frozen")
EOF
sha256sum /root/medicoes/7b/control/scenarios.jsonl'
```
Expected: `20 control scenarios validated and frozen` and a sha256 (recorded in Task 11).

- [ ] **Step 6: Commit**

```bash
git add eval/brief-action-probe/probe/control.py eval/brief-action-probe/tests/test_control.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): positive-control planting and hit detection"
```

---

### Task 11: Phase runner, pilot, frozen parameters (§5)

**Files:**
- Create: `eval/brief-action-probe/scripts/run_phase.py`, `eval/brief-action-probe/scripts/freeze_params.py`
- Commit later: `eval/brief-action-probe/frozen/params.json`

**Interfaces:**
- Consumes: `probe.runner.run_unit`, `probe.canon.{serialize, divergence, CANON_VERSION, MAX_TOKENS, MASKS}`, `probe.stats.{simulate_mde, mde_from_curve}`.
- Produces: `/root/medicoes/7b/results-<phase>.jsonl` (one line per run: `{"unit_id","arm","rep","attempts","ok","returncode","message","hook_calls","hook_mismatch","rate_limited","started"}`); `frozen/params.json`:
  `{"canon_version","canon_sha256","max_tokens","ceiling": 0.5,"pilot_aa": {"C","H"},"valid": {"C","H"},"mde": {"C","H"},"mde_curve": {...},"seeds": {...},"scaffold_sha256","config_dir_sha256","manifest_sha256","h_requests_sha256","control_sha256","cli_version"}`.

- [ ] **Step 1: Implement `scripts/run_phase.py`**

```python
#!/usr/bin/env python3
"""Runs a phase: pilot (B1 × 4), main (B0/B1/BS × 2), control (B1/BP × 2). Resumable: units already
complete in results-<phase>.jsonl are skipped. Run inside tmux; serial by design."""
import argparse
import hashlib
import json
import os
import random
import sys
import time

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.runner import run_unit  # noqa: E402
from probe.scaffold import agent_root  # noqa: E402

R = "/root/medicoes/7b"
REPS = {"pilot": 4, "main": 2, "control": 2}
SPACING_S = 20


def units_for(phase):
    if phase == "control":
        owners = {o["scenario_id"]: o["agent"] for o in map(json.loads, open(f"{R}/control/owners.jsonl"))}
        for l in open(f"{R}/control/scenarios.jsonl", encoding="utf-8"):
            s = json.loads(l)
            d = f"{R}/control/arms/{s['scenario_id']}"
            yield s["scenario_id"], {a: f"{d}/{a}.md" for a in ("B1", "BP")}, \
                open(f"{R}/control/inputs-{s['scenario_id']}.txt", encoding="utf-8").read(), owners[s["scenario_id"]]
        return
    for l in open(f"{R}/manifest.jsonl"):
        u = json.loads(l)
        if (phase == "pilot") != u["stratum"].startswith("pilot"):
            continue
        arms = ("B1",) if phase == "pilot" else ("B0", "B1", "BS")
        yield u["unit_id"], {a: f"{R}/arms/{u['unit_id']}/{a}.md" for a in arms}, \
            open(f"{R}/inputs/{u['unit_id']}.txt", encoding="utf-8").read(), u["agent"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=sorted(REPS))
    a = ap.parse_args()
    out = f"{R}/results-{a.phase}.jsonl"
    done = set()
    if os.path.exists(out):
        for l in open(out):
            done.add(json.loads(l)["unit_id"])
    rng = random.Random(20261014)
    todo = list(units_for(a.phase))
    rng.shuffle(todo)
    for uid, arms, text, agent in todo:
        if uid in done:
            continue
        cwd = agent_root(agent) if agent else R
        seed = int(hashlib.sha256(f"20261014:{uid}".encode()).hexdigest()[:8], 16)
        res = run_unit(uid, arms, text, cwd, f"{R}/runs/{a.phase}", REPS[a.phase], random.Random(seed))
        with open(out, "a") as f:
            for r in res:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(uid, sum(r["ok"] for r in res), "/", len(res), flush=True)
        time.sleep(SPACING_S)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the pilot in tmux on the VPS**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'tmux new -d -s 7b-pilot "cd /root/medicoes/7b/code && python3 scripts/run_phase.py pilot 2>&1 | tee -a /root/medicoes/7b/pilot.log"'
```
Expected: about 30 units × 4 runs; the log prints `<unit> 4 / 4` per unit. Check progress with `ssh root@100.92.12.18 'tail -3 /root/medicoes/7b/pilot.log; wc -l /root/medicoes/7b/results-pilot.jsonl'`. Wait for 120 lines (use a background wait on line count, not on `pgrep -f` of a pattern that appears in the waiting command itself).

- [ ] **Step 3: Implement `scripts/freeze_params.py`**

```python
#!/usr/bin/env python3
"""§5: pilot A/A per stratum, validity ceiling, MDE by simulation; writes params.json (no content)."""
import hashlib
import json
import subprocess
import sys
from itertools import combinations

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe import canon  # noqa: E402
from probe.stats import mde_from_curve, simulate_mde  # noqa: E402

R = "/root/medicoes/7b"
CODE = __file__.rsplit("/scripts/", 1)[0]
Q_GRID = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]


def fsha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    man = [json.loads(l) for l in open(f"{R}/manifest.jsonl")]
    stratum = {u["unit_id"]: u["stratum"] for u in man}
    runs = [json.loads(l) for l in open(f"{R}/results-pilot.jsonl")]
    seqs, by_unit = {}, {}
    for r in runs:
        if r["ok"]:
            rid = (r["unit_id"], r["rep"])
            seqs[rid] = canon.serialize(r["message"])
            by_unit.setdefault(r["unit_id"], []).append(rid)
    params = {"canon_version": canon.CANON_VERSION, "canon_sha256": fsha(f"{CODE}/probe/canon.py"),
              "max_tokens": canon.MAX_TOKENS, "ceiling": 0.5, "pilot_aa": {}, "valid": {}, "mde": {},
              "mde_curve": {}, "seeds": {"manifest": 20261014, "mde": 7}}
    cache = {}

    def dist(a, b):
        k = (a, b) if a <= b else (b, a)
        if k not in cache:
            cache[k] = canon.divergence(seqs[a], seqs[b])
        return cache[k]

    for s in ("C", "H"):
        units = [ids for uid, ids in by_unit.items() if stratum[uid] == f"pilot_{s}" and len(ids) == 4]
        aa = [sum(dist(a, b) for a, b in combinations(ids, 2)) / 6 for ids in units]
        params["pilot_aa"][s] = sum(aa) / len(aa)
        params["valid"][s] = params["pilot_aa"][s] <= 0.5
        sizes = {}
        for u in man:
            if u["stratum"] == s:
                sizes[u["cluster"]] = sizes.get(u["cluster"], 0) + 1
        curve = simulate_mde(units, dist, list(sizes.values()), Q_GRID, n_sim=200, n_boot=1000, alpha=0.0125, seed=7)
        params["mde_curve"][s] = curve
        params["mde"][s] = mde_from_curve(curve)
        params[f"pilot_units_{s}"] = len(units)
    params["scaffold_sha256"] = "7b4b0820009bc170d178e0ce8bf16af5780a9d394e90bf678b2addee0dffb75c"
    params["config_dir_sha256"] = open(f"{R}/config-dir.sha256").read().strip()
    params["manifest_sha256"] = fsha(f"{R}/manifest.jsonl")
    params["h_requests_sha256"] = fsha(f"{R}/h_requests.jsonl")
    params["rubrics_sha256"] = fsha(f"{R}/rubrics.jsonl")
    params["control_sha256"] = fsha(f"{R}/control/scenarios.jsonl")
    params["cli_version"] = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    json.dump(params, open(f"{R}/params.json", "w"), indent=1)
    print(json.dumps({k: params[k] for k in ("pilot_aa", "valid", "mde")}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Freeze and commit the parameters**

```bash
ssh root@100.92.12.18 'cd /root/medicoes/7b/code && python3 scripts/freeze_params.py'
scp root@100.92.12.18:/root/medicoes/7b/params.json eval/brief-action-probe/frozen/params.json
git add eval/brief-action-probe/scripts/run_phase.py eval/brief-action-probe/scripts/freeze_params.py eval/brief-action-probe/frozen/params.json
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): phase runner and pilot-frozen parameters (A/A, ceiling, MDE)"
git push -u origin feat/7b-action-probe
```
Expected: `params.json` holds only numbers, hashes and versions (check with `grep -c '"text"' eval/brief-action-probe/frozen/params.json` → `0`). Report pilot A/A, validity and MDE per stratum to Toto before Task 12. Nothing under `probe/canon.py` may change after this commit.

---

### Task 12: Main run and control run

**Files:** none new (uses `scripts/run_phase.py`).

- [ ] **Step 1: Verify the freeze still holds, then start the main run**

```bash
ssh root@100.92.12.18 'cd /root/medicoes/7b/code && python3 - <<EOF
import hashlib, json
p = json.load(open("/root/medicoes/7b/params.json"))
assert hashlib.sha256(open("probe/canon.py","rb").read()).hexdigest() == p["canon_sha256"]
assert hashlib.sha256(open("/root/medicoes/7b/manifest.jsonl","rb").read()).hexdigest() == p["manifest_sha256"]
assert open("/root/medicoes/7b/config-dir.sha256").read().strip() == p["config_dir_sha256"]
print("freeze intact")
EOF
tmux new -d -s 7b-main "cd /root/medicoes/7b/code && python3 scripts/run_phase.py main 2>&1 | tee -a /root/medicoes/7b/main.log"'
```
Expected: `freeze intact`, then ≈ 124 units × 6 runs over one to two days. Monitor with `wc -l /root/medicoes/7b/results-main.jsonl` (target ≈ 744) and the per-unit `ok / total` lines.

- [ ] **Step 2: Run the control after the main run finishes**

```bash
ssh root@100.92.12.18 'tmux new -d -s 7b-control "cd /root/medicoes/7b/code && python3 scripts/run_phase.py control 2>&1 | tee -a /root/medicoes/7b/control.log"'
```
Expected: 20 scenarios × 4 runs = 80 lines in `results-control.jsonl`.

---

### Task 13: Judge (§6.2)

**Files:**
- Create: `eval/brief-action-probe/probe/judge.py`, `eval/brief-action-probe/scripts/run_judge.py`
- Test: `eval/brief-action-probe/tests/test_judge.py`

**Interfaces:**
- Consumes: `probe.llm.gemini_json`.
- Produces: `render_candidate(msg) -> str`; `judge_prompt(input_text, rubric, a, b) -> str`; `parse_verdict(obj) -> "A"|"B"|"tie"`; `score(winner_arm, first_arm) -> float`; `corrupt(msg, op, tool_names, rubric) -> tuple[dict, str]`; `/root/medicoes/7b/judgments.jsonl` (`{"unit_id","contrast","first","second","a_arm","verdict","winner_arm","reason","known_answer": bool,"op"}`).

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from probe.judge import parse_verdict, score, corrupt, render_candidate


def m(name, inp, text=""):
    return {"text": text, "tool_calls": [{"name": name, "input": inp}]}


class JudgeTest(unittest.TestCase):
    def test_parse_verdict(self):
        self.assertEqual(parse_verdict({"winner": "A"}), "A")
        self.assertEqual(parse_verdict({"winner": "tie"}), "tie")
        self.assertEqual(parse_verdict({"winner": "both"}), "tie")

    def test_score(self):
        self.assertEqual(score("B1", "B1"), 1.0)
        self.assertEqual(score(None, "B1"), 0.5)
        self.assertEqual(score("B0", "B1"), 0.0)

    def test_corrupt_path(self):
        out, op = corrupt(m("Read", {"file_path": "/root/x/report.md"}), "path", ["Read", "Bash"], {})
        self.assertEqual(op, "path")
        self.assertEqual(out["tool_calls"][0]["input"]["file_path"], "/root/x/nonexistent-report.md")

    def test_corrupt_tool_and_required_and_fallback(self):
        out, op = corrupt(m("Read", {"file_path": "/a"}), "tool", ["Bash", "Read", "Write"], {})
        self.assertEqual((op, out["tool_calls"][0]["name"]), ("tool", "Write"))
        out, op = corrupt(m("Read", {"file_path": "/a", "limit": 3}), "required", ["Read"], {"required_args": ["limit"]})
        self.assertNotIn("limit", out["tool_calls"][0]["input"])
        out, op = corrupt(m("Bash", {"command": "ls"}), "path", ["Bash", "Read"], {})
        self.assertEqual(op, "tool")  # no path to corrupt -> next operator in the cycle

    def test_render_candidate_truncates(self):
        self.assertLessEqual(len(render_candidate({"text": "x" * 9000, "tool_calls": []})), 4100)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_judge -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement `probe/judge.py`**

```python
"""Judge helpers (spec §6.2): candidate rendering, verdict parsing, scores, known-answer corruption."""
import copy
import json
import os

OPS = ("path", "tool", "required")
MAX_CHARS = 4000
PROMPT = """You are judging two candidate FIRST ACTIONS that an AI agent took in response to the input
below. Judge only against the rubric. Do not reward length, confidence or style. If neither is better,
answer tie.

INPUT:
{input}

RUBRIC (JSON):
{rubric}

CANDIDATE A:
{a}

CANDIDATE B:
{b}

Return JSON: {{"winner": "A" | "B" | "tie", "reason": "<one line>"}}"""


def render_candidate(msg):
    parts = [f"TOOL {c['name']}: {json.dumps(c.get('input'), ensure_ascii=False)}" for c in msg.get("tool_calls") or []]
    if (msg.get("text") or "").strip():
        parts.append(f"TEXT: {msg['text']}")
    return "\n".join(parts)[:MAX_CHARS]


def judge_prompt(input_text, rubric, a, b):
    return PROMPT.format(input=input_text[:6000], rubric=json.dumps(rubric, ensure_ascii=False),
                         a=render_candidate(a), b=render_candidate(b))


def parse_verdict(obj):
    w = str(obj.get("winner", "")).strip()
    return w if w in ("A", "B") else "tie"


def score(winner_arm, first_arm):
    if winner_arm is None:
        return 0.5
    return 1.0 if winner_arm == first_arm else 0.0


def _first_path_key(inp):
    for k, v in (inp or {}).items():
        if isinstance(v, str) and v.startswith("/") and len(v) > 1:
            return k
    return None


def corrupt(msg, op, tool_names, rubric):
    """Apply operator `op`; if it cannot apply, try the next operator in OPS order (cyclic)."""
    start = OPS.index(op)
    for i in range(len(OPS)):
        o = OPS[(start + i) % len(OPS)]
        m = copy.deepcopy(msg)
        call = (m.get("tool_calls") or [None])[0]
        if call is None:
            break
        if o == "path":
            k = _first_path_key(call["input"])
            if k:
                p = call["input"][k]
                call["input"][k] = os.path.join(os.path.dirname(p), "nonexistent-" + os.path.basename(p))
                return m, o
        elif o == "tool":
            others = [t for t in sorted(tool_names) if t != call["name"]]
            if others:
                later = [t for t in others if t > call["name"]]
                call["name"] = (later or others)[0]
                return m, o
        elif o == "required":
            req = [k for k in rubric.get("required_args", []) if k in (call["input"] or {})]
            if req:
                del call["input"][req[0]]
                return m, o
    raise ValueError("no corruption operator applies")
```

- [ ] **Step 4: Run tests** — `python3 -m unittest tests.test_judge -v` → 5 tests OK.

- [ ] **Step 5: Implement `scripts/run_judge.py`**

```python
#!/usr/bin/env python3
"""§6.2: judged pairs for every main unit (B1×B0, B1×BS, B0×BS, B1r1×B1r2) and 20 known-answer pairs."""
import json
import os
import random
import sys

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.judge import OPS, corrupt, judge_prompt, parse_verdict  # noqa: E402
from probe.llm import gemini_json  # noqa: E402

R = "/root/medicoes/7b"
PAIRS = (("B1", 1, "B0", 1), ("B1", 1, "BS", 1), ("B0", 1, "BS", 1), ("B1", 1, "B1", 2))


def main():
    out = f"{R}/judgments.jsonl"
    done = set()
    if os.path.exists(out):
        done = {(j["unit_id"], j["contrast"]) for j in map(json.loads, open(out))}
    man = {u["unit_id"]: u for u in map(json.loads, open(f"{R}/manifest.jsonl"))}
    rub = {r["unit_id"]: r for r in map(json.loads, open(f"{R}/rubrics.jsonl", encoding="utf-8"))}
    runs = {}
    for r in map(json.loads, open(f"{R}/results-main.jsonl")):
        if r["ok"]:
            runs[(r["unit_id"], r["arm"], r["rep"])] = r["message"]
    rng = random.Random(20261014)
    tool_names = sorted({c["name"] for m in runs.values() for c in m["tool_calls"]})
    with open(out, "a", encoding="utf-8") as f:
        for uid in sorted(man):
            if man[uid]["stratum"] not in ("C", "R", "H"):
                continue
            text = open(f"{R}/inputs/{uid}.txt", encoding="utf-8").read()
            for xa, xr, ya, yr in PAIRS:
                contrast = f"{xa}r{xr}x{ya}r{yr}"
                x, y = runs.get((uid, xa, xr)), runs.get((uid, ya, yr))
                if (uid, contrast) in done or x is None or y is None:
                    continue
                a_is_x = rng.random() < 0.5
                a, b = (x, y) if a_is_x else (y, x)
                v = parse_verdict(gemini_json(judge_prompt(text, rub[uid], a, b)) or {})
                first, second = f"{xa}r{xr}", f"{ya}r{yr}"
                winner = None if v == "tie" else (first if (v == "A") == a_is_x else second)
                f.write(json.dumps({"unit_id": uid, "contrast": contrast, "first": first, "second": second,
                                    "a_arm": first if a_is_x else second, "verdict": v, "winner_arm": winner,
                                    "known_answer": False}) + "\n")
        # Known answer: 20 B1r1 runs with a tool call, seeded draw from C and H; operators cycle.
        pool = sorted(uid for uid in man if man[uid]["stratum"] in ("C", "H")
                      and runs.get((uid, "B1", 1), {}).get("tool_calls"))
        for i, uid in enumerate(random.Random(7).sample(pool, 20)):
            if (uid, "known") in done:
                continue
            orig = runs[(uid, "B1", 1)]
            bad, op = corrupt(orig, OPS[i % 3], tool_names, rub[uid])
            text = open(f"{R}/inputs/{uid}.txt", encoding="utf-8").read()
            a_is_orig = rng.random() < 0.5
            a, b = (orig, bad) if a_is_orig else (bad, orig)
            v = parse_verdict(gemini_json(judge_prompt(text, rub[uid], a, b)) or {})
            winner = None if v == "tie" else ("original" if (v == "A") == a_is_orig else "corrupted")
            f.write(json.dumps({"unit_id": uid, "contrast": "known", "first": "original", "second": "corrupted",
                                "a_arm": "original" if a_is_orig else "corrupted", "verdict": v,
                                "winner_arm": winner, "known_answer": True, "op": op}) + "\n")
    print("judgments written")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run on the VPS after the main run**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'set -a; . /root/.openclaw/.env; set +a; cd /root/medicoes/7b/code && python3 scripts/run_judge.py && wc -l /root/medicoes/7b/judgments.jsonl'
```
Expected: ≈ 4 × 124 + 20 ≈ 516 lines (fewer only where a run failed after retry).

- [ ] **Step 7: Commit**

```bash
git add eval/brief-action-probe/probe/judge.py eval/brief-action-probe/scripts/run_judge.py eval/brief-action-probe/tests/test_judge.py
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): blind pairwise judge with known-answer corruption"
```

---

### Task 14: Analysis exactly as §6–7, aggregates, audit, PR

**Files:**
- Create: `eval/brief-action-probe/scripts/analyze.py`, `eval/brief-action-probe/tests/test_analyze.py`, `audits/<run-date>-7b-action-probe.md`
- Commit: `eval/brief-action-probe/out/aggregates.json`
- Modify: `docs/HANDOFF.md`, `docs/ROADMAP.md` (item 7 row)

**Interfaces:**
- Consumes: `probe.canon.{serialize, divergence}`, `probe.stats.*`, `probe.control.{scenario_hit, false_hit}`, `probe.judge.score`.
- Produces: `unit_deltas(msgs: dict[(arm, rep), dict]) -> dict | None`; `decide(by_stratum, params, inconclusive, seed=11) -> dict`; `out/aggregates.json`.

- [ ] **Step 1: Write the failing tests for the decision logic**

```python
import unittest
from probe_analyze import unit_deltas, decide  # scripts/analyze.py is importable as probe_analyze via the test shim

M = lambda t: {"text": t, "tool_calls": []}


class AnalyzeTest(unittest.TestCase):
    def test_unit_deltas_needs_all_six_runs(self):
        msgs = {(a, r): M("same words here") for a in ("B0", "B1", "BS") for r in (1, 2)}
        d = unit_deltas(msgs)
        self.assertEqual((d["dp"], d["dc"]), (0.0, 0.0))
        del msgs[("BS", 2)]
        self.assertIsNone(unit_deltas(msgs))

    def test_presence_effect_detected_and_holm_family_of_four(self):
        by = {"C": {"dp": {f"c{i}": [0.4] for i in range(12)}, "dc": {f"c{i}": [0.0] for i in range(12)}},
              "H": {"dp": {f"h{i}": [0.0] for i in range(12)}, "dc": {f"h{i}": [0.0] for i in range(12)}}}
        params = {"valid": {"C": True, "H": True}, "mde": {"C": 0.1, "H": 0.1}}
        out = decide(by, params, inconclusive=set())
        self.assertTrue(out["C"]["dp"]["effect"])
        self.assertFalse(out["C"]["dc"]["effect"])
        self.assertEqual(len(out["holm"]), 4)

    def test_invalid_stratum_has_no_delta_and_p_one(self):
        by = {"C": {"dp": {"c": [0.4]}, "dc": {"c": [0.4]}}, "H": {"dp": {"h": [0.0]}, "dc": {"h": [0.0]}}}
        out = decide(by, {"valid": {"C": False, "H": True}, "mde": {"C": 0.1, "H": 0.1}}, inconclusive=set())
        self.assertEqual(out["C"], {"invalid": True})
        self.assertEqual(out["holm_raw"]["C.dp"], 1.0)

    def test_inconclusive_contrast_gets_p_one(self):
        by = {"C": {"dp": {f"c{i}": [0.4] for i in range(12)}, "dc": {f"c{i}": [0.4] for i in range(12)}},
              "H": {"dp": {"h": [0.0]}, "dc": {"h": [0.0]}}}
        out = decide(by, {"valid": {"C": True, "H": True}, "mde": {"C": 0.1, "H": 0.1}}, inconclusive={"C.dc"})
        self.assertEqual(out["holm_raw"]["C.dc"], 1.0)
        self.assertTrue(out["C"]["dc"]["inconclusive"])

    def test_null_reading_branches(self):
        by = {"C": {"dp": {f"c{i}": [0.0] for i in range(12)}, "dc": {f"c{i}": [0.0] for i in range(12)}},
              "H": {"dp": {"h": [0.0]}, "dc": {"h": [0.0]}}}
        out = decide(by, {"valid": {"C": True, "H": True}, "mde": {"C": 0.05, "H": 0.05}}, inconclusive=set())
        self.assertEqual(out["C"]["dp"]["null_reading"], "effects >= MDE excluded")


if __name__ == "__main__":
    unittest.main()
```

Create the import shim `eval/brief-action-probe/tests/probe_analyze.py`:

```python
import importlib.util
import os

_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "analyze.py")
_spec = importlib.util.spec_from_file_location("analyze", _p)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
unit_deltas, decide = _mod.unit_deltas, _mod.decide
```

- [ ] **Step 2: Run to verify failure** — `python3 -m unittest tests.test_analyze -v` → file-not-found for `scripts/analyze.py`.

- [ ] **Step 3: Implement `scripts/analyze.py`**

```python
#!/usr/bin/env python3
"""§6–7 decisions, exactly as pre-registered. Writes out/aggregates.json (no session content)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from probe.canon import divergence, serialize  # noqa: E402
from probe.control import false_hit, scenario_hit  # noqa: E402
from probe.judge import score  # noqa: E402
from probe.stats import (cluster_bootstrap, fisher_2x2, holm, one_sided_p, percentile_ci,  # noqa: E402
                         stratum_estimate, tost_proportion)

R = "/root/medicoes/7b"
ARMS = ("B0", "B1", "BS")


def unit_deltas(msgs):
    if any((a, r) not in msgs for a in ARMS for r in (1, 2)):
        return None
    s = {k: serialize(v) for k, v in msgs.items()}
    aa = sum(divergence(s[(a, 1)], s[(a, 2)]) for a in ARMS) / 3

    def D(x, y):
        return sum(divergence(s[(x, i)], s[(y, j)]) for i in (1, 2) for j in (1, 2)) / 4

    return {"aa": aa, "dp": D("B1", "B0") - aa, "dc": D("B1", "BS") - aa}


def decide(by, params, inconclusive, seed=11):
    out, raw, stats = {}, {}, {}
    for s in ("C", "H"):
        if not params["valid"][s]:
            out[s] = {"invalid": True}
            raw[f"{s}.dp"] = raw[f"{s}.dc"] = 1.0
            continue
        out[s] = {}
        for k in ("dp", "dc"):
            name = f"{s}.{k}"
            est = stratum_estimate(by[s][k])
            draws = cluster_bootstrap(by[s][k], 10000, seed)
            lo, hi = percentile_ci(draws)
            stats[name] = (est, lo, hi)
            raw[name] = 1.0 if name in inconclusive else one_sided_p(draws)
    adj = holm(raw)
    for s in ("C", "H"):
        if out[s].get("invalid"):
            continue
        for k in ("dp", "dc"):
            name = f"{s}.{k}"
            est, lo, hi = stats[name]
            eff = adj[name] < 0.05
            row = {"estimate": est, "ci95": [lo, hi], "p": raw[name], "p_holm": adj[name], "effect": eff,
                   "inconclusive": name in inconclusive, "mde": params["mde"][s]}
            if not eff and not row["inconclusive"] and lo <= 0 <= hi:
                mde = params["mde"][s]
                row["null_reading"] = ("effects >= MDE excluded" if mde is not None and hi < mde
                                       else "underpowered for effects of MDE size")
            out[s][k] = row
    out["holm_raw"], out["holm"] = raw, adj
    return out


def main():
    params = json.load(open(f"{R}/params.json"))
    man = {u["unit_id"]: u for u in map(json.loads, open(f"{R}/manifest.jsonl"))}
    runs = list(map(json.loads, open(f"{R}/results-main.jsonl")))
    msgs, fails = {}, {}
    for r in runs:
        st = man[r["unit_id"]]["stratum"]
        fails.setdefault(st, {a: [0, 0] for a in ARMS})[r["arm"]][0 if r["ok"] else 1] += 1
        if r["ok"]:
            msgs.setdefault(r["unit_id"], {})[(r["arm"], r["rep"])] = r["message"]
    # §4 failure branch: 2×2 Fisher per arm vs the other two pooled.
    inconclusive, fisher = set(), {}
    for st in ("C", "H"):
        f = fails.get(st, {a: [0, 0] for a in ARMS})
        for a in ARMS:
            ok_o = sum(f[b][0] for b in ARMS if b != a)
            bad_o = sum(f[b][1] for b in ARMS if b != a)
            p = fisher_2x2(f[a][0], f[a][1], ok_o, bad_o)
            fisher[f"{st}.{a}"] = p
            if p < 0.05:
                if a in ("B1", "B0"):
                    inconclusive.add(f"{st}.dp")
                if a in ("B1", "BS"):
                    inconclusive.add(f"{st}.dc")
    by, leak_by, units_used, r_desc = {}, {}, {}, []
    for uid, m in msgs.items():
        u = man[uid]
        d = unit_deltas(m)
        if d is None:
            continue
        if u["stratum"] == "R":
            r_desc.append(d)
            continue
        if u["stratum"] not in ("C", "H"):
            continue
        units_used[u["stratum"]] = units_used.get(u["stratum"], 0) + 1
        for k in ("dp", "dc"):
            by.setdefault(u["stratum"], {"dp": {}, "dc": {}})[k].setdefault(u["cluster"], []).append(d[k])
            if not u["leak_flag"]:
                leak_by.setdefault(u["stratum"], {"dp": {}, "dc": {}})[k].setdefault(u["cluster"], []).append(d[k])
    primary = decide(by, params, inconclusive)
    sensitivity = decide(leak_by, params, inconclusive) if all(s in leak_by for s in ("C", "H")) else None
    # §6.2
    js = list(map(json.loads, open(f"{R}/judgments.jsonl")))
    main_j = [j for j in js if not j["known_answer"]]
    nontie = [j for j in main_j if j["verdict"] != "tie"]
    k_a = sum(1 for j in nontie if j["verdict"] == "A")
    pos_ok, p_lo, p_hi = tost_proportion(k_a, len(nontie))
    known = [j for j in js if j["known_answer"]]
    known_ok = sum(1 for j in known if j["winner_arm"] == "original")
    gates = {"position": {"k_A": k_a, "n": len(nontie), "pass": pos_ok, "p_low": p_lo, "p_high": p_hi},
             "known_answer": {"correct": known_ok, "n": len(known), "pass": known_ok >= 17}}
    judged = {}
    for st in ("C", "H", "R"):
        judged[st] = {}
        for contrast, first in (("B1r1xB0r1", "B1r1"), ("B1r1xBSr1", "B1r1"), ("B0r1xBSr1", "B0r1"),
                                ("B1r1xB1r2", "B1r1")):
            cl = {}
            for j in main_j:
                if j["contrast"] == contrast and man[j["unit_id"]]["stratum"] == st:
                    cl.setdefault(man[j["unit_id"]]["cluster"], []).append(score(j["winner_arm"], first))
            if not cl:
                continue
            draws = cluster_bootstrap(cl, 10000, 13)
            judged[st][contrast] = {"score": stratum_estimate(cl), "ci95": list(percentile_ci(draws)), "n_clusters": len(cl)}
        if st in ("C", "H") and gates["position"]["pass"] and gates["known_answer"]["pass"]:
            judged[st]["helps"] = all(judged[st].get(c, {"ci95": [0, 0]})["ci95"][0] > 0.5
                                      for c in ("B1r1xB0r1", "B1r1xBSr1"))
    # §7
    ctrl = list(map(json.loads, open(f"{R}/results-control.jsonl")))
    sc = {s["scenario_id"]: s for s in map(json.loads, open(f"{R}/control/scenarios.jsonl", encoding="utf-8"))}
    cm = {}
    for r in ctrl:
        if r["ok"]:
            cm.setdefault(r["unit_id"], {}).setdefault(r["arm"], []).append(r["message"])
    hits = {"decisive": 0, "typical": 0}
    false = 0
    for sid, s in sc.items():
        bp, b1 = cm.get(sid, {}).get("BP", []), cm.get(sid, {}).get("B1", [])
        if len(bp) == 2 and scenario_hit(bp, s["planted"], s["superseded"]):
            hits[s["kind"]] += 1
        if s["kind"] == "decisive" and false_hit(b1, s["planted"]):
            false += 1
    control = {"decisive_hits": hits["decisive"], "typical_hits": hits["typical"], "false_hits": false,
               "pass": hits["decisive"] >= 7 and false <= 1}
    control["nulls_informative"] = control["pass"] and hits["typical"] >= 3
    rel = [json.loads(l) for l in open(f"{R}/relevance.jsonl")]
    summary = json.load(open(f"{R}/manifest-summary.json"))
    agg = {"params": {k: params[k] for k in ("pilot_aa", "valid", "mde", "canon_sha256", "manifest_sha256")},
           "units_used": units_used, "fisher": fisher, "inconclusive": sorted(inconclusive),
           "primary": primary, "leak_sensitivity": sensitivity, "judge_gates": gates, "judged": judged,
           "control": control, "R_descriptive": {"n": len(r_desc), **({k: sum(d[k] for d in r_desc) / len(r_desc)
                                                                       for k in ("aa", "dp", "dc")} if r_desc else {})},
           "h_relevance_rate": sum(r["present"] for r in rel) / len(rel) if rel else None,
           "bs_drop_rate": summary["bs_drop_rate"],
           "bs_drop_flag": {s: v > 0.20 for s, v in summary["bs_drop_rate"].items()},
           "drops": summary["drops"]}
    json.dump(agg, open(f"{R}/aggregates.json", "w"), indent=1)
    print(json.dumps({"primary": primary, "gates": gates, "control": control}, indent=1))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests** — `python3 -m unittest tests.test_analyze -v` → 5 tests OK. Then the full suite: `python3 -m unittest discover -s tests -v` → all OK.

- [ ] **Step 5: Run the analysis on the VPS and bring back the aggregates**

```bash
NOX_VPS=root@100.92.12.18 eval/brief-action-probe/scripts/sync_to_vps.sh
ssh root@100.92.12.18 'cd /root/medicoes/7b/code && python3 scripts/analyze.py'
scp root@100.92.12.18:/root/medicoes/7b/aggregates.json eval/brief-action-probe/out/aggregates.json
grep -c '"text"\|chk ' eval/brief-action-probe/out/aggregates.json
```
Expected: the last command prints `0` (no content in the committed file).

- [ ] **Step 6: Write the audit `audits/<run-date>-7b-action-probe.md`** (English) with: question and scope (first action, today's scaffold); fidelity gate rate; manifest counts and drops; pilot A/A, validity and MDE per stratum; the four primary decisions with estimate, CI, raw and Holm p, and the null reading where applicable; leak sensitivity; judge gates and the helps verdict per stratum; positive control and how it conditions the reading; R descriptive; H relevance rate; BS drop flags; limits from spec §8. Numbers only from `out/aggregates.json`.

- [ ] **Step 7: Update `docs/HANDOFF.md` and the item 7 row of `docs/ROADMAP.md`** with the result in two sentences and a link to the audit.

- [ ] **Step 8: Commit, push and open the PR**

```bash
git add eval/brief-action-probe/scripts/analyze.py eval/brief-action-probe/tests/test_analyze.py \
        eval/brief-action-probe/tests/probe_analyze.py eval/brief-action-probe/out/aggregates.json \
        audits/*-7b-action-probe.md docs/HANDOFF.md docs/ROADMAP.md
COMMIT_TO_NON_MAIN_OK=1 git commit -m "feat(7b): pre-registered analysis, aggregates and audit"
git push
gh pr create --title "feat(7b): brief action probe — harness, frozen parameters, results" --body "$(cat <<'EOF'
**What:** offline replay probe for ROADMAP item 7(b), implementing specs/2026-10-14-7b-brief-action-probe-design.md (v3.1).
**Why:** 7(a) ruled out visible use of the brief; 7(b) measures whether it changes the first action.
**How tested:** unit suite (stdlib unittest) on Python 3.12 and 3.14; render-fidelity gate over git-archived briefs; smoke test of the deny-all hook; analysis code tested on synthetic inputs before reading results. Raw data stays on the VPS.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
