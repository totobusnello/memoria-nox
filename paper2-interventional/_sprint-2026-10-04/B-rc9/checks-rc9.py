#!/usr/bin/env python3
"""Numbers Paper B rc9 needs that no earlier artifact holds (sprint 2026-10-04, rc9).

rc9 reports the registered analysis with the FIFTH switch on (washout removed from the
session-hour denominator; review C1), i.e. `out/ITT-REGISTRADO-v2-2026-10-05.json` produced
by `measurement/estimador_itt_registrado.py` (sha256 recorded in that file). This script
recomputes, under v2, what checks-rc8.json block A held under v1, and aborts (exit 1) when a
reproduced reference value does not match. Read-only on every input; writes only --out.

  G  guards: inputs and script equal to the v2 provenance; the leg builder below reproduces
     `pernas.atual`, `pernas.registrado` and `pernas.registrado_sem_washout_in_denominator`
     of v2 exactly (points, both intervals, per-arm totals); the last one also equals v1's
     `pernas.registrado` (v1 = switch 5 at the locked value).
  A  the registered analysis (v2) on the two declared sensitivity legs (pre-committed: the
     partials 09-01, 09-03, 09-20 removed; post-hoc: 09-14 removed); per-epoch session-hours;
     H1 reductions and proportional-dilution ratios; per-epoch volumes; H1 = H1c x H1a
     identity; BCa adjusted quantiles and the replicate rank they select.
  W  the washout: episodes removed in the registered set; 09-14's sparse session.
  S  boundary-straddling sessions (PREREG §2 item 3): the sessions with episodes in more than
     one epoch, and the 'without' leg from v2.

Usage: python3 checks-rc9.py [--out checks-rc9.json]
"""
from __future__ import annotations

import argparse, collections, hashlib, json, random, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
P2 = HERE.parent.parent
sys.path.insert(0, str(P2)); sys.path.insert(0, str(P2 / "measurement"))
import estimador_itt_registrado as R  # noqa: E402
from pilot_replay import carregar_verdicts, carregar_episodios, WASHOUT_H  # noqa: E402

V2 = P2 / "out" / "ITT-REGISTRADO-v2-2026-10-05.json"
V1 = P2 / "out" / "ITT-REGISTRADO-2026-10-05.json"
PARCIAIS = ["2026-09-01", "2026-09-03", "2026-09-20"]
POS_HOC = ["2026-09-14"]


def falha(msg):
    sys.exit(f"ABORT {msg}")


def contexto():
    P = {k: Path(v) for k, v in R.DEFAULTS.items()}
    reg = json.loads(V2.read_text())
    prov = reg["proveniencia"]
    for k, p in P.items():
        if R.sha(p) != prov["entradas"][k]["sha256"]:
            falha(f"G: input {k} differs from the v2 provenance")
    if R.sha(P2 / prov["script"]["caminho"]) != prov["script"]["sha256"]:
        falha("G: estimador_itt_registrado.py changed since ITT-REGISTRADO-v2 was produced")
    with tempfile.TemporaryDirectory() as td:
        v3 = carregar_verdicts(P["verdicts"])
        vs, _ = R.verdicts_substituicao(P["verdicts"], P["verdicts_ds"], Path(td))
    return dict(P=P, reg=reg,
                eps={"3fam": carregar_episodios(P["episodes"], v3),
                     "substituicao": carregar_episodios(P["episodes"], vs)},
                b_ids={l.strip() for l in P["estrato_b"].read_text().splitlines() if l.strip()},
                arm={e["epoch_inicio"]: (e["arm"], float(e["w"]))
                     for e in json.loads(P["assignment"].read_text())["epochs"]},
                jan=R.janelas_de_exposicao(P["serving"]))


def perna(ctx, cfg, extra=()):
    eps = ctx["eps"][cfg.painel]
    Q = R.por_epoch(eps, ctx["b_ids"], R.predicado_janela(cfg.janela, ctx["jan"]),
                    cfg.washout_in_denominator == "sim", cfg.sem_atravessadas)
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
    return dict(removidos=sorted(excl), n_epochs={b: len(v) for b, v in sorted(pb.items())},
                por_braco={b: ag(v) for b, v in sorted(pb.items())}, hipoteses=hip,
                horas_por_epoch=dict(sorted(horas.items())), _Q=Q)


def resumo_perna(p):
    return dict(removidos=p["removidos"], n_epochs=p["n_epochs"], por_braco=p["por_braco"],
                **{k: dict(ponto=v["dif_pontual"], ic95=v["ic95"], construcao=v["construcao"],
                           ic95_percentil=v["ic95_percentil"], bca=v["bca"],
                           exclui_zero=(v["ic95"][1] < 0 or v["ic95"][0] > 0))
                   for k, v in p["hipoteses"].items()})


