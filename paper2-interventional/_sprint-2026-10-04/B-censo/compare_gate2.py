#!/usr/bin/env python3
"""Gate 2 comparison: September 3-family verdicts vs the 2026-10-05 re-run, on gate2-ids.txt.
Rules as declared in GATE-RULES-PREDECLARED.md. Writes gate2-compare.json (no episode text)."""
import collections, json, math, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # paper2-interventional/
from pilot_replay import carregar_verdicts

B = Path(__file__).resolve().parent
ids = [l.strip() for l in (B / "gate2-ids.txt").read_text().splitlines() if l.strip()]
S = set(ids)
SEP = Path.home() / ".paper2-verdicts/ensaio-20260921-PRIMARIO-3fam.jsonl"
NEW = B / "raw/gate2-verdicts.jsonl"
PANEL = ("zhipu", "xai", "google")

def rows(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]

def first_ok(rs):
    d = {}
    for r in rs:
        if r["episode_id"] in S and r["status"] == "ok":
            d.setdefault((r["episode_id"], r["panelist"]), r)
    return d

def outcome(rs):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as t:
        for r in rs:
            if r["episode_id"] in S and r["panelist"] in PANEL:
                t.write(json.dumps(r) + "\n")
    o = carregar_verdicts(Path(t.name)); Path(t.name).unlink()
    return {i: o.get(i, "unknown") for i in ids}

def wilson(k, n, z=1.96):
    if n == 0: return None
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return [round((c-h)/d, 4), round((c+h)/d, 4)]

sep_rows, new_rows = rows(SEP), rows(NEW)
sep, new = first_ok(sep_rows), first_ok(new_rows)
res = {"n_episodes": len(ids), "per_provider": {}}
for pid in PANEL:
    pairs = [(sep[(i, pid)], new[(i, pid)]) for i in ids if (i, pid) in sep and (i, pid) in new]
    same = sum(a["verdict"] == b["verdict"] for a, b in pairs)
    same_lvl = sum(a["verdict"] == b["verdict"] and a["level"] == b["level"] for a, b in pairs)
    trans = collections.Counter(f'{a["verdict"]}/{a["level"]} -> {b["verdict"]}/{b["level"]}'
                                for a, b in pairs if (a["verdict"], a["level"]) != (b["verdict"], b["level"]))
    res["per_provider"][pid] = {
        "pairs_compared": len(pairs), "label_agree": same,
        "label_agreement": round(same / len(pairs), 4) if pairs else None,
        "label_wilson95": wilson(same, len(pairs)),
        "label_changes": [{"episode_id": a["episode_id"], "sep": a["verdict"], "new": b["verdict"],
                           "sep_level": a["level"], "new_level": b["level"]}
                          for a, b in pairs if a["verdict"] != b["verdict"]],
        "level_agree": same_lvl, "level_agreement": round(same_lvl / len(pairs), 4) if pairs else None,
        "level_transitions": dict(trans),
        "abstain_sep": sum(1 for i in ids if sep.get((i, pid), {}).get("verdict") == "abstain"),
        "abstain_new": sum(1 for i in ids if new.get((i, pid), {}).get("verdict") == "abstain"),
        "not_ok_sep": sum(1 for i in ids if (i, pid) not in sep),
        "not_ok_new": sum(1 for i in ids if (i, pid) not in new),
        "model_served_sep": dict(collections.Counter(r.get("model_served") for r in sep_rows
                                  if r["episode_id"] in S and r["panelist"] == pid)),
        "model_served_new": dict(collections.Counter(r.get("model_served") for r in new_rows
                                  if r["episode_id"] in S and r["panelist"] == pid)),
        "verdicts_sep": dict(collections.Counter(sep[(i, pid)]["verdict"] for i in ids if (i, pid) in sep)),
        "verdicts_new": dict(collections.Counter(new[(i, pid)]["verdict"] for i in ids if (i, pid) in new)),
    }
o_sep, o_new = outcome(sep_rows), outcome(new_rows)
agree = sum(o_sep[i] == o_new[i] for i in ids)
res["panel_outcome"] = {
    "rule": "pilot_replay.carregar_verdicts, tau=S1, strict majority, abstain absent, <3 substantive -> unknown; 3 families",
    "agree": agree, "agreement": round(agree / len(ids), 4), "wilson95": wilson(agree, len(ids)),
    "sep": dict(collections.Counter(o_sep.values())), "new": dict(collections.Counter(o_new.values())),
    "changes": [{"episode_id": i, "sep": o_sep[i], "new": o_new[i]} for i in ids if o_sep[i] != o_new[i]],
}
(B / "gate2-compare.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
print(json.dumps(res, indent=1, sort_keys=True))
