#!/usr/bin/env python3
"""Share of opportunities the locked dose can actually reach.

[!] PRE-TREATMENT MEASUREMENT, over the historical corpus. No arm assignment
exists. It changes no locked number by itself; it produces the input that Sec. 1
needs in order to state a hypothesis the design can test.

WHY THIS EXISTS
An independent whole-package review (Codex, 2026-08-16) found that Sec. 1's H1 is
stated on the **unconditional** repeated-failure density and sized for a 30%
relative change in it, while the locked treatment can only act on failures of
severity S2 and above -- 30.27% of the corpus. Detecting the locked MDE would
therefore require ~99% efficacy on everything the treatment can touch, and a null
result could not distinguish "outcome weighting does not work" from "almost
nothing was exposed to it". Each constraint had been declared honestly and
separately; the sum was never taken.

WHAT IS MEASURED
For each opportunity in the canonical estimator, whether the treatment could have
displaced anything for it, at each locked dose `w`. Reachability needs two
properties of the matched past failure:

  severity  -- consolidated panel level, which decides `pain` on the written
               chunk and therefore the size of the boost `w * Delta_cut * sev`;
  age       -- how old that chunk is at the opportunity, which decides the
               baseline the boost is added to through the 0.15-weighted recency
               term.

An opportunity is reachable at dose `w` iff `w >= w_min(sev, age)`, with
`w_min` exactly as Sec. 2 publishes it.

TWO MODELLING CHOICES, BOTH DECLARED
1. **The MOST RECENT prior failure governs, not the first.** `pilot_replay.py`
   keeps `primeiro_failure[sig]` because condition (i) only asks whether *any*
   qualifying past failure exists, and the earliest one settles that with the
   least work. Reachability is a different question: the design writes a chunk
   per adjudicated-failure episode, so at any opportunity the *freshest* matching
   chunk is the one that competes for a slot. Using the first would age every
   chunk artificially and understate reach. The opportunity SET is untouched --
   it stays exactly what the canonical estimator produces.
2. **Severity is the panel's lower median** for even counts, matching the strict
   majority rule that `carregar_verdicts` applies to the binary verdict
   (correction of 2026-07-29). Using the upper median would inflate severity, and
   severity is the term that carries the dose.

WHAT THIS SCRIPT DOES NOT DO
It does not re-size the study. It emits `r_hat` restricted to the reachable set
so that `sizing.py` can be run over it unchanged, and it does not choose which
hypothesis the pre-registration should state.
"""
from __future__ import annotations

import argparse
import collections
import json
from datetime import timedelta
from pathlib import Path

import pilot_replay as pr

# Salience v2 (production), and the constants Sec. 2 locks.
W_IMPORTANCE, W_RECENCY, W_PAIN, W_ACCESS = 0.55, 0.15, 0.10, 0.20
IMPORTANCE_LESSON = 0.90          # IMPORTANCE_BY_TYPE['lesson']
RETENTION_LESSON = 180            # typed retention for `lesson`
CUT_FRESH = 0.7342                # coverage-slot cut, measured (LINK-FEASIBILITY)
DELTA_CUT = 0.043                 # frozen at the 2026-07-29 lock
DOSES = (0.5, 1.0, 2.0)           # the locked band
SEV_VALUE = {"S1": 0.25, "S2": 0.50, "S3": 0.75, "S4": 1.00}


def base_salience(sev: float, age_days: float) -> float:
    """Salience of a freshly written `lesson` chunk, never served."""
    rec = 2 ** (-age_days / RETENTION_LESSON) if age_days > 0 else 1.0
    return (W_IMPORTANCE * IMPORTANCE_LESSON
            + W_RECENCY * rec
            + W_PAIN * sev
            + W_ACCESS * 0.0)


def w_min(sev: float, age_days: float) -> float:
    """Minimum dose to enter the two coverage slots. 0 means already in."""
    gap = CUT_FRESH - base_salience(sev, age_days)
    return 0.0 if gap <= 0 else gap / (DELTA_CUT * sev)


