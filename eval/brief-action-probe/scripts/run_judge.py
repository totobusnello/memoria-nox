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
