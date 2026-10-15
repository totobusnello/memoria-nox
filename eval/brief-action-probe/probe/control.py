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