def bloco_G(ctx):
    reg = ctx["reg"]; out = {}
    v1 = json.loads(V1.read_text())
    sem5 = R.replace(R.REGISTRADO, washout_in_denominator="sim")
    for nome, cfg in (("atual", R.ATUAL), ("registrado", R.REGISTRADO),
                      ("registrado_sem_washout_in_denominator", sem5)):
        p = perna(ctx, cfg); ref = reg["pernas"][nome]
        for h in ("H1", "H1a", "H1c"):
            for k in ("dif_pontual", "ic95_percentil", "ic95_bca", "ic95"):
                if p["hipoteses"][h][k] != ref["hipoteses"][h][k]:
                    falha(f"G: leg {nome} {h}.{k} differs from v2")
        if p["por_braco"] != ref["por_braco"]:
            falha(f"G: leg {nome} per-arm totals differ from v2")
        out[nome] = "reproduced: points, percentile and BCa intervals, per-arm totals"
    a, b = reg["pernas"]["registrado_sem_washout_in_denominator"], v1["pernas"]["registrado"]
    for h in ("H1", "H1a", "H1c"):
        for k in ("dif_pontual", "ic95", "p_rerand"):
            if a["hipoteses"][h][k] != b["hipoteses"][h][k]:
                falha(f"G: switch 5 at the locked value does not give v1's {h}.{k}")
    out["v1_igual_a_v2_sem_switch_5"] = "points, intervals and p-values equal"
    return out


def bloco_A(ctx):
    legs = {"registrado": perna(ctx, R.REGISTRADO),
            "registrado_precomprometida": perna(ctx, R.REGISTRADO, PARCIAIS),
            "registrado_pos_hoc_sem_0914": perna(ctx, R.REGISTRADO, POS_HOC)}
    out = {k: resumo_perna(v) for k, v in legs.items()}
    reg = legs["registrado"]; arm = ctx["arm"]
    horas = reg["horas_por_epoch"]
    tot_t = sum(v for k, v in horas.items() if arm[k][0] == "treatment")
    pico = max(horas, key=horas.get)
    outros = {k: v for k, v in horas.items() if k != pico}
    out["horas_por_epoch_registrado"] = dict(
        por_epoch=horas, pico=pico, pico_h=horas[pico], pico_share_tratamento=round(horas[pico] / tot_t, 4),
        outros_n=len(outros), outros_min=min(outros.values()), outros_max=max(outros.values()),
        outros_min_epoch=min(outros, key=outros.get), outros_max_epoch=max(outros, key=outros.get))
    shares = {"calibracao_11_de_350": 11 / 350, "realizada_335_de_7350": 335 / 7350,
              "maior_por_epoch_6.85pct": 0.0685}
    red = {}
    for k in ("registrado", "registrado_pos_hoc_sem_0914", "registrado_precomprometida"):
        pb = legs[k]["por_braco"]
        t, c = pb["treatment"]["H1_densidade"], pb["control"]["H1_densidade"]
        red[k] = dict(H1_t=t, H1_c=c, reducao=round(1 - t / c, 4),
                      razoes={s: round((1 - t / c) / v, 2) for s, v in shares.items()})
    out["H1_reducoes_e_razoes"] = red
    vol = {}
    for k in ("registrado", "registrado_pos_hoc_sem_0914"):
        pb = legs[k]["por_braco"]
        vol[k] = {b: dict(oport_por_epoch=round(pb[b]["oportunidades"] / pb[b]["n_epochs"], 1),
                          repeats_por_epoch=round(pb[b]["repeats"] / pb[b]["n_epochs"], 2),
                          horas_por_epoch=round(pb[b]["horas_sessao"] / pb[b]["n_epochs"], 3))
                  for b in ("treatment", "control")}
    out["volumes_por_epoch"] = vol
    ident = {}
    for k, p in legs.items():
        for b, x in p["por_braco"].items():
            ident[f"{k}/{b}"] = abs(x["H1c_prop"] * x["H1a_taxa_oport"] - x["H1_densidade"]) / x["H1_densidade"]
    out["identidade_H1_igual_H1c_vezes_H1a"] = dict(celulas=len(ident),
                                                     erro_relativo_max=float(f"{max(ident.values()):.2e}"))
    h = reg["hipoteses"]["H1c"]; c = reg["por_braco"]["control"]["H1c_prop"]
    out["H1c_registrado"] = dict(controle=c, reducao_relativa=round(-h["dif_pontual"] / c, 4),
                                 eliminacao_total=-c, ic95=h["ic95"],
                                 distancia_ic_inferior_a_eliminacao_total=round(h["ic95"][0] - (-c), 4))
    bca = {}
    for hh in ("H1", "H1a", "H1c"):
        b = reg["hipoteses"][hh]["bca"]; n = reg["hipoteses"][hh]["n_replicas"]
        idx = [min(max(int(x * n), 0), n - 1) for x in b["alfa_ajustado"]]
        bca[hh] = dict(alfa_ajustado=b["alfa_ajustado"], indice_0_based=idx,
                       rank_inferior_1_based=idx[0] + 1, n=n, z0=b["z0"], acel=b["acel"])
    out["bca_quantis"] = bca
    return out, legs


