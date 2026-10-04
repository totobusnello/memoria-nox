#!/usr/bin/env python3
"""§5.7.2 comparability control at IDENTITY level, not count level.

Why this exists
---------------
§5.7.2 validates that the 30/08 corpus is comparable to the published 26/08 one
by showing the no-exclusion arm returns 17/350 on both. The same section shows
(17 vs 13 sensitive states, 1 in common) that equal totals can hide nearly
disjoint sets. A count-level control is therefore the kind of evidence the
section itself disqualifies.

This script replaces it with a content-level control over artifacts that
already exist on disk (no replay is rerun, no DB is opened):

  L1  state key      (ts, agent, rowid_corte) equal, element by element, 350/350
  L2  sensitive set  the SET of states with churn > 0 is identical (not just its size)
  L3  per-state      would_enter / would_leave / churn identical in every one of the 350
  L4  control arm    ids_controle_replay (the top-10 served WITHOUT dose) identical
                     as ordered lists in 350/350 -- this is the arm that depends on
                     corpus + serve_state and NOT on the dose, so it isolates the
                     corpus swap from the intervention

Pairs compared (corpus 26/08 = e20260826T060003Z.db, corpus 30/08 = e20260830T060001Z.db):

  A  out/gran-seg.json            26/08, dose w=100000, granularity seg, no exclusion
  A' out/dose-350-v3.json         26/08, dose sweep; the w=100000 slice
  B  out/CEILING-PROBE-EXCLUSION-none-2026-08-30.json   30/08, w=100000, seg, no exclusion
  C  out/c-350-v3.json            26/08, mode campo (w=2); carries ids_controle_replay
  P  out/CEILING-PROBE-EXCLUSION-probes-2026-08-30.json 30/08, probes excluded

L4 uses C vs B because A/A' do not record ids_controle_replay. The control arm
is dose-independent by construction (it is the w=0 ranking), so comparing the
w=2 run's control list with the w=100000 run's control list is legitimate; the
script ALSO checks that inside the 26/08 corpus two runs at different doses
(C vs out/sens-01.json, which carries the field) give the same control lists --
a positive check that the field really is dose- and designation-independent.

Negative control: the probes arm P MUST fail L2 against B (the paper reports
1 sensitive state in common). If it does not, the comparison is blind.

Exit 0 = identity-level comparability holds; 1 = it fails; 2 = instrument fault.
"""
import json
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def load(name, section):
    with open(os.path.join(OUT, name), encoding="utf-8") as fh:
        d = json.load(fh)
    return d["procedencia"], d[section]["detalhe"]


def key(r):
    return (r["ts"], r["agent"], r["rowid_corte"])


def sensitive(rows):
    return {i for i, r in enumerate(rows) if r["churn"] > 0}


