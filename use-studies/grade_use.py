#!/usr/bin/env python3
"""Grading for the use studies (PREREGISTRATION.md section 5). Reuses the 2026-11-07 grader
(`note-unconsulted-memory/skill-eval/harness/grade.py`, Gemini 4 Argon, temperature 0, JSON
schema, verbatim-quote check, `grader_invalid` after two failed quotes), imported, not copied.

  K runs (study S): the reply text, exactly as on 2026-11-07.
  W+ runs that wrote (study W): the text of the run's memory write calls, judged against the
    task's stated decision and pass criterion ("at least one memory write call whose content
    captures ..."). A W+ run with no write call fails without a grader call. W- runs are scored
    from tool calls only (did it write), as on 2026-11-07.

  grade_use.py --results runs/<label>/results.jsonl --out grading/<label>.graded.jsonl
"""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "grade", HERE.parent / "note-unconsulted-memory" / "skill-eval" / "harness" / "grade.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
WRITE_TOOLS = {"nox_mem_decision_set", "nox_mem_ingest", "nox_mem_crystallize"}


def write_text(rec):
    calls = [c for c in rec.get("tool_calls") or [] if c["name"] in WRITE_TOOLS]
    return "\n".join(f"{c['name']}: {json.dumps(c['input'], ensure_ascii=False)}" for c in calls)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bank", default=str(Path.home() / "nox-skill-eval/bank/tasks-v1.jsonl"))
    p.add_argument("--results", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    tasks = {t["id"]: t for t in map(json.loads, open(a.bank)) if t}
    done = set()
    if Path(a.out).exists():
        done = {json.loads(l)["key"] for l in open(a.out) if l.strip()}
    with open(a.out, "a") as out:
        for rec in map(json.loads, open(a.results)):
            if rec["run_id"] in done:
                continue
            t = tasks[rec["task"]]
            row = {"kind": "run", "key": rec["run_id"], "task": rec["task"], "arm": rec["arm"],
                   "set": t["set"]}
            if t["set"] == "K":
                g = G.grade(t, rec.get("result") or "")
            elif t["set"] == "W+":
                text = write_text(rec)
                if not text:
                    g = {"verdict": "fail", "evidence_quote": "", "reason": "no write call",
                         "quote_ok": None}
                else:
                    g = G.grade({**t, "decisive_fact": t["decision_stated"]}, text)
            else:
                continue
            out.write(json.dumps({**row, **g}) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
