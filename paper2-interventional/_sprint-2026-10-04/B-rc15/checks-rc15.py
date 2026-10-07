#!/usr/bin/env python3
"""Numbers Paper B rc15 needs, recomputed under v4 (sprint 2026-10-04, rc15).

rc15 = copy of `B-rc10/checks-rc10.py` (NOT modified; checks-rc10.json stays) with one change of
substance: the estimator now uses the arm-stratified (multi-sample) BCa acceleration (v4; review
of rc14, Codex C1), so every BCa interval below is the v4 one, and the guards read
`out/ITT-REGISTRADO-v4-2026-10-05.json`. New guard V: under the v3 construction (carried in each
`bca` block as `ic95_bca_uma_amostra_v3`) the two declared sensitivity legs and the BCa ranks must
equal checks-rc10.json exactly, so the acceleration is the only thing that moved.

--- rc10 docstring, kept ---

rc10 reports the registered analysis with the SIXTH switch on (sessions attributed to the epoch
of their start, PREREG §2 item 3; author decision 2026-10-05), i.e.
`out/ITT-REGISTRADO-v3-2026-10-05.json` produced by `measurement/estimador_itt_registrado.py`
(sha256 recorded in that file). This script recomputes, under v3, what checks-rc9.json held under
v2, and aborts (exit 1) when a reproduced reference value does not match. Read-only on every
input; writes only --out.

  G  guards: inputs and script equal to the v3 provenance; the leg builder below reproduces
     `pernas.atual`, `pernas.registrado`, `pernas.sens_registrado_sem_sessoes_atravessadas` and
     `pernas.registrado_v2_equivalente` of v3 exactly (points, both intervals, per-arm totals);
     the last one also equals v2's `pernas.registrado`.
  A  the registered analysis (v2) on the two declared sensitivity legs (pre-committed: the
     partials 09-01, 09-03, 09-20 removed; post-hoc: 09-14 removed); per-epoch session-hours;
     H1 reductions and proportional-dilution ratios; per-epoch volumes; H1 = H1c x H1a
     identity; BCa adjusted quantiles and the replicate rank they select.
  W  the washout: episodes removed in the registered set; 09-14's sparse session.
  S  boundary-straddling sessions (PREREG §2 item 3): the sessions with episodes in more than
     one epoch, their start epoch, arm, span and hours (the registered "own stratum").
  R  (rc15) rc8's and rc9's analyses on the three legs under v4, with their v3-construction
     intervals checked against checks-rc8.json / checks-rc9.json.
  C  the four-vote ties under the v3 analysis (attribution + washout + window + 19 set) and the
     four-vote H1c points under the paper's tie rule and with ties as failure.

Usage: python3 checks-rc10.py [--out checks-rc10.json]
"""
from __future__ import annotations

import argparse, collections, hashlib, json, random, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
P2 = HERE.parent.parent
sys.path.insert(0, str(P2)); sys.path.insert(0, str(P2 / "measurement"))
import estimador_itt_registrado as R  # noqa: E402
from pilot_replay import carregar_verdicts, carregar_episodios, WASHOUT_H  # noqa: E402

V3 = P2 / "out" / "ITT-REGISTRADO-v4-2026-10-05.json"   # name kept; holds v4
CHK10 = HERE.parent / "B-rc10" / "checks-rc10.json"
V2 = P2 / "out" / "ITT-REGISTRADO-v2-2026-10-05.json"
PARCIAIS = ["2026-09-01", "2026-09-03", "2026-09-20"]
POS_HOC = ["2026-09-14"]


def falha(msg):
    sys.exit(f"ABORT {msg}")


def contexto():
    P = {k: Path(v) for k, v in R.DEFAULTS.items()}
    reg = json.loads(V3.read_text())
    prov = reg["proveniencia"]
    for k, p in P.items():
        if R.sha(p) != prov["entradas"][k]["sha256"]:
            falha(f"G: input {k} differs from the v4 provenance")
    if R.sha(P2 / prov["script"]["caminho"]) != prov["script"]["sha256"]:
        falha("G: estimador_itt_registrado.py changed since ITT-REGISTRADO-v4 was produced")
    with tempfile.TemporaryDirectory() as td:
        v3 = carregar_verdicts(P["verdicts"])
        vs, _ = R.verdicts_substituicao(P["verdicts"], P["verdicts_ds"], Path(td))
    return dict(P=P, reg=reg, v3=v3, vs=vs,
                eps={"3fam": carregar_episodios(P["episodes"], v3),
                     "substituicao": carregar_episodios(P["episodes"], vs)},
                b_ids={l.strip() for l in P["estrato_b"].read_text().splitlines() if l.strip()},
                arm={e["epoch_inicio"]: (e["arm"], float(e["w"]))
                     for e in json.loads(P["assignment"].read_text())["epochs"]},
                jan=R.janelas_de_exposicao(P["serving"]))