def main():
    pa, A = load("gran-seg.json", "dose")
    pd, Dall = load("dose-350-v3.json", "dose")
    D = [r for r in Dall if r["w"] == 100000]
    pb, B = load("CEILING-PROBE-EXCLUSION-none-2026-08-30.json", "dose")
    pc, C = load("c-350-v3.json", "campo")
    pp, P = load("CEILING-PROBE-EXCLUSION-probes-2026-08-30.json", "dose")
    ps, S = load("sens-01.json", "dose")

    res = {"pares": {}, "procedencia": {}}
    for nome, p in (("A gran-seg", pa), ("A' dose-350-v3", pd), ("B none-30/08", pb),
                    ("C c-350-v3", pc), ("P probes-30/08", pp), ("S sens-01", ps)):
        res["procedencia"][nome] = {k: p.get(k) for k in (
            "corpus", "corpus_sha256_primeiros_1MB", "designacao_sha256",
            "sondas_excluidas", "granularidade_last_served", "fonte_brief_ts_sha256",
            "corte_serve_state", "gerado_em")}

    for n, rows in (("A", A), ("A'", D), ("B", B), ("C", C), ("P", P), ("S", S)):
        if len(rows) != 350:
            print(f"instrument fault: {n} has {len(rows)} states, expected 350", file=sys.stderr)
            return 2

    # corpora must actually differ, otherwise this is not a cross-corpus check
    if pa["corpus_sha256_primeiros_1MB"] == pb["corpus_sha256_primeiros_1MB"]:
        print("instrument fault: A and B carry the same corpus hash", file=sys.stderr)
        return 2

    def compare(x, y, with_control=False):
        out = {}
        out["L1_state_key_equal"] = sum(key(a) == key(b) for a, b in zip(x, y))
        sx, sy = sensitive(x), sensitive(y)
        out["sensitive_x"], out["sensitive_y"] = len(sx), len(sy)
        out["sensitive_in_common"] = len(sx & sy)
        out["L2_sensitive_set_identical"] = sx == sy
        out["L3_per_state_identical"] = sum(
            (a["churn"], sorted(a["would_enter"]), sorted(a["would_leave"]))
            == (b["churn"], sorted(b["would_enter"]), sorted(b["would_leave"]))
            for a, b in zip(x, y))
        if with_control:
            out["L4_control_ordered_identical"] = sum(
                a["ids_controle_replay"] == b["ids_controle_replay"] for a, b in zip(x, y))
            out["L4_control_set_identical"] = sum(
                set(a["ids_controle_replay"]) == set(b["ids_controle_replay"]) for a, b in zip(x, y))
        out["sensitive_states"] = [
            {"i": i, "ts": x[i]["ts"], "agent": x[i]["agent"],
             "enter_x": x[i]["would_enter"], "leave_x": x[i]["would_leave"],
             "enter_y": y[i]["would_enter"], "leave_y": y[i]["would_leave"]}
            for i in sorted(sx | sy)]
        return out

    res["pares"]["A_vs_B (26/08 vs 30/08, dose arm)"] = compare(A, B)
    res["pares"]["A'_vs_B (26/08 sweep slice vs 30/08)"] = compare(D, B)
    res["pares"]["C_vs_B (26/08 vs 30/08, control arm)"] = compare(C, B, with_control=True)
    res["pares"]["C_vs_S (same corpus, other dose+designation; positive check on L4)"] = compare(C, S, with_control=True)
    res["pares"]["B_vs_P (negative control: exclusion must break identity)"] = compare(B, P, with_control=True)

    ab = res["pares"]["A_vs_B (26/08 vs 30/08, dose arm)"]
    cb = res["pares"]["C_vs_B (26/08 vs 30/08, control arm)"]
    cs = res["pares"]["C_vs_S (same corpus, other dose+designation; positive check on L4)"]
    bp = res["pares"]["B_vs_P (negative control: exclusion must break identity)"]

    # instrument checks
    if bp["L2_sensitive_set_identical"] or bp["sensitive_in_common"] != 1:
        print("NEGATIVE CONTROL FAILED: probes arm does not break identity as published "
              f"(in common = {bp['sensitive_in_common']})", file=sys.stderr)
        return 2
    if cs["L4_control_ordered_identical"] != 350:
        print("POSITIVE CHECK FAILED: control arm differs across dose/designation inside "
              "one corpus => L4 does not isolate the corpus", file=sys.stderr)
        return 2

    ok = (ab["L1_state_key_equal"] == 350 and ab["L2_sensitive_set_identical"]
          and ab["L3_per_state_identical"] == 350
          and cb["L1_state_key_equal"] == 350
          and cb["L4_control_ordered_identical"] == 350)
    res["veredito"] = "IDENTITY-LEVEL COMPARABILITY HOLDS" if ok else "IDENTITY-LEVEL COMPARABILITY FAILS"

    dest = sys.argv[1] if len(sys.argv) > 1 else None
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if dest:
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")
    for k, v in res["pares"].items():
        print(k, {kk: vv for kk, vv in v.items() if kk != "sensitive_states"})
    print(res["veredito"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
