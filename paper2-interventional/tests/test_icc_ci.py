#!/usr/bin/env python3
"""Confronta a F implementada em stdlib no `pilot_replay` com a do `scipy`.

POR QUE ESTE TESTE EXISTE
O `pilot_replay.py` e pre-registrado: um terceiro tem de conseguir rodar o
replay sem instalar nada. Por isso a beta incompleta e o quantil da F sao
implementados a mao la dentro. O risco obvio de reimplementar estatistica e
errar em silencio — uma cauda mal calculada nao levanta excecao, so devolve um
intervalo errado com cara de certo.

Este teste importa `scipy` (aqui, e SO aqui) e exige concordancia. Se o
`scipy` nao estiver instalado ele PULA, e diz que pulou — nunca passa por
omissao.

    python3 tests/test_icc_ci.py
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pilot_replay as pr  # noqa: E402

TOL_CDF = 1e-10
TOL_PPF = 1e-6      # bissecao de 200 passos; folga bem acima do necessario


def test_f_contra_scipy() -> tuple[int, int]:
    from scipy import stats
    ok = falhas = 0
    graus = [(1, 1), (2, 5), (5, 2), (29, 100), (29, 1200), (100, 30),
             (1, 1000), (500, 500), (3, 7), (11, 13)]
    for d1, d2 in graus:
        for x in (0.001, 0.05, 0.5, 1.0, 2.0, 7.5, 50.0, 500.0):
            meu = pr._f_cdf(x, d1, d2)
            dele = float(stats.f.cdf(x, d1, d2))
            if abs(meu - dele) > TOL_CDF:
                print(f"  FALHA cdf({x}, {d1}, {d2}): {meu!r} vs {dele!r}")
                falhas += 1
            else:
                ok += 1
        for p in (0.005, 0.025, 0.1, 0.5, 0.9, 0.975, 0.995):
            meu = pr._f_ppf(p, d1, d2)
            dele = float(stats.f.ppf(p, d1, d2))
            if abs(meu - dele) > TOL_PPF * max(1.0, abs(dele)):
                print(f"  FALHA ppf({p}, {d1}, {d2}): {meu!r} vs {dele!r}")
                falhas += 1
            else:
                ok += 1
    return ok, falhas


def test_icc_degenerado() -> tuple[int, int]:
    """Casos de borda que devem devolver 0 sem estourar."""
    ok = falhas = 0
    casos = {
        "vazio": {},
        "um grupo so": {1: [1.0, 2.0]},
        "n <= k": {1: [1.0], 2: [2.0]},
        "variancia zero": {1: [3.0, 3.0], 2: [3.0, 3.0]},
    }
    for nome, dados in casos.items():
        out = pr.icc_anova(dados)
        if out["icc"] != 0.0:
            print(f"  FALHA {nome}: icc={out['icc']}, esperado 0.0")
            falhas += 1
        else:
            ok += 1
    return ok, falhas


def test_icc_contem_o_ponto() -> tuple[int, int]:
    """O IC tem de conter a estimativa pontual. Trivial, e por isso mesmo o
    primeiro a quebrar se as caudas estiverem trocadas."""
    ok = falhas = 0
    rng = [i * 0.37 % 1.0 for i in range(200)]      # deterministico, sem random
    for desloc in (0.0, 0.3, 1.5):
        dados = {}
        for g in range(12):
            base = g * desloc
            dados[g] = [base + rng[(g * 17 + j) % len(rng)] for j in range(8)]
        out = pr.icc_anova(dados)
        if out["ic_low"] is None:
            print(f"  FALHA desloc={desloc}: IC nao calculado")
            falhas += 1
            continue
        if not (out["ic_low"] <= out["icc"] <= out["ic_high"]):
            print(f"  FALHA desloc={desloc}: {out['ic_low']} <= {out['icc']} "
                  f"<= {out['ic_high']} e falso")
            falhas += 1
        else:
            ok += 1
    return ok, falhas


def test_ms_reproduzem_icc() -> tuple[int, int]:
    """Os MS expostos tem de reconstruir o ICC publicado.

    Esta e a razao de o campo existir: o SIZING-2026-08-14 teve de reconstruir
    a ANOVA num script separado e chegou a 0,0964 contra 0,1175 do canonico,
    obrigando o documento a dizer que o IC indicava "a largura, nao o intervalo
    oficial". Com os MS vindo do mesmo codigo que produz o ponto, reconstruir
    tem de dar exatamente o mesmo numero.
    """
    dados = {g: [(g * 13 + j * 7) % 11 / 3.0 for j in range(6)] for g in range(9)}
    out = pr.icc_anova(dados)
    msb, msw, m_bar = out["ms_between"], out["ms_within"], out["m_bar"]
    recon = max(0.0, (msb - msw) / (msb + (m_bar - 1) * msw))
    if abs(recon - out["icc"]) > 1e-5:
        print(f"  FALHA: reconstruido {recon:.8f} != publicado {out['icc']:.8f}")
        return 0, 1
    return 1, 0


def main() -> int:
    total_ok = total_falhas = 0
    pulados = []

    try:
        import scipy  # noqa: F401
    except ImportError:
        pulados.append("test_f_contra_scipy (scipy ausente)")
    else:
        print("test_f_contra_scipy")
        o, f = test_f_contra_scipy()
        total_ok += o
        total_falhas += f

    for nome, fn in (("test_icc_degenerado", test_icc_degenerado),
                     ("test_icc_contem_o_ponto", test_icc_contem_o_ponto),
                     ("test_ms_reproduzem_icc", test_ms_reproduzem_icc)):
        print(nome)
        o, f = fn()
        total_ok += o
        total_falhas += f

    print(f"\n{total_ok} ok, {total_falhas} falhas")
    for p in pulados:
        print(f"PULADO: {p}")
    if pulados and not total_falhas:
        print("⚠️ a comparacao contra scipy NAO rodou — isto nao e um passe completo")
    return 1 if total_falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