def perna(ctx, cfg, extra=()):
    eps = ctx["eps"][cfg.painel]
    Q = R.por_epoch(eps, ctx["b_ids"], R.predicado_janela(cfg.janela, ctx["jan"]),
                    cfg.washout_in_denominator == "sim", cfg.sem_atravessadas,
                    cfg.sessao_ao_epoch_de_inicio == "sim")
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
    v2 = json.loads(V2.read_text())
    for nome, cfg in (("atual", R.ATUAL), ("registrado", R.REGISTRADO),
                      ("sens_registrado_sem_sessoes_atravessadas", R.replace(R.REGISTRADO, sem_atravessadas=True)),
                      ("registrado_v2_equivalente", R.replace(R.REGISTRADO, sessao_ao_epoch_de_inicio="nao"))):
        p = perna(ctx, cfg); ref = reg["pernas"][nome]
        for h in ("H1", "H1a", "H1c"):
            for k in ("dif_pontual", "ic95_percentil", "ic95_bca", "ic95"):
                if p["hipoteses"][h][k] != ref["hipoteses"][h][k]:
                    falha(f"G: leg {nome} {h}.{k} differs from v4")
        if p["por_braco"] != ref["por_braco"]:
            falha(f"G: leg {nome} per-arm totals differ from v4")
        out[nome] = "reproduced: points, percentile and BCa intervals, per-arm totals"
    a, b = reg["pernas"]["registrado_v2_equivalente"], v2["pernas"]["registrado"]
    for h in ("H1", "H1a", "H1c"):
        for k in ("dif_pontual", "ic95", "p_rerand"):
            va = a["hipoteses"][h]["bca"]["ic95_bca_uma_amostra_v3"] if k == "ic95" else a["hipoteses"][h][k]
            if va != b["hipoteses"][h][k]:
                falha(f"G: switch 6 at the locked value does not give v2's {h}.{k}")
    out["v2_igual_a_v4_sem_switch_6_com_aceleracao_v3"] = "points, intervals (one-sample acceleration) and p-values equal"
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
                       rank_inferior_1_based=idx[0] + 1, n=n, z0=b["z0"], acel=b["acel"],
                       acel_uma_amostra_v3=b["acel_uma_amostra_v3"])
    out["bca_quantis"] = bca
    return out, legs


def bloco_V(A, legs):
    """v3 construction carried alongside must give checks-rc10.json's values exactly."""
    c10 = json.loads(CHK10.read_text())["A_pernas_registradas"]
    out = {}
    for k in ("registrado", "registrado_precomprometida", "registrado_pos_hoc_sem_0914"):
        for h in ("H1", "H1a", "H1c"):
            r = legs[k]["hipoteses"][h]
            if r["bca"]["ic95_bca_uma_amostra_v3"] != c10[k][h]["ic95"] or r["dif_pontual"] != c10[k][h]["ponto"] \
                    or r["ic95_percentil"] != c10[k][h]["ic95_percentil"]:
                falha(f"V: {k}.{h} under the v3 construction differs from checks-rc10.json")
            out[f"{k}.{h}"] = dict(v3=c10[k][h]["ic95"], v4=r["ic95"],
                                   exclui_zero=[c10[k][h]["exclui_zero"], A[k][h]["exclui_zero"]])
    for hh in ("H1", "H1a", "H1c"):
        if A["bca_quantis"][hh]["acel_uma_amostra_v3"] != c10["bca_quantis"][hh]["acel"] or \
                A["bca_quantis"][hh]["z0"] != c10["bca_quantis"][hh]["z0"]:
            falha(f"V: BCa z0/acceleration of {hh} under the v3 construction differs from checks-rc10.json")
    out["sha256_checks_rc10"] = hashlib.sha256(CHK10.read_bytes()).hexdigest()
    return out


