#!/usr/bin/env python3
"""Paper B — the ITT analysis AS REGISTERED, with the current analysis as a switchable leg.

Decision of the author, 2026-10-05: the registered analysis becomes the reported one; the
analysis implemented in `estimador_itt.py` (locked output `ITT-2026-09-21.json`) becomes a
sensitivity. `estimador_itt.py` and `rerandomizacao.py` are NOT modified; this file imports
their building blocks (`pilot_replay`, `assign_arms`, `rerandomizacao.residualiza`) and adds
four switches, one per divergence found by two independent reviewers.

COMPOSITION, NOT REIMPLEMENTATION
  carregar_verdicts / carregar_episodios / span_por_sessao   <- pilot_replay.py
  assign / build_epochs                                      <- assign_arms.py
  residualiza                                                <- rerandomizacao.py
  tokens_da_mensagem                                         <- task_regret.py
The aggregation (`agrega`), the stratified epoch bootstrap and the re-randomization loop are
copied from estimador_itt.py / rerandomizacao.py line for line, and the copy is guarded: with
all four switches at the CURRENT value this script must rebuild ITT-2026-09-21.json and
RERANDOMIZACAO-2026-09-21.json BYTE FOR BYTE (sha256 compared at run time; exit 2 if not).

THE FOUR SWITCHES
-----------------
(1) painel  ∈ {3fam, substituicao}
    Registered rule, DEVIATIONS-FOR-PAPER.md §10.31, quoted verbatim:
      "O que passa a valer: o DeepSeek entra como **substituto** apenas nos episódios sem
       piso de 3 vereditos substantivos — a função que o PREREG §695 lhe atribui — e
       **nunca como 4.º voto** onde os três responderam. Assim não gera empate nenhum, e o
       efeito dele é o resgate, que é o que o §695 previa. O conjunto de 4 votos fica
       publicado como **sensibilidade declarada**, com a regra de 2-2 nomeada."
    PREREG §695 (l.695): "With exactly three panelists a single abstention drops an episode
    below the 3-verdict floor [...] Mitigation [...]: seat a fourth API family."
    Implementation: an episode is "without the floor" iff `carregar_verdicts(3fam)` does not
    resolve it (that function returns exactly the episodes with >=3 substantive verdicts,
    deduped per panelist, abstentions absent). For those episodes, and only those, the
    deepseek records are appended to the 3-family records and `carregar_verdicts` is re-run
    on the union: same dedupe, same abstention rule, same strict majority, same <3 floor.
    Episodes resolved by the three families never see the fourth vote.

(2) janela  ∈ {data, exposicao}   (+ diagnostic sub-legs so_expiracao, so_offsets)
    Current: analysis = every episode whose EPOCH DATE is in 2026-09-01..2026-09-20.
    Registered, SPEC-ANALISE-2026-09-10.md header and §2, quoted verbatim:
      header: "Escrita em 2026-09-10, dez dias antes do fecho da janela
               (`2026-09-20 22:51:23Z`)."
      §2 `09-03`: "parcial por volume | **incluída, com offset**; e a cobertura do PREREG §5
               é computada e reportada **antes** de qualquer decisão de exclusão"
      §2 `09-01`: "parcial por relógio (arranque tardio, fases **sequenciais**) |
               **incluída no ITT** pelo braço designado, com offset sobre a exposição
               tratada (630 briefs / 22,38 h)"
      §2 `09-20`: "parcial por relógio | **incluída, com offset** | truncamento puro; o corte
               cai **dentro** do epoch, às 22:51:23Z"
    Implementation (an interpretation, declared): the ratio estimator's exposure is
    session-hours, so an "offset" is realised as an exposure WINDOW on the timestamp axis —
    episodes outside it leave the numerator AND the session-hour denominator (spans are
    recomputed on the in-window episodes). The windows are read from p2-serving.ndjson,
    never typed in, and cross-checked against the values the spec/incident quote:
      09-01  from the first `active` record          (spec: 10:37:01.943Z)
      09-03  from the first served record            (INCIDENT-2026-09-02: 17:23:39.777Z)
      09-20  until designation expiry 22:51:23Z      (spec header and §2)
    The a_past corpus (condition (i)) stays the WHOLE corpus in every leg — cutting it would
    delete the August a_past, exactly as estimador_itt.py l.18-20 warns.

(3) ic  ∈ {percentil, bca}
    PREREG-DRAFT.md §5 (l.997), quoted verbatim: "**Construction: BCa** (bias-corrected and
    accelerated), acceleration from the **leave-one-epoch-out jackknife** over all 234
    epochs (**AMENDED 2026-08-17**; was 174). Percentile is the declared fallback, used
    **only** if the acceleration is undefined (zero jackknife variance), and its use is
    reported."  Resampling stays stratified by arm (l.993). The jackknife runs over the
    REALISED analysis epochs (the 234 never happened). Same 10,000 draws as the percentile
    interval — the switch does not change the random stream. z0 = Phi^-1(#{theta* < theta^}/B);
    quantile index = int(alpha_adj * B), the same index rule estimador_itt.py uses.
    Percentile fallback fires if the jackknife variance is zero OR z0 is infinite (all
    replicates on one side) — the second trigger is not in the registration and is reported
    whenever it fires.

(4) conjunto  ∈ {20, 19}
    SPEC-ANALISE §2, quoted verbatim: "`09-02` | vazia | **excluída do conjunto de análise**,
    contada e reportada | zero exposição e zero desfecho. Não é dado ausente, é unidade não
    realizada. É controle, logo excluí-la **piora** o desbalanço (9→8) e isso é declarado,
    não compensado"

(5) washout_in_denominator  ∈ {sim, nao}          (added in v2, 2026-10-05; review C1)
    Current (`sim`, the locked value): the outcome loop drops episodes with offset < WASHOUT_H,
    but `span_por_sessao` is computed BEFORE that filter, so the washout stays in the
    session-hour denominator of H1/H1a. estimador_itt.py has the same defect; the v1 control
    rebuilt the locked files byte for byte and therefore preserved it.
    Registered (`nao`), PREREG-DRAFT.md, quoted verbatim:
      §2 item 3: "Washout: first 2 h of each epoch excluded from analysis"
      §2 item 4: "the primary analysis set is **all post-washout session-hours**"
      §4.1 (l.642): "Opportunity. An executed action `a`, in a session starting after the
               epoch's 2 h washout, [...]"
      §4.1 (l.644): "The denominator is post-washout exposure"
      §5 (l.1036): "Sessions excluded by the washout are excluded from both sets"
    Implementation: a (epoch, session) unit is eligible iff its first episode in that epoch
    (over the WHOLE corpus, not only the in-window episodes) has offset >= WASHOUT_H. Only
    eligible units enter span_por_sessao AND the outcome loop. On the locked corpus this set
    is identical to dropping washout episodes one by one (0 post-washout episodes sit in a
    unit that started inside the washout; checked at run time and recorded). The a_past
    corpus (condition (i)) is never cut. H2's population follows the same predicate.
    NOT applied here (declared, measured as a diagnostic leg): PREREG §2 item 3 also assigns
    boundary-straddling sessions to the epoch of their START, flagged, with a with/without
    sensitivity. The estimator keys sessions by (epoch of the episode, session); the
    diagnostic leg `diag_registrado_sem_sessoes_atravessadas` drops every unit of a session
    with episodes in more than one epoch (the registered 'without' leg).

Re-randomization (PREREG §5 item 1; SPEC §4) and H1b/H2/H3 handling: see main() and the
RESULTADO.md next to the output. H1b is unevaluable (DEVIATIONS §10.32). H2 (task regret) is
computed from the locked action archive with the locked task_regret.py definitions; H3 is not
computable (no relevance judgments exist).

    python3 measurement/estimador_itt_registrado.py --out out/ITT-REGISTRADO-v2-2026-10-05.json

v1 (four switches; output out/ITT-REGISTRADO-2026-10-05.json) was produced by sha256
c28b064f…, frozen at _sprint-2026-10-04/B-registered/estimador_itt_registrado-v1-c28b064f.py.
This script asserts that its leg `registrado_sem_washout_in_denominator` (switch 5 at the
locked value) equals v1's `resumo.registrado` field for field.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import tempfile
from dataclasses import dataclass, asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
P2 = AQUI.parent
sys.path.insert(0, str(P2))
from pilot_replay import (  # noqa: E402
    carregar_verdicts, carregar_episodios, span_por_sessao, parse_ts, epoch_de,
    EPOCH_H, WASHOUT_H, TAU,
)
import assign_arms as AA  # noqa: E402
from rerandomizacao import residualiza  # noqa: E402
import task_regret as TR  # noqa: E402
from extract_episodes import assinaturas  # noqa: E402  (LOCKED c0abe143 — imported, never modified)

LOCK = Path.home() / "Backups/paper2-ensaio-2026-09-21"
VERD = Path.home() / ".paper2-verdicts"
DEFAULTS = dict(
    episodes=LOCK / "episodios-ensaio-20260921.jsonl",
    verdicts=VERD / "ensaio-20260921-PRIMARIO-3fam.jsonl",
    verdicts_ds=VERD / "ensaio-20260921-SENSIB-deepseek.jsonl",
    estrato_b=LOCK / "estrato-b-ids-20260921.txt",
    serving=LOCK / "p2-serving.ndjson",
    archive=LOCK / "action-archive",
    assignment=P2 / "ASSIGNMENT-SERVING.json",
    locked_itt=LOCK / "ITT-2026-09-21.json",
    locked_rerand=LOCK / "RERANDOMIZACAO-2026-09-21.json",
    v1_registrado=P2 / "out" / "ITT-REGISTRADO-2026-10-05.json",
)

JANELA_INI, JANELA_FIM = "2026-09-01", "2026-09-20"
EXPIRACAO = parse_ts("2026-09-20T22:51:23Z")
EPOCH_VAZIO = "2026-09-02"
SEED = 20260921
BOOT = 10000
SEED_PREFIX = "p2-rerand-2026-09-21"
# Locked 2026-08-15, PREREG §4.2: winsorization points of the two task-regret components.
WINSOR = {"tempo_s": 7.45, "tokens": 65206.0}
ESPERADO = {  # values quoted by the spec / incident; the serving log must agree
    "2026-09-01": "2026-09-01T10:37:01.943Z",
    "2026-09-03": "2026-09-03T17:23:39.777Z",
}
N = statistics.NormalDist()


@dataclass(frozen=True)
class Config:
    painel: str      # 3fam | substituicao
    janela: str      # data | exposicao | so_expiracao | so_offsets
    ic: str          # percentil | bca
    conjunto: str    # 20 | 19
    washout_in_denominator: str = "sim"   # sim (locked) | nao (registered)
    sem_atravessadas: bool = False        # diagnostic only: drop sessions with episodes in >1 epoch


ATUAL = Config("3fam", "data", "percentil", "20", "sim")
REGISTRADO = Config("substituicao", "exposicao", "bca", "19", "nao")
SWITCHES = ("painel", "janela", "ic", "conjunto", "washout_in_denominator")


def sha(p: Path) -> str:
    if p.is_dir():
        h = hashlib.sha256()
        for f in sorted(x for x in p.rglob("*") if x.is_file()):
            h.update(str(f.relative_to(p)).encode()); h.update(b"\0")
            h.update(hashlib.sha256(f.read_bytes()).digest())
        return h.hexdigest()
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ─── (1) panel ────────────────────────────────────────────────────────────────
def verdicts_substituicao(p3: Path, pds: Path, tmpdir: Path) -> tuple[dict, dict]:
    v3 = carregar_verdicts(p3)
    linhas3 = [l for l in p3.read_text().splitlines() if l.strip()]
    sub = [l for l in pds.read_text().splitlines()
           if l.strip() and json.loads(l)["episode_id"] not in v3]
    alvo = {json.loads(l)["episode_id"] for l in linhas3}
    uniao = tmpdir / "verdicts-substituicao.jsonl"
    uniao.write_text("\n".join(linhas3 + sub) + "\n")
    v = carregar_verdicts(uniao)
    resgatados = sorted(set(v) - set(v3))
    info = dict(
        episodios_adjudicados=len(alvo),
        resolvidos_3fam=len(v3), unknown_3fam=len(alvo - set(v3)),
        resolvidos_substituicao=len(v), unknown_substituicao=len(alvo - set(v)),
        resgatados=len(resgatados),
        resgatados_failure=sum(1 for e in resgatados if v[e] == "failure"),
        linhas_deepseek_acrescentadas=len(sub),
        vereditos_alterados_em_resolvidos_3fam=sum(1 for e in v3 if v[e] != v3[e]),
        sha256_uniao=sha(uniao),
        regra="DEVIATIONS §10.31: deepseek only where the 3 families leave < 3 substantive verdicts",
    )
    assert info["vereditos_alterados_em_resolvidos_3fam"] == 0, "4th vote leaked into a resolved episode"
    return v, info


# ─── (2) window ──────────────────────────────────────────────────────────────
def janelas_de_exposicao(serving: Path) -> dict:
    primeiro_active = None; primeiro_0903 = None
    for l in serving.read_text().splitlines():
        if not l.strip():
            continue
        r = json.loads(l); t = parse_ts(r["ts"])
        ep = epoch_de(t)[0].strftime("%Y-%m-%d")
        if ep == "2026-09-01" and r.get("modo") == "active":
            primeiro_active = t if primeiro_active is None else min(primeiro_active, t)
        if ep == "2026-09-03":
            primeiro_0903 = t if primeiro_0903 is None else min(primeiro_0903, t)
    j = {"2026-09-01": (primeiro_active, None), "2026-09-03": (primeiro_0903, None),
         "2026-09-20": (None, EXPIRACAO)}
    for k, s in ESPERADO.items():
        assert j[k][0] == parse_ts(s), f"serving log disagrees with the quoted start of {k}"
    return j


def predicado_janela(modo: str, jan: dict):
    if modo == "data":
        return lambda e: True
    usa_ini = modo in ("exposicao", "so_offsets")
    usa_fim = modo in ("exposicao", "so_expiracao")

    def ok(e):
        k = e.epoch.strftime("%Y-%m-%d")
        ini, fim = jan.get(k, (None, None))
        if usa_ini and ini is not None and e.ts < ini:
            return False
        if usa_fim and fim is not None and e.ts >= fim:
            return False
        return True
    return ok


# ─── per-epoch quantities (copy of estimador_itt.py l.62-105, plus the window) ─
def unidades_elegiveis(eps, sem_atravessadas=False):
    """Switch (5): the (epoch, session) units whose first episode in that epoch, over the
    WHOLE corpus, is past the washout (PREREG l.642, l.1036). With `sem_atravessadas`
    (diagnostic, PREREG §2 item 3 'boundary-straddling ... flag + sensitivity with/without'),
    every unit of a session that has episodes in more than one epoch is dropped (the 'without'
    leg; the registered 'with' leg, attribution to the epoch of the session's start, is not
    implemented)."""
    inicio = {}
    epochs_da_sessao = collections.defaultdict(set)
    for e in eps:
        k = (e.epoch, e.sessao)
        inicio[k] = min(inicio.get(k, e.offset_h), e.offset_h)
        epochs_da_sessao[e.sessao].add(e.epoch)
    ok = {k for k, off in inicio.items() if off >= WASHOUT_H}
    if sem_atravessadas:                            # 'without' leg: the whole straddling session leaves
        ok = {k for k in ok if len(epochs_da_sessao[k[1]]) == 1}
    return ok


def por_epoch(eps, b_ids, na_analise, washout_no_denominador=True, sem_atravessadas=False):
    resto = [e for e in eps if not e.err]
    peso_b = len(resto) / len(b_ids) if b_ids else 1.0
    primeiro_failure: dict = {}
    for e in eps:                                   # WHOLE corpus — a_past never cut
        if e.estado == "failure" and e.sig not in primeiro_failure:
            primeiro_failure[e.sig] = e.epoch
    limiar = timedelta(hours=EPOCH_H)
    eps_an = [e for e in eps if na_analise(e)]
    diag = None
    if not washout_no_denominador:                  # switch (5), registered: BEFORE spans
        ok = unidades_elegiveis(eps, sem_atravessadas)
        antes = [e for e in eps_an if JANELA_INI <= e.epoch.strftime("%Y-%m-%d") <= JANELA_FIM]
        eps_an = [e for e in eps_an if (e.epoch, e.sessao) in ok]
        fora = [e for e in antes if (e.epoch, e.sessao) not in ok]
        diag = dict(
            escopo="episodes of the analysis window 2026-09-01..2026-09-20 (09-02 included)",
            episodios_removidos=len(fora),
            episodios_removidos_dentro_do_washout=sum(1 for e in fora if e.offset_h < WASHOUT_H),
            pos_washout_em_unidade_iniciada_no_washout=sum(1 for e in fora if e.offset_h >= WASHOUT_H
                                                           and not sem_atravessadas),
        )
    horas = span_por_sessao(eps_an)
    oport = collections.defaultdict(float); repet = collections.defaultdict(float)
    unk = collections.defaultdict(int); unk_w = collections.defaultdict(float)
    h_ep = collections.defaultdict(float)
    for (ep, _s), h in horas.items():
        h_ep[ep] += h
    for e in eps_an:
        if e.offset_h < WASHOUT_H:
            continue
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue
        if e.err:
            w = 1.0
        elif e.id in b_ids:
            w = peso_b
        else:
            continue
        oport[e.epoch] += w
        if e.estado == "failure":
            repet[e.epoch] += w
        elif e.estado == "unknown":
            unk[e.epoch] += 1; unk_w[e.epoch] += w
    dentro = [ep for ep in sorted(set(oport) | set(h_ep))
              if JANELA_INI <= ep.strftime("%Y-%m-%d") <= JANELA_FIM]
    return dict(oport=oport, repet=repet, unk=unk, unk_w=unk_w, h_ep=h_ep,
                dentro=dentro, peso_b=peso_b, n_resto=len(resto), diag_washout=diag)


def agrega_fn(Q):
    oport, repet, h_ep, unk = Q["oport"], Q["repet"], Q["h_ep"], Q["unk"]

    def agrega(lista):                              # estimador_itt.py l.119-127, verbatim
        o = sum(oport[e] for e in lista); r = sum(repet[e] for e in lista)
        h = sum(h_ep[e] for e in lista)
        return dict(n_epochs=len(lista), oportunidades=round(o, 2), repeats=round(r, 2),
                    horas_sessao=round(h, 2),
                    H1_densidade=round(r / h, 6) if h else None,
                    H1a_taxa_oport=round(o / h, 6) if h else None,
                    H1c_prop=round(r / o, 6) if o else None,
                    unknown_no_denominador=sum(unk[e] for e in lista))
    return agrega


def montar(Q, arm, excluidos):
    d = collections.defaultdict(list)
    for ep in Q["dentro"]:
        k = ep.strftime("%Y-%m-%d")
        if k not in arm or k in excluidos:
            continue
        d[arm[k][0]].append(ep)
    return d


# ─── (3) interval ────────────────────────────────────────────────────────────
def bootstrap(agrega, pb, metrica, rng, B):
    """estimador_itt.py l.133-150 (same draws, same order) + BCa on the same draws."""
    t, c = pb.get("treatment", []), pb.get("control", [])
    if not t or not c:
        return None
    difs = []
    for _ in range(B):
        at = [t[rng.randrange(len(t))] for _ in t]
        ac = [c[rng.randrange(len(c))] for _ in c]
        vt, vc = agrega(at)[metrica], agrega(ac)[metrica]
        if vt is not None and vc is not None:
            difs.append(vt - vc)
    if not difs:
        return None
    theta = (agrega(t)[metrica] or 0) - (agrega(c)[metrica] or 0)
    menores = sum(1 for d in difs if d < theta)
    difs.sort()
    n = len(difs)
    perc = [round(difs[int(.025 * n)], 6), round(difs[int(.975 * n)], 6)]

    # leave-one-epoch-out jackknife, each deletion inside its own arm
    jk = []
    for braco, lst in (("treatment", t), ("control", c)):
        for i in range(len(lst)):
            red = lst[:i] + lst[i + 1:]
            tt, cc = (red, c) if braco == "treatment" else (t, red)
            a, b = agrega(tt)[metrica], agrega(cc)[metrica]
            if a is not None and b is not None:
                jk.append(a - b)
    m = sum(jk) / len(jk)
    s2 = sum((m - x) ** 2 for x in jk); s3 = sum((m - x) ** 3 for x in jk)
    bca = dict(n_jackknife=len(jk), z0=None, acel=None, alfa_ajustado=None, fallback=None)
    if s2 == 0:
        bca["fallback"] = "percentile: jackknife variance is zero (registered trigger)"
    elif menores == 0 or menores == n:
        bca["fallback"] = "percentile: z0 infinite, all replicates on one side (NOT a registered trigger)"
    if bca["fallback"]:
        ic_bca = perc
    else:
        z0 = N.inv_cdf(menores / n)
        acel = s3 / (6 * s2 ** 1.5)
        alf = []
        for q in (.025, .975):
            zq = N.inv_cdf(q)
            alf.append(N.cdf(z0 + (z0 + zq) / (1 - acel * (z0 + zq))))
        idx = [min(max(int(a * n), 0), n - 1) for a in alf]
        ic_bca = [round(difs[idx[0]], 6), round(difs[idx[1]], 6)]
        bca.update(z0=round(z0, 6), acel=round(acel, 6), alfa_ajustado=[round(a, 6) for a in alf])
    return dict(dif_pontual=round(theta, 6), ic95_percentil=perc, ic95_bca=ic_bca,
                n_replicas=n, bca=bca)


# ─── re-randomization (copy of rerandomizacao.py l.109-156) ───────────────────
def mapas_rerand(n: int, datas: list[str]):
    EP234 = AA.build_epochs("2026-09-01", 234)
    out = []
    for i in range(n):
        m = AA.assign(EP234, hashlib.sha256(f"{SEED_PREFIX}|{i}".encode()).hexdigest())
        out.append({k: m[k] for k in datas})
    return out


def rerand(dados: dict, real: dict, mapas: list):
    chaves = sorted(dados)
    sem_oport = [k for k in chaves if dados[k]["oport"] <= 0]
    usaveis = [k for k in chaves if dados[k]["oport"] > 0]
    desfechos = {
        "H1c_prop": [dados[k]["repet"] / dados[k]["oport"] for k in usaveis],
        "H1_dens": [dados[k]["repet"] / dados[k]["horas"] if dados[k]["horas"] else 0.0 for k in usaveis],
        "H1a_taxa": [dados[k]["oport"] / dados[k]["horas"] if dados[k]["horas"] else 0.0 for k in usaveis],
    }
    return _rerand_desfechos(desfechos, usaveis, real, mapas, sem_oport)


def _rerand_desfechos(desfechos, usaveis, real, mapas, sem_oport):
    def estatistica(y_res, bracos):
        t = [v for v, b in zip(y_res, bracos) if b == "treatment"]
        c = [v for v, b in zip(y_res, bracos) if b == "control"]
        if not t or not c:
            return None
        return sum(t) / len(t) - sum(c) / len(c)
    res = {}; padroes = set()
    for nome, y in desfechos.items():
        y_res = residualiza(usaveis, y)
        obs = estatistica(y_res, [real[k] for k in usaveis])
        mais = 0; validas = 0; nulo = []
        for m in mapas:
            br = [("treatment" if m[k] != AA.CONTROL else "control") for k in usaveis]
            if nome == "H1c_prop":
                padroes.add("".join("T" if x == "treatment" else "C" for x in br))
            s = estatistica(y_res, br)
            if s is None:
                continue
            validas += 1; nulo.append(s)
            if abs(s) >= abs(obs) - 1e-12:
                mais += 1
        nulo.sort()
        res[nome] = dict(
            observado=round(obs, 6),
            p_bilateral=round(mais / validas, 5) if validas else None,
            replicas_validas=validas,
            nulo_p025=round(nulo[int(.025 * len(nulo))], 6),
            nulo_p975=round(nulo[int(.975 * len(nulo))], 6),
            rejeita_nulo_agudo_a_5pct=(mais / validas) < 0.05 if validas else None,
        )
    return res, len(padroes), usaveis, sem_oport


# ─── one leg ─────────────────────────────────────────────────────────────────
def correr_perna(cfg: Config, ctx: dict) -> dict:
    eps = ctx["eps"][cfg.painel]
    na = predicado_janela(cfg.janela, ctx["jan"])
    Q = por_epoch(eps, ctx["b_ids"], na, cfg.washout_in_denominator == "sim", cfg.sem_atravessadas)
    agrega = agrega_fn(Q)
    excl = {EPOCH_VAZIO} if cfg.conjunto == "19" else set()
    pb = montar(Q, ctx["arm"], excl)
    rng = random.Random(SEED)
    hip = {}
    for nome, met in (("H1", "H1_densidade"), ("H1a", "H1a_taxa_oport"), ("H1c", "H1c_prop")):
        r = bootstrap(agrega, pb, met, rng, BOOT)
        r["ic95"] = r["ic95_bca"] if cfg.ic == "bca" else r["ic95_percentil"]
        r["construcao"] = ("BCa" if not r["bca"]["fallback"] else "percentile (BCa fallback)") \
            if cfg.ic == "bca" else "percentile"
        hip[nome] = r
    por_braco = {b: agrega(v) for b, v in sorted(pb.items())}
    analise = [ep for b in pb.values() for ep in b]
    dados = {ep.strftime("%Y-%m-%d"): dict(oport=Q["oport"][ep], repet=Q["repet"][ep], horas=Q["h_ep"][ep])
             for ep in sorted(analise)}
    real = {k: v[0] for k, v in ctx["arm"].items()}
    rr, padroes, usaveis, sem_oport = rerand(dados, real, ctx["mapas"])
    for nome, chave in (("H1", "H1_dens"), ("H1a", "H1a_taxa"), ("H1c", "H1c_prop")):
        hip[nome]["rerand"] = rr[chave]
        hip[nome]["p_rerand"] = rr[chave]["p_bilateral"]
    o_tot = sum(Q["oport"][e] for e in analise)
    u_tot = sum(Q["unk_w"][e] for e in analise)
    return dict(
        config=asdict(cfg),
        epochs_analisados=sorted(k for k in dados),
        excluidos_do_conjunto=sorted(excl),
        n_epochs={b: len(v) for b, v in sorted(pb.items())},
        por_braco=por_braco,
        hipoteses=hip,
        rerand_padroes_distintos=padroes, rerand_epochs_usaveis=len(usaveis),
        rerand_epochs_sem_oportunidade=sem_oport,
        unknown_ponderado_sobre_oportunidades=round(u_tot / o_tot, 6) if o_tot else None,
        regra_10pct_dados_ausentes_dispara=(u_tot / o_tot) > 0.10 if o_tot else None,
        gatilho_desbalanco_mais_de_5_epochs=abs(len(pb.get("treatment", [])) - len(pb.get("control", []))) > 5,
        washout_diagnostico=Q["diag_washout"],
        _cfg=cfg,
        por_epoch={k: dict(braco=ctx["arm"][k][0], horas=round(v["horas"], 5), oport=round(v["oport"], 4),
                           repet=round(v["repet"], 4)) for k, v in dados.items()},
        _Q=Q, _pb=pb,
    )


def limpa(perna: dict) -> dict:
    return {k: v for k, v in perna.items() if not k.startswith("_")}


# ─── control: rebuild the two locked files byte for byte ─────────────────────
def reproduzir_itt(ctx, a) -> tuple[str, dict]:
    eps = ctx["eps"]["3fam"]
    Q = por_epoch(eps, ctx["b_ids"], predicado_janela("data", ctx["jan"]))
    agrega = agrega_fn(Q)
    rng = random.Random(SEED)

    def ic(metrica, pb):
        r = bootstrap(agrega, pb, metrica, rng, BOOT)
        return None if r is None else dict(dif_pontual=r["dif_pontual"], ic95=r["ic95_percentil"],
                                           n_replicas=r["n_replicas"])
    pb = montar(Q, ctx["arm"], set()); pbs = montar(Q, ctx["arm"], {"2026-09-14"})
    excl = "2026-09-14"
    saida = dict(
        estimando="Opportunity = ACAO (lock 2026-07-29); ver DEVIATIONS 10.32",
        tau=TAU, washout_h=WASHOUT_H, epoch_h=EPOCH_H,
        janela=[JANELA_INI, JANELA_FIM],
        braco_de="ASSIGNMENT-SERVING.json (designacao; nao inferido dos dados)",
        peso_estrato_b=round(Q["peso_b"], 4), n_estrato_b_amostrado=len(ctx["b_ids"]),
        n_resto_no_corpus=Q["n_resto"],
        epochs_na_janela=len(Q["dentro"]),
        primario=dict(
            nota="definicao TRAVADA: todos os epochs da janela, denominador = span por sessao",
            por_braco={b: agrega(v) for b, v in sorted(pb.items())},
            H1_diferenca=ic("H1_densidade", pb),
            H1a_diferenca=ic("H1a_taxa_oport", pb),
            H1c_diferenca=ic("H1c_prop", pb),
        ),
        sensibilidade=dict(
            nota="perna declarada: remove " + excl + " — reportada AO LADO, nunca adjudicada em favor de uma (SPEC-ANALISE 2)",
            epochs_removidos=[excl],
            por_braco={b: agrega(v) for b, v in sorted(pbs.items())},
            H1_diferenca=ic("H1_densidade", pbs),
            H1a_diferenca=ic("H1a_taxa_oport", pbs),
            H1c_diferenca=ic("H1c_prop", pbs),
        ),
        H1b="INAVALIAVEL — colisao de locks, ver DEVIATIONS 10.32",
        bootstrap=dict(replicas=BOOT, seed=SEED, unidade="epoch inteiro"),
    )
    texto = json.dumps(saida, indent=2, sort_keys=True, ensure_ascii=False)
    return texto, saida


def reproduzir_rerand(ctx) -> str:
    eps = ctx["eps"]["3fam"]
    Q = por_epoch(eps, ctx["b_ids"], predicado_janela("data", ctx["jan"]))
    dados = {ep.strftime("%Y-%m-%d"): dict(oport=Q["oport"][ep], repet=Q["repet"][ep], horas=Q["h_ep"][ep])
             for ep in Q["dentro"]}
    real = {k: v[0] for k, v in ctx["arm"].items()}
    res, padroes, usaveis, sem_oport = rerand(dados, real, ctx["mapas"])
    out = dict(
        teste="nulo agudo, PREREG §5 — re-randomizacao redesenhando os 234",
        escopo_declarado="testa o nulo agudo de efeito TOTAL zero (direto + carry-over); "
                         "rejeicao sozinha nao atribui magnitude",
        armadilha_evitada="permutar entre os 20 NAO reproduz a distribuicao: os 20 caem "
                          "todos na 1a metade de calendario, onde a estratificacao colapsa",
        desfecho="residualizado por tendencia (regressao em study-day), conforme PREREG §5",
        replicas=BOOT, seed_prefix=SEED_PREFIX,
        padroes_distintos_de_braco=padroes,
        epochs_usaveis=len(usaveis), epochs_sem_oportunidade=sem_oport,
        peso_estrato_b=round(Q["peso_b"], 4),
        resultados=res,
    )
    return json.dumps(out, indent=2, ensure_ascii=False)


# ─── H2: task regret (PREREG §4.2; task_regret.py definitions) ───────────────
def regret_por_episodio(archive: Path, corpus: dict) -> tuple[dict, dict]:
    """The pairing loop of task_regret.py l.95-145, re-walked because that script does not
    expose it as a function. Guard: every pair must land on a corpus episode_id and every
    corpus episode must be found (the id formula is extract_episodes')."""
    linhas = {}
    sig_diverge = 0
    for arq in sorted(archive.rglob("*.jsonl")):
        agente = arq.parent.name.replace("-root--openclaw-workspace-", "") or "workspace"
        pend = {}
        for linha in arq.read_text(errors="replace").splitlines():
            if "tool_use" not in linha and "tool_result" not in linha:
                continue
            try:
                ev = json.loads(linha)
            except json.JSONDecodeError:
                continue
            conteudo = (ev.get("message") or {}).get("content")
            if not isinstance(conteudo, list):
                continue
            for b in conteudo:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and b.get("id"):
                    pend[b["id"]] = {"tool": b.get("name") or "?", "input": b.get("input"),
                                     "ts": ev.get("timestamp") or "", "session": arq.stem,
                                     "tokens": TR.tokens_da_mensagem(ev)}
                elif b.get("type") == "tool_result":
                    o = pend.pop(b.get("tool_use_id"), None)
                    if o is None:
                        continue
                    t0, t1 = TR.parse_ts(o["ts"]), TR.parse_ts(ev.get("timestamp") or "")
                    if t0 is None or t1 is None:
                        continue
                    bruto = f"{agente}|{o['session']}|{o['ts']}|{o['tool']}|{b.get('tool_use_id')}"
                    eid = hashlib.sha256(bruto.encode()).hexdigest()[:16]
                    sig = assinaturas(o["tool"], o["input"])["primary"]
                    if eid in corpus and corpus[eid]["sig_primary"] != sig:
                        sig_diverge += 1
                    linhas[eid] = dict(sig=sig, dur_s=(t1 - t0).total_seconds(), tokens=o["tokens"],
                                       is_error=bool(b.get("is_error")))
    info = dict(pares=len(linhas), no_corpus=len(set(linhas) & set(corpus)),
                so_no_arquivo=len(set(linhas) - set(corpus)), corpus_sem_par=len(set(corpus) - set(linhas)),
                sig_divergente_do_corpus=sig_diverge)
    assert info["so_no_arquivo"] == 0 and info["corpus_sem_par"] == 0 and sig_diverge == 0, info
    # best known resolution: min over SUCCESSFUL episodes of the signature, >=5 of them
    por_sig = collections.defaultdict(list)
    for eid, r in linhas.items():
        por_sig[r["sig"]].append(r)
    base = {}
    for s, rs in por_sig.items():
        ok = [r for r in rs if not r["is_error"]]
        if len(ok) < 5:
            continue
        ct = [r["tokens"] for r in ok if r["tokens"] is not None]
        base[s] = (min(r["dur_s"] for r in ok), min(ct) if ct else None)
    reg = {}
    for eid, r in linhas.items():
        if r["sig"] not in base:
            continue
        bt, bk = base[r["sig"]]
        reg[eid] = (max(0.0, r["dur_s"] - bt),
                    max(0.0, r["tokens"] - bk) if bk is not None and r["tokens"] is not None else None)
    info.update(assinaturas_com_piso=len(base), assinaturas_sem_piso=len(por_sig) - len(base),
                episodios_com_regret=len(reg))
    return reg, info


def h2(cfg: Config, ctx: dict, reg: dict) -> dict:
    eps = ctx["eps"][cfg.painel]          # regret does not depend on verdicts; panel irrelevant
    na = predicado_janela(cfg.janela, ctx["jan"])
    excl = {EPOCH_VAZIO} if cfg.conjunto == "19" else set()
    ok_unid = None if cfg.washout_in_denominator == "sim" else unidades_elegiveis(eps, cfg.sem_atravessadas)
    soma = collections.defaultdict(lambda: collections.defaultdict(float))
    for e in eps:
        k = e.epoch.strftime("%Y-%m-%d")
        if not (JANELA_INI <= k <= JANELA_FIM) or k not in ctx["arm"] or k in excl:
            continue
        if not na(e) or e.offset_h < WASHOUT_H or e.id not in reg:
            continue
        if ok_unid is not None and (e.epoch, e.sessao) not in ok_unid:
            continue
        rt, rk = reg[e.id]
        S = soma[e.epoch]
        S["n_t"] += 1; S["t_raw"] += rt; S["t_win"] += min(rt, WINSOR["tempo_s"])
        if rk is not None:
            S["n_k"] += 1; S["k_raw"] += rk; S["k_win"] += min(rk, WINSOR["tokens"])
    pb = collections.defaultdict(list)
    for ep in sorted(soma):
        pb[ctx["arm"][ep.strftime("%Y-%m-%d")][0]].append(ep)

    def ag_fn(num, den):
        def ag(lista):
            n = sum(soma[e][den] for e in lista)
            return {"m": (sum(soma[e][num] for e in lista) / n) if n else None}
        return ag
    rng = random.Random(SEED)
    out = {}
    for comp, den, chave in (("tempo_s", "n_t", "t"), ("tokens", "n_k", "k")):
        rw = bootstrap(ag_fn(chave + "_win", den), pb, "m", rng, BOOT)
        rr_ = bootstrap(ag_fn(chave + "_raw", den), pb, "m", rng, BOOT)
        for r in (rw, rr_):
            r["ic95"] = r["ic95_bca"] if cfg.ic == "bca" else r["ic95_percentil"]
        ag_w, ag_r = ag_fn(chave + "_win", den), ag_fn(chave + "_raw", den)
        out[comp] = dict(
            winsorizado_em=WINSOR[comp],
            por_braco={b: dict(n_epochs=len(v), n_episodios=int(sum(soma[e][den] for e in v)),
                               media_winsorizada=round(ag_w(v)["m"], 6), media_bruta=round(ag_r(v)["m"], 6))
                       for b, v in sorted(pb.items())},
            estimador_winsorizado=rw, estimador_bruto=rr_,
        )
    # sharp-null test on RAW per-epoch means (PREREG §4.2: "the permutation test on H2 runs on
    # raw, unwinsorized values"), trend-residualized like every §5 permutation outcome
    usaveis = [ep.strftime("%Y-%m-%d") for ep in sorted(soma) if soma[ep]["n_t"] > 0 and soma[ep]["n_k"] > 0]
    por_k = {ep.strftime("%Y-%m-%d"): soma[ep] for ep in soma}
    desf = {"H2_tempo": [por_k[k]["t_raw"] / por_k[k]["n_t"] for k in usaveis],
            "H2_tokens": [por_k[k]["k_raw"] / por_k[k]["n_k"] for k in usaveis]}
    real = {k: v[0] for k, v in ctx["arm"].items()}
    rr, _, _, _ = _rerand_desfechos(desf, usaveis, real, ctx["mapas"], [])
    out["tempo_s"]["rerand_bruto"] = rr["H2_tempo"]; out["tokens"]["rerand_bruto"] = rr["H2_tokens"]
    out["epochs"] = len(usaveis)
    return out


# ─── Holm ────────────────────────────────────────────────────────────────────
def holm(ps: dict, alpha=0.05) -> dict:
    """Holm step-down. Members with p=None are unevaluable: variant A keeps them in m
    (as p=1, they can never reject); variant B drops them from the family."""
    def run(fam):
        ordem = sorted(fam.items(), key=lambda kv: kv[1])
        m = len(ordem); adj = {}; prev = 0.0; parou = False; rej = {}
        for i, (k, p) in enumerate(ordem):
            a = min(1.0, max(prev, (m - i) * p)); prev = a; adj[k] = round(a, 5)
            if not parou and p <= alpha / (m - i):
                rej[k] = True
            else:
                parou = True; rej[k] = False
        return dict(m=m, p_ajustado=adj, rejeita=rej)
    A = run({k: (1.0 if v is None else v) for k, v in ps.items()})
    B = run({k: v for k, v in ps.items() if v is not None})
    return dict(p_brutos=ps, A_familia_registada_inavaliaveis_como_p1=A, B_so_membros_avaliaveis=B)


def resumo(perna: dict) -> dict:
    out = {}
    for h, r in perna["hipoteses"].items():
        out[h] = dict(ponto=r["dif_pontual"], ic95=r["ic95"], construcao=r["construcao"], p_rerand=r["p_rerand"],
                      horas={b: v["horas_sessao"] for b, v in perna["por_braco"].items()},
                      oportunidades={b: v["oportunidades"] for b, v in perna["por_braco"].items()},
                      repeats={b: v["repeats"] for b, v in perna["por_braco"].items()},
                      n_epochs=perna["n_epochs"])
    return out


def delta(a: dict, b: dict) -> dict:
    out = {}
    for h in ("H1", "H1a", "H1c"):
        x, y = a["hipoteses"][h], b["hipoteses"][h]
        out[h] = dict(d_ponto=round(y["dif_pontual"] - x["dif_pontual"], 6),
                      d_ic_inf=round(y["ic95"][0] - x["ic95"][0], 6),
                      d_ic_sup=round(y["ic95"][1] - x["ic95"][1], 6),
                      d_p_rerand=round(y["p_rerand"] - x["p_rerand"], 5),
                      ic_contem_zero=[x["ic95"][0] <= 0 <= x["ic95"][1], y["ic95"][0] <= 0 <= y["ic95"][1]],
                      p_menor_005=[x["p_rerand"] < 0.05, y["p_rerand"] < 0.05])
    return out


def pos_expiracao(ctx) -> dict:
    """What the expiry cut removes from 09-20, under each panel."""
    out = {}
    for painel, eps in ctx["eps"].items():
        Qd = por_epoch(eps, ctx["b_ids"], predicado_janela("data", ctx["jan"]))
        Qe = por_epoch(eps, ctx["b_ids"], predicado_janela("so_expiracao", ctx["jan"]))
        ep = [e for e in Qd["dentro"] if e.strftime("%Y-%m-%d") == "2026-09-20"][0]
        n_pos = sum(1 for e in eps if e.epoch == ep and e.ts >= EXPIRACAO)
        out[painel] = dict(episodios_pos_expiracao=n_pos,
                           oportunidades_removidas=round(Qd["oport"][ep] - Qe["oport"][ep], 4),
                           repeats_removidos=round(Qd["repet"][ep] - Qe["repet"][ep], 4),
                           horas_sessao_antes=round(Qd["h_ep"][ep], 4), horas_sessao_depois=round(Qe["h_ep"][ep], 4))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k, v in DEFAULTS.items():
        ap.add_argument("--" + k.replace("_", "-"), default=str(v))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    P = {k: Path(getattr(a, k)) for k in DEFAULTS}

    with tempfile.TemporaryDirectory() as td:
        v3 = carregar_verdicts(P["verdicts"])
        vs, painel_info = verdicts_substituicao(P["verdicts"], P["verdicts_ds"], Path(td))
    ctx = dict(
        eps={"3fam": carregar_episodios(P["episodes"], v3),
             "substituicao": carregar_episodios(P["episodes"], vs)},
        b_ids={l.strip() for l in P["estrato_b"].read_text().splitlines() if l.strip()},
        arm={e["epoch_inicio"]: (e["arm"], float(e["w"]))
             for e in json.loads(P["assignment"].read_text())["epochs"]},
        jan=janelas_de_exposicao(P["serving"]),
    )
    datas = [k for k in sorted(ctx["arm"]) if JANELA_INI <= k <= JANELA_FIM]
    ctx["mapas"] = mapas_rerand(BOOT, datas)

    # ── (b-i) control: the current switches must rebuild the locked files byte for byte
    itt_txt, _ = reproduzir_itt(ctx, a)
    rr_txt = reproduzir_rerand(ctx)
    controle = dict(
        ITT=dict(sha256_travado=sha(P["locked_itt"]),
                 sha256_reconstruido=hashlib.sha256(itt_txt.encode()).hexdigest()),
        RERANDOMIZACAO=dict(sha256_travado=sha(P["locked_rerand"]),
                            sha256_reconstruido=hashlib.sha256(rr_txt.encode()).hexdigest()),
    )
    for v in controle.values():
        v["identico"] = v["sha256_travado"] == v["sha256_reconstruido"]
    if not all(v["identico"] for v in controle.values()):
        print(json.dumps(controle, indent=2)); return 2

    # ── legs
    pernas = {"atual": ATUAL, "registrado": REGISTRADO}
    for campo in SWITCHES:
        pernas["so_" + campo] = replace(ATUAL, **{campo: getattr(REGISTRADO, campo)})
        pernas["registrado_sem_" + campo] = replace(REGISTRADO, **{campo: getattr(ATUAL, campo)})
    pernas["so_janela_expiracao"] = replace(ATUAL, janela="so_expiracao")
    pernas["so_janela_offsets"] = replace(ATUAL, janela="so_offsets")
    # diagnostic, NOT a switch: PREREG §2 item 3 boundary-straddling sessions (flag + sensitivity)
    pernas["diag_registrado_sem_sessoes_atravessadas"] = replace(REGISTRADO, sem_atravessadas=True)
    R = {k: correr_perna(c, ctx) for k, c in pernas.items()}

    # switch (5) at the locked value must give back v1's registered analysis, field for field
    v1 = json.loads(P["v1_registrado"].read_text())["resumo"]["registrado"]
    v1_agora = json.loads(json.dumps(resumo(R["registrado_sem_washout_in_denominator"]), default=str))
    controle_v1 = dict(arquivo=str(P["v1_registrado"].relative_to(P2)), sha256=sha(P["v1_registrado"]),
                       identico=v1_agora == v1)
    if not controle_v1["identico"]:
        print(json.dumps(dict(v1=v1, agora=v1_agora), indent=1)); return 3

    # current leg must agree with the locked numbers it was rebuilt from
    trav = json.loads(P["locked_itt"].read_text())["primario"]
    for h, ch in (("H1", "H1_diferenca"), ("H1a", "H1a_diferenca"), ("H1c", "H1c_diferenca")):
        assert R["atual"]["hipoteses"][h]["dif_pontual"] == trav[ch]["dif_pontual"]
        assert R["atual"]["hipoteses"][h]["ic95"] == trav[ch]["ic95"]

    reg, reg_info = regret_por_episodio(P["archive"], {json.loads(l)["episode_id"]: json.loads(l)
                                                        for l in P["episodes"].read_text().splitlines() if l.strip()})
    H2 = {"registrado": h2(REGISTRADO, ctx, reg), "atual": h2(ATUAL, ctx, reg),
          "registrado_sem_washout_in_denominator": h2(R["registrado_sem_washout_in_denominator"]["_cfg"], ctx, reg)}

    def familia(perna, h2r):
        return holm({"H1a": perna["hipoteses"]["H1a"]["p_rerand"], "H1b": None,
                     "H1c": perna["hipoteses"]["H1c"]["p_rerand"],
                     "H2_tempo": h2r["tempo_s"]["rerand_bruto"]["p_bilateral"],
                     "H2_tokens": h2r["tokens"]["rerand_bruto"]["p_bilateral"]})
    def familia_troca(perna, h2r, com_h1c):
        ps = {"H1": perna["hipoteses"]["H1"]["p_rerand"], "H1a": perna["hipoteses"]["H1a"]["p_rerand"],
              "H1b": None,
              "H2_tempo": h2r["tempo_s"]["rerand_bruto"]["p_bilateral"],
              "H2_tokens": h2r["tokens"]["rerand_bruto"]["p_bilateral"]}
        if com_h1c:
            ps["H1c"] = perna["hipoteses"]["H1c"]["p_rerand"]
        return holm(ps)
    multiplicidade = {
        nome: dict(
            leitura_depositada=dict(
                regra="PREREG l.1025: H1 primary, alone at alpha=0.05; H1a-c + H2 Holm within the secondary family",
                H1_isolada_a_005=dict(p=R[nome]["hipoteses"]["H1"]["p_rerand"],
                                      rejeita=R[nome]["hipoteses"]["H1"]["p_rerand"] < 0.05),
                holm_H1a_H1b_H1c_H2x2=familia(R[nome], H2[nome])),
            leitura_da_troca=dict(
                regra="PROSPECTIVE-ESTIMAND §3-bis: H1c primary; H1/H1a/H1b secondary; the registration's rule "
                      "for secondaries (Holm) applied to them. Variant m6/m5 keeps H1c in the family (review F2); "
                      "variant sem_H1c tests H1c alone and Holms the rest",
                H1c_primaria_isolada_a_005=dict(p=R[nome]["hipoteses"]["H1c"]["p_rerand"],
                                                rejeita=R[nome]["hipoteses"]["H1c"]["p_rerand"] < 0.05),
                holm_H1_H1a_H1b_H1c_H2x2_m6_m5=familia_troca(R[nome], H2[nome], True),
                holm_H1_H1a_H1b_H2x2_sem_H1c_m5_m4=familia_troca(R[nome], H2[nome], False)),
            # v1 keys kept so readers of v1 find them unchanged in meaning
            H1_isolada_a_005=dict(p=R[nome]["hipoteses"]["H1"]["p_rerand"],
                                  rejeita=R[nome]["hipoteses"]["H1"]["p_rerand"] < 0.05),
            H1c_primaria_PROSPECTIVE_ESTIMAND=dict(p=R[nome]["hipoteses"]["H1c"]["p_rerand"],
                                                   rejeita=R[nome]["hipoteses"]["H1c"]["p_rerand"] < 0.05),
            holm_H1a_H1b_H1c_H2x2=familia(R[nome], H2[nome]))
        for nome in ("atual", "registrado", "registrado_sem_washout_in_denominator")}

    script = Path(__file__).resolve()
    saida = dict(
        objeto="Paper B ITT v2 — registered analysis with five switches (washout fix added) vs implemented analysis",
        gerado_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        proveniencia=dict(
            script=dict(caminho=str(script.relative_to(P2)), sha256=sha(script)),
            importados={n: sha(P2 / n) for n in ("pilot_replay.py", "assign_arms.py", "rerandomizacao.py",
                                                  "task_regret.py", "extract_episodes.py", "estimador_itt.py")},
            entradas={k: dict(caminho=str(p).replace(str(Path.home()), "~"), sha256=sha(p)) for k, p in P.items()},
            seed_bootstrap=SEED, replicas=BOOT, seed_prefix_rerand=SEED_PREFIX,
            python=platform.python_version(),
        ),
        controle_reproducao=controle,
        controle_v1_registrado=controle_v1,
        painel=painel_info,
        janelas_de_exposicao={k: [x.isoformat() if x else None for x in v] for k, v in ctx["jan"].items()},
        corte_pos_expiracao=pos_expiracao(ctx),
        resumo={k: resumo(R[k]) for k in ("atual", "registrado", "registrado_sem_washout_in_denominator",
                                          "diag_registrado_sem_sessoes_atravessadas")},
        washout=dict(
            regra="PREREG l.642/l.644/l.1036: units (epoch, session) starting inside the 2 h washout leave "
                  "the session-hour denominator AND the outcomes; a_past corpus never cut",
            registrado=R["registrado"]["washout_diagnostico"],
            delta_v1_para_v2=delta(R["registrado_sem_washout_in_denominator"], R["registrado"]),
        ),
        deltas_um_a_um={k: delta(R["atual"], R[k]) for k in R if k.startswith("so_")},
        deltas_registrado_menos_um={k: delta(R[k], R["registrado"]) for k in R if k.startswith("registrado_sem_")},
        delta_atual_para_registrado=delta(R["atual"], R["registrado"]),
        diagnostico_sessoes_atravessadas=dict(
            regra="PREREG §2 item 3: boundary-straddling sessions belong to the epoch of their start, flagged, "
                  "with/without sensitivity. NOT applied as a switch; this leg drops units whose session "
                  "has episodes in more than one epoch (the registered 'without' leg; the 'with' leg, attribution to the start epoch, is not implemented)",
            delta_registrado_para_sem=delta(R["registrado"], R["diag_registrado_sem_sessoes_atravessadas"])),
        multiplicidade=multiplicidade,
        H1b="UNEVALUABLE — collision between the 2026-07-29 Opportunity lock and the 2026-08-16 H1b lock (DEVIATIONS §10.32)",
        H2=dict(definicao="PREREG §4.2 + task_regret.py: regret = max(0, x - min over successful (not is_error) "
                          "episodes of the same sig_primary, >=5 of them); tokens = input+output+cache_creation; "
                          "winsorized at the LOCKED p95 for the estimator, raw for the sharp-null test",
                escolhas_nao_fixadas_pelo_registo=[
                    "baseline ('best known resolution') computed over the whole locked corpus (5,951 episodes, "
                    "2026-08-23..2026-09-21), both arms pooled, arm-blind",
                    "population = every post-washout action in the analysis epochs (not only opportunities)",
                    "effect = difference of per-arm means pooled over episodes (ratio of sums), same epoch "
                    "bootstrap/BCa as H1; sharp-null statistic = per-epoch raw mean, trend-residualized",
                ],
                instrumento=reg_info, **H2),
        H3="NOT COMPUTABLE — see RESULTADO.md",
        pernas={k: limpa(v) for k, v in R.items()},
    )
    Path(a.out).write_text(json.dumps(saida, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(dict(controle=controle, resumo=saida["resumo"], multiplicidade=multiplicidade),
                     indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
