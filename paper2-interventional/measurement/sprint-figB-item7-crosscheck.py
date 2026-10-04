#!/usr/bin/env python3
"""
sprint-figB-item7-crosscheck.py — an INDEPENDENT second measurement of §4.7, not a
reproduction of ITEM7-DOSE-TOPO-2026-09-21.json.

Why it exists: §4.7 quotes "the conditional mean for `control` is 9.991 against 9
realized", and that number is in NO artifact — ITEM7-DOSE-TOPO-*.json keeps only the
w=7.5 distribution, and the 9.991 lives only in DEVIATIONS-FOR-PAPER.md prose. The seed
recipe of the 2 000-seed run is not recorded either, so the run cannot be replayed.

This re-draws the 234-epoch design with the published `assign_arms.assign`, under a
DECLARED seed recipe  seed_i = SHA256("sprint-figB-item7-crosscheck|<i>"),  and reports,
for the first 20 dates, the mean count per arm with its Monte-Carlo standard error.
Agreement within MC error corroborates the quoted numbers; it does not make them
reproducible.

Usage: ./sprint-figB-item7-crosscheck.py --seeds 20000 --out <json>
"""
import argparse, collections, hashlib, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assign_arms import build_epochs, assign  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--seeds", type=int, default=20000)
ap.add_argument("--k", type=int, default=20)
ap.add_argument("--out", required=True)
a = ap.parse_args()

eps = build_epochs("2026-09-01", 234)
janela = [e.date for e in eps[: a.k]]
arms = ["control", "w2", "w4", "w7.5"]
soma = collections.Counter(); soma2 = collections.Counter()
dist_topo = collections.Counter()
for i in range(a.seeds):
    m = assign(eps, hashlib.sha256(f"sprint-figB-item7-crosscheck|{i}".encode()).hexdigest())
    c = collections.Counter(m[d] for d in janela)
    for b in arms:
        soma[b] += c[b]; soma2[b] += c[b] ** 2
    dist_topo[c["w7.5"]] += 1
res = {}
for b in arms:
    mu = soma[b] / a.seeds
    var = soma2[b] / a.seeds - mu ** 2
    res[b] = {"media": round(mu, 4), "ep_mc": round(math.sqrt(var / a.seeds), 4)}
p1 = dist_topo[1] / a.seeds
saida = {
    "receita_semente": "SHA256('sprint-figB-item7-crosscheck|<i>')",
    "sementes": a.seeds, "K": a.k, "janela": [janela[0], janela[-1]],
    "media_por_braco": res,
    "P_n_eq_1_topo": round(p1, 4), "ep_mc_P_n_eq_1": round(math.sqrt(p1 * (1 - p1) / a.seeds), 4),
    "P_n_le_1_topo": round((dist_topo[0] + dist_topo[1]) / a.seeds, 4),
    "dist_topo": dict(sorted(dist_topo.items())),
    "comparar_com": {"ITEM7 media_condicional w7.5": 3.3565, "ITEM7 P_n_eq_1": 0.1015,
                     "manuscrito control (sem artefato)": 9.991},
}
Path(a.out).write_text(json.dumps(saida, indent=1))
print(json.dumps(saida, indent=1))