def bloco_R(ctx):
    """rc8's and rc9's analyses (switches 6, and 5+6, at the locked value) on the three legs, under
    v4; their v3-construction intervals must equal what checks-rc8/checks-rc9 recorded (the values
    those versions reported), when those files hold the leg."""
    out = {}
    ref = {}
    for nome, f in (("rc8", HERE.parent / "B-rc8" / "checks-rc8.json"), ("rc9", HERE.parent / "B-rc9" / "checks-rc9.json")):
        if f.exists():
            ref[nome] = (json.loads(f.read_text()).get("A_pernas_registradas") or {}, hashlib.sha256(f.read_bytes()).hexdigest())
    cfgs = {"rc9": R.replace(R.REGISTRADO, sessao_ao_epoch_de_inicio="nao"),
            "rc8": R.replace(R.REGISTRADO, sessao_ao_epoch_de_inicio="nao", washout_in_denominator="sim")}
    for v, cfg in cfgs.items():
        for leg, extra in (("registrado", ()), ("registrado_precomprometida", PARCIAIS),
                           ("registrado_pos_hoc_sem_0914", POS_HOC)):
            p = perna(ctx, cfg, extra)
            linha = {}
            for h in ("H1", "H1a", "H1c"):
                r = p["hipoteses"][h]
                v3ic = r["bca"]["ic95_bca_uma_amostra_v3"]
                conf = None
                if v in ref and leg in ref[v][0] and h in ref[v][0][leg]:
                    conf = ref[v][0][leg][h]["ic95"] == v3ic and ref[v][0][leg][h]["ponto"] == r["dif_pontual"]
                    if not conf:
                        falha(f"R: {v} {leg} {h} under the v3 construction differs from checks-{v}.json")
                linha[h] = dict(ponto=r["dif_pontual"], ic95_v4=r["ic95"], ic95_v3=v3ic,
                                exclui_zero_v4=(r["ic95"][1] < 0 or r["ic95"][0] > 0),
                                exclui_zero_v3=(v3ic[1] < 0 or v3ic[0] > 0), confere_checks=conf)
            linha["horas"] = {b: x["horas_sessao"] for b, x in p["por_braco"].items()}
            out[f"{v}.{leg}"] = linha
    out["sha256_checks"] = {k: v[1] for k, v in ref.items()}
    return out


def bloco_W(ctx, legs):
    reg = ctx["reg"]; arm = ctx["arm"]
    na = R.predicado_janela("exposicao", ctx["jan"])
    eps = R.atribui_ao_inicio(ctx["eps"]["substituicao"])
    an = [e for e in eps if R.JANELA_INI <= e.epoch.strftime("%Y-%m-%d") <= R.JANELA_FIM
          and e.epoch.strftime("%Y-%m-%d") != R.EPOCH_VAZIO and na(e)]
    ok = R.unidades_elegiveis(eps)
    fora = [e for e in an if (e.epoch, e.sessao) not in ok]
    if any(e.offset_h >= WASHOUT_H for e in fora):
        falha("W: an excluded episode is past the washout (session rule != episode rule)")
    porb = collections.Counter(arm[e.epoch.strftime("%Y-%m-%d")][0] for e in fora)
    v1h = reg["pernas"]["registrado_v2_equivalente"]["por_braco"]
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
        horas_v2={b: v1h[b]["horas_sessao"] for b in v1h}, horas_v3={b: v2h[b]["horas_sessao"] for b in v2h},
        sessao_mais_longa_0914=dict(span_h=round(spans[0][0], 4), episodios=spans[0][1], id_prefix=spans[0][2]),
        sessoes_0914=len(spans),
    )


def bloco_S(ctx):
    reg = ctx["reg"]; arm = ctx["arm"]
    eps = ctx["eps"]["substituicao"]
    atrav = R.sessoes_atravessadas(eps)
    por = collections.defaultdict(list)
    for e in eps:
        if e.sessao in atrav:
            por[e.sessao].append(e)
    linhas = {}
    for s_, v in por.items():
        v.sort(key=lambda e: e.ts)
        ep0 = v[0].epoch.strftime("%Y-%m-%d")
        epochs = sorted({e.epoch.strftime("%Y-%m-%d") for e in v})
        linhas[s_[:8]] = dict(inicio=v[0].ts.isoformat(), epoch_de_inicio=ep0,
                              braco_de_inicio=arm.get(ep0, (None,))[0],
                              offset_inicio_h=round(v[0].offset_h, 2),
                              span_h=round((v[-1].ts - v[0].ts).total_seconds() / 3600, 2),
                              episodios=len(v), epochs_tocados=epochs,
                              na_janela=any(R.JANELA_INI <= x <= R.JANELA_FIM for x in epochs),
                              inicio_na_janela=R.JANELA_INI <= ep0 <= R.JANELA_FIM)
    pe = reg["pernas"]["registrado"]["por_epoch"]
    return dict(sessoes=linhas, sessoes_em_mais_de_um_epoch=len(linhas),
                das_quais_tocam_a_janela=sum(1 for x in linhas.values() if x["na_janela"]),
                das_quais_iniciam_na_janela=sum(1 for x in linhas.values() if x["inicio_na_janela"]),
                todas_na_janela_com_span_maior_que_24h=all(x["span_h"] > 24 for x in linhas.values() if x["inicio_na_janela"]),
                horas_por_epoch_v3={k: v["horas"] for k, v in pe.items()},
                com=reg["resumo"]["registrado"], sem=reg["resumo"]["sens_registrado_sem_sessoes_atravessadas"])


