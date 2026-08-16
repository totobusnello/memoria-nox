#!/usr/bin/env python3
"""
Sec. 9 item 7 — the pilot replay harness.

Produces EXACTLY three numbers — `r_hat`, `p0_hat`, `icc` — plus the two
exposure quantities that `sizing.py` consumes (`hours_per_epoch`,
`session_hours_per_epoch`). Nothing beyond that: the pre-registration chooses
`mde`, `sizing.py` computes `N_epochs`, and this runs exactly once.

DEFINITIONS (locked in PREREG-DRAFT.md Sec. 3, "Pilot metric definitions")
-------------------------------------------------------------------------
Epoch       24 h, boundary 06:00 BRT = 09:00 UTC.
Washout     the first 2 h of each epoch, excluded from analysis.
Failure     STRICT MAJORITY of the panel on `failure` (>50% of substantive
            verdicts). Corrected 2026-07-29 — see the note below.
Opportunity an action `a` executed post-washout such that a failure episode
            `a_past` exists with sig_primary(a_past) == sig_primary(a),
            written >= 1 epoch length BEFORE the start of `a`'s epoch.
            Depends on condition (i) alone — it does NOT look at how `a`
            turned out.
Repeat      an opportunity whose own outcome is failure (condition (ii)).
r_hat       opportunities / analysed session-hours.
p0_hat      repeats / opportunities  (in the replay every epoch is control).
icc         random-effects ANOVA, epoch as the factor; negative -> 0.

THE CIRCULARITY, AND HOW IT IS HANDLED
--------------------------------------
Marking an opportunity requires knowing which PAST episodes are failures, and
measuring `p0_hat` requires knowing whether the CURRENT episode is a failure.
Both come from the panel. Since adjudication is expensive, this script does not
assume full coverage: every episode enters as `failure`, `not_failure` or
`unknown`, and the report states how much mass sits in `unknown`. A `p0_hat`
computed over partial coverage is reported with its coverage alongside, never
on its own.

DECLARED APPROXIMATION
----------------------
Condition (i) asks what the snapshot CONTAINED. `pruneEpochs(keep=3)` deletes
the historical .db files by design, so membership is reconstructed by timestamp
(`ts < boundary`). Known divergence: 0.144%/epoch (T7). See the sensitivity
note in the pre-registration.
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

BOUNDARY_UTC_H = 9      # 06:00 BRT
EPOCH_H = 24.0
WASHOUT_H = 2.0
PISO_SESSAO_H = 1 / 60  # a single-action session counts as 1 minute, not zero
TAU = "S1"
NIVEIS = ["S0", "S1", "S2", "S3", "S4"]


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def epoch_de(t: datetime) -> tuple[datetime, float]:
    """Devolve (inicio_do_epoch, horas_desde_o_inicio)."""
    e = t.replace(hour=BOUNDARY_UTC_H, minute=0, second=0, microsecond=0)
    if t < e:
        e -= timedelta(days=1)
    return e, (t - e).total_seconds() / 3600


def episodios_instaveis(padroes: list[str]) -> set[str]:
    """Episodes whose verdict from the SAME panelist oscillates across replicas.

    Rule from STABILITY-TEST.md Sec. 9.2, adopted 2026-08-14. A census of the 21
    tie-break episodes (xai and zhipu on opposite sides of tau) with 5 replicas
    each showed that **10 of them (47.6%) oscillate** -- three at an exact 3F/3N.
    In those the panelist is the casting vote by definition, so the consolidated
    outcome comes out of the execution, not out of the episode.

    BROAD CRITERION: any oscillation marks the episode, treating 5-1 the same as
    3-3. A graded criterion (only 4-2 and 3-3) is defensible, but was NOT
    pre-specified -- choosing it after seeing the distribution would be choosing
    with the data in hand. The broad one is the least favourable to us, and for
    that reason the least suspect. To be revisited with data once replicas of the
    full corpus exist.

    Cost measured on the 2026-08-14 corpus: 10 episodes, 0.69% raw and 0.79%
    Horvitz-Thompson weighted (amplification by stratum B's 5.2 weight came out
    at 1.14x, not the feared 15x).

    A marked episode receives NO verdict: `carregar_episodios` resolves it to
    `unknown`, exactly as "fewer than 3 substantive verdicts" does. That is,
    instability becomes absence of evidence, not a coin toss.
    """
    corte = NIVEIS.index(TAU)
    lados: dict[tuple[str, str], set[bool]] = collections.defaultdict(set)
    for padrao in padroes:
        for caminho in sorted(glob.glob(padrao)):
            for linha in Path(caminho).read_text().splitlines():
                if not linha.strip():
                    continue
                r = json.loads(linha)
                if r.get("status") != "ok" or r.get("verdict") == "abstain":
                    continue
                nivel = r.get("level")
                if nivel in NIVEIS:
                    lados[(r["episode_id"], r.get("panelist"))].add(
                        NIVEIS.index(nivel) >= corte)
    return {ep for (ep, _), s in lados.items() if len(s) > 1}


def carregar_verdicts(p: Path, instaveis: frozenset[str] = frozenset()) -> dict[str, str]:
    """episode_id -> 'failure' | 'not_failure', por MAIORIA ESTRITA.

    `instaveis` (from `episodios_instaveis`) are omitted from the result and so
    resolve to `unknown` -- see STABILITY-TEST.md Sec. 9.2.

    CORRECTION 2026-07-29 -- the previous version used `v[len(v)//2]`, the UPPER
    median, for both conditions. Two things were wrong with that.

    1. O §4.1 do pre-registro trava, literalmente: *"condition (ii) is the
       binary verdict. Severity governs condition (i) only."* Severity
       decides which PAST episodes seed a repeat; the current episode's
       outcome is the binary verdict by **simple majority**.
    2. With an EVEN count the upper median is not the majority. For 4 ordered
       verdicts v0<=v1<=v2<=v3, `v[2] >= tau` means 2 of 4 above the cut -- a
       TIE resolved in favour of `failure`. A simple majority requires 3 of 4.
       It is the LOWER median (`v[1]`) that coincides with it.

    Why this is not a detail: 987 of piece 3's 1,140 episodes have exactly 4
    substantive verdicts (moonshot stopped at 88/1,140 on quota). An even count
    is the RULE, not the exception -- and the pre-registration only asserts the
    absence of ties by assuming an odd panel ("odd panel => no binary tie"), a
    premise that abstention and quota failure knock down.
    Measured: the two faithful readings (strict majority; tie => unadjudicable)
    give K = 64; the upper median gives 53. A 20% swing in a parameter the
    pre-registration never specified.

    An exact tie (n/2 failures, possible only with even n) resolves to
    `not_failure` -- a tie is not a majority. Conservative: it underestimates
    failures, hence underestimates lambda_0, hence INFLATES K. It errs towards a
    longer study.

    Abstencao conta como ausente (§4.1); < 3 vereditos substantivos vira
    `unknown`.
    """
    # Dedupe by (episode_id, panelist) — not by episode_id alone.
    #
    # Reason (incident 2026-08-13, docs/INCIDENTS.md): two processes adjudicated
    # the same queue in parallel and 40 episodes received TWO verdicts from the
    # same panelist. Aggregating by episode_id alone, the second enters as an
    # extra vote: 39 episodes became EVEN panels (4 votes), and the strict
    # majority below resolves a 2-2 tie silently to `not_failure`. In that case
    # the measured impact was ZERO (the pairs agreed), but the odd-panel premise
    # — "no ties by construction" — had been violated without anyone noticing.
    #
    # Rule: keep the FIRST record of each (episode, panelist) in input-file
    # order. When the file is assembled by concatenating the rounds in order of
    # generation, "first in the file" == chronologically earlier, which is the
    # rule declared in STABILITY-TEST.md Sec. 6. If the caller concatenates out
    # of order, the rule degrades to "first seen" — still deterministic and
    # independent of verdict content, which is the property that matters for not
    # choosing a result.
    por_ep: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for linha in p.read_text().splitlines():
        if not linha.strip():
            continue
        r = json.loads(linha)
        if r.get("status") != "ok" or r.get("verdict") == "abstain":
            continue
        nivel = r.get("level")
        if nivel in NIVEIS:
            por_ep[r["episode_id"]].setdefault(r.get("panelist"), NIVEIS.index(nivel))

    out: dict[str, str] = {}
    corte = NIVEIS.index(TAU)
    for ep, por_painelista in por_ep.items():
        if ep in instaveis:
            continue  # oscillates across replicas -> `unknown` (STABILITY-TEST.md Sec. 9.2)
        v = list(por_painelista.values())
        if len(v) < 3:
            continue
        n_falha = sum(1 for x in v if x >= corte)
        out[ep] = "failure" if n_falha * 2 > len(v) else "not_failure"
    return out


@dataclass
class Episodio:
    id: str
    ts: datetime
    sessao: str
    sig: str
    epoch: datetime
    offset_h: float
    estado: str  # failure | not_failure | unknown
    err: bool    # is_error — estratificador do desenho (§4 de PILOT-PROJECTION.md)


def carregar_episodios(p: Path, verdicts: dict[str, str]) -> list[Episodio]:
    eps: list[Episodio] = []
    for linha in p.read_text().splitlines():
        if not linha.strip():
            continue
        d = json.loads(linha)
        if not d.get("ts") or not d.get("session"):
            continue
        t = parse_ts(d["ts"])
        e, off = epoch_de(t)
        eps.append(Episodio(
            id=d["episode_id"], ts=t, sessao=d["session"],
            sig=d["sig_primary"], epoch=e, offset_h=off,
            estado=verdicts.get(d["episode_id"], "unknown"),
            err=bool(d.get("is_error")),
        ))
    eps.sort(key=lambda x: x.ts)
    return eps


def span_por_sessao(eps: list[Episodio]) -> dict[tuple[datetime, str], float]:
    """Hours of each session, keyed by (epoch, session).

    The SESSION is the ANOVA's unit of analysis -- the epoch is the cluster.
    That is why the span stays per session rather than pre-summed: with one
    observation per epoch there is no within variance, and the ICC comes out
    identically 0 by construction.
    """
    ts_por_sessao: dict[tuple[datetime, str], list[datetime]] = collections.defaultdict(list)
    for e in eps:
        ts_por_sessao[(e.epoch, e.sessao)].append(e.ts)
    return {
        k: max((max(v) - min(v)).total_seconds() / 3600, PISO_SESSAO_H)
        for k, v in ts_por_sessao.items()
    }


def _betainc(a: float, b: float, x: float) -> float:
    """Beta incompleta regularizada I_x(a,b) — fracao continuada de Lentz.

    Pure stdlib ON PURPOSE. This script is pre-registered: a third party must be
    able to run the replay without installing anything. `scipy` would give the
    same thing in one line, and `tests/test_icc_ci.py` confronts the two
    implementations -- but the dependency stays in the TEST, never in the
    canonical path.
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def _betacf(a: float, b: float, x: float, itmax: int = 300, eps: float = 3e-16) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < 1e-300:
            d = 1e-300
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < 1e-300:
            d = 1e-300
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _f_cdf(x: float, d1: float, d2: float) -> float:
    if x <= 0.0:
        return 0.0
    return _betainc(d1 / 2.0, d2 / 2.0, d1 * x / (d1 * x + d2))


