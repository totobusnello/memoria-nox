#!/usr/bin/env python3
"""v3.2 §4.1: index every git-archived served brief (window plus 3 days before, for BS) and report the
item turnover between consecutive snapshots. Read-only on git. Writes /root/medicoes/7b/snapshots.jsonl."""
import json
import os
import subprocess
import sys
from statistics import median

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.snapshots import FILES, build_index, turnover  # noqa: E402

WS = "/root/.openclaw/workspace"
SINCE, UNTIL = "2026-09-18T00:00:00Z", "2026-10-15T00:00:00Z"
OUT = "/root/medicoes/7b/snapshots.jsonl"


def git(*args):
    return subprocess.run(["git", "-C", WS, *args], capture_output=True, text=True, check=True).stdout


def main():
    entries = []
    for persona, rel in FILES.items():
        for sha in git("log", f"--since={SINCE}", f"--until={UNTIL}", "--format=%H", "--", rel).split():
            entries.append((persona, git("show", f"{sha}:{rel}")))
    idx = build_index(entries)
    with open(OUT, "w", encoding="utf-8") as f:
        for persona, snaps in idx.items():
            for s in snaps:
                f.write(json.dumps({"persona": persona, "text": s["text"]}, ensure_ascii=False) + "\n")
    report = {}
    for persona, snaps in sorted(idx.items()):
        t = [turnover(a, b) for a, b in zip(snaps, snaps[1:])]
        report[persona] = {"snapshots": len(snaps), "first": snaps[0]["generated_at"], "last": snaps[-1]["generated_at"],
                           "turnover_median": median(t) if t else None, "turnover_max": max(t) if t else None}
    json.dump(report, open("/root/medicoes/7b/snapshot-report.json", "w"), indent=1)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
