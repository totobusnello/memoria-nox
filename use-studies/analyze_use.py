#!/usr/bin/env python3
"""Analysis for the use studies, written before any bank run (PREREGISTRATION.md sections 6-7).

  analyze_use.py W   # study W: runs/W-main, grading/W-main.graded.jsonl
  analyze_use.py S   # study S: runs/S-main + the 2026-11-07 runs v1-main (S0) and v1-T2 (T2-hand)

Unit: the task. Per task, the rate over its replicas; a contrast is the mean over tasks of the
per-task difference; 95% CI by bootstrap over tasks (10,000 resamples, seed 1). Same code shape
as the 2026-11-07 analysis (analyze_T2.py).
"""
import collections
import json
import random
import statistics
import sys
from pathlib import Path

EV = Path.home() / "nox-skill-eval"
WRITE_TOOLS = {"nox_mem_decision_set", "nox_mem_ingest", "nox_mem_crystallize"}
BUILTIN = {"Bash", "Read", "Grep", "Glob", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch",
           "Task", "Agent"}
EXCL = {"K08", "K12", "K15", "K38"}  # leakage screen of 2026-11-07 (arm N), unchanged
MODEL = "claude-sonnet-5-5"


def load(path, arm=None):
    rows = []
    for l in open(path):
        if l.strip():
            r = json.loads(l)
            if arm:
                r["arm"] = arm
            rows.append(r)
    return rows


def grades(*paths):
    g = {}
    for p in paths:
        if Path(p).exists():
            for l in open(p):
                if l.strip():
                    x = json.loads(l)
                    g[x["key"]] = x
    return g


def per_task(rows, f):
    d = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        v = f(r)
        if v is not None:
            d[r["task"]][r["arm"]].append(v)
    return d


def boot(d, A, B, n=10000, seed=1):
    ts = sorted(t for t in d if d[t][A] and d[t][B])
    dl = [statistics.mean(d[t][A]) - statistics.mean(d[t][B]) for t in ts]
    if not dl:
        return None
    rng = random.Random(seed)
    bs = sorted(statistics.mean(dl[rng.randrange(len(dl))] for _ in dl) for _ in range(n))
    return {"delta": round(statistics.mean(dl), 3), "lo": round(bs[int(.025 * n)], 3),
            "hi": round(bs[int(.975 * n) - 1], 3), "tasks": len(dl),
            "up": sum(x > 0 for x in dl), "down": sum(x < 0 for x in dl)}


def rate(rows, f):
    v = [f(r) for r in rows]
    v = [x for x in v if x is not None]
    return (round(sum(v) / len(v), 3), len(v)) if v else (None, 0)


def builtin_ran(r):
    # a built-in tool call counts as a leak; with --disallowedTools it is answered "No such tool"
    return [c["name"] for c in r.get("tool_calls") or [] if c["name"] in BUILTIN]


def gates(rows, arms):
    out = {}
    for a in arms:
        rs = [r for r in rows if r["arm"] == a]
        fail = sum(1 for r in rs if str(r["rc"]) != "0" or str(r.get("is_error")) == "True")
        out[a] = {"runs": len(rs),
                  "model_ok": all(r["model"] == MODEL for r in rs),
                  "connection_fail_rate": round(fail / len(rs), 3) if rs else None,
                  "instrument_agree": all(str(r["instrument_agree"]) == "True" for r in rs),
                  "builtin_calls": sum(bool(builtin_ran(r)) for r in rs)}
    return out