def _f_ppf(p: float, d1: float, d2: float) -> float:
    """F quantile by bisection over the CDF. Monotone, so bisection suffices."""
    lo, hi = 1e-12, 1.0
    while _f_cdf(hi, d1, d2) < p and hi < 1e12:
        hi *= 2.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _f_cdf(mid, d1, d2) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def icc_anova(por_epoch: dict[datetime, list[float]],
              alfa: float = 0.05) -> dict[str, float | int | None]:
    """ICC de efeitos aleatorios (one-way) com IC exato de Searle.

    Returns the MEAN SQUARES alongside the point estimate and the interval.
    This function previously returned only the `float`, and SIZING-2026-08-14 had
    to estimate the CI width by RECONSTRUCTING the ANOVA in a separate script --
    which gave 0.0964 against the canonical 0.1175 and forced the document to say
    "this indicates the width, it is not the official interval". With the mean
    squares exposed, the CI comes out of the same code that produces the point,
    and the divergence ceases to exist.

    IC (Searle 1971, one-way): com F = MSb/MSw e g.l. (k-1, n-k),
        F_L = F / F_{1-alfa/2},  F_U = F / F_{alfa/2}
        ICC_bound = (F_bound - 1) / (F_bound + m_bar - 1)

    WARNING -- DECLARED APPROXIMATION: `m_bar = n/k` is the arithmetic mean of
    the cluster sizes. Searle's exact CI assumes BALANCED clusters, and ours are
    not (30 epochs, sizes from 1 to ~100, two of them partial through
    right-censoring). For moderate imbalance the interval is known to be slightly
    ANTICONSERVATIVE -- too narrow. It serves to decide whether the uncertainty
    is of the order of tens or of hundreds of days; it does not serve as a
    publishable interval without a note. A cluster-bootstrap CI resolves this,
    costs more, and was not pre-specified.

    `icc` negativo -> 0 (conservador), e o limite inferior tambem.
    """
    grupos = [v for v in por_epoch.values() if v]
    vazio = {"icc": 0.0, "ms_between": None, "ms_within": None, "f": None,
             "gl_between": None, "gl_within": None, "m_bar": None,
             "ic_low": None, "ic_high": None, "ic_alfa": alfa}
    if len(grupos) < 2:
        return vazio
    todos = [x for g in grupos for x in g]
    n, k = len(todos), len(grupos)
    if n <= k:
        return vazio
    media = statistics.fmean(todos)
    ms_between = sum(len(g) * (statistics.fmean(g) - media) ** 2 for g in grupos) / (k - 1)
    ms_within = sum((x - statistics.fmean(g)) ** 2 for g in grupos for x in g) / (n - k)
    m_bar = n / k
    denom = ms_between + (m_bar - 1) * ms_within
    if denom <= 0:
        return vazio
    icc = max(0.0, (ms_between - ms_within) / denom)

    out: dict[str, float | int | None] = {
        "icc": round(icc, 6),
        "ms_between": round(ms_between, 8),
        "ms_within": round(ms_within, 8),
        "gl_between": k - 1,
        "gl_within": n - k,
        "m_bar": round(m_bar, 4),
        "ic_alfa": alfa,
        "f": None, "ic_low": None, "ic_high": None,
    }
    if ms_within > 0:
        f = ms_between / ms_within
        d1, d2 = float(k - 1), float(n - k)
        fl = f / _f_ppf(1.0 - alfa / 2.0, d1, d2)
        fu = f / _f_ppf(alfa / 2.0, d1, d2)
        lim = lambda fb: (fb - 1.0) / (fb + m_bar - 1.0)
        # Clamp to [0,1] at BOTH limits. The upper one can also come out
        # negative: when F < F_{alpha/2}, the data are compatible with a complete
        # absence of cluster effect and the formula returns a number below zero.
        # Since the ICC is not defined outside [0,1], the interval collapses to
        # [0, 0] — which reads as "no evidence of cluster structure", not as "the
        # ICC is exactly zero".
        out["f"] = round(f, 6)
        out["ic_low"] = round(min(1.0, max(0.0, lim(fl))), 6)
        out["ic_high"] = round(min(1.0, max(0.0, lim(fu))), 6)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay do piloto — produz r_hat, p0_hat, icc")
    ap.add_argument("--episodes", required=True, help="JSONL do extract_episodes")
    ap.add_argument("--verdicts", required=True, help="JSONL do run_panel")
    ap.add_argument("--min-epochs", type=int, default=0,
                    help="refuse to run with fewer analysable epochs than this (Sec. 3 gate)")
    ap.add_argument("--seed-b", default="",
                    help="SEED_B of the stratified design (Sec. 4 of PILOT-PROJECTION.md); "
                         "without it the script runs in census mode, unweighted")
    ap.add_argument("--estrato-b-ids", default="",
                    help="file with one episode_id per line: the already-drawn sample "
                         "from stratum B. Use it when the corpus unites universes from "
                         "different seeds (see the comment in the body). Takes precedence "
                         "over --seed-b/--n-b; requires the same sampling RATE across them.")
    ap.add_argument("--n-b", type=int, default=800,
                    help="sample size of the non-is_error stratum (default 800)")
    ap.add_argument("--json", action="store_true", help="JSON output only")
    ap.add_argument("--replicas", nargs="*", default=[],
                    help="JSONL globs with panel replicas (e.g. "
                         "'~/.paper2-verdicts/tiebreak-rep*.jsonl'). Episodes whose "
                         "verdict oscillates across replicas become `unknown` -- "
                         "STABILITY-TEST.md Sec. 9.2. Without this the script runs without the rule.")
    a = ap.parse_args()

    instaveis = frozenset()
    if a.replicas:
        padroes = [str(Path(x).expanduser()) for x in a.replicas]
        instaveis = frozenset(episodios_instaveis(padroes))
        print(f"instability rule active: {len(instaveis)} episodes -> unknown",
              file=sys.stderr)

    verdicts = carregar_verdicts(Path(a.verdicts), instaveis)
    eps = carregar_episodios(Path(a.episodes), verdicts)
    if not eps:
        print("ERROR: no episode with ts+session", file=sys.stderr)
        return 2

    spans = span_por_sessao(eps)
    horas: dict[datetime, float] = collections.defaultdict(float)
    sessoes_por_epoch: dict[datetime, int] = collections.defaultdict(int)
    for (ep, _), h in spans.items():
        horas[ep] += h
        sessoes_por_epoch[ep] += 1

    # known failure episodes, by signature, with the earliest timestamp
    primeiro_failure: dict[str, datetime] = {}
    for e in eps:
        if e.estado == "failure" and (e.sig not in primeiro_failure or e.ts < primeiro_failure[e.sig]):
            primeiro_failure[e.sig] = e.ts

    limiar = timedelta(hours=EPOCH_H)
    oport_por_epoch: dict[datetime, int] = collections.defaultdict(int)
    repeat_por_epoch: dict[datetime, int] = collections.defaultdict(int)
    repeat_por_sessao: dict[tuple[datetime, str], int] = collections.defaultdict(int)
    oport_unknown = 0
    analisaveis = [e for e in eps if e.offset_h >= WASHOUT_H]

    # -- Sampling design -------------------------------------------------------
    # Without `--seed-b`, the script assumes a CENSUS: every episode weighs 1.
    # Episodes of unknown outcome enter as opportunities in BOTH modes — see the
    # missing-data note in the estimator loop below — which makes `p0_hat` a
    # FLOOR, and the warning at the end says so.
    #
    # With `--seed-b`, it reproduces the stratified design declared in Sec. 4 of
    # PILOT-PROJECTION.md (census of the is_error stratum + uniform sample of
    # `--n-b` from the complement, ordered by hash) and applies Horvitz-Thompson
    # weights. Without those weights the estimator undercounts the sampled
    # stratum's repeats by a factor N_B/n_B — here, 5.2x — and `lambda_0` comes
    # out deflated. It is neither conservative nor optimistic by accident: it is
    # simply the wrong estimator for the design.
    # -- Corpus with MORE THAN ONE seed (extension 2, 2026-08-14) ---------------
    # The draw above orders ALL of `resto` by a single seed. That stops working
    # when the corpus is the union of two universes sampled under different
    # seeds, each declared before its own round: re-drawing the union would
    # produce a THIRD sample, which neither declaration covers.
    #
    # `--estrato-b-ids` solves this the only honest way: it reads the list of
    # drawn IDs from a file instead of re-deriving it. Every ID in the list
    # remains derivable from its own public seed applied to its own universe —
    # third-party audit loses nothing, it just becomes a two-step check.
    #
    # [!] THE ESTIMATOR DOES NOT CHANGE. The weight remains
    # `len(resto)/len(estrato_b)`, and it stays valid only because both
    # extensions use the SAME RATE (19.2%): 1,576/8,194 = 5.199 and 122/635 =
    # 5.205, union 1,698/8,829 = 5.200. If a future extension uses a different
    # rate, this path becomes WRONG and the code needs per-stratum weights — not
    # another file of IDs.
    estratificado = bool(a.estrato_b_ids or a.seed_b)
    if a.estrato_b_ids:
        ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
        estrato_a = [e for e in analisaveis if e.err]
        resto = [e for e in analisaveis if not e.err]
        estrato_b = [e for e in resto if e.id in ids]
        faltando = len(ids) - len(estrato_b)
        if faltando:
            print(f"warning: {faltando} sample ids are not in the universe/post-washout",
                  file=sys.stderr)
        peso = {e.id: 1.0 for e in estrato_a}
        peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})
        analisaveis = estrato_a + estrato_b
    elif a.seed_b:
        # CORRECTION 2026-08-14 — the draw runs over `eps` (the RAW universe),
        # not over `analisaveis` (post-washout). The previous version drew the
        # `n_b` from the complement ALREADY filtered by washout, and that was
        # wrong for two compounding reasons:
        #
        # 1. WRONG SET. The design declared in EXTENSION-SEED-2026-08-11,
        #    "Design", is "1,576 of 8,194" — 8,194 is the complement in the raw,
        #    and that is where the sample was actually drawn and adjudicated
        #    (99.3% reproduction). Drawing post-washout (6,675) made the script
        #    pick ANOTHER set of 1,576: only 1,259 of them had verdicts, and the
        #    remaining 317 entered as `unknown`. Measured: `unknown` falls from
        #    232 to 44 with the fix.
        # 2. WRONG WEIGHT. `len(resto_pw)/n_b` = 6,675/1,576 = 4.235, against the
        #    HT weight of 5.2x that the design itself declares as the target.
        #    Stratum B came out undercounted by ~20%.
        #
        # Effect on the pilot's three numbers (extension-1 corpus):
        #   r_hat  22.78 -> 27.86 | p0_hat 0.1310 -> 0.1159 | icc 0.1169 -> 0.1016
        estrato_a = [e for e in analisaveis if e.err]
        resto = [e for e in analisaveis if not e.err]
        chave = lambda e: hashlib.sha256(
            a.seed_b.encode("ascii") + b"|" + e.id.encode()).hexdigest()
        sorteados = {e.id for e in sorted(
            [e for e in eps if not e.err], key=chave)[: a.n_b]}
        estrato_b = [e for e in resto if e.id in sorteados]
        peso = {e.id: 1.0 for e in estrato_a}
        peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})
        analisaveis = estrato_a + estrato_b
    else:
        peso = {e.id: 1.0 for e in analisaveis}

    for e in analisaveis:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue                      # condition (i) not satisfied
        # -- Missing data: ONE rule, in both modes (corrected 2026-08-16) --------
        # Sec. 5 locks it on 2026-07-29: "Unadjudicable outcomes -> third
        # category, reported, **excluded from numerator**". Excluded from the
        # numerator, NOT from the denominator.
        #
        # The stratified branch used to `continue` here, dropping the episode
        # from both — complete-case analysis, which is a different rule and was
        # never the registered one. The census branch always did what Sec. 5
        # says. So the same script implemented two rules depending on a flag,
        # and every canonical number came out of the branch that contradicts the
        # document. Measured on the 30-epoch corpus: p0_hat 0.116457
        # (complete-case) against 0.111813 (Sec. 5's rule) — 3.99% apart, and
        # N_epochs 174 against 180.
        #
        # The comment that justified the drop ("weight undefined") was also
        # wrong: `analisaveis` has been reassigned to `estrato_a + estrato_b`
        # above, so every episode reaching this loop carries a weight.
        #
        # Why Sec. 5's rule and not the code's: it makes `p0_hat` a genuine
        # FLOOR — an unknown can only ever move an opportunity into the
        # numerator, never out of it — hence a CEILING on N. That is the same
        # direction of error the rest of this design takes deliberately (strict
        # majority inflates K; sizing on the ICC's upper limit), and it is the
        # property the warning printed at the end of this script asserts.
        oport_por_epoch[e.epoch] += peso[e.id]
        if e.estado == "failure":
            repeat_por_epoch[e.epoch] += peso[e.id]
            repeat_por_sessao[(e.epoch, e.sessao)] += peso[e.id]
        elif e.estado == "unknown":
            oport_unknown += 1            # in the denominator, out of the numerator

    epochs = sorted(ep for ep in horas if horas[ep] > 0)
    if a.min_epochs and len(epochs) < a.min_epochs:
        print(f"ERROR: {len(epochs)} analysable epochs, minimum required {a.min_epochs}", file=sys.stderr)
        return 3

    tot_oport = sum(oport_por_epoch.values())
    tot_repeat = sum(repeat_por_epoch.values())
    tot_horas = sum(horas[ep] for ep in epochs)

    # ANOVA: one observation per SESSION (unit), grouped by epoch (cluster).
    # Epochs with < 2 sessions contribute no within variance and are excluded
    # from the ICC — reported separately so they do not vanish silently.
    dens: dict[datetime, list[float]] = collections.defaultdict(list)
    for (ep, s), h in spans.items():
        if ep in epochs and sessoes_por_epoch[ep] >= 2:
            dens[ep].append(repeat_por_sessao.get((ep, s), 0) / h)
    epochs_degenerados = [ep for ep in epochs if sessoes_por_epoch[ep] < 2]

    icc_out = icc_anova(dict(dens))

    saida = {
        "r_hat": round(tot_oport / tot_horas, 6) if tot_horas else None,
        "p0_hat": round(tot_repeat / tot_oport, 6) if tot_oport else None,
        "icc": icc_out["icc"],
        "icc_anova": icc_out,
        "hours_per_epoch": round(tot_horas / len(epochs), 4) if epochs else None,
        "session_hours_per_epoch": round(
            sum(sessoes_por_epoch[ep] for ep in epochs) / len(epochs), 4) if epochs else None,
        "epochs_analisaveis": len(epochs),
        "epochs_fora_do_icc": len(epochs_degenerados),
        "oportunidades": tot_oport,
        "repeats": tot_repeat,
        "cobertura_adjudicacao": {
            "episodios_total": len(eps),
            "com_veredito": sum(1 for e in eps if e.estado != "unknown"),
            "pct": round(100 * sum(1 for e in eps if e.estado != "unknown") / len(eps), 2),
            "oportunidades_com_desfecho_unknown": oport_unknown,
        },
        "assinaturas_com_failure_conhecido": len(primeiro_failure),
        "desenho": "estratificado-HT" if estratificado else "censo",
        "regra_desfecho": "maioria estrita (>50%); empate => not_failure",
        "tau": TAU,
    }

    if a.json:
        print(json.dumps(saida, indent=2, sort_keys=True, default=str))
        return 0

    print(json.dumps(saida, indent=2, sort_keys=True, default=str))
    cob = saida["cobertura_adjudicacao"]
    if cob["pct"] < 100:
        print(f"\n⚠️  cobertura de adjudicacao {cob['pct']}% — "
              f"{cob['oportunidades_com_desfecho_unknown']} opportunities with no adjudicated outcome.\n"
              f"    the p0_hat above is a FLOOR: the unknowns can only raise it.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
