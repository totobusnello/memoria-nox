#!/usr/bin/env python3
"""Runner for the two use studies (PREREGISTRATION.md). It is the runner of the 2026-11-07
evaluation (`note-unconsulted-memory/skill-eval/harness/run_eval.py`, imported, not copied) with
five new arms. Every arm runs the T2 build of 2026-11-07 (nox-mem 3.8.0 with the scoped
instructions), so each arm differs from the measured T2 in one thing only:

  W0  T2 as measured                                   (study W control)
  WH  T2 + a project Stop hook that asks once to record a stated decision (stop_hook.py)
  WN  T2 build whose read tools end every result with one line asking to record a stated decision
      (arm-WN-mcp-server.diff)
  WP  T2 + the prompt says "Record in nox-mem memory any decision I state here."   (ceiling)
  SD  T2 build with the scope sentence derived from the database (derive_scope.py,
      arm-SD-mcp-server.diff) in place of the hand-written one                     (study S)

Usage:
  run_use.py --bank tasks-v1.jsonl --arms W0,WH,WN,WP --replicas 3 --label W-main [--tasks ...] [--dry-run]
"""
import argparse
import importlib.util
import json
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
spec = importlib.util.spec_from_file_location(
    "run_eval", REPO / "note-unconsulted-memory" / "skill-eval" / "harness" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)

EVAL = Path.home() / "nox-skill-eval"

# Claude Code 2.1.332 runs Bash under `--permission-mode dontAsk` when it is not in --allowedTools
# (smoke of 2026-11-26: an `ls` in the run's cwd succeeded with no denial); 2.1.319, used on
# 2026-11-07, denied it. From the cwd the agent could reach the run's copy of the database and skip
# the MCP. Deny the built-in tools by name, which restores the 2026-11-07 condition.
DENY = ["Bash", "Read", "Grep", "Glob", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch",
        "Task", "Agent"]
_orig_run = run_eval.subprocess.run


def _run_with_deny(cmd, *args, **kw):
    if isinstance(cmd, list) and "--allowedTools" in cmd:
        i = cmd.index("--allowedTools")
        cmd = cmd[:i] + ["--disallowedTools", *DENY] + cmd[i:]
    return _orig_run(cmd, *args, **kw)


run_eval.subprocess.run = _run_with_deny
BUILD = {"W0": "nox-mem-3.8.0-T2", "WH": "nox-mem-3.8.0-T2", "WP": "nox-mem-3.8.0-T2",
         "WN": "nox-mem-3.8.0-T2-WN", "SD": "nox-mem-3.8.0-T2-SD"}
WP_PREFIX = "Record in nox-mem memory any decision I state here.\n\n"
ARMS = set(BUILD)


def one_run(task, arm, rep, a, work_root, out, frozen):
    """run_eval.one_run with arm T semantics (no skill, MCP from a given build), plus the
    per-arm change. run_eval knows arms S0/S1/P+/N/T; every arm here is passed to it as T."""
    a = argparse.Namespace(**vars(a))
    a.noxmem_t = str(EVAL / BUILD[arm])
    t = dict(task)
    if arm == "WP":
        t["prompt"] = WP_PREFIX + task["prompt"]
    if arm == "WH":
        # run_eval creates <work>/<run_id>/cwd; the hook must be in that cwd before claude starts.
        # One subclass-free way: wrap Path.mkdir for the duration of this run.
        orig_mkdir = Path.mkdir

        def mkdir_and_hook(self, *args, **kw):
            orig_mkdir(self, *args, **kw)
            if self.name == "cwd" and not (self / ".claude").exists():
                d = self / ".claude"
                orig_mkdir(d)
                shutil.copy(HERE / "stop_hook.py", d / "stop_hook.py")
                (d / "settings.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
                    {"type": "command", "command": f"python3 -I {d / 'stop_hook.py'}"}]}]}}))

        Path.mkdir = mkdir_and_hook
        try:
            rec = run_eval.one_run(t, "T", rep, a, work_root, out, frozen)
        finally:
            Path.mkdir = orig_mkdir
    else:
        rec = run_eval.one_run(t, "T", rep, a, work_root, out, frozen)
    rec["arm"] = arm
    rec["build"] = BUILD[arm]
    rec["hook_fired"] = None
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bank", default=str(EVAL / "bank" / "tasks-v1.jsonl"))
    p.add_argument("--arms", required=True)
    p.add_argument("--replicas", type=int, default=3)
    p.add_argument("--tasks", default="")
    p.add_argument("--sets", default="", help="comma list of task sets, e.g. W+,W-")
    p.add_argument("--label", required=True)
    p.add_argument("--db", default="")
    p.add_argument("--keyfile", default=str(Path.home() / ".config/secrets/GEMINI_API_KEY"))
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--max-budget", type=float, default=1.0)
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--seed", type=int, default=20261126)
    p.add_argument("--keep-work", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    a.noxmem = ""  # unused: every arm sets its own build
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    assert set(arms) <= ARMS, f"unknown arm in {arms}"
    tasks = [json.loads(l) for l in open(a.bank) if l.strip()]
    if a.sets:
        keep = set(a.sets.split(","))
        tasks = [t for t in tasks if t["set"] in keep]
    if a.tasks:
        keep = set(a.tasks.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    frozen = Path(a.db) if a.db else sorted((EVAL / "db").glob("eval-*.db"))[-1]
    plan = [(t, arm, r) for t in tasks for arm in arms for r in range(1, a.replicas + 1)]
    random.Random(a.seed).shuffle(plan)
    print(f"{len(plan)} runs, db {frozen.name}, model {a.model}, arms {arms}", file=sys.stderr)
    if a.dry_run:
        for t, arm, r in plan:
            print(arm, t["id"], r)
        return
    out = EVAL / "runs" / a.label
    out.mkdir(parents=True, exist_ok=True)
    work_root = EVAL / "work" / a.label
    work_root.mkdir(parents=True, exist_ok=True)
    with open(out / "results.jsonl", "a") as res:
        for i, (t, arm, r) in enumerate(plan, 1):
            rec = one_run(t, arm, r, a, work_root, out, frozen)
            res.write(json.dumps(rec) + "\n")
            res.flush()
            print(f"[{i}/{len(plan)}] {arm} {t['id']} r{r} rc={rec['rc']} mem={rec['memory_calls']} "
                  f"write={rec['write_calls']} {rec['wall_s']}s", file=sys.stderr)


if __name__ == "__main__":
    main()
