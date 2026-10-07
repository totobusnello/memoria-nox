#!/usr/bin/env python3
"""Numbers added to Paper B in rc7 that no earlier artifact holds (sprint 2026-10-04, rc7).

Read-only on its inputs; writes one JSON (default: checks-rc7.json beside this file).
Each block aborts (exit 1) if a reproduced reference value from an existing artifact does
not match, so a wrong input path or a changed rule cannot pass silently.

  A  realized altered-brief share in treatment epochs, active vs shadow (Codex 5 / Fable M7)
     - membership semantics and epoch rule imported in spirit from controles_instrumento.py
       (set comparison, 09:00 UTC boundary); must reproduce the artifact's per-epoch
       `mexeu` (sum 337 over 7,392) before splitting by `modo`.
  B  coverage over active-mode briefs only (Fable LOW-10); must reproduce 2,068 / 7,392 and
     1,385 / 5,145 of COBERTURA-M10 before splitting.
  C  power: two-sided reach of `p1 > p0` and `09-01` by clock (Codex 6, Fable LOW-12), with
     poder_z / the harmonic effective size copied from measurement/potencia-h1c.py; must
     reproduce 84.8 and 91.49.
  D  adjudication submission vs three-substantive-verdict requirement (Codex 2), through
     pilot_replay.carregar_verdicts.
  E  concentration statistic of the planning corpus (Codex 1): 573 / 611.
  F  file time of ITT-PRELIMINAR.json and its H1a estimate (Fable M6).

Usage: python3 checks-rc7.py --ensaio <dir with p2-serving.ndjson, CONTROLES-*, ITT-*>
                             --verdicts <ensaio-20260921-PRIMARIO-3fam.jsonl> [--out X]
"""
import argparse
import collections
import datetime as dt
import json
import math
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P2 = HERE.parent.parent  # paper2-interventional/
sys.path.insert(0, str(P2))


def epoch_de(ts):
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (d - dt.timedelta(hours=9)).strftime("%Y-%m-%d")


