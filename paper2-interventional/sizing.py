#!/usr/bin/env python3
"""
§9 item 7a — the pre-registered sizing function `f`.

    N_epochs = f(r_hat, p0_hat, icc, mde, ...)

The pre-registration requires this function to be **locked before the pilot
runs**, evaluated **exactly once** afterwards, and its output locked with no
re-runs and no post-hoc MDE shopping. Committing the executable is what makes
"we did not shop for a sample size" checkable rather than asserted.

WHY THIS IS DECIDABLE NOW, WHILE ITEMS 6 AND 8 ARE NOT
------------------------------------------------------
The *form* of `f` is a design decision; only its *inputs* need data. Locking
the form now is precisely what the pre-registration asks for — and it makes the
pilot's job unambiguous: produce `r_hat`, `p0_hat`, `icc`, and nothing else.

THE MODEL
---------
Primary outcome is a **density**: repeated failures per session-hour. Counts
over exposure ⇒ Poisson. Randomization is at the **epoch**, while outcomes
accrue per session-hour *within* an epoch ⇒ intra-cluster correlation, handled
by a design effect.

Under control, the repeated-failure density factorizes:

    lambda_0 = r_hat * p0_hat

    r_hat  — eligible opportunities per session-hour
    p0_hat — conditional repeat rate given opportunity, control arm

Treatment is expected to reduce it: lambda_1 = lambda_0 * (1 - mde).

Testing H0: lambda_1 == lambda_0 on the log rate ratio, whose variance under
the normal approximation is 1/E_1 + 1/E_0 with E_a the expected events in arm
`a`. With `K` epochs per arm and `T` session-hours of analyzed exposure per
epoch, E_a = K * T * lambda_a. Requiring

    |log(RR)| >= (z_{1-alpha/2} + z_{1-beta}) * sqrt(1/E_1 + 1/E_0)

and solving for K gives the expression in `epochs_per_arm()`.

The design effect DE = 1 + (m_bar - 1) * icc inflates K, with m_bar the mean
number of session-hours per epoch. Two deliberate conservatisms:

1. The crossover is analyzed as a **two-sample contrast** over post-washout
   session-hours, ignoring the within-fleet pairing that a crossover normally
   buys. Real power will be no worse.
2. Exposure `T` is *analyzed* exposure — post-washout only. Washout hours are
   excluded from the epoch's contribution, so `T` must already net them out.

WHAT THIS FUNCTION DELIBERATELY DOES NOT DO
-------------------------------------------
It does not pick `mde`. It does not choose among its own outputs. It returns a
**power curve** alongside the point, because §3 commits to reporting the curve
rather than a single number — a study powered only for effects >= X% must say
so in the abstract, and that requires the curve to exist at lock time.

Run `python3 sizing.py --selftest` to print the synthetic-input vector and its
SHA-256. That hash is the "synthetic-input PAP hash" of §9 item 5: it pins the
behaviour of this file, so any later edit that changes a number is detectable
by a reader who never saw the original.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, asdict

# Normal quantiles, hard-coded so the script has **no dependencies** and cannot
# drift with a library version. A pre-registered artifact that silently changes
# because scipy changed is not pre-registered.
_Z = {0.80: 0.8416212335729143, 0.90: 1.2815515655446004,
      0.95: 1.6448536269514722, 0.975: 1.9599639845400545,
      0.99: 2.3263478740408408, 0.995: 2.5758293035489004}


def z(p: float) -> float:
    if p not in _Z:
        raise ValueError(f"quantil {p} nao esta na tabela travada: {sorted(_Z)}")
    return _Z[p]


@dataclass(frozen=True)
class SizingInputs:
    r_hat: float        # oportunidades elegiveis por hora-sessao
    p0_hat: float       # taxa condicional de repeticao no controle
    icc: float          # correlacao intra-epoch
    mde: float          # efeito relativo minimo detectavel (0.20 = 20%)
    hours_per_epoch: float          # T — exposicao ANALISADA (pos-washout)
    session_hours_per_epoch: float  # m_bar — para o design effect
    alpha: float = 0.05
    power: float = 0.80

    def validate(self) -> None:
        if not 0 < self.mde < 1:
            raise ValueError("mde tem que estar em (0,1) — e efeito RELATIVO")
        if not 0 <= self.icc < 1:
            raise ValueError("icc tem que estar em [0,1)")
        for nome in ("r_hat", "p0_hat", "hours_per_epoch", "session_hours_per_epoch"):
            if getattr(self, nome) <= 0:
                raise ValueError(f"{nome} tem que ser > 0")
        if self.p0_hat >= 1:
            raise ValueError("p0_hat e uma taxa condicional — tem que ser < 1")


def design_effect(icc: float, m_bar: float) -> float:
    """DE = 1 + (m_bar - 1) * icc. Com m_bar <= 1 nao ha cluster: DE = 1."""
    return 1.0 + max(0.0, m_bar - 1.0) * icc


def epochs_per_arm(inp: SizingInputs) -> tuple[int, dict]:
    """K por braco. Devolve tambem os intermediarios, para auditoria."""
    inp.validate()
    lam0 = inp.r_hat * inp.p0_hat
    lam1 = lam0 * (1.0 - inp.mde)
    if lam1 <= 0:
        raise ValueError("mde de 100% — rate ratio zero nao tem log")

    zsum = z(1 - inp.alpha / 2) + z(inp.power)
    log_rr = math.log(lam1 / lam0)          # negativo; so o quadrado importa
    k_bruto = (zsum ** 2) * (1 / lam1 + 1 / lam0) / (inp.hours_per_epoch * log_rr ** 2)
    de = design_effect(inp.icc, inp.session_hours_per_epoch)
    k = math.ceil(k_bruto * de)

    return k, {
        "lambda_0": lam0, "lambda_1": lam1, "log_rate_ratio": log_rr,
        "z_sum": zsum, "k_bruto": k_bruto, "design_effect": de,
        "eventos_esperados_controle": k * inp.hours_per_epoch * lam0,
        "eventos_esperados_tratamento": k * inp.hours_per_epoch * lam1,
    }


def power_at(inp: SizingInputs, k_per_arm: int, efeito: float) -> float:
    """Poder para um efeito relativo verdadeiro, com K fixo. É a curva do §3."""
    lam0 = inp.r_hat * inp.p0_hat
    lam1 = lam0 * (1.0 - efeito)
    if lam1 <= 0:
        return 1.0
    de = design_effect(inp.icc, inp.session_hours_per_epoch)
    e0 = k_per_arm * inp.hours_per_epoch * lam0 / de
    e1 = k_per_arm * inp.hours_per_epoch * lam1 / de
    se = math.sqrt(1 / e0 + 1 / e1)
    # Normal padrao via erf — sem dependencia externa.
    zc = z(1 - inp.alpha / 2)
    arg = abs(math.log(lam1 / lam0)) / se - zc
    return 0.5 * (1.0 + math.erf(arg / math.sqrt(2.0)))


def f(inp: SizingInputs, grade: tuple[float, ...] = (0.05, 0.10, 0.15, 0.20, 0.30, 0.40)) -> dict:
    """A funcao pre-registrada. Deterministica: mesmos inputs, mesmo output."""
    k, detalhe = epochs_per_arm(inp)
    return {
        "inputs": asdict(inp),
        "epochs_por_braco": k,
        "N_epochs_total": 2 * k,
        "curva_de_poder": {f"{e:.2f}": round(power_at(inp, k, e), 4) for e in grade},
        "intermediarios": {x: (round(v, 6) if isinstance(v, float) else v)
                           for x, v in detalhe.items()},
    }


# ── Vetor sintetico: fixa o comportamento do arquivo, nao o resultado do estudo ──
# Os numeros abaixo NAO sao estimativas do sistema real. Sao entradas arbitrarias
# e fixas cuja unica funcao e produzir um hash estavel. Trocar a matematica muda
# o hash; um leitor detecta a troca sem ter visto o original.
SINTETICO = SizingInputs(
    r_hat=0.40, p0_hat=0.25, icc=0.05, mde=0.20,
    hours_per_epoch=12.0, session_hours_per_epoch=8.0,
)


def selftest() -> str:
    out = f(SINTETICO)
    blob = json.dumps(out, sort_keys=True, separators=(",", ":")).encode()
    h = hashlib.sha256(blob).hexdigest()
    print(json.dumps(out, indent=2, sort_keys=True))
    print(f"\nSHA-256 do vetor sintetico: {h}")
    return h


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Funcao de sizing pre-registrada (§9 item 7a)")
    ap.add_argument("--selftest", action="store_true",
                    help="roda o vetor sintetico e imprime o hash do PAP")
    for campo in ("r-hat", "p0-hat", "icc", "mde", "hours-per-epoch", "session-hours-per-epoch"):
        ap.add_argument(f"--{campo}", type=float)
    a = ap.parse_args()

    if a.selftest or a.r_hat is None:
        selftest()
    else:
        print(json.dumps(f(SizingInputs(
            r_hat=a.r_hat, p0_hat=a.p0_hat, icc=a.icc, mde=a.mde,
            hours_per_epoch=a.hours_per_epoch,
            session_hours_per_epoch=a.session_hours_per_epoch,
        )), indent=2, sort_keys=True))
