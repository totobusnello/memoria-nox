#!/usr/bin/env python3
"""ICC confidence interval by cluster bootstrap — checks whether Searle's CI is
too narrow.

[!] EXPLORATORY, NOT PRE-SPECIFIED. It does not replace the CI published by
`pilot_replay`; it exists to tell whether that interval can be trusted.

WHY
The Searle CI implemented in `pilot_replay.icc_anova` assumes BALANCED
clusters. Ours are not: 30 epochs with sizes from 1 to ~100, two of them
partial through right-censoring, m_bar = 55.96. For moderate imbalance
Searle's interval is known to be slightly ANTICONSERVATIVE — too narrow.
`SIZING-2026-08-14-v2.md` Sec. 5 declares this and says a bootstrap settles it.

This script settles it. It resamples WHOLE EPOCHS with replacement (the cluster
is the resampling unit — resampling sessions would destroy precisely the
structure the ICC measures) and recomputes the ICC on each replicate, with the
same `icc_anova` as the canonical path. The interval comes from the
percentiles.

DETERMINISM
No unseeded `random`. The seed comes from `--seed`, and the default is derived
from extension 2's beacon — a third party running with the same seed obtains
the same numbers.

    python3 icc_bootstrap.py --episodes ... --verdicts ... --estrato-b-ids ... [-B 5000]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_replay as pr

# Extension 2's seed (drand round 31309420), declared before the round existed.
# Using an ALREADY PUBLIC seed rather than inventing a new one: nothing here
# depends on unauditable randomness.
SEED_PADRAO = "fd9b4027dbdf223d689e02a2b33f6bca09b92ced41acebc332b0c8d4efc1aa85"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--replicas", nargs="*", default=[])
    ap.add_argument("-B", "--reamostras", type=int, default=5000)
    ap.add_argument("--seed", default=SEED_PADRAO)
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

    analisaveis = [e for e in eps if e.offset_h >= pr.WASHOUT_H]
    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    estrato_a = [e for e in analisaveis if e.err]
    resto = [e for e in analisaveis if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})
    selecionados = estrato_a + estrato_b

    # [!] `eps`, not `selecionados`. A session's duration is a fact about the
    # session, not about the sample: computing the span over only the drawn
    # episodes shrinks the density's denominator and inflates the ICC. Measured:
    # 0.1204 against the canonical 0.0985 — a CI built on that point would not be
    # the CI of the published estimator.
    spans = pr.span_por_sessao(eps)
    repeat_por_sessao: dict[tuple, float] = collections.defaultdict(float)
    sessoes_por_epoch: dict[object, set] = collections.defaultdict(set)
    horas: dict[object, float] = collections.defaultdict(float)
    for (ep, s), h in spans.items():
        sessoes_por_epoch[ep].add(s)
        horas[ep] += h
    for e in selecionados:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar or e.estado == "unknown":
            continue
        if e.estado == "failure":
            repeat_por_sessao[(e.epoch, e.sessao)] += peso[e.id]

    # Per-session density, grouped by epoch — exactly the ANOVA input of the
    # canonical path, including the exclusion of epochs with < 2 sessions.
    epochs = sorted(ep for ep in horas if horas[ep] > 0)
    dens: dict[object, list[float]] = collections.defaultdict(list)
    for (ep, s), h in spans.items():
        if ep in epochs and len(sessoes_por_epoch[ep]) >= 2:
            dens[ep].append(repeat_por_sessao.get((ep, s), 0) / h)

    ponto = pr.icc_anova(dict(dens))
    chaves = sorted(dens)
    k = len(chaves)

    # Resampling of WHOLE CLUSTERS. If an epoch is drawn twice it enters as two
    # distinct clusters — that is what preserves the between-cluster variance
    # structure the ICC estimates.
    rng = random.Random(int(hashlib.sha256(a.seed.encode()).hexdigest()[:16], 16))
    amostras: list[float] = []
    degenerados = 0
    for _ in range(a.reamostras):
        rep: dict[int, list[float]] = {}
        for i in range(k):
            escolhido = chaves[rng.randrange(k)]
            rep[i] = dens[escolhido]
        out = pr.icc_anova(rep)
        if out["ms_within"] is None:
            degenerados += 1
            continue
        amostras.append(out["icc"])

    amostras.sort()
    def pct(p: float) -> float:
        if not amostras:
            return float("nan")
        i = min(len(amostras) - 1, max(0, int(round(p * (len(amostras) - 1)))))
        return round(amostras[i], 6)

    searle = (ponto["ic_low"], ponto["ic_high"])
    boot = (pct(0.025), pct(0.975))
    print(json.dumps({
        "metodo": "bootstrap de cluster (epochs inteiros, com reposicao)",
        "reamostras": a.reamostras,
        "reamostras_degeneradas": degenerados,
        "seed": a.seed,
        "clusters": k,
        "icc_ponto": ponto["icc"],
        "ic_searle": list(searle),
        "ic_bootstrap_percentil": list(boot),
        "largura_searle": round(searle[1] - searle[0], 6) if None not in searle else None,
        "largura_bootstrap": round(boot[1] - boot[0], 6),
        "razao_larguras_boot_sobre_searle": (
            round((boot[1] - boot[0]) / (searle[1] - searle[0]), 3)
            if None not in searle and searle[1] > searle[0] else None),
        "fracao_reamostras_com_icc_zero": round(
            sum(1 for x in amostras if x == 0.0) / len(amostras), 4) if amostras else None,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