def die(msg):
    sys.exit(f"ABORT {msg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensaio", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--out", default=str(HERE / "checks-rc7.json"))
    a = ap.parse_args()
    E = Path(a.ensaio)
    arm = {e["epoch_inicio"]: e["arm"] for e in json.loads((P2 / "ASSIGNMENT-SERVING.json").read_text())["epochs"]}
    dset = set(json.loads((E / "DESIGNATION-2026-08-26.json").read_text())["designados"].values())
    ctrl = json.loads((E / "CONTROLES-JANELA-COMPLETA-2026-09-21.json").read_text())
    cob = json.loads((E / "COBERTURA-M10-2026-09-21.json").read_text())
    out = {"gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}

    # ---- A and B: one pass over the serving log
    n = collections.Counter(); mex = collections.Counter()
    covn = collections.Counter(); covc = collections.Counter()
    per_ep = collections.Counter()
    for line in (E / "p2-serving.ndjson").open():
        o = json.loads(line)
        ep = epoch_de(o["ts"])
        if not ("2026-09-01" <= ep <= "2026-09-20") or ep not in arm:
            continue
        modo = o.get("modo")
        ic, it = o.get("ids_controle"), o.get("ids_tratado")
        if arm[ep] == "treatment":
            n[modo] += 1; per_ep[(ep, modo, "n")] += 1
            if ic is not None and it is not None and set(ic) != set(it):
                mex[modo] += 1; per_ep[(ep, modo, "mexeu")] += 1
        ids = it if o.get("servido") == "tratado" else ic
        if ids is not None:
            covn[(arm[ep], modo)] += 1
            if any(i in dset for i in ids):
                covc[(arm[ep], modo)] += 1
    ref_mex = sum(v["mexeu"] for v in ctrl["controle_positivo"]["por_epoch"].values())
    ref_n = sum(v["n"] for v in ctrl["controle_positivo"]["por_epoch"].values())
    if (sum(mex.values()), sum(n.values())) != (ref_mex, ref_n):
        die(f"A: {sum(mex.values())}/{sum(n.values())} does not reproduce artifact {ref_mex}/{ref_n}")
    out["A_share"] = {
        "artifact_mexeu_over_n": [ref_mex, ref_n, round(ref_mex / ref_n, 6)],
        "active": [mex["active"], n["active"], round(mex["active"] / n["active"], 6)],
        "shadow": [mex["shadow"], n["shadow"]],
        "0901_active": [per_ep[("2026-09-01", "active", "mexeu")], per_ep[("2026-09-01", "active", "n")],
                        round(per_ep[("2026-09-01", "active", "mexeu")] / per_ep[("2026-09-01", "active", "n")], 6)],
        "calibration_share_w2": [11, 350, round(11 / 350, 6)],
    }
    pb = cob.get("por_braco") or cob.get("cobertura_por_braco") or {}
    t_all = sum(v for (b, _), v in covn.items() if b == "treatment")
    t_cov = sum(v for (b, _), v in covc.items() if b == "treatment")
    c_all = sum(v for (b, _), v in covn.items() if b == "control")
    c_cov = sum(v for (b, _), v in covc.items() if b == "control")
    if (t_cov, t_all, c_cov, c_all) != (2068, 7392, 1385, 5145):
        die(f"B: coverage {t_cov}/{t_all}, {c_cov}/{c_all} does not reproduce 2068/7392, 1385/5145")
    out["B_coverage"] = {
        "treatment_all": [t_cov, t_all], "control_all": [c_cov, c_all],
        "treatment_active": [covc[("treatment", "active")], covn[("treatment", "active")],
                             round(covc[("treatment", "active")] / covn[("treatment", "active")], 6)],
        "treatment_shadow": [covc[("treatment", "shadow")], covn[("treatment", "shadow")]],
    }

    # ---- A': ratios of the H1 reductions (ITT-2026-09-21.json) to each share
    itt = json.loads((E / "ITT-2026-09-21.json").read_text())
    c1 = itt["primario"]["por_braco"]["control"]["H1_densidade"]
    red = {"locked": 1 - itt["primario"]["por_braco"]["treatment"]["H1_densidade"] / c1,
           "sem_0914": 1 - itt["sensibilidade"]["por_braco"]["treatment"]["H1_densidade"] / c1}
    sh = {"calibration": 11 / 350, "realized_active": mex["active"] / n["active"], "max_epoch": 0.0685}
    out["A_ratios"] = {k: {s: round(r / v, 2) for s, v in sh.items()} for k, r in red.items()}
    out["A_reductions"] = {k: round(v, 5) for k, v in red.items()}
    if (round(out["A_ratios"]["locked"]["calibration"], 1), round(out["A_ratios"]["sem_0914"]["max_epoch"], 1)) != (22.5, 6.9):
        die(f"A': ratios {out['A_ratios']} do not reproduce 22.5 and 6.9")

    # ---- C: power (copied from measurement/potencia-h1c.py, unchanged)
    z_a, z_b = 1.959964, 0.8416
    def poder_z(p0, p1, nn):
        pbar = (p0 + p1) / 2
        num = abs(p1 - p0) * math.sqrt(nn) - z_a * math.sqrt(2 * pbar * (1 - pbar))
        den = math.sqrt(p1 * (1 - p1) + p0 * (1 - p0))
        return num / den if den else 0.0
    de = 1 + (213 - 1) * 0.098459
    def nef(t, c):
        nt, nc = t * 213 / de, c * 213 / de
        return 2 * nt * nc / (nt + nc)
    base19, base20 = nef(10.9375, 7.23375), nef(10.9375, 8.23375)
    if (round(base19, 1), round(base20, 2)) != (84.8, 91.49):
        die(f"C: effective sizes {base19}, {base20} do not reproduce 84.8 and 91.49")
    N = statistics.NormalDist()
    out["C_power"] = {
        "effective_19_served": round(base19, 3), "effective_20_itt": round(base20, 3),
        "0901_clock_22.38h": {"19_served": round(nef(10 + 22.38 / 24, 7.23375), 3),
                              "20_itt": round(nef(10 + 22.38 / 24, 8.23375), 3)},
        "power_p1_increase": {f"{nn}:{p1}": round(N.cdf(poder_z(0.0782, p1, x)), 3)
                              for nn, x in (("19", base19), ("20", base20)) for p1 in (0.20, 0.25, 0.30)},
        "power_p1_zero": {"19": round(N.cdf(poder_z(0.0782, 0.0, base19)), 3),
                          "20": round(N.cdf(poder_z(0.0782, 0.0, base20)), 3)},
    }

    # ---- D: adjudication
    from pilot_replay import carregar_verdicts
    vp = Path(a.verdicts)
    v = carregar_verdicts(vp)
    eps = {json.loads(l)["episode_id"] for l in vp.open()}
    fam = collections.Counter(json.loads(l).get("panelist", "?") for l in vp.open())
    out["D_adjudication"] = {"submitted": len(eps), "three_substantive": len(v),
                             "unknown": len(eps) - len(v), "families": dict(fam)}

    # ---- E: planning concentration
    conc = json.loads((P2 / "out" / "CONCENTRATION-2026-08-30.json").read_text())
    big = conc["por_assinatura"]["Bash|shell:outro"]["total"]
    out["E_concentration"] = {"bucket": big, "covered_opportunities": conc["oportunidades_cobertas"],
                              "share": round(big / conc["oportunidades_cobertas"], 4)}

    # ---- F: preliminary ITT file time
    pre = E / "ITT-PRELIMINAR.json"
    st = os.stat(pre)
    d = json.loads(pre.read_text())
    out["F_preliminar"] = {
        "mtime_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(timespec="seconds"),
        "replicas": d["bootstrap"]["replicas"], "H1a": d["H1a_diferenca"],
        "cites": d["H1b"],
    }
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
