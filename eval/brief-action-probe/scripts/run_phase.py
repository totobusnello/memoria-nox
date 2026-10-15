#!/usr/bin/env python3
"""Runs a phase: pilot (B1 × 4), main (B0/B1/BS × 2), control (B1/BP × 2). Resumable: units already
complete in results-<phase>.jsonl are skipped. Run inside tmux; serial by design. Same subscription as
the agents (spec v3.3 §4): units are spaced 300 s apart and the phase stops at the first rate-limit."""
import argparse
import hashlib
import json
import os
import random
import sys
import time

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.runner import RateLimited, oauth_token, run_unit  # noqa: E402
from probe.scaffold import agent_root  # noqa: E402

R = "/root/medicoes/7b"
REPS = {"pilot": 4, "main": 2, "control": 2}
SPACING_S = 300


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


def seed_of(uid):
    return int(hashlib.sha256(f"20261014:{uid}".encode()).hexdigest()[:8], 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=sorted(REPS))
    a = ap.parse_args()
    out = f"{R}/results-{a.phase}.jsonl"
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["unit_id"] for l in open(out)}
    token = oauth_token()
    todo = list(units_for(a.phase))
    random.Random(20261014).shuffle(todo)
    for uid, arms, text, agent in todo:
        if uid in done:
            continue
        cwd = agent_root(agent) if agent else R
        try:
            res = run_unit(uid, arms, text, cwd, f"{R}/runs/{a.phase}", REPS[a.phase], random.Random(seed_of(uid)), token=token)
        except RateLimited as e:
            print(f"RATE LIMIT at {e}; phase stopped (resume with the same command)", flush=True)
            sys.exit(3)
        with open(out, "a") as f:
            for r in res:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(time.strftime("%H:%M:%S"), uid, sum(r["ok"] for r in res), "/", len(res), flush=True)
        time.sleep(SPACING_S)
    print("phase complete", flush=True)


if __name__ == "__main__":
    main()
