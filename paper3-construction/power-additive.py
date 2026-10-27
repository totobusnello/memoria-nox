"""Item 2: resize §11 for the ADDITIVE estimand, with the dose as a 3-level factor.

Two corrections drive this, both from the adversarial pass:

CODEX FINDING 3 — the old table treated an assumed "discordance 0.30" as if it
were Var(D). The estimand is D_i = Y11 - Y10 - Y01 + Y00 with D_i in {-2..2},
and Var(D) = Var(A) + Var(B) - 2Cov(A,B) with A = Y11-Y10, B = Y01-Y00. A pair
discordance says nothing about Cov(A,B), so the sizing is redone over PLAUSIBLE
JOINT distributions instead of one assumed scalar.

CODEX FINDING 2 + the measurement it asked for — the dose 0.240 rests on n=6
sessions whose fractions are [0.020, 0.030, 0.183, 0.297, 0.422, 0.894]. A point
anchor is not defensible, so W becomes a 3-level factor at the observed order
statistics, which changes the cell count and therefore the cost.
"""
import itertools, math

Z_A = {0.05: 1.959964, 0.03: 2.170090, 0.02: 2.326348}
Z_B = 0.8416212          # power 0.80

# ---- Var(D) over joint distributions, instead of one assumed number.
# Model each cell outcome as Bernoulli with cell means (p00,p01,p10,p11) and let
# the within-instance correlation rho couple them. Var(D) is computed exactly for
# a simple exchangeable-correlation model, then the WORST case over a plausible
# rho range is used for sizing — which is what "conservative" has to mean.
def var_D(p00, p01, p10, p11, rho):
    """Var of D = Y11 - Y10 - Y01 + Y00 under exchangeable correlation rho."""
    ps = [p11, p10, p01, p00]
    sg = [math.sqrt(p * (1 - p)) for p in ps]
    sign = [1.0, -1.0, -1.0, 1.0]
    v = sum(s * s for s in sg)
    for i, j in itertools.combinations(range(4), 2):
        v += 2 * sign[i] * sign[j] * rho * sg[i] * sg[j]
    return max(v, 1e-9)

# cell means anchored on what we measured in production's replay:
#   B (memory, truncated window, old prompt)  = 0.424
#   C (full window, old prompt)               = 0.465
#   D (truncated window, new prompt)          = 0.465 estimated same order
#   D_full (full window, new prompt)          = 0.636
CELLS = (0.424, 0.465, 0.465, 0.636)      # p00, p01, p10, p11
DELTA = (CELLS[3] - CELLS[2] - CELLS[1] + CELLS[0])
print(f"cell means (p00,p01,p10,p11) = {CELLS}")
print(f"implied additive interaction = {DELTA:+.3f} = {DELTA*100:+.1f} pp")
print(f"  (production's own measured interaction on the 56 varying pairs: +21.4 pp)")

print(f"\nVar(D) across a plausible correlation range:")
for rho in (0.0, 0.2, 0.4, 0.6):
    print(f"  rho={rho:.1f} -> Var(D) = {var_D(*CELLS, rho):.4f} "
          f"(sd {math.sqrt(var_D(*CELLS, rho)):.4f})")
WORST = max(var_D(*CELLS, r) for r in (0.0, 0.2, 0.4, 0.6))
print(f"  worst case used for sizing: {WORST:.4f}")

def n_for(delta, var, alpha):
    return math.ceil((Z_A[alpha] + Z_B) ** 2 * var / delta ** 2)

print(f"\nn for the ADDITIVE contrast, at the alpha each stage actually spends:")
print(f"{'effect':>9s} {'a=.05':>7s} {'a=.03':>7s} {'a=.02':>7s}")
for d in (0.214, 0.15, 0.10, 0.08):
    row = "  ".join(f"{n_for(d, WORST, a):5d}" for a in (0.05, 0.03, 0.02))
    print(f"{d*100:8.1f}pp  {row}")
print(f"\n⚠️ the old table said n=52 for 21.4 pp. Under the additive estimand with")
print(f"   Var(D)={WORST:.3f} and the alpha the first stage actually spends (0.03),")
print(f"   it is {n_for(0.214, WORST, 0.03)}.")

# ---- cost, with W as a 3-level factor
BLOCK, C_BLOCK = 2000, 0.35 / 563
C_JUDGE, C_ANSWER = 0.0098 / 152, 0.0005
MED = 489_763
DOSES = [0.020, 0.240, 0.894]          # observed order statistics: both ends + middle
print(f"\ncost with W at 3 observed levels {DOSES} x C at 2 levels = 6 cells:")
blocks = sum(MED * d / BLOCK for d in DOSES) * 2      # 2 criterion levels
per_inst = blocks * C_BLOCK + 6 * (C_ANSWER + C_JUDGE)
print(f"  distiller blocks per instance: {blocks:.0f} "
      f"(vs 608 for the old 4-cell design)")
print(f"  cost per instance: US$ {per_inst:.3f} (old: US$ 0.380)")
for n in (sorted({n_for(0.214, WORST, 0.03), 100, 240, 500})):
    if n <= 500:
        print(f"    n={n:3d} -> US$ {per_inst*n:7.2f} · "
              f"{int(blocks*n):,} distiller calls · "
              f"~{blocks*n*2/8/3600:.1f} h at 8 concurrent")
print(f"\n⇒ a 3-level dose costs MORE per instance but needs the same n, and the")
print(f"  corpus ceiling of 500 still bounds everything.")
