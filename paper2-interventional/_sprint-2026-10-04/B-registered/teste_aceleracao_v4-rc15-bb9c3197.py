#!/usr/bin/env python3
"""Paper B v4 — test of the arm-stratified (multi-sample) BCa acceleration (review of rc14, C1).

Three legs, each aborts (exit != 0) on failure:
  1. hand case: a two-arm toy (T = 1,2,4; C = 0,3; statistic = difference of means) computed in
     exact fractions from the review's formula; the script's `aceleracao_estratificada` must match.
  2. SciPy on the toy: `scipy.stats._resampling._bca_interval` returns a_hat "for testing"; it must
     equal the exact value. The one-sample (v3) construction must NOT (it is the defect).
  3. SciPy on the real data: for every hypothesis of the registered leg and of the sensitivity
     leg, and for the four H2 estimators of the registered leg, SciPy's a_hat computed with the
     estimator's own aggregation over epoch indices must equal the v4 `acel` (to 1e-12 before
     rounding; to the 6th decimal after).

    python3 _sprint-2026-10-04/B-registered/teste_aceleracao_v4.py [--out <json>]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from fractions import Fraction as F
from pathlib import Path

import numpy as np
from scipy.stats import _resampling as R
from scipy._lib._array_api import array_namespace

P2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(P2 / "measurement"))
import estimador_itt_registrado as E  # noqa: E402

XP = array_namespace(np.asarray(0.0))
falhas = []


def scipy_a(n_t, n_c, stat2, theta_b):
    """a_hat from SciPy's multi-sample BCa, statistic over epoch-index arrays."""
    def statistic(it, ic, axis=-1):
        it, ic = np.asarray(it), np.asarray(ic)
        shp = np.broadcast_shapes(it.shape[:-1], ic.shape[:-1])
        it = np.broadcast_to(it, shp + it.shape[-1:]); ic = np.broadcast_to(ic, shp + ic.shape[-1:])
        out = np.empty(shp)
        for idx in np.ndindex(shp):
            out[idx] = stat2([int(x) for x in it[idx]], [int(x) for x in ic[idx]])
        return out
    data = (np.arange(n_t, dtype=float), np.arange(n_c, dtype=float))
    _, _, a = R._bca_interval(data, statistic, axis=-1, alpha=0.025,
                              theta_hat_b=np.asarray(theta_b, dtype=float), batch=None, xp=XP)
    return float(np.asarray(a))


# ── 1. hand case, exact ──────────────────────────────────────────────────────
T, C = [F(1), F(2), F(4)], [F(0), F(3)]
mean = lambda v: sum(v, F(0)) / len(v)  # noqa: E731
jk = {"treatment": [mean(T[:i] + T[i + 1:]) - mean(C) for i in range(3)],
      "control": [mean(T) - mean(C[:i] + C[i + 1:]) for i in range(2)]}
q = []
for g, vals in jk.items():
    n = len(vals); m = mean(vals)
    q += [F(n - 1, n) * (m - x) for x in vals]
S2, S3 = sum(x * x for x in q), sum(x ** 3 for x in q)
a_exato = float(S3) / (6 * float(S2) ** 1.5)
s2, s3 = E.aceleracao_estratificada({k: [float(x) for x in v] for k, v in jk.items()},
                                    {"treatment": 3, "control": 2})
a_script = s3 / (6 * s2 ** 1.5)
mao = dict(T=[1, 2, 4], C=[0, 3], sum_q2=str(S2), sum_q3=str(S3), a_exato=a_exato, a_script=a_script)
if abs(a_script - a_exato) > 1e-15:
    falhas.append("hand case: script != exact")

# ── 2. SciPy on the toy ──────────────────────────────────────────────────────
Tf, Cf = [1.0, 2.0, 4.0], [0.0, 3.0]
st = lambda it, ic: np.mean([Tf[i] for i in it]) - np.mean([Cf[i] for i in ic])  # noqa: E731
a_scipy_toy = scipy_a(3, 2, st, [0.0, 1.0, 2.0])
u2, u3 = E.aceleracao_uma_amostra([float(x) for x in jk["treatment"] + jk["control"]])
a_v3_toy = u3 / (6 * u2 ** 1.5)
mao.update(a_scipy=a_scipy_toy, a_uma_amostra_v3=a_v3_toy)
if abs(a_scipy_toy - a_exato) > 1e-12:
    falhas.append("toy: scipy != exact")
if abs(a_v3_toy - a_exato) < 1e-6:
    falhas.append("toy: one-sample construction coincides with multi-sample (test has no bite)")

# ── 3. SciPy on the real data ────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("--out")
args = ap.parse_args()
Pp = {k: Path(v) for k, v in E.DEFAULTS.items()}
with tempfile.TemporaryDirectory() as td:
    v3 = E.carregar_verdicts(Pp["verdicts"])
    vs, _ = E.verdicts_substituicao(Pp["verdicts"], Pp["verdicts_ds"], Path(td))
