#!/usr/bin/env python3
"""§7: validate the 20 control scenarios against their units' archived B1 and freeze the arm files.
Index "last" resolves to the last B1 item (keeps the pinned high-pain items intact). Refuses to overwrite."""
import hashlib
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.control import plant, validate_scenario  # noqa: E402
from probe.corpus import load_turns  # noqa: E402
from probe.scaffold import assert_only_brief_differs, build_prompt, parse_template, read_bootstrap  # noqa: E402
from probe.snapshots import build_index, snapshot_at  # noqa: E402

R = "/root/medicoes/7b"
SCAFFOLD = "/root/medicoes/7b-scaffold/forge-2026-09-30T2231.system-prompt.md"


def main():
    if os.path.exists(f"{R}/control/owners.jsonl"):
        sys.exit("control already frozen")
    turns = {t["unit_id"]: t for t in load_turns("/root/.claude-nuvini-team/projects", "2026-09-21T00:00:00Z", "2026-10-15T00:00:00Z")}
    used = {json.loads(l)["unit_id"] for l in open(f"{R}/manifest.jsonl")}
    tpl = parse_template(open(SCAFFOLD, encoding="utf-8").read())
    idx = build_index((e["persona"], e["text"]) for e in map(json.loads, open(f"{R}/snapshots.jsonl", encoding="utf-8")))
    sc = [json.loads(l) for l in open(f"{R}/control/scenarios.jsonl", encoding="utf-8")]
    assert len(sc) == 20 and sum(s["kind"] == "decisive" for s in sc) == 10
    owners = []
    for s in sc:
        u = turns[s["unit_id"]]
        assert s["unit_id"] not in used, "control unit overlaps the manifest"
        t = u["ts"][:19].replace("T", " ")
        snap = snapshot_at(idx, u["agent"], t)
        lines = [i["line"] for i in snap["items"]]
        index = len(lines) - 1 if s["index"] == "last" else s["index"]
        validate_scenario(dict(s, index=index), u["text"], lines)
        files = read_bootstrap(u["agent"])
        arms = {"B1": snap["text"], "BP": plant(snap["text"], index, s["line"])}
        texts = {a: build_prompt(tpl, u["agent"], files, x, t[:10], False) for a, x in arms.items()}
        assert_only_brief_differs(texts, u["agent"])
        for a, x in texts.items():
            p = f"{R}/control/arms/{s['scenario_id']}/{a}.md"
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(x)
        open(f"{R}/control/inputs-{s['scenario_id']}.txt", "w", encoding="utf-8").write(u["text"])
        owners.append({"scenario_id": s["scenario_id"], "agent": u["agent"], "index": index})
    with open(f"{R}/control/owners.jsonl", "w") as f:
        for o in owners:
            f.write(json.dumps(o) + "\n")
    print("20 control scenarios validated and frozen",
          hashlib.sha256(open(f"{R}/control/scenarios.jsonl", "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
