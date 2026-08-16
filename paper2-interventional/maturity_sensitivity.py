#!/usr/bin/env python3
"""Sensitivity of the sizing parameters to corpus MATURITY.

[!] EXPLORATORY, NOT PRE-SPECIFIED. It changes no locked number. It exists
because computing delta (Appendix B) exposed something none of the earlier
analyses had looked at.

WHAT WAS FOUND
Repeated-failure density per epoch is not stationary. In the corpus's first
epochs it is practically zero and then rises by an order of magnitude. The
cause is not noise: opportunity condition (i) requires a *failure episode* with
the same signature written >= 1 epoch earlier, and that stock **grows from 0 to
64 signatures across the corpus without saturating**. On 2026-08-14, the last
available epoch, it was still climbing.

WHY THIS MATTERS FOR SIZING
`r_hat`, `p0_hat` and the ICC were estimated over the whole corpus, that is,
over a mixture of regimes. Three consequences, in directions that do **not**
cancel:

1. `p0_hat` is pulled down by the early epochs (rate ~0.005 against ~0.12
   later). A smaller `p0_hat` => a larger `N`.
2. The ICC is inflated, because the early-regime -> mature-regime transition is
   between-cluster variance that is not cluster structure — it is trend.
   A larger ICC => a larger design effect => a larger `N`.
3. delta (Sec. B.5) inherits the same transition and comes out inflated.

That is: all three parameters err in the same direction, and the locked
`N = 174` is probably **conservative** — but for a reason that was not known when it was
locked, and that has to be said.

WHAT THIS SCRIPT DOES NOT SETTLE
It does not know whether the non-stationarity is a window artefact or a
property of the system. If the signature stock grows indefinitely with use,
then the real study **will also** run under a trend, and residualising in the
sizing would be optimistic. Sec. 5 of the pre-registration already residualises
trend **in the test** (outcome regressed on study-day, residuals permuted); the
sizing does not. That asymmetry is the finding, and resolving it is the
principal's decision, not this script's.

The maturity split is made by **stock of eligible signatures**, which depends
only on condition (i) and never on the current epoch's outcome — it is not a
cut chosen by looking at the result.

    python3 maturity_sensitivity.py --episodes ... --verdicts ... --estrato-b-ids ...
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_replay as pr


def p95(xs: list[float]) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = 0.95 * (len(s) - 1)
    lo = int(pos)
    return s[lo] + (pos - lo) * (s[min(lo + 1, len(s) - 1)] - s[lo])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--replicas", nargs="*", default=[])
    a = ap.parse_args()

    instaveis = frozenset(pr.episodios_instaveis(a.replicas)) if a.replicas else frozenset()
    verdicts = pr.carregar_verdicts(Path(a.verdicts), instaveis)
    eps = pr.carregar_episodios(Path(a.episodes), verdicts)

    primeiro_failure: dict[str, object] = {}
    for e in sorted(eps, key=lambda x: x.ts):
        if e.estado == "failure" and (e.sig not in primeiro_failure
                                      or e.ts < primeiro_failure[e.sig]):
            primeiro_failure[e.sig] = e.ts
    limiar = timedelta(hours=pr.EPOCH_H)

    spans = pr.span_por_sessao(eps)
    horas: dict[object, float] = collections.defaultdict(float)
    sessoes: dict[object, set] = collections.defaultdict(set)
    for (ep, s), h in spans.items():
        horas[ep] += h
        sessoes[ep].add(s)

    analisaveis = [e for e in eps if e.offset_h >= pr.WASHOUT_H]
    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    estrato_a = [e for e in analisaveis if e.err]
    resto = [e for e in analisaveis if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})

    op: dict[object, float] = collections.defaultdict(float)
    rp: dict[object, float] = collections.defaultdict(float)
    rp_sessao: dict[tuple, float] = collections.defaultdict(float)
    for e in estrato_a + estrato_b:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar or e.estado == "unknown":
            continue
        op[e.epoch] += peso[e.id]
        if e.estado == "failure":
            rp[e.epoch] += peso[e.id]
            rp_sessao[(e.epoch, e.sessao)] += peso[e.id]

    todos_epochs = sorted(ep for ep in horas if horas[ep] > 0)
    estoque = {ep: sum(1 for t0 in primeiro_failure.values() if t0 <= ep - limiar)
               for ep in todos_epochs}

    def bloco(epochs_sel: list) -> dict:
        tot_op = sum(op.get(ep, 0.0) for ep in epochs_sel)
        tot_rp = sum(rp.get(ep, 0.0) for ep in epochs_sel)
        tot_h = sum(horas[ep] for ep in epochs_sel)
        dens = {ep: rp.get(ep, 0.0) / horas[ep] for ep in epochs_sel}
        difs = []
        for k in range(len(epochs_sel) - 1):
            gap = (epochs_sel[k + 1] - epochs_sel[k]).total_seconds() / 3600
            if abs(gap - pr.EPOCH_H) < 1e-6:
                difs.append(abs(dens[epochs_sel[k + 1]] - dens[epochs_sel[k]]))
        d: dict[object, list[float]] = collections.defaultdict(list)
        for (ep, s), h in spans.items():
            if ep in set(epochs_sel) and len(sessoes[ep]) >= 2:
                d[ep].append(rp_sessao.get((ep, s), 0) / h)
        icc = pr.icc_anova(dict(d))
        return {
            "epochs": len(epochs_sel),
            "estoque_min": min(estoque[e] for e in epochs_sel) if epochs_sel else None,
            "estoque_max": max(estoque[e] for e in epochs_sel) if epochs_sel else None,
            "r_hat": round(tot_op / tot_h, 6) if tot_h else None,
            "p0_hat": round(tot_rp / tot_op, 6) if tot_op else None,
            "icc": icc["icc"],
            "icc_ic": [icc["ic_low"], icc["ic_high"]],
            "delta_p95": round(p95(difs), 6) if difs else None,
            "n_transicoes": len(difs),
        }

    # Split by stock, NOT by outcome. The stock median cuts the corpus into two
    # maturity halves without looking at repeats.
    mediana_estoque = sorted(estoque.values())[len(estoque) // 2]
    maduros = [ep for ep in todos_epochs if estoque[ep] >= mediana_estoque]
    jovens = [ep for ep in todos_epochs if estoque[ep] < mediana_estoque]

    print(json.dumps({
        "corte": f"stock of eligible signatures >= median ({mediana_estoque})",
        "corpus_inteiro": bloco(todos_epochs),
        "metade_madura": bloco(maduros),
        "metade_jovem": bloco(jovens),
        "estoque_por_epoch": {ep.date().isoformat(): estoque[ep] for ep in todos_epochs},
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