def bloco_W(ctx, legs):
    reg = ctx["reg"]; arm = ctx["arm"]
    na = R.predicado_janela("exposicao", ctx["jan"])
    eps = ctx["eps"]["substituicao"]
    an = [e for e in eps if R.JANELA_INI <= e.epoch.strftime("%Y-%m-%d") <= R.JANELA_FIM
          and e.epoch.strftime("%Y-%m-%d") != R.EPOCH_VAZIO and na(e)]
    ok = R.unidades_elegiveis(eps)
    fora = [e for e in an if (e.epoch, e.sessao) not in ok]
    if any(e.offset_h >= WASHOUT_H for e in fora):
        falha("W: an excluded episode is past the washout (session rule != episode rule)")
    porb = collections.Counter(arm[e.epoch.strftime("%Y-%m-%d")][0] for e in fora)
    v1h = reg["pernas"]["registrado_sem_washout_in_denominator"]["por_braco"]
    v2h = reg["pernas"]["registrado"]["por_braco"]
    # 09-14 under v2: the sessions that make its exposure
    sess = collections.defaultdict(list)
    for e in an:
        if e.epoch.strftime("%Y-%m-%d") == "2026-09-14" and (e.epoch, e.sessao) in ok:
            sess[e.sessao].append(e.ts)
    spans = sorted((((max(v) - min(v)).total_seconds() / 3600, len(v), s[:8]) for s, v in sess.items()),
                   reverse=True)
    return dict(
        episodios_no_conjunto_registrado=len(an),
        episodios_removidos_pelo_washout=len(fora), por_braco=dict(porb),
        horas_v1={b: v1h[b]["horas_sessao"] for b in v1h}, horas_v2={b: v2h[b]["horas_sessao"] for b in v2h},
        sessao_mais_longa_0914=dict(span_h=round(spans[0][0], 4), episodios=spans[0][1], id_prefix=spans[0][2]),
        sessoes_0914=len(spans),
    )


def bloco_S(ctx):
    reg = ctx["reg"]
    ses = collections.defaultdict(set)
    for e in ctx["eps"]["substituicao"]:
        ses[e.sessao].add(e.epoch.strftime("%Y-%m-%d"))
    multi = {s: sorted(v) for s, v in ses.items() if len(v) > 1}
    na_janela = {s: v for s, v in multi.items() if any(R.JANELA_INI <= x <= R.JANELA_FIM for x in v)}
    d = reg["resumo"]["diag_registrado_sem_sessoes_atravessadas"]
    return dict(sessoes_em_mais_de_um_epoch=len(multi), das_quais_tocam_a_janela=len(na_janela),
                epochs_por_sessao={s[:8]: v for s, v in na_janela.items()},
                perna_sem=d, washout_diagnostico=reg["pernas"]["diag_registrado_sem_sessoes_atravessadas"]["washout_diagnostico"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "checks-rc9.json"))
    a = ap.parse_args()
    ctx = contexto()
    G = bloco_G(ctx)
    A, legs = bloco_A(ctx)
    W = bloco_W(ctx, legs)
    S = bloco_S(ctx)
    saida = dict(
        objeto="Paper B rc9 checks (registered analysis v2: washout removed from the denominator)",
        gerado_por="_sprint-2026-10-04/B-rc9/checks-rc9.py",
        sha256_script=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256_ITT_REGISTRADO_v2=hashlib.sha256(V2.read_bytes()).hexdigest(),
        G_guardas=G, A_pernas_registradas=A, W_washout=W, S_sessoes_atravessadas=S,
        F_do_artefato_v2=dict(multiplicidade=ctx["reg"]["multiplicidade"],
                              rerand_observado={h: ctx["reg"]["pernas"]["registrado"]["hipoteses"][h]["rerand"]["observado"]
                                                for h in ("H1", "H1a", "H1c")}),
    )
    Path(a.out).write_text(json.dumps(saida, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(dict(G=G, W=W, S={k: S[k] for k in ("sessoes_em_mais_de_um_epoch", "das_quais_tocam_a_janela")}), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