def bloco_C(ctx):
    import importlib.util
    from pilot_replay import NIVEIS, TAU
    spec = importlib.util.spec_from_file_location("c12", P2 / "measurement" / "sprint-c12-empates-por-braco.py")
    C12 = importlib.util.module_from_spec(spec); spec.loader.exec_module(C12)
    P = ctx["P"]
    with tempfile.TemporaryDirectory() as td:
        q = Path(td) / "q.jsonl"
        q.write_text(P["verdicts"].read_text() + P["verdicts_ds"].read_text())
        v4 = carregar_verdicts(q)
    votos4 = C12.votos_substantivos([P["verdicts"], P["verdicts_ds"]])
    corte = NIVEIS.index(TAU)
    empate = {ep for ep, pp in votos4.items() if len(pp) >= 3 and len(pp) % 2 == 0
              and 2 * sum(1 for x in pp.values() if x >= corte) == len(pp)}
    if len(empate) != 28:
        falha(f"C: tie census {len(empate)} != 28")
    v4f = dict(v4)
    for ep in empate:
        v4f[ep] = "failure"
    eps4 = carregar_episodios(P["episodes"], v4)
    eps4f = carregar_episodios(P["episodes"], v4f)
    arm = {k: v[0] for k, v in ctx["arm"].items()}
    atr = R.atribui_ao_inicio(eps4)
    ok_w = R.predicado_janela("exposicao", ctx["jan"])
    eleg = R.unidades_elegiveis(atr)
    cont = collections.Counter()
    for e in atr:
        if e.id not in empate:
            continue
        k = e.epoch.strftime("%Y-%m-%d")
        if not (R.JANELA_INI <= k <= R.JANELA_FIM) or k not in arm:
            cont["fora_das_datas"] += 1
        elif k == R.EPOCH_VAZIO:
            cont["epoch_excluido"] += 1
        elif not ok_w(e):
            cont["fora_da_exposicao"] += 1
        elif (e.epoch, e.sessao) not in eleg:
            cont["washout"] += 1
        else:
            cont[arm[k]] += 1
    atravessadas = R.sessoes_atravessadas(eps4)
    em_atrav = sum(1 for e in eps4 if e.id in empate and e.sessao in atravessadas)

    def h1c(eps):
        Q = R.por_epoch(eps, ctx["b_ids"], ok_w, False, False, True)
        ag = R.agrega_fn(Q)
        pb = R.montar(Q, ctx["arm"], {R.EPOCH_VAZIO})
        a = {b: ag(v) for b, v in pb.items()}
        return round(a["treatment"]["H1c_prop"] - a["control"]["H1c_prop"], 6)
    return dict(empates=len(empate), por_destino=dict(cont), empates_em_sessoes_atravessadas=em_atrav,
                h1c_4votos_regra_do_paper=h1c(eps4), h1c_4votos_empate_como_failure=h1c(eps4f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "checks-rc15.json"))
    a = ap.parse_args()
    ctx = contexto()
    G = bloco_G(ctx)
    A, legs = bloco_A(ctx)
    V = bloco_V(A, legs)
    RR = bloco_R(ctx)
    W = bloco_W(ctx, legs)
    S = bloco_S(ctx)
    C = bloco_C(ctx)
    saida = dict(
        objeto="Paper B rc15 checks (registered analysis v4: v3 + arm-stratified BCa acceleration)",
        gerado_por="_sprint-2026-10-04/B-rc15/checks-rc15.py",
        sha256_script=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256_ITT_REGISTRADO_v4=hashlib.sha256(V3.read_bytes()).hexdigest(),
        G_guardas=G, A_pernas_registradas=A, V_v3_para_v4=V,
        R_analises_rc8_rc9_em_v4=RR, W_washout=W, S_sessoes_atravessadas=S,
        C_empates_v3=C,
        F_do_artefato_v4=dict(multiplicidade=ctx["reg"]["multiplicidade"],
                              rerand_observado={h: ctx["reg"]["pernas"]["registrado"]["hipoteses"][h]["rerand"]["observado"]
                                                for h in ("H1", "H1a", "H1c")}),
    )
    Path(a.out).write_text(json.dumps(saida, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(dict(G=G, V=V, W=W, C=C, S={k: S[k] for k in ("sessoes", "das_quais_iniciam_na_janela",
                                                              "todas_na_janela_com_span_maior_que_24h")}), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
