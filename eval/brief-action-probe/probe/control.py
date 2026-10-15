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


def score_control(rows, scenarios):
    """§7: decisive/typical scenario hits, decisive false hits, pass and nulls_informative."""
    cm = {}
    for r in rows:
        if r["ok"]:
            cm.setdefault(r["unit_id"], {}).setdefault(r["arm"], []).append(r["message"])
    hits = {"decisive": 0, "typical": 0}
    false = 0
    for s in scenarios:
        bp, b1 = cm.get(s["scenario_id"], {}).get("BP", []), cm.get(s["scenario_id"], {}).get("B1", [])
        if len(bp) == 2 and scenario_hit(bp, s["planted"], s["superseded"]):
            hits[s["kind"]] += 1
        if s["kind"] == "decisive" and false_hit(b1, s["planted"]):
            false += 1
    out = {"decisive_hits": hits["decisive"], "typical_hits": hits["typical"], "false_hits": false,
           "pass": hits["decisive"] >= 7 and false <= 1, "runs_ok": sum(r["ok"] for r in rows)}
    out["nulls_informative"] = out["pass"] and hits["typical"] >= 3
    return out