def study_w():
    rows = load(EV / "runs" / "W-main" / "results.jsonl")
    g = grades(EV / "grading" / "W-main.graded.jsonl")
    arms = ["W0", "WH", "WN", "WP"]
    wrote = lambda r: 1 if int(float(r["write_calls"])) > 0 else 0

    def content(r):
        x = g.get(r["run_id"])
        if x is None or x["verdict"] in ("grader_invalid", "error"):
            return None
        return 1 if x["verdict"] == "pass" else 0

    wp = [r for r in rows if r["set"] == "W+"]
    wm = [r for r in rows if r["set"] == "W-"]
    rep = {"gates": gates(rows, arms), "rates": {}, "contrasts": {}, "decision": {}}
    for a in arms:
        rep["rates"][a] = {"W+ content": rate([r for r in wp if r["arm"] == a], content),
                           "W+ wrote": rate([r for r in wp if r["arm"] == a], wrote),
                           "W- wrote": rate([r for r in wm if r["arm"] == a], wrote)}
    dc, dw = per_task(wp, content), per_task(wm, wrote)
    ceiling = rep["rates"]["WP"]["W+ content"][0]
    rep["ceiling_ok"] = ceiling is not None and ceiling >= 0.70
    for a in ("WH", "WN"):
        c, n = boot(dc, a, "W0"), boot(dw, a, "W0")
        rep["contrasts"][a] = {"W+ content vs W0": c, "W- wrote vs W0": n}
        if not rep["ceiling_ok"] or not all(v["model_ok"] for v in rep["gates"].values()):
            verdict = "not interpreted (a gate failed)"
        elif c and c["lo"] > 0 and n and n["delta"] <= 0.15:
            verdict = "works"
        elif c and c["hi"] < 0:
            verdict = "hurts"
        else:
            verdict = "no detectable effect over W0"
        rep["decision"][a] = verdict
    return rep


def study_s(sd_path=None, sd_arm=None):
    rows = load(sd_path or EV / "runs" / "S-main" / "results.jsonl", arm=sd_arm)
    old = [r for r in load(EV / "runs" / "v1-main" / "results.jsonl") if r["arm"] == "S0"]
    old += load(EV / "runs" / "v1-T2" / "results.jsonl", arm="T2")
    allr = rows + old
    g = grades(EV / "grading" / "S-main.graded.jsonl", EV / "grading" / "v1-main.graded.jsonl",
               EV / "grading" / "v1-T2.graded.jsonl")

    def passed(r):
        x = g.get(r["run_id"])
        if x is None or x["verdict"] in ("grader_invalid", "error"):
            return None
        return 1 if x["verdict"] == "pass" else 0

    searched = lambda r: 1 if int(float(r["search_calls"])) > 0 else 0  # H1 of 2026-11-07: nox_mem_search
    K = [r for r in allr if r["set"] == "K" and r["task"] not in EXCL]
    Gs = [r for r in allr if r["set"] == "G"]
    rep = {"gates": gates(rows, ["SD"]), "rates": {}, "contrasts": {}}
    for a in ("S0", "T2", "SD"):
        rep["rates"][a] = {"K pass": rate([r for r in K if r["arm"] == a], passed),
                           "K searched": rate([r for r in K if r["arm"] == a], searched),
                           "G false trigger": rate([r for r in Gs if r["arm"] == a], searched)}
    dk, dg = per_task(K, passed), per_task(Gs, searched)
    rep["contrasts"] = {"SD - T2 (K pass)": boot(dk, "SD", "T2"), "SD - S0 (K pass)": boot(dk, "SD", "S0"),
                        "SD - S0 (G false trigger)": boot(dg, "SD", "S0")}
    c_t2, c_s0, c_g = (rep["contrasts"][k] for k in rep["contrasts"])
    gate_ok = all(v["model_ok"] for v in rep["gates"].values())
    if not gate_ok:
        rep["decision"] = "not interpreted (a gate failed)"
    elif c_t2 and c_t2["lo"] > -0.10 and c_s0 and c_s0["lo"] > 0 and c_g and c_g["delta"] <= 0.15:
        rep["decision"] = "derived scope works as well as the hand-written one (margin 0.10)"
    elif c_s0 and c_s0["lo"] > 0 and c_g and c_g["delta"] <= 0.15:
        rep["decision"] = "derived scope beats no instructions but is not shown within 0.10 of the hand-written one"
    else:
        rep["decision"] = "derived scope fails the T2 rule"
    return rep


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in ("W", "S"):
        sys.exit(__doc__)
    print(json.dumps(study_w() if which == "W" else study_s(), indent=1))