def severidade_consolidada(p: Path, instaveis: frozenset[str]) -> dict[str, str]:
    """episode_id -> consolidated severity level, by the panel's LOWER median.

    Mirrors `carregar_verdicts` exactly on which records count (status ok,
    non-abstain, dedupe by (episode, panelist), >= 3 substantive verdicts) so
    that this map and the binary verdicts always describe the same episodes.
    """
    por_ep: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for linha in p.read_text().splitlines():
        if not linha.strip():
            continue
        r = json.loads(linha)
        if r.get("status") != "ok" or r.get("verdict") == "abstain":
            continue
        if r.get("level") in pr.NIVEIS:
            por_ep[r["episode_id"]].setdefault(r.get("panelist"),
                                               pr.NIVEIS.index(r["level"]))
    out: dict[str, str] = {}
    for ep, por_pan in por_ep.items():
        if ep in instaveis:
            continue
        v = sorted(por_pan.values())
        if len(v) < 3:
            continue
        out[ep] = pr.NIVEIS[v[(len(v) - 1) // 2]]     # lower median
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--replicas", nargs="*", default=[])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--politica", choices=("recente", "melhor"), default="recente",
                    help="which matching chunk the treatment designates: the most "
                         "recent (default) or the easiest to reach")
    ap.add_argument("--doses", default="",
                    help="comma-separated doses to evaluate instead of the locked band; "
                         "exploratory only, does not change any locked value")
    a = ap.parse_args()

    doses = tuple(float(x) for x in a.doses.split(",")) if a.doses else DOSES
    globals()["DOSES"] = doses
    instaveis = frozenset(pr.episodios_instaveis(a.replicas)) if a.replicas else frozenset()
    verdicts = pr.carregar_verdicts(Path(a.verdicts), instaveis)
    sev_por_ep = severidade_consolidada(Path(a.verdicts), instaveis)
    eps = pr.carregar_episodios(Path(a.episodes), verdicts)
    limiar = timedelta(hours=pr.EPOCH_H)

    # Failure episodes per signature, in time order — the candidate chunks.
    falhas_por_sig: dict[str, list] = collections.defaultdict(list)
    for e in sorted(eps, key=lambda x: x.ts):
        if e.estado == "failure":
            falhas_por_sig[e.sig].append(e)

    spans = pr.span_por_sessao(eps)
    horas: dict[object, float] = collections.defaultdict(float)
    for (ep, _), h in spans.items():
        horas[ep] += h

    # Same stratification and weights as the canonical estimator.
    analisaveis = [e for e in eps if e.offset_h >= pr.WASHOUT_H]
    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    estrato_a = [e for e in analisaveis if e.err]
    resto = [e for e in analisaveis if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})

    tot = 0.0
    repeats_tot = 0.0
    por_sev: dict[str, float] = collections.defaultdict(float)
    alcanca: dict[float, float] = {w: 0.0 for w in doses}
    alcanca_rep: dict[float, float] = {w: 0.0 for w in doses}
    op_alc: dict[float, dict[object, float]] = {w: collections.defaultdict(float) for w in doses}
    rp_alc: dict[float, dict[object, float]] = {w: collections.defaultdict(float) for w in doses}
    idades: list[float] = []
    competidores: dict[int, float] = collections.defaultdict(float)
    comp_por_dose: dict[float, dict[int, float]] = {w: collections.defaultdict(float) for w in doses}
    sem_severidade = 0

    for e in estrato_a + estrato_b:
        cands = falhas_por_sig.get(e.sig)
        if not cands:
            continue
        # condition (i): written >= 1 epoch length before this epoch's start
        elegiveis = [c for c in cands if c.ts <= e.epoch - limiar]
        if not elegiveis:
            continue
        if e.estado == "unknown":
            continue                      # outside the estimator, as in the replay
        w_ep = peso[e.id]
        tot += w_ep
        if e.estado == "failure":
            repeats_tot += w_ep
        if a.politica == "melhor":
            # Pick the candidate that is EASIEST to reach, not the newest. Under a
            # one-boosted-chunk-per-opportunity policy this is the chunk the
            # treatment would designate, and it can only raise reach.
            cands_sev = [(c, sev_por_ep.get(c.id)) for c in elegiveis]
            cands_sev = [(c, nv) for c, nv in cands_sev if nv is not None]
            if not cands_sev:
                sem_severidade += w_ep
                continue
            a_past = min(cands_sev, key=lambda cn: w_min(
                SEV_VALUE[cn[1]], (e.ts - cn[0].ts).total_seconds() / 86400.0))[0]
        else:
            a_past = elegiveis[-1]        # MOST RECENT — see module docstring
        nivel = sev_por_ep.get(a_past.id)
        if nivel is None:
            sem_severidade += w_ep
            continue
        sev = SEV_VALUE[nivel]
        idade = (e.ts - a_past.ts).total_seconds() / 86400.0

        # How many chunks would be boosted AT THE SAME TIME for this opportunity.
        #
        # This is the question `dose_reach.mjs` cannot answer: its `reaches`
        # counts chunks that WOULD cross the cut if boosted, but only chunks
        # matching the signature are boosted. If typically 1-2 match, the
        # treatment occupies 1-2 of 10 slots and the brief stays diverse; if 8
        # match, the treated brief becomes nothing but failure lessons and the
        # arm is a different system rather than a reweighted ranking.
        n_boost = 0
        for c in elegiveis:
            nv = sev_por_ep.get(c.id)
            if nv is None:
                continue
            idade_c = (e.ts - c.ts).total_seconds() / 86400.0
            for w in doses:
                if w >= w_min(SEV_VALUE[nv], idade_c):
                    n_boost += 1
                    break
        competidores[min(n_boost, 12)] += w_ep
        for w in doses:
            k = sum(1 for c in elegiveis
                    if sev_por_ep.get(c.id) is not None
                    and w >= w_min(SEV_VALUE[sev_por_ep[c.id]],
                                   (e.ts - c.ts).total_seconds() / 86400.0))
            comp_por_dose[w][min(k, 12)] += w_ep
        idades.append(idade)
        por_sev[nivel] += w_ep
        need = w_min(sev, idade)
        for w in doses:
            if w >= need:
                alcanca[w] += w_ep
                op_alc[w][e.epoch] += w_ep
                if e.estado == "failure":
                    alcanca_rep[w] += w_ep
                    rp_alc[w][e.epoch] += w_ep

    horas_tot = sum(h for h in horas.values() if h > 0)
    idades.sort()
    med = idades[len(idades) // 2] if idades else float("nan")

    out = {
        "oportunidades_ponderadas": round(tot, 2),
        "sem_severidade_do_a_past": round(sem_severidade, 2),
        "distribuicao_severidade_do_a_past": {k: round(v / tot, 4) for k, v in sorted(por_sev.items())},
        "idade_do_a_past_dias": {
            "mediana": round(med, 2),
            "p25": round(idades[len(idades) // 4], 2) if idades else None,
            "p75": round(idades[3 * len(idades) // 4], 2) if idades else None,
            "max": round(idades[-1], 2) if idades else None,
        },
        "fracao_alcancavel_por_dose": {str(w): round(alcanca[w] / tot, 4) for w in doses},
        "r_hat_restrito_por_dose": {str(w): round(alcanca[w] / horas_tot, 4) for w in doses},
        "p0_hat_restrito_por_dose": {
            str(w): (round(alcanca_rep[w] / alcanca[w], 6) if alcanca[w] else None) for w in DOSES
        },
        "chunks_impulsionados_simultaneos": {
            str(k): round(v / tot, 4) for k, v in sorted(competidores.items())
        },
        "chunks_impulsionados_por_dose": {
            str(w): {str(k): round(v / tot, 4) for k, v in sorted(comp_por_dose[w].items())}
            for w in doses
        },
        "r_hat_irrestrito": round(tot / horas_tot, 4),
        "horas_analisadas": round(horas_tot, 2),
        # H1's outcome is repeated failures per session-hour. A "repeat" is an
        # opportunity that failed -- NOT every failure in the corpus. The ceiling
        # is the share of repeats the dose can touch: if the treatment removed
        # 100% of what it reaches, the unconditional density would fall by this.
        "repeats_ponderados": round(repeats_tot, 2),
        "teto_de_efeito_incondicional_por_dose": {
            str(w): (round(alcanca_rep[w] / repeats_tot, 4) if repeats_tot else None)
            for w in DOSES
        },
    }
    if a.json:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        print(json.dumps(out, indent=2, sort_keys=True))
        print("\n-- reading --", flush=True)
        print(f"  opportunities (HT-weighted): {tot:,.0f} over {horas_tot:,.0f} session-hours")
        print(f"  a_past age (days): median {med:.1f}")
        for w in doses:
            print(f"  w={w}: reaches {alcanca[w]/tot*100:5.2f}% of opportunities  "
                  f"=> r_hat restricted {alcanca[w]/horas_tot:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
