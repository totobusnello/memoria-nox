#!/usr/bin/env python3
"""§6–7 decisions, exactly as pre-registered. Writes out/aggregates.json (no session content)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from probe.canon import divergence, serialize  # noqa: E402
from probe.control import score_control  # noqa: E402
from probe.judge import score  # noqa: E402
from probe.stats import (cluster_bootstrap, fisher_2x2, holm, one_sided_p, percentile_ci,  # noqa: E402
                         stratum_estimate, tost_proportion)

R = "/root/medicoes/7b"
ARMS = ("B0", "B1", "BS")


def unit_deltas(msgs):
    if any((a, r) not in msgs for a in ARMS for r in (1, 2)):
        return None
    s = {k: serialize(v) for k, v in msgs.items()}
    aa = sum(divergence(s[(a, 1)], s[(a, 2)]) for a in ARMS) / 3

    def D(x, y):
        return sum(divergence(s[(x, i)], s[(y, j)]) for i in (1, 2) for j in (1, 2)) / 4

    return {"aa": aa, "dp": D("B1", "B0") - aa, "dc": D("B1", "BS") - aa}


def decide(by, params, inconclusive, seed=11):
    out, raw, stats = {}, {}, {}
    for s in ("C", "H"):
        if not params["valid"][s]:
            out[s] = {"invalid": True}
            raw[f"{s}.dp"] = raw[f"{s}.dc"] = 1.0
            continue
        out[s] = {}
        for k in ("dp", "dc"):
            name = f"{s}.{k}"
            est = stratum_estimate(by[s][k])
            draws = cluster_bootstrap(by[s][k], 10000, seed)
            lo, hi = percentile_ci(draws)
            stats[name] = (est, lo, hi)
            raw[name] = 1.0 if name in inconclusive else one_sided_p(draws)
    adj = holm(raw)
    for s in ("C", "H"):
        if out[s].get("invalid"):
            continue
        for k in ("dp", "dc"):
            name = f"{s}.{k}"
            est, lo, hi = stats[name]
            eff = adj[name] < 0.05
            row = {"estimate": est, "ci95": [lo, hi], "p": raw[name], "p_holm": adj[name], "effect": eff,
                   "inconclusive": name in inconclusive, "mde": params["mde"][s]}
            if not eff and not row["inconclusive"] and lo <= 0 <= hi:
                mde = params["mde"][s]
                row["null_reading"] = ("effects >= MDE excluded" if mde is not None and hi < mde
                                       else "underpowered for effects of MDE size")
            out[s][k] = row
    out["holm_raw"], out["holm"] = raw, adj
    return out


def main():
    params = json.load(open(f"{R}/params.json"))
    man = {u["unit_id"]: u for u in map(json.loads, open(f"{R}/manifest.jsonl"))}
    runs = list(map(json.loads, open(f"{R}/results-main.jsonl")))
    msgs, fails = {}, {}
    for r in runs:
        st = man[r["unit_id"]]["stratum"]
        fails.setdefault(st, {a: [0, 0] for a in ARMS})[r["arm"]][0 if r["ok"] else 1] += 1
        if r["ok"]:
            msgs.setdefault(r["unit_id"], {})[(r["arm"], r["rep"])] = r["message"]
    # §4 failure branch: 2×2 Fisher per arm vs the other two pooled.
    inconclusive, fisher = set(), {}
    for st in ("C", "H"):
        f = fails.get(st, {a: [0, 0] for a in ARMS})
        for a in ARMS:
            ok_o = sum(f[b][0] for b in ARMS if b != a)
            bad_o = sum(f[b][1] for b in ARMS if b != a)
            p = fisher_2x2(f[a][0], f[a][1], ok_o, bad_o)
            fisher[f"{st}.{a}"] = p
            if p < 0.05:
                if a in ("B1", "B0"):
                    inconclusive.add(f"{st}.dp")
                if a in ("B1", "BS"):
                    inconclusive.add(f"{st}.dc")
    by, leak_by, units_used, r_desc = {}, {}, {}, []
    for uid, m in msgs.items():
        u = man[uid]
        d = unit_deltas(m)
        if d is None:
            continue
        if u["stratum"] == "R":
            r_desc.append(d)
            continue
        if u["stratum"] not in ("C", "H"):
            continue
        units_used[u["stratum"]] = units_used.get(u["stratum"], 0) + 1
        for k in ("dp", "dc"):
            by.setdefault(u["stratum"], {"dp": {}, "dc": {}})[k].setdefault(u["cluster"], []).append(d[k])
            if not u["leak_flag"]:
                leak_by.setdefault(u["stratum"], {"dp": {}, "dc": {}})[k].setdefault(u["cluster"], []).append(d[k])
    primary = decide(by, params, inconclusive)
    sensitivity = decide(leak_by, params, inconclusive) if all(s in leak_by for s in ("C", "H")) else None
    # §6.2
    js = list(map(json.loads, open(f"{R}/judgments.jsonl")))
    main_j = [j for j in js if not j["known_answer"]]
    nontie = [j for j in main_j if j["verdict"] != "tie"]
    k_a = sum(1 for j in nontie if j["verdict"] == "A")
    pos_ok, p_lo, p_hi = tost_proportion(k_a, len(nontie))
    known = [j for j in js if j["known_answer"]]
    known_ok = sum(1 for j in known if j["winner_arm"] == "original")
    gates = {"position": {"k_A": k_a, "n": len(nontie), "pass": pos_ok, "p_low": p_lo, "p_high": p_hi},
             "known_answer": {"correct": known_ok, "n": len(known), "pass": known_ok >= 17}}
    judged = {}
    for st in ("C", "H", "R"):
        judged[st] = {}
        for contrast, first in (("B1r1xB0r1", "B1r1"), ("B1r1xBSr1", "B1r1"), ("B0r1xBSr1", "B0r1"),
                                ("B1r1xB1r2", "B1r1")):
            cl = {}
            for j in main_j:
                if j["contrast"] == contrast and man[j["unit_id"]]["stratum"] == st:
                    cl.setdefault(man[j["unit_id"]]["cluster"], []).append(score(j["winner_arm"], first))
            if not cl:
                continue
            draws = cluster_bootstrap(cl, 10000, 13)
            judged[st][contrast] = {"score": stratum_estimate(cl), "ci95": list(percentile_ci(draws)), "n_clusters": len(cl)}
        if st in ("C", "H") and gates["position"]["pass"] and gates["known_answer"]["pass"]:
            judged[st]["helps"] = all(judged[st].get(c, {"ci95": [0, 0]})["ci95"][0] > 0.5
                                      for c in ("B1r1xB0r1", "B1r1xBSr1"))
    # §7
    ctrl = list(map(json.loads, open(f"{R}/results-control.jsonl")))
    sc = {s["scenario_id"]: s for s in map(json.loads, open(f"{R}/control/scenarios.jsonl", encoding="utf-8"))}
    control = score_control(ctrl, list(sc.values()))
    rel = [json.loads(l) for l in open(f"{R}/relevance.jsonl")]
    summary = json.load(open(f"{R}/manifest-summary.json"))
    agg = {"params": {k: params[k] for k in ("pilot_aa", "valid", "mde", "canon_sha256", "manifest_sha256")},
           "units_used": units_used, "fisher": fisher, "inconclusive": sorted(inconclusive),
           "primary": primary, "leak_sensitivity": sensitivity, "judge_gates": gates, "judged": judged,
           "control": control, "R_descriptive": {"n": len(r_desc), **({k: sum(d[k] for d in r_desc) / len(r_desc)
                                                                       for k in ("aa", "dp", "dc")} if r_desc else {})},
           "h_relevance_rate": sum(r["present"] for r in rel) / len(rel) if rel else None,
           "bs_drop_rate": summary["bs_drop_rate"],
           "b1_gap_hours": summary.get("b1_gap_hours"),
           "snapshot_turnover": {p: v["turnover_median"] for p, v in json.load(open(f"{R}/snapshot-report.json")).items()},
           "leak_flagged": summary.get("leak_flagged"),
           "bs_drop_flag": {s: v > 0.20 for s, v in summary["bs_drop_rate"].items()},
           "drops": summary["drops"]}
    json.dump(agg, open(f"{R}/aggregates.json", "w"), indent=1)
    print(json.dumps({"primary": primary, "gates": gates, "control": control}, indent=1))


if __name__ == "__main__":
    main()
