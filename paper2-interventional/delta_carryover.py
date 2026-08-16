#!/usr/bin/env python3
"""delta of Appendix B — the empirical anchor of the carry-over bound.

Sec. B.5 defines it: *"delta is set to the p95 of the absolute epoch-to-epoch
difference in those same-arm transitions"*, over H1's primary outcome —
**repeated failures per session-hour**. It is deliberately conservative: it
attributes **all** same-arm drift to carry-over, when most of it is traffic
noise.

WHY ONLY NOW, AND WHY NOT LATER
A `[TO LOCK]` item from the start, with its window spelled out in Sec. B.5
itself: locking before the pilot would mean inventing a number; locking after
seeing treatment effects would be adaptive. The pilot is the only honest
window — and it closed with 30 epochs, **all of them control**, which is
exactly the same-arm (control->control) distribution the definition asks for.

[!] TRANSITIONS ONLY BETWEEN CALENDAR-ADJACENT EPOCHS. The corpus has gaps
(2026-07-16/17 with no usable episodes, 2026-08-01 absent). A difference
between epochs days apart is not an "epoch-to-epoch transition": it accumulates
drift over the whole interval and would inflate delta. Non-adjacent pairs are
counted and reported, never used.

    python3 delta_carryover.py --episodes ... --verdicts ... --estrato-b-ids ...
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
    """p95 by linear interpolation. With small n the method matters:
    'nearest-rank' would jump to the maximum and delta would inherit a single
    outlier."""
    if not xs:
        return float("nan")
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = 0.95 * (len(s) - 1)
    lo = int(pos)
    frac = pos - lo
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + frac * (s[hi] - s[lo])


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

    spans = pr.span_por_sessao(eps)          # `eps`, nao selecionados — ver icc_bootstrap
    horas: dict[object, float] = collections.defaultdict(float)
    for (ep, _), h in spans.items():
        horas[ep] += h

    analisaveis = [e for e in eps if e.offset_h >= pr.WASHOUT_H]
    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    estrato_a = [e for e in analisaveis if e.err]
    resto = [e for e in analisaveis if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})

    repeat: dict[object, float] = collections.defaultdict(float)
    for e in estrato_a + estrato_b:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar or e.estado == "unknown":
            continue
        if e.estado == "failure":
            repeat[e.epoch] += peso[e.id]

    epochs = sorted(ep for ep in horas if horas[ep] > 0)
    dens = {ep: repeat.get(ep, 0.0) / horas[ep] for ep in epochs}

    adjacentes, saltos = [], []
    for k in range(len(epochs) - 1):
        a_ep, b_ep = epochs[k], epochs[k + 1]
        gap_h = (b_ep - a_ep).total_seconds() / 3600
        d = abs(dens[b_ep] - dens[a_ep])
        (adjacentes if abs(gap_h - pr.EPOCH_H) < 1e-6 else saltos).append(
            {"de": a_ep.date().isoformat(), "para": b_ep.date().isoformat(),
             "gap_h": round(gap_h, 1), "abs_dif": round(d, 6)})

    difs = [t["abs_dif"] for t in adjacentes]
    media = sum(dens.values()) / len(dens) if dens else 0.0
    d95 = p95(difs)

    print(json.dumps({
        "definicao": "p95 da |diferenca epoch-a-epoch| na densidade de repeated "
                     "failure per session-hour, same-arm transitions (control->control)",
        "epochs": len(epochs),
        "transicoes_adjacentes_usadas": len(adjacentes),
        "transicoes_descartadas_por_salto": len(saltos),
        "saltos": saltos,
        "densidade_media_por_epoch": round(media, 6),
        "dif_min": round(min(difs), 6) if difs else None,
        "dif_mediana": round(sorted(difs)[len(difs) // 2], 6) if difs else None,
        "dif_max": round(max(difs), 6) if difs else None,
        "DELTA_p95": round(d95, 6),
        "delta_relativo_a_densidade_media": round(d95 / media, 4) if media else None,
        "densidade_por_epoch": {ep.date().isoformat(): round(dens[ep], 6) for ep in epochs},
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
