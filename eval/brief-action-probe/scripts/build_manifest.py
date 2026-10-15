#!/usr/bin/env python3
"""Freeze units, B1, BS and arm files (spec v3.3 §2, §3, §4, §4.1). Refuses to overwrite.

B1 is the git-archived served snapshot (scripts/snapshot_index.py output), verbatim; BS is built from
other agents' snapshots served in [t − 3 d, t] (probe.snapshots).
"""
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone
from statistics import median

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.corpus import build_strata, load_turns  # noqa: E402
from probe.scaffold import assert_only_brief_differs, build_prompt, parse_template, read_bootstrap  # noqa: E402
from probe.sham import build_sham, common_tokens, filter_candidates, item_tokens  # noqa: E402
from probe.snapshots import block, build_index, candidate_items, snapshot_at  # noqa: E402

ROOT = "/root/medicoes/7b"
SCAFFOLD = "/root/medicoes/7b-scaffold/forge-2026-09-30T2231.system-prompt.md"
SCAFFOLD_SHA = "7b4b0820009bc170d178e0ce8bf16af5780a9d394e90bf678b2addee0dffb75c"
START, END = "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z"
SEED = 20261014
LEAK = 0.5
FMT = "%Y-%m-%d %H:%M:%S"


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def stable_seed(unit_id):
    # Python's hash() of str changes per process (PYTHONHASHSEED); seeds must be reproducible.
    return int(sha(f"{SEED}:{unit_id}")[:8], 16)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def hours(a, b):
    return (datetime.strptime(a, FMT) - datetime.strptime(b, FMT)).total_seconds() / 3600


def draw_t(rng, idx, agent):
    lo = datetime(2026, 9, 21, tzinfo=timezone.utc).timestamp()
    hi = datetime(2026, 10, 15, tzinfo=timezone.utc).timestamp()
    for redraw in range(100):
        t = datetime.fromtimestamp(rng.uniform(lo, hi), timezone.utc).strftime(FMT)
        if snapshot_at(idx, agent, t):
            return t, redraw
    raise RuntimeError(f"no snapshot for {agent} in window")


def main():
    if os.path.exists(f"{ROOT}/manifest.jsonl"):
        sys.exit("manifest exists: frozen")
    raw = open(SCAFFOLD, encoding="utf-8").read()
    assert sha(raw) == SCAFFOLD_SHA, "scaffold hash mismatch"
    tpl = parse_template(raw)
    idx = build_index((e["persona"], e["text"]) for e in map(json.loads, open(f"{ROOT}/snapshots.jsonl", encoding="utf-8")))
    rng = random.Random(SEED)
    turns = load_turns("/root/.claude-nuvini-team/projects", START, END)
    strata = build_strata(turns, seed=SEED)
    units = [dict(u, stratum=s, cluster=(u["unit_id"] if s == "R" else u["template"]),
                  t=u["ts"][:19].replace("T", " "), input=u["text"]) for s in ("C", "R", "pilot_C") for u in strata[s]]
    redraws = 0
    for h in (json.loads(l) for l in open(f"{ROOT}/h_requests.jsonl", encoding="utf-8")):
        t, r = draw_t(rng, idx, h["owner_agent"])
        redraws += r
        units.append({"unit_id": h["h_id"], "stratum": "H" if h["set"] == "main" else "pilot_H",
                      "cluster": h["source_task"], "agent": h["owner_agent"], "t": t, "input": h["request"]})
    # Frozen common-token set: tokens in >= 5% of distinct served items in the index.
    texts = {}
    for snaps in idx.values():
        for s in snaps:
            for i in s["items"]:
                texts.setdefault(i["id"], i["text"])
    common = common_tokens(list(texts.values()))
    boot = {a: read_bootstrap(a) for a in {u["agent"] for u in units}}
    drops, bs_drops, kept, gaps = {}, {}, [], {}
    for u in units:
        snap = snapshot_at(idx, u["agent"], u["t"])
        if snap is None:
            drops["no_b1"] = drops.get("no_b1", 0) + 1
            continue
        b1_items = [dict(i, created_at=snap["generated_at"]) for i in snap["items"]]
        arms = {"B1": snap["text"]}
        bs_ids = None
        if not u["stratum"].startswith("pilot"):
            cands = candidate_items(idx, u["agent"], u["t"], seed=stable_seed(u["unit_id"]))
            filt = filter_candidates(cands, b1_items, u["t"], common)
            mk = lambda w: block(snap["agent_label"], snap["scope"], snap["generated_iso"], [x["line"] for x in w])
            win = build_sham(filt, len(b1_items), len(snap["text"]), lambda w: len(mk(w)))
            if win is None:
                bs_drops[u["stratum"]] = bs_drops.get(u["stratum"], 0) + 1
                continue
            bs_ids = [x["id"] for x in win]
            arms["BS"] = mk(win)
            arms["B0"] = None
        files = boot[u["agent"]]
        texts_by_arm = {a: build_prompt(tpl, u["agent"], files, blk, u["t"][:10], u["stratum"] == "R")
                        for a, blk in arms.items()}
        assert_only_brief_differs(texts_by_arm, u["agent"])
        boot_toks = item_tokens(" ".join(files.values())) - common

        def leaks(text):
            toks = item_tokens(text) - common
            return len(toks & boot_toks) / max(1, len(toks)) > LEAK

        leak = any(leaks(i["text"]) for i in b1_items)
        for a, text in texts_by_arm.items():
            write(f"{ROOT}/arms/{u['unit_id']}/{a}.md", text)
        write(f"{ROOT}/inputs/{u['unit_id']}.txt", u["input"])
        gaps.setdefault(u["stratum"], []).append(hours(u["t"], snap["generated_at"]))
        kept.append({"unit_id": u["unit_id"], "stratum": u["stratum"], "cluster": u["cluster"], "agent": u["agent"],
                     "t": u["t"], "input_sha256": sha(u["input"]), "b1_persona": u["agent"],
                     "b1_generated_iso": snap["generated_iso"], "b1_ids": [i["id"] for i in b1_items],
                     "bs_ids": bs_ids, "leak_flag": leak,
                     "arm_sha256": {a: sha(x) for a, x in texts_by_arm.items()}})
    with open(f"{ROOT}/manifest.jsonl", "w") as f:
        for k in kept:
            f.write(json.dumps(k) + "\n")
    by = {}
    for k in kept:
        by[k["stratum"]] = by.get(k["stratum"], 0) + 1
    summary = {"units": by, "drops": drops, "bs_drops": bs_drops, "h_redraws": redraws,
               "bs_drop_rate": {s: bs_drops.get(s, 0) / (by.get(s, 0) + bs_drops.get(s, 0))
                                for s in ("C", "R", "H") if by.get(s, 0) + bs_drops.get(s, 0)},
               "b1_gap_hours": {s: {"median": median(v), "max": max(v)} for s, v in gaps.items()},
               "leak_flagged": sum(k["leak_flag"] for k in kept),
               "common_tokens": len(common),
               "manifest_sha256": hashlib.sha256(open(f"{ROOT}/manifest.jsonl", "rb").read()).hexdigest()}
    json.dump(summary, open(f"{ROOT}/manifest-summary.json", "w"), indent=1)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
