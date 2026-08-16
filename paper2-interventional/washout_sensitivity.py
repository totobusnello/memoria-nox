#!/usr/bin/env python3
"""Washout sensitivity — how much epoch-boundary time must be discarded?

[!] EXPLORATORY ANALYSIS, NOT PRE-SPECIFIED. It does not enter the study
outcome and changes no `pilot_replay` number. It exists to answer a question
that blocks a design decision: **is the 2 h washout enough?**

WHY THE QUESTION MATTERS NOW
`SIZING-2026-08-14-v2.md` Sec. 4 shows that shortening the epoch is the only
lever that buys calendar without selling MDE (24 h->242 d, 8 h->113 d). But the
washout is FIXED at 2 h: it costs 8% of a 24 h epoch and 25% of an 8 h one.
Worse, the premise that 2 h suffices to wash out the previous arm's effect was
calibrated for 24 h epochs and was never verified. Shortening the epoch brings
arm switches closer together, and an unverified premise is then asked for more,
not less.

WHAT THIS SCRIPT MEASURES, AND WHAT IT CANNOT MEASURE
It measures the profile of `p0` (repeats/opportunities) and of opportunity
density across the hours since the epoch boundary, in the replay corpus. If any
residual boundary effect survives past 2 h, it shows up as a gradient in the
first post-washout hours.

[!] FUNDAMENTAL LIMIT: in the replay corpus **every epoch is control** — no arm
switch ever occurred. So this does NOT measure treatment carry-over. It
measures whatever intra-epoch temporal structure exists in the absence of
intervention: work rhythm, sessions crossing the boundary, time-zone effects. A
gradient here is evidence that the epoch boundary is not a neutral point —
which is a NECESSARY condition for the washout to be sufficient, not enough to
assert it. Absence of a gradient does not prove 2 h suffices under treatment;
presence of a gradient proves 2 h does not suffice even without it.

    python3 washout_sensitivity.py --episodes ... --verdicts ... --estrato-b-ids ...
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_replay as pr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--replicas", nargs="*", default=[])
    ap.add_argument("--bin-h", type=float, default=2.0, help="largura do bin, horas")
    a = ap.parse_args()

    instaveis = frozenset(pr.episodios_instaveis(a.replicas)) if a.replicas else frozenset()
    verdicts = pr.carregar_verdicts(Path(a.verdicts), instaveis)
    eps = pr.carregar_episodios(Path(a.episodes), verdicts)

    primeiro_failure: dict[str, object] = {}
    for e in sorted(eps, key=lambda x: x.ts):
        if e.estado == "failure" and (e.sig not in primeiro_failure
                                      or e.ts < primeiro_failure[e.sig]):
            primeiro_failure[e.sig] = e.ts
    from datetime import timedelta
    limiar = timedelta(hours=pr.EPOCH_H)

    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    # No washout filter: the whole point of the exercise is to LOOK AT the
    # discarded zone.
    estrato_a = [e for e in eps if e.err]
    resto = [e for e in eps if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})

    oport: dict[int, float] = collections.defaultdict(float)
    repeat: dict[int, float] = collections.defaultdict(float)
    desconhecido: dict[int, int] = collections.defaultdict(int)
    # RAW counts kept in parallel. The HT weight amplifies stratum B by ~5.2x,
    # which inflates any n used in a proportion test and manufactures
    # significance where there is none. Every test below runs on raw counts; the
    # weights are reserved for the point estimate, which is what they exist to
    # correct.
    oport_n: dict[int, int] = collections.defaultdict(int)
    repeat_n: dict[int, int] = collections.defaultdict(int)
    for e in estrato_a + estrato_b:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue
        b = int(e.offset_h // a.bin_h)
        if e.estado == "unknown":
            desconhecido[b] += 1
            continue
        oport[b] += peso[e.id]
        oport_n[b] += 1
        if e.estado == "failure":
            repeat[b] += peso[e.id]
            repeat_n[b] += 1

    def agreg(ls):
        o = sum(l["oportunidades"] for l in ls)
        r = sum(l["repeats"] for l in ls)
        n = sum(l["n_bruto"] for l in ls)
        rn = sum(l["repeats_bruto"] for l in ls)
        return {"oportunidades": round(o, 1), "repeats": round(r, 1),
                "p0": round(r / o, 4) if o else None,
                "n_bruto": n, "repeats_bruto": rn,
                "p0_bruto": round(rn / n, 4) if n else None}

    def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
        """Wilson CI — does not degenerate at k=0 or small n, unlike the normal
        interval, which returns [0,0] and feigns certainty."""
        if n == 0:
            return None
        p = k / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
        return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))

    def compara(nome: str, a_ls, b_ls) -> dict:
        """Difference of proportions between two sets of bins, on RAW counts."""
        ka, na = sum(l["repeats_bruto"] for l in a_ls), sum(l["n_bruto"] for l in a_ls)
        kb, nb = sum(l["repeats_bruto"] for l in b_ls), sum(l["n_bruto"] for l in b_ls)
        if not (na and nb):
            return {"comparacao": nome, "conclusivo": False}
        pa, pb = ka / na, kb / nb
        # Standard error of the difference under independent proportions.
        se = (pa * (1 - pa) / na + pb * (1 - pb) / nb) ** 0.5
        dif = pa - pb
        return {
            "comparacao": nome,
            "p0_A": round(pa, 4), "n_A": na, "ic_A": wilson(ka, na),
            "p0_B": round(pb, 4), "n_B": nb, "ic_B": wilson(kb, nb),
            "diferenca": round(dif, 4),
            "ic_diferenca": [round(dif - 1.96 * se, 4), round(dif + 1.96 * se, 4)],
            "cruza_zero": bool(dif - 1.96 * se <= 0 <= dif + 1.96 * se),
        }

    bins = sorted(set(oport) | set(desconhecido))
    linhas = []
    for b in bins:
        o, r = oport[b], repeat[b]
        linhas.append({
            "bin": f"{b*a.bin_h:.0f}-{(b+1)*a.bin_h:.0f}h",
            "inicio_h": b * a.bin_h,
            "oportunidades": round(o, 1),
            "repeats": round(r, 1),
            "p0": round(r / o, 4) if o else None,
            "n_bruto": oport_n[b],
            "repeats_bruto": repeat_n[b],
            "p0_bruto": round(repeat_n[b] / oport_n[b], 4) if oport_n[b] else None,
            "unknown": desconhecido[b],
        })

    # -- p0 BY STRATUM: the aggregate comparison is confounded -----------------
    # The first reading of this analysis concluded "there is a boundary effect":
    # raw p0 of 0.397 in 0-2h against 0.316 in 2h+, difference CI not crossing
    # zero. It was WRONG. The share of stratum A varies by zone (37.5% in 0-2h
    # against ~30% later) and p0_A ~ 0.96 against p0_B ~ 0.05 — so the aggregate
    # difference measures COMPOSITION, not the boundary. Applying the 2h+
    # composition to the 0-2h zone: 0.30*0.967 + 0.70*0.056 = 0.329, against the
    # 0.316 observed. The "effect" vanishes.
    #
    # Within each stratum there is no gradient at all. That is why the aggregate
    # stays flagged DO-NOT-USE in the output rather than being removed: whoever
    # reproduces the analysis needs to see the trap, not a clean result that
    # hides that it existed.
    zonas: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"A": 0, "B": 0, "repA": 0, "repB": 0})
    for e in estrato_a + estrato_b:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar or e.estado == "unknown":
            continue
        z = "0-2h" if e.offset_h < 2 else ("2-6h" if e.offset_h < 6 else "6h+")
        k = "A" if e.err else "B"
        zonas[z][k] += 1
        if e.estado == "failure":
            zonas[z]["rep" + k] += 1
    por_estrato = []
    for z in ("0-2h", "2-6h", "6h+"):
        d = zonas[z]
        n = d["A"] + d["B"]
        por_estrato.append({
            "zona": z, "pct_estrato_A": round(d["A"] / n, 4) if n else None,
            "n_A": d["A"], "p0_A": round(d["repA"] / d["A"], 4) if d["A"] else None,
            "n_B": d["B"], "p0_B": round(d["repB"] / d["B"], 4) if d["B"] else None,
        })

    # -- Error incidence over the UNIVERSE: the test that actually answers -----
    # `is_error` is a census: no sampling, no weighting, no composition to
    # confound. If the epoch boundary has an effect, it shows up here cleanly.
    inc_bins = [(0, 2), (2, 4), (4, 6), (6, 12), (12, 24)]
    incidencia = []
    for lo, hi in inc_bins:
        sub = [e for e in eps if lo <= e.offset_h < hi]
        k = sum(1 for e in sub if e.err)
        incidencia.append({"zona": f"{lo}-{hi}h", "n": len(sub), "erros": k,
                           "taxa": round(k / len(sub), 4) if sub else None,
                           "ic": wilson(k, len(sub))})

    dentro = [l for l in linhas if l["inicio_h"] < pr.WASHOUT_H]
    fora = [l for l in linhas if l["inicio_h"] >= pr.WASHOUT_H]

    # First 2h AFTER the washout vs the rest of the epoch — the test that
    # matters: if the 2h washout were too short, the zone right after it would
    # still carry the boundary effect.
    logo_apos = [l for l in linhas if pr.WASHOUT_H <= l["inicio_h"] < pr.WASHOUT_H + 4]
    restante = [l for l in linhas if l["inicio_h"] >= pr.WASHOUT_H + 4]

    print(json.dumps({
        "bin_h": a.bin_h,
        "washout_h": pr.WASHOUT_H,
        "perfil": linhas,
        "zona_descartada_0_2h": agreg(dentro),
        "zona_analisada_2h_em_diante": agreg(fora),
        "logo_apos_washout_2_6h": agreg(logo_apos),
        "restante_6h_em_diante": agreg(restante),
        "testes_confundidos_NAO_USAR": [
            compara("zona descartada (0-2h) vs analisada (2h+)", dentro, fora),
            compara("just after washout (2-6h) vs remainder (6h+)", logo_apos, restante),
        ],
        "por_estrato": por_estrato,
        "incidencia_de_erro_no_universo": incidencia,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
