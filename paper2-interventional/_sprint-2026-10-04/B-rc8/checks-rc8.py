#!/usr/bin/env python3
"""Numbers Paper B rc8 needs that no earlier artifact holds (sprint 2026-10-04, rc8).

rc8 reports the analysis AS REGISTERED (`out/ITT-REGISTRADO-2026-10-05.json`, produced by
`measurement/estimador_itt_registrado.py`) and keeps the analysis of rc7 as a sensitivity.
This script is read-only on every input; it writes this JSON (default `checks-rc8.json`
beside it) and, in block C, one NEW artifact `out/C12-EMPATES-REGISTRADO-2026-10-05.json`
(the rc4 files `out/C12-EMPATES-*.json` are read, never written).

COMPOSITION, NOT REIMPLEMENTATION. Every rule is imported:
  por_epoch, agrega_fn, montar, bootstrap, predicado_janela, janelas_de_exposicao,
  verdicts_substituicao, Config, ATUAL, REGISTRADO, SEED, BOOT  <- estimador_itt_registrado.py
  carregar_verdicts, carregar_episodios, NIVEIS, TAU, EPOCH_H, WASHOUT_H, epoch_de <- pilot_replay.py
  votos_substantivos                                              <- sprint-c12-empates-por-braco.py
  atribuir, sha_da_atribuicao  (the rule DECLARED in ASSIGN-SEED)  <- assignment_derive.py
  build_epochs, assign, seed_from_randomness_hex (registered rule) <- assign_arms.py

Blocks (each aborts, exit 1, if a reproduced reference value does not match):
  G  guards: input sha256 equal to the provenance recorded in ITT-REGISTRADO; the leg
     builder below reproduces `pernas.atual` and `pernas.registrado` of that file exactly
     (points, both intervals, per-arm totals), and the POINTS of the two locked
     sensitivity legs (`ITT-SENSIB-PRECOMPROMETIDA.json`, `ITT-2026-09-21.json`).
  A  the registered analysis on the two declared sensitivity legs (pre-committed: the
     partials 09-01, 09-03, 09-20 removed, SPEC §9.1; post-hoc: 09-14 removed), BCa as
     registered; per-epoch session-hours under the registered window; H1 reductions and
     the proportional-dilution ratios; per-epoch volumes (§4.3, §7).
  C  the exact ties of the four-vote set under the registered window (expiry cut +
     offsets) and the 19-epoch set; the four-vote H1c point under the paper's tie rule
     and with every tie resolved as failure; ties in the registered (substitution) panel.
  D  the stopping rule of PROSPECTIVE-ESTIMAND-2026-08-30.md §3-bis: coverage measured
     in Epoch 1 (2026-09-01) against 36.7%.
  E  the assignment rule declared in ASSIGN-SEED-2026-08-30.md against assign_arms.py,
     both run offline on round 31774052's published randomness.

Usage: python3 checks-rc8.py [--out checks-rc8.json] [--c12-out ../../out/C12-EMPATES-REGISTRADO-2026-10-05.json]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import random
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
P2 = HERE.parent.parent                      # paper2-interventional/
sys.path.insert(0, str(P2))
sys.path.insert(0, str(P2 / "measurement"))
import estimador_itt_registrado as R        # noqa: E402
from pilot_replay import (                   # noqa: E402
    carregar_verdicts, carregar_episodios, NIVEIS, TAU, EPOCH_H, WASHOUT_H, parse_ts,
)
import assign_arms as AA                     # noqa: E402
import assignment_derive as AD               # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "c12", P2 / "measurement" / "sprint-c12-empates-por-braco.py")
C12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C12)

ITT_REG = P2 / "out" / "ITT-REGISTRADO-2026-10-05.json"
C12_OLD = P2 / "out" / "C12-EMPATES-COMO-FAILURE-2026-10-05.json"
SENSIB = R.LOCK / "ITT-SENSIB-PRECOMPROMETIDA.json"
CONC = P2 / "out" / "CONCENTRATION-2026-08-30.json"
DESIG = P2 / "DESIGNATION-2026-08-26.json"
PARCIAIS = ["2026-09-01", "2026-09-03", "2026-09-20"]
POS_HOC = ["2026-09-14"]
EPOCH1 = "2026-09-01"
LIMIAR_PARADA = 0.367
# ASSIGN-SEED-2026-08-30.md, section "Resultado" (published before the retraction)
RANDOMNESS = "b32cf63d65fd6ca8dbd9d9b08a0bb77efe7144f18bad3dbbfce6816d498d55fd"
SEED_PUBLICADA = "e86436153592e2655e095c58a96400ed4292b69ace6f53f65c0e41b87b290087"
SHA_ATRIB_DECLARADA = "2426d13de4cd90e6391573e9edc54786c9fb4ca4304f0ea51e09ca916e5c5bd9"


def falha(msg):
    sys.exit(f"ABORT {msg}")


def r6(x):
    return None if x is None else round(x, 6)


# ─────────────────────────────────────────────── context (as estimador_itt_registrado.main)
def contexto():
    P = {k: Path(v) for k, v in R.DEFAULTS.items()}
    reg = json.loads(ITT_REG.read_text())
    prov = reg["proveniencia"]["entradas"]
    for k, p in P.items():
        if k in ("locked_itt", "locked_rerand", "archive"):
            continue
        h = R.sha(p)
        if h != prov[k]["sha256"]:
            falha(f"G: {k} sha256 {h[:12]} != ITT-REGISTRADO provenance {prov[k]['sha256'][:12]}")
    if R.sha(P2 / reg["proveniencia"]["script"]["caminho"]) != reg["proveniencia"]["script"]["sha256"]:
        falha("G: estimador_itt_registrado.py changed since ITT-REGISTRADO was produced")
    with tempfile.TemporaryDirectory() as td:
        v3 = carregar_verdicts(P["verdicts"])
        vs, info = R.verdicts_substituicao(P["verdicts"], P["verdicts_ds"], Path(td))
    ctx = dict(
        P=P, reg=reg, v3=v3, vs=vs, painel=info,
        eps={"3fam": carregar_episodios(P["episodes"], v3),
             "substituicao": carregar_episodios(P["episodes"], vs)},
        b_ids={l.strip() for l in P["estrato_b"].read_text().splitlines() if l.strip()},
        arm={e["epoch_inicio"]: (e["arm"], float(e["w"]))
             for e in json.loads(P["assignment"].read_text())["epochs"]},
        jan=R.janelas_de_exposicao(P["serving"]),
    )
    return ctx


def perna(ctx, cfg, extra=(), eps=None):
    """estimador_itt_registrado.correr_perna without the re-randomization, plus extra
    epochs removed. Fresh rng(SEED) per leg, as correr_perna does."""
    eps = ctx["eps"][cfg.painel] if eps is None else eps
    Q = R.por_epoch(eps, ctx["b_ids"], R.predicado_janela(cfg.janela, ctx["jan"]))
    ag = R.agrega_fn(Q)
    excl = ({R.EPOCH_VAZIO} if cfg.conjunto == "19" else set()) | set(extra)
    pb = R.montar(Q, ctx["arm"], excl)
    rng = random.Random(R.SEED)
    hip = {}
    for nome, met in (("H1", "H1_densidade"), ("H1a", "H1a_taxa_oport"), ("H1c", "H1c_prop")):
        r = R.bootstrap(ag, pb, met, rng, R.BOOT)
        r["ic95"] = r["ic95_bca"] if cfg.ic == "bca" else r["ic95_percentil"]
        r["construcao"] = ("BCa" if not r["bca"]["fallback"] else "percentile (BCa fallback)") \
            if cfg.ic == "bca" else "percentile"
        hip[nome] = r
    horas = {ep.strftime("%Y-%m-%d"): round(Q["h_ep"][ep], 4) for b in pb.values() for ep in b}
    return dict(config=dict(cfg.__dict__), removidos=sorted(excl),
                n_epochs={b: len(v) for b, v in sorted(pb.items())},
                por_braco={b: ag(v) for b, v in sorted(pb.items())},
                hipoteses=hip, horas_por_epoch=dict(sorted(horas.items())),
                _Q=Q, _pb=pb, _ag=ag)


def limpa(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


# ─────────────────────────────────────────────── G: guards
def bloco_G(ctx):
    reg = ctx["reg"]
    out = {}
    for nome, cfg in (("atual", R.ATUAL), ("registrado", R.REGISTRADO)):
        p = perna(ctx, cfg)
        ref = reg["pernas"][nome]
        for h in ("H1", "H1a", "H1c"):
            for k in ("dif_pontual", "ic95_percentil", "ic95_bca", "ic95"):
                if p["hipoteses"][h][k] != ref["hipoteses"][h][k]:
                    falha(f"G: leg {nome} {h}.{k} {p['hipoteses'][h][k]} != artifact {ref['hipoteses'][h][k]}")
        if p["por_braco"] != ref["por_braco"]:
            falha(f"G: leg {nome} per-arm totals differ from the artifact")
        out[nome] = "reproduced: points, percentile and BCa intervals, per-arm totals"
    # the POINTS of the locked sensitivity legs (their intervals came from another rng stream)
    sens = json.loads(SENSIB.read_text())["sensibilidade"]
    itt = json.loads(ctx["P"]["locked_itt"].read_text())["sensibilidade"]
    for rot, extra, art in (("pre-committed", PARCIAIS, sens), ("post-hoc", POS_HOC, itt)):
        p = perna(ctx, R.ATUAL, extra)
        if sorted(art["epochs_removidos"]) != sorted(extra):
            falha(f"G: {rot} artifact removes {art['epochs_removidos']}, not {extra}")
        for h, ch in (("H1", "H1_diferenca"), ("H1a", "H1a_diferenca"), ("H1c", "H1c_diferenca")):
            if p["hipoteses"][h]["dif_pontual"] != art[ch]["dif_pontual"]:
                falha(f"G: {rot} {h} point {p['hipoteses'][h]['dif_pontual']} != locked {art[ch]['dif_pontual']}")
        for b in ("treatment", "control"):
            if p["por_braco"][b]["horas_sessao"] != art["por_braco"][b]["horas_sessao"]:
                falha(f"G: {rot} {b} hours differ from the locked leg")
        out[f"atual_{rot}"] = "reproduced: points and per-arm hours of the locked leg"
    return out


# ─────────────────────────────────────────────── A: registered sensitivity legs
def resumo_perna(p):
    h = p["hipoteses"]
    return dict(
        removidos=p["removidos"], n_epochs=p["n_epochs"], por_braco=p["por_braco"],
        **{k: dict(ponto=v["dif_pontual"], ic95=v["ic95"], construcao=v["construcao"],
                   ic95_percentil=v["ic95_percentil"], bca=v["bca"],
                   exclui_zero=(v["ic95"][1] < 0 or v["ic95"][0] > 0))
           for k, v in h.items()})


def bloco_A(ctx):
    legs = {"registrado": perna(ctx, R.REGISTRADO),
            "registrado_precomprometida": perna(ctx, R.REGISTRADO, PARCIAIS),
            "registrado_pos_hoc_sem_0914": perna(ctx, R.REGISTRADO, POS_HOC)}
    out = {k: resumo_perna(v) for k, v in legs.items()}
    reg = legs["registrado"]
    arm = ctx["arm"]
    horas = reg["horas_por_epoch"]
    tot_t = sum(v for k, v in horas.items() if arm[k][0] == "treatment")
    pico = max(horas, key=horas.get)
    outros = {k: v for k, v in horas.items() if k != pico}
    out["horas_por_epoch_registrado"] = dict(
        por_epoch=horas, pico=pico, pico_h=horas[pico],
        pico_share_tratamento=round(horas[pico] / tot_t, 4),
        outros_n=len(outros), outros_min=min(outros.values()), outros_max=max(outros.values()),
        outros_min_epoch=min(outros, key=outros.get))
    # H1 reductions and proportional-dilution ratios (shares as in rc7: 3.14%, 4.56%, 6.85%)
    shares = {"calibracao_11_de_350": 11 / 350, "realizada_335_de_7350": 335 / 7350,
              "maior_por_epoch_6.85pct": 0.0685}
    red = {}
    for k in ("registrado", "registrado_pos_hoc_sem_0914", "registrado_precomprometida"):
        pb = legs[k]["por_braco"]
        t, c = pb["treatment"]["H1_densidade"], pb["control"]["H1_densidade"]
        red[k] = dict(H1_t=t, H1_c=c, reducao=round(1 - t / c, 4),
                      razoes={s: round((1 - t / c) / v, 2) for s, v in shares.items()})
    out["H1_reducoes_e_razoes"] = red
    # per-epoch volumes
    vol = {}
    for k in ("registrado", "registrado_pos_hoc_sem_0914"):
        pb = legs[k]["por_braco"]
        vol[k] = {b: dict(oport_por_epoch=round(pb[b]["oportunidades"] / pb[b]["n_epochs"], 1),
                          repeats_por_epoch=round(pb[b]["repeats"] / pb[b]["n_epochs"], 2),
                          horas_por_epoch=round(pb[b]["horas_sessao"] / pb[b]["n_epochs"], 3))
                  for b in ("treatment", "control")}
    out["volumes_por_epoch"] = vol
    # H1c: relative reduction and distance from total elimination
    h = reg["hipoteses"]["H1c"]; c = reg["por_braco"]["control"]["H1c_prop"]
    # H1 = H1c x H1a, cell by cell (registered legs)
    ident = {}
    for k, p in legs.items():
        for b, x in p["por_braco"].items():
            ident[f"{k}/{b}"] = abs(x["H1c_prop"] * x["H1a_taxa_oport"] - x["H1_densidade"]) / x["H1_densidade"]
    out["identidade_H1_igual_H1c_vezes_H1a"] = dict(celulas=len(ident),
                                                     erro_relativo_max=float(f"{max(ident.values()):.2e}"))
    out["H1c_registrado"] = dict(
        controle=c, reducao_relativa=round(-h["dif_pontual"] / c, 4),
        eliminacao_total=-c, ic95=h["ic95"],
        distancia_ic_inferior_a_eliminacao_total=round(h["ic95"][0] - (-c), 4))
    return out, legs


# ─────────────────────────────────────────────── C: ties of the four-vote set, registered window
def bloco_C(ctx, c12_out: Path):
    P = ctx["P"]
    with tempfile.TemporaryDirectory() as td:
        q = Path(td) / "q.jsonl"
        q.write_text(P["verdicts"].read_text() + P["verdicts_ds"].read_text())
        v4 = carregar_verdicts(q)
    votos4 = C12.votos_substantivos([P["verdicts"], P["verdicts_ds"]])
    corte = NIVEIS.index(TAU)
    empate = {ep for ep, pp in votos4.items()
              if len(pp) >= 3 and len(pp) % 2 == 0
              and 2 * sum(1 for x in pp.values() if x >= corte) == len(pp)}
    if len(empate) != 28 or any(v4.get(ep) != "not_failure" for ep in empate):
        falha(f"C: tie census {len(empate)} != 28, or a tie not resolved to not_failure")
    # registered panel: substitution only below the three-verdict floor -> no tie possible
    votos_sub = collections.defaultdict(dict)
    for ep, pp in votos4.items():
        if ep in ctx["v3"]:
            votos_sub[ep] = {k: v for k, v in pp.items() if k != "deepseek"}
        else:
            votos_sub[ep] = pp
    empates_sub = sorted(ep for ep, pp in votos_sub.items()
                         if len(pp) >= 3 and len(pp) % 2 == 0
                         and 2 * sum(1 for x in pp.values() if x >= corte) == len(pp)
                         and ep in ctx["vs"])
    v4f = dict(v4)
    for ep in empate:
        v4f[ep] = "failure"
    eps4 = carregar_episodios(P["episodes"], v4)
    eps4f = carregar_episodios(P["episodes"], v4f)
    arm = {k: v[0] for k, v in ctx["arm"].items()}
    peso_b = len([e for e in eps4 if not e.err]) / len(ctx["b_ids"])
    primeiro = {}
    for e in eps4:
        if e.estado == "failure" and e.sig not in primeiro:
            primeiro[e.sig] = e.epoch
    limiar = timedelta(hours=EPOCH_H)

    def oportunidade(e):                       # sprint-c12-empates-por-braco.py, as written
        if e.offset_h < WASHOUT_H:
            return 0.0
        t0 = primeiro.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            return 0.0
        if e.err:
            return 1.0
        return peso_b if e.id in ctx["b_ids"] else 0.0

    def censo(janela, excl):
        ok = R.predicado_janela(janela, ctx["jan"])
        zero = lambda: dict(empates=0, empates_oportunidade=0, empates_oportunidade_peso=0.0)  # noqa: E731
        pb = {"treatment": zero(), "control": zero()}
        fora = collections.Counter()
        for e in eps4:
            if e.id not in empate:
                continue
            k = e.epoch.strftime("%Y-%m-%d")
            if not (R.JANELA_INI <= k <= R.JANELA_FIM) or k not in arm:
                fora["fora_da_janela_de_datas"] += 1
                continue
            if k in excl:
                fora["epoch_excluido_" + k] += 1
                continue
            if not ok(e):
                fora["fora_da_exposicao_" + k] += 1
                continue
            d = pb[arm[k]]
            d["empates"] += 1
            w = oportunidade(e)
            if w:
                d["empates_oportunidade"] += 1
                d["empates_oportunidade_peso"] += w
        for d in pb.values():
            d["empates_oportunidade_peso"] = round(d["empates_oportunidade_peso"], 3)
        return dict(por_braco=pb, fora=dict(fora))

    def h1c(eps, janela, excl):
        Q = R.por_epoch(eps, ctx["b_ids"], R.predicado_janela(janela, ctx["jan"]))
        ag = R.agrega_fn(Q)
        pb = R.montar(Q, ctx["arm"], set(excl))
        a = {b: ag(v) for b, v in pb.items()}
        return dict(por_braco={b: dict(oportunidades=a[b]["oportunidades"], repeats=a[b]["repeats"],
                                       H1c_prop=a[b]["H1c_prop"]) for b in sorted(a)},
                    diferenca=round(a["treatment"]["H1c_prop"] - a["control"]["H1c_prop"], 6))

    # guard: the rc4 numbers under the current window and the 20-epoch set
    old = json.loads(C12_OLD.read_text())
    c_atual = censo("data", set())
    for b in ("treatment", "control"):
        for k in ("empates", "empates_oportunidade", "empates_oportunidade_peso"):
            if c_atual["por_braco"][b][k] != old["por_braco"][b][k]:
                falha(f"C: current-window census {b}.{k} {c_atual['por_braco'][b][k]} != rc4 {old['por_braco'][b][k]}")
    if c_atual["fora"].get("fora_da_janela_de_datas") != old["empates_fora_da_janela"]:
        falha("C: ties outside the window differ from rc4")
    a4, a4f = h1c(eps4, "data", []), h1c(eps4f, "data", [])
    if a4["diferenca"] != old["h1c_ponto"]["diferenca_4votos"] or \
            a4f["diferenca"] != old["contrafactual_empate_como_failure"]["diferenca_4votos_empate_como_failure"]:
        falha(f"C: four-vote H1c points {a4['diferenca']}/{a4f['diferenca']} != rc4")
    excl = {R.EPOCH_VAZIO}
    c_reg = censo("exposicao", excl)
    r4, r4f = h1c(eps4, "exposicao", excl), h1c(eps4f, "exposicao", excl)
    saida = dict(
        gerado_em="2026-10-05",
        objeto="Paper B rc8: exact ties of the four-vote set under the REGISTERED window "
               "(expiry cut + SPEC §2 offsets) and the 19-epoch set (09-02 excluded); "
               "the rc4 files out/C12-EMPATES-*.json are unchanged",
        gerado_por="_sprint-2026-10-04/B-rc8/checks-rc8.py (block C)",
        regra="carregar_verdicts (pilot_replay.py): floor 3 substantive; strict majority; "
              "tie (n/2 failures, n even) -> not_failure; failure = level >= TAU",
        janela_registrada={k: [x.isoformat() if x else None for x in v] for k, v in ctx["jan"].items()},
        conjunto_excluido=sorted(excl),
        controle_rc4_reproduzido="ok: per-arm ties, tied opportunities and HT weights, ties outside the "
                                 "window, four-vote H1c points (-0.020843 / -0.026571) under the current window",
        empates_total_conjunto_4v=len(empate),
        empates_no_painel_registrado_substituicao=len(empates_sub),
        censo_registrado=c_reg,
        censo_atual=c_atual,
        h1c_ponto_4votos_registrado=dict(regra_do_paper=r4, empate_como_failure=r4f,
                                         nota="point only; no interval; not a result of the paper"),
        h1c_ponto_4votos_atual=dict(regra_do_paper=a4, empate_como_failure=a4f),
    )
    c12_out.write_text(json.dumps(saida, indent=2, ensure_ascii=False) + "\n")
    return saida


# ─────────────────────────────────────────────── D: the stopping rule of §3-bis
def bloco_D(ctx):
    conc = json.loads(CONC.read_text())
    promovidas = set(conc["assinaturas_promovidas_sob_w2"])
    if (conc["oportunidades"], conc["oportunidades_cobertas"]) != (1526, 611):
        falha("D: CONCENTRATION artifact is not the 1,526 / 611 the threshold was derived from")
    desig = set(json.loads(DESIG.read_text())["designados"])
    ini = datetime(2026, 9, 1, 9, tzinfo=timezone.utc)
    fim = ini + timedelta(hours=EPOCH_H)
    active = ctx["jan"][EPOCH1][0]
    # (a) the rule the threshold was derived from (concentracao-de-oportunidades.py, as
    #     written): an action is an opportunity if its sig_primary already had an
    #     is_error episode EARLIER in the corpus; covered if that signature is promoted.
    eps = [json.loads(l) for l in ctx["P"]["episodes"].read_text().splitlines() if l.strip()]
    eps.sort(key=lambda e: e.get("ts", ""))
    ja = set(); ops = []
    for e in eps:
        if e.get("sig_primary") in ja:
            ops.append(e)
        if e.get("is_error"):
            ja.add(e.get("sig_primary"))
    def cob(lista, conj):
        n = len(lista); c = sum(1 for e in lista if e["sig_primary"] in conj)
        if not n:
            return dict(oportunidades=0, cobertas=0, cobertura=None)
        z = 1.959964; ph = c / n; den = 1 + z * z / n          # Wilson 95%, descriptive only
        mid = (ph + z * z / (2 * n)) / den
        half = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / den
        return dict(oportunidades=n, cobertas=c, cobertura=round(ph, 4),
                    wilson95=[round(mid - half, 4), round(mid + half, 4)])
    def em(e, t0, t1):
        t = parse_ts(e["ts"]); return t0 <= t < t1
    a = {
        "epoch_1_inteiro": cob([e for e in ops if em(e, ini, fim)], promovidas),
        "epoch_1_pos_washout": cob([e for e in ops if em(e, ini + timedelta(hours=WASHOUT_H), fim)], promovidas),
        "epoch_1_fase_active": cob([e for e in ops if em(e, active, fim)], promovidas),
        "epoch_1_inteiro_19_grupos_designados": cob([e for e in ops if em(e, ini, fim)], desig),
    }
    # (b) the trial's own opportunity rule (registered estimator: adjudicated failure of the
    #     same signature >= 1 epoch before, washout, HT weights, registered window and panel)
    def ponderada(conj):
        base = R.predicado_janela("exposicao", ctx["jan"])
        eps_s = ctx["eps"]["substituicao"]
        Qall = R.por_epoch(eps_s, ctx["b_ids"], base)
        Qcov = R.por_epoch(eps_s, ctx["b_ids"], lambda e: base(e) and e.sig in conj)
        ep1 = [ep for ep in Qall["dentro"] if ep.strftime("%Y-%m-%d") == EPOCH1][0]
        o, c = Qall["oport"][ep1], Qcov["oport"][ep1]
        return dict(oportunidades_ponderadas=round(o, 3), cobertas_ponderadas=round(c, 3),
                    cobertura=round(c / o, 4) if o else None)
    b = {"assinaturas_promovidas_7": ponderada(promovidas),
         "grupos_designados_19": ponderada(desig)}
    prim = a["epoch_1_inteiro"]["cobertura"]
    return dict(
        regra="PROSPECTIVE-ESTIMAND-2026-08-30.md §3-bis: if coverage measured in Epoch 1 falls below "
              "36.7%, the interventional arm ends with a null 'por impossibilidade de desenho'",
        limiar=LIMIAR_PARADA,
        definicao_de_cobertura="out/CONCENTRATION-2026-08-30.json (measurement/concentracao-de-oportunidades.py): "
                               "opportunities whose signature the dose can promote / all opportunities; "
                               "40.0% = 611/1,526 in the planning corpus",
        assinaturas_promovidas=sorted(promovidas),
        epoch_1=EPOCH1, epoch_1_arm=ctx["arm"][EPOCH1],
        a_regra_do_artefato_de_planejamento=a,
        b_regra_de_oportunidade_do_ensaio=b,
        cobertura_primaria=prim,
        abaixo_do_limiar=prim < LIMIAR_PARADA,
        todas_as_leituras_abaixo_do_limiar=all(
            x["cobertura"] < LIMIAR_PARADA for x in list(a.values()) + list(b.values())),
    )


# ─────────────────────────────────────────────── E: declared rule vs assign_arms.py
def bloco_E(ctx):
    seed = AA.seed_from_randomness_hex(RANDOMNESS)
    if seed != SEED_PUBLICADA or seed != hashlib.sha256(RANDOMNESS.encode("ascii")).hexdigest():
        falha("E: seed does not follow from the published randomness")
    dec = AD.atribuir(seed)                                   # rule of ASSIGN-SEED (global sort)
    if AD.sha_da_atribuicao(dec) != SHA_ATRIB_DECLARADA:
        falha("E: declared rule does not reproduce the published sha256_da_atribuicao 2426d13d…")
    eps234 = AA.build_epochs("2026-09-01", 234)
    reg = AA.assign(eps234, seed)                            # registered rule
    canon = json.loads((P2 / "ASSIGNMENT.json").read_text())
    if canon["randomness_hex"] != RANDOMNESS or canon["atribuicao"] != reg:
        falha("E: assign_arms.py on round 31774052 does not reproduce ASSIGNMENT.json")
    serv = {e["epoch_inicio"]: e for e in json.loads((P2 / "ASSIGNMENT-SERVING.json").read_text())["epochs"]}
    for d, g in reg.items():
        want = ("control", 0.0) if g == AA.CONTROL else ("treatment", float(g[1:]))
        if (serv[d]["arm"], float(serv[d]["w"])) != want:
            falha(f"E: ASSIGNMENT-SERVING disagrees with assign_arms.py at {d}")
    datas = sorted(reg)
    ini = datetime(2026, 9, 1).date()
    idx = {d: (datetime.strptime(d, "%Y-%m-%d").date() - ini).days + 1 for d in datas}
    # declared groups have no dose; the natural reading tratamento_k -> k-th registered dose
    mapa = {"controle": "control", "tratamento_1": "w2", "tratamento_2": "w4", "tratamento_3": "w7.5"}
    dec_d = {d: mapa[dec[idx[d]]] for d in datas}
    bin_ = lambda g: "control" if g in ("control", "controle") else "treatment"  # noqa: E731
    dif_bin = [d for d in datas if bin_(dec_d[d]) != bin_(reg[d])]
    dif_grp = [d for d in datas if dec_d[d] != reg[d]]
    real = [d for d in datas if "2026-09-01" <= d <= "2026-09-20"]
    return dict(
        seed=seed, randomness=RANDOMNESS,
        regra_declarada="ASSIGN-SEED-2026-08-30.md: global sort by SHA256(seed|epoch_index), first 117 control, "
                        "then 39 x tratamento_1/2/3 (no dose named)",
        regra_registrada="assign_arms.py (committed 2026-08-16, last changed 2026-08-17; in Zenodo v1.12): "
                         "stratified block randomization",
        sha_declarada_reproduzida=SHA_ATRIB_DECLARADA,
        assign_arms_reproduz_ASSIGNMENT_json=True,
        ASSIGNMENT_SERVING_coerente=True,
        contagens_declarada=dict(collections.Counter(dec.values())),
        contagens_registrada=dict(collections.Counter(reg.values())),
        epochs_234_braco_binario_diferente=len(dif_bin),
        epochs_234_grupo_diferente_mapa_natural=len(dif_grp),
        janela_realizada=dict(
            epochs=len(real),
            braco_binario_diferente=[dict(epoch=d, declarada=dec_d[d], registrada=reg[d])
                                     for d in real if d in dif_bin],
            grupo_diferente_mapa_natural=len([d for d in real if d in dif_grp]),
            declarada={d: dec_d[d] for d in real}, registrada={d: reg[d] for d in real},
            contagem_declarada=dict(collections.Counter(bin_(dec_d[d]) for d in real)),
            contagem_registrada=dict(collections.Counter(bin_(reg[d]) for d in real)),
        ),
        nota="both rules run offline on the randomness published in ASSIGN-SEED-2026-08-30.md; no network",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "checks-rc8.json"))
    ap.add_argument("--c12-out", default=str(P2 / "out" / "C12-EMPATES-REGISTRADO-2026-10-05.json"))
    a = ap.parse_args()
    c12 = Path(a.c12_out)
    if c12.resolve() in {p.resolve() for p in (P2 / "out").glob("C12-EMPATES-*-2026-10-05.json")} and \
            c12.name != "C12-EMPATES-REGISTRADO-2026-10-05.json":
        falha("refusing to overwrite an rc4 C12 artifact")
    ctx = contexto()
    G = bloco_G(ctx)
    A, _ = bloco_A(ctx)
    C = bloco_C(ctx, c12)
    D = bloco_D(ctx)
    E = bloco_E(ctx)
    reg = ctx["reg"]
    saida = dict(
        objeto="Paper B rc8 checks (registered analysis, sensitivity legs, C12 under the registered "
               "window, stopping rule, assignment rule)",
        gerado_por="_sprint-2026-10-04/B-rc8/checks-rc8.py",
        sha256_script=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256_ITT_REGISTRADO=hashlib.sha256(ITT_REG.read_bytes()).hexdigest(),
        G_guardas=G, A_pernas_registradas=A,
        C_empates_registrado=dict(arquivo="out/C12-EMPATES-REGISTRADO-2026-10-05.json",
                                  empates_total=C["empates_total_conjunto_4v"],
                                  empates_no_painel_registrado=C["empates_no_painel_registrado_substituicao"],
                                  censo_registrado=C["censo_registrado"],
                                  h1c_ponto_4votos_registrado=C["h1c_ponto_4votos_registrado"]),
        D_regra_de_parada=D, E_regra_de_atribuicao=E,
        F_do_artefato_registrado=dict(
            multiplicidade=reg["multiplicidade"], painel=reg["painel"],
            corte_pos_expiracao=reg["corte_pos_expiracao"]["substituicao"],
            rerand_observado={h: reg["pernas"]["registrado"]["hipoteses"][h]["rerand"]["observado"]
                              for h in ("H1", "H1a", "H1c")}),
    )
    Path(a.out).write_text(json.dumps(saida, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: saida[k] for k in ("G_guardas",)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
