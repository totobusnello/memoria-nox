#!/usr/bin/env python3
"""sprint-determinismo-janela2.py — JANELA-LANCAMENTO.md §8 step 2 (sprint 2026-10-04, B-sham-v2).

Determinism check of the whole-window sham job (`job-janela2`, 11,812 states) against the
earlier job on the w = 4 epochs (`job-v2b`, 2,646 states) and against the job-v2b-era
200-state calibration sample. The replay is deterministic, so every (ts, agent, w) record
present in both runs of the SAME designation must be identical, key order included
(compared as serialized JSON, no sort_keys).

Checks, each reported as N identical of N shared:
  1. REAL (job-janela2) vs REAL (job-v2b): the 2,016 states of the w = 4 epochs 09-12, 09-14,
     09-15 (09-01 is not in the window), both doses.
  2. REAL (job-janela2) vs calibration/REAL-amostra200.json, both doses, for the sampled
     states that are in the 11,812.
  3. Each SHAM-0xx (job-janela2) vs the same SHAM-0xx (job-v2b): the shared states.
     Requires the designation hash of the two runs to be equal (the same sham file).

Exit 0 only if every shared record is identical and the shared counts are the expected ones
(2,016 states x 2 doses for checks 1 and 3). Writes nothing but --json.

Usage:
  python3 sprint-determinismo-janela2.py --novo B-sham-v2/job-janela2 --velho B-sham-v2/job-v2b \
      --amostra B-sham-v2/calibration/REAL-amostra200.json --json B-sham-v2/job-janela2/DETERMINISMO.json
"""
import argparse, json, pathlib, sys

ap = argparse.ArgumentParser()
ap.add_argument("--novo", required=True)
ap.add_argument("--velho", required=True)
ap.add_argument("--amostra", required=True)
ap.add_argument("--esperado-compartilhado", type=int, default=2016)
ap.add_argument("--json")
a = ap.parse_args()


def registros(p):
    d = json.load(open(p))
    out = {}
    for x in d["dose"]["detalhe"]:
        k = (x["ts"], x.get("agent"), float(x["w"]))
        if k in out:
            sys.exit(f"chave duplicada em {p}: {k}")
        out[k] = json.dumps(x, ensure_ascii=False)
    return d["procedencia"].get("designacao_sha256"), out


def compara(novo, velho):
    comum = sorted(set(novo) & set(velho))
    dif = [k for k in comum if novo[k] != velho[k]]
    return dict(compartilhados=len(comum), estados=len({k[:2] for k in comum}),
                identicos=len(comum) - len(dif), divergentes=[list(k) for k in dif[:10]])


N, V = pathlib.Path(a.novo) / "runs", pathlib.Path(a.velho) / "runs"
res, ok = {}, True
_, real_n = registros(N / "REAL.json")
_, real_v = registros(V / "REAL.json")
res["REAL_vs_job_v2b"] = c = compara(real_n, real_v)
ok &= c["identicos"] == c["compartilhados"] == 2 * a.esperado_compartilhado
_, amo = registros(a.amostra)
res["REAL_vs_amostra200"] = c = compara(real_n, amo)
res["REAL_vs_amostra200"]["amostra_fora_da_janela2"] = len({k[:2] for k in amo} - {k[:2] for k in real_n})
ok &= c["identicos"] == c["compartilhados"] > 0
shams = {}
for p in sorted(N.glob("SHAM-*.json")):
    hn, rn = registros(p)
    hv, rv = registros(V / p.name)
    c = compara(rn, rv)
    c["mesma_designacao"] = hn == hv
    shams[p.stem] = c
    ok &= c["mesma_designacao"] and c["identicos"] == c["compartilhados"] == 2 * a.esperado_compartilhado
res["SHAMS_vs_job_v2b"] = shams
res["shams_todos_identicos"] = f"{sum(1 for c in shams.values() if c['identicos'] == c['compartilhados'] and c['mesma_designacao'])}/{len(shams)}"
res["ok"] = bool(ok)
txt = json.dumps(res, indent=1, ensure_ascii=False)
print(txt)
if a.json:
    pathlib.Path(a.json).write_text(txt + "\n")
sys.exit(0 if ok else 1)