ctx = dict(eps={"3fam": E.carregar_episodios(Pp["episodes"], v3),
                "substituicao": E.carregar_episodios(Pp["episodes"], vs)},
           b_ids={l.strip() for l in Pp["estrato_b"].read_text().splitlines() if l.strip()},
           arm={e["epoch_inicio"]: (e["arm"], float(e["w"]))
                for e in json.loads(Pp["assignment"].read_text())["epochs"]},
           jan=E.janelas_de_exposicao(Pp["serving"]))
ctx["mapas"] = E.mapas_rerand(10, [k for k in sorted(ctx["arm"]) if E.JANELA_INI <= k <= E.JANELA_FIM])
E.ACELERACAO = "estratificada"
reais = []
for perna, cfg in (("registrado", E.REGISTRADO),
                   ("sens_registrado_sem_sessoes_atravessadas", E.replace(E.REGISTRADO, sem_atravessadas=True))):
    Q = E.por_epoch(ctx["eps"][cfg.painel], ctx["b_ids"], E.predicado_janela(cfg.janela, ctx["jan"]),
                    False, cfg.sem_atravessadas, True)
    ag = E.agrega_fn(Q)
    pb = E.montar(Q, ctx["arm"], {E.EPOCH_VAZIO})
    t, c = pb["treatment"], pb["control"]
    for h, met in (("H1", "H1_densidade"), ("H1a", "H1a_taxa_oport"), ("H1c", "H1c_prop")):
        r = E.bootstrap(ag, pb, met, E.random.Random(E.SEED), 200)
        stat = lambda it, ic, ag=ag, met=met: ag([t[i] for i in it])[met] - ag([c[i] for i in ic])[met]  # noqa: E731
        a_sc = scipy_a(len(t), len(c), stat, [0.0])
        reais.append(dict(perna=perna, h=h, n=[len(t), len(c)], a_v4=r["bca"]["acel"], a_scipy=a_sc,
                          a_v3=r["bca"]["acel_uma_amostra_v3"]))
# H2, registered leg: same aggregation as E.h2, rebuilt here to reach its per-epoch sums
import collections  # noqa: E402
cfg = E.REGISTRADO
reg, _ = E.regret_por_episodio(Pp["archive"], {json.loads(l)["episode_id"]: json.loads(l)
                                               for l in Pp["episodes"].read_text().splitlines() if l.strip()})
eps = E.atribui_ao_inicio(ctx["eps"][cfg.painel])
na = E.predicado_janela(cfg.janela, ctx["jan"])
ok_unid = E.unidades_elegiveis(eps, False, E.sessoes_atravessadas(ctx["eps"][cfg.painel]))
soma = collections.defaultdict(lambda: collections.defaultdict(float))
for e in eps:
    k = e.epoch.strftime("%Y-%m-%d")
    if not (E.JANELA_INI <= k <= E.JANELA_FIM) or k not in ctx["arm"] or k == E.EPOCH_VAZIO:
        continue
    if not na(e) or e.offset_h < E.WASHOUT_H or e.id not in reg or (e.epoch, e.sessao) not in ok_unid:
        continue
    rt, rk = reg[e.id]; S = soma[e.epoch]
    S["n_t"] += 1; S["t_raw"] += rt; S["t_win"] += min(rt, E.WINSOR["tempo_s"])
    if rk is not None:
        S["n_k"] += 1; S["k_raw"] += rk; S["k_win"] += min(rk, E.WINSOR["tokens"])
pb = collections.defaultdict(list)
for ep in sorted(soma):
    pb[ctx["arm"][ep.strftime("%Y-%m-%d")][0]].append(ep)
t, c = pb["treatment"], pb["control"]
for chave, den in (("t_win", "n_t"), ("t_raw", "n_t"), ("k_win", "n_k"), ("k_raw", "n_k")):
    def ag(lista, chave=chave, den=den):
        n = sum(soma[e][den] for e in lista)
        return {"m": (sum(soma[e][chave] for e in lista) / n) if n else None}
    r = E.bootstrap(ag, pb, "m", E.random.Random(E.SEED), 200)
    stat = lambda it, ic, ag=ag: ag([t[i] for i in it])["m"] - ag([c[i] for i in ic])["m"]  # noqa: E731
    reais.append(dict(perna="registrado", h="H2_" + chave, n=[len(t), len(c)], a_v4=r["bca"]["acel"],
                      a_scipy=scipy_a(len(t), len(c), stat, [0.0]), a_v3=r["bca"]["acel_uma_amostra_v3"]))
for x in reais:
    x["confere"] = x["a_v4"] is not None and round(x["a_scipy"], 6) == x["a_v4"]
    if not x["confere"]:
        falhas.append(f"real: {x['perna']}.{x['h']} v4 {x['a_v4']} != scipy {x['a_scipy']}")

out = dict(scipy=__import__("scipy").__version__, numpy=np.__version__, caso_a_mao=mao, dados_reais=reais,
           falhas=falhas, ok=not falhas)
txt = json.dumps(out, indent=2, ensure_ascii=False)
if args.out:
    Path(args.out).write_text(txt + "\n")
print(txt)
sys.exit(1 if falhas else 0)
