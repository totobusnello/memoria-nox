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
