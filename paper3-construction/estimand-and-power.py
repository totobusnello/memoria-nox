#!/usr/bin/env python3
"""The estimand, the serial null, and what 500 instances can actually resolve.

Why this file exists. On 2026-10-27 two adversarial voices from different
families (OpenAI gpt-6-astra, DeepSeek v4-pro) independently reported the same
defect in §11.4: the power table sized the test of the INTERACTION using the
TOTAL effect as delta. The two are not the same number and the document said
both, ten lines apart.

  main effect of the window   +4.1 pp
  main effect of the prompt   +4.1 pp
  interaction                +13.0 pp   <- the estimand
                             -------
  total                      +21.2 pp   <- what the table used as delta

Sizing an interaction test on the total effect overstates power by the ratio of
their squares. This script recomputes every number §11.4 cites, and exits 1 if
the document and the arithmetic disagree, so the defect cannot come back in
silence the way it arrived.

THREE THINGS IT ESTABLISHES, each of which changed the design:

1. The interaction does not fit. n = 522 at alpha=0.03 against a corpus of 500.
   So the interaction cannot be the confirmatory primary, and the primary is now
   the TOTAL effect, which does fit at n ~ 196.

2. "Worst case over rho in [0, 0.6]" was not a worst case. gpt-6-astra supplied a
   joint distribution with the SAME four marginals and Var(D) = 3.3471 against
   the 0.973 the document called conservative. Reproduced exactly below. A
   maximum inside a dependence family one chose oneself is not an upper bound,
   and calling it "conservative" was false.

3. A positive interaction is NOT evidence of joint repair on its own. In a
   two-stage system P(correct | w,c) = e_w * q_c — the window decides whether
   evidence arrives, the prompt decides whether it is used — the additive
   interaction is (e1-e0)(q1-q0) > 0 with no joint mechanism at all. That model
   is therefore the substantive null, and it is testable: fitted to our own
   three other cells it predicts +0.4 pp, against +13.0 pp measured. The
   observed effect is 33x what serial chaining explains. This is what gives the
   design a refutable prediction, which it did not have before: if the benchmark
   returns I ~ I_serial, the thesis is refuted.

Pure arithmetic over the four published cell means. No network, no database,
nothing to mutate. Run: python3 paper3-construction/estimand-and-power.py
"""
import pathlib
import sys
from statistics import NormalDist

ND = NormalDist()

# The four cell means the production replay measured (PREREGISTRATION-DRAFT §11.4).
# Y[w][c]: w = window (0 truncated, 1 full), c = criterion (0 v1, 1 v2).
Y00, Y01, Y10, Y11 = 0.424, 0.465, 0.465, 0.636

CORPUS = 500          # LongMemEval s_cleaned, after §11.1's exclusions
POWER = 0.80
ALPHA_STAGE1 = 0.03   # the alpha stage 1 actually spends
ALPHA_STAGE2 = 0.02   # and stage 2's, which only the document used to carry


def n_required(delta, var, alpha, power=POWER):
    """Paired two-sided n for mean difference `delta` with variance `var`."""
    z_a = ND.inv_cdf(1 - alpha / 2)
    z_b = ND.inv_cdf(power)
    return (z_a + z_b) ** 2 * var / delta ** 2


def power_at(n, delta, var, alpha):
    """Achieved power of a given n — the question the table never asked."""
    z_a = ND.inv_cdf(1 - alpha / 2)
    return ND.cdf(delta / (var / n) ** 0.5 - z_a)


def var_d_exchangeable(rho):
    """Var(D) under exchangeable within-instance correlation rho.

    D = Y11 - Y10 - Y01 + Y00, each term Bernoulli with the measured marginal.
    Var(sum of signed terms) = sum Var + 2 * sum_{i<j} sign_i sign_j Cov_ij,
    with Cov_ij = rho * sd_i * sd_j. The signs are (+,-,-,+), so the six pairs
    carry signs (-,-,+,+,-,-): four negative, two positive.
    """
    means = (Y11, Y10, Y01, Y00)
    signs = (1, -1, -1, 1)
    sds = [(m * (1 - m)) ** 0.5 for m in means]
    total = sum(sd ** 2 for sd in sds)
    for i in range(4):
        for j in range(i + 1, 4):
            total += 2 * signs[i] * signs[j] * rho * sds[i] * sds[j]
    return total


def var_d_codex_counterexample():
    """gpt-6-astra's joint distribution: same marginals, Var(D) far larger.

    U ~ Uniform(0,1);  Y11 = 1[U < 0.636],  Y00 = 1[U < 0.424],
    Y10 = Y01 = 1[U > 0.535].  Integrated exactly over the intervals on which
    every indicator is constant — no simulation, so the number is not a sample.
    """
    cuts = sorted({0.0, 0.424, 0.535, 0.636, 1.0})
    e_d = e_d2 = 0.0
    marg = {"11": 0.0, "00": 0.0, "10": 0.0}
    for a, b in zip(cuts, cuts[1:]):
        w, u = b - a, (a + b) / 2
        y11 = 1 if u < 0.636 else 0
        y00 = 1 if u < 0.424 else 0
        y10 = 1 if u > 0.535 else 0
        d = y11 - y10 - y10 + y00
        marg["11"] += w * y11
        marg["00"] += w * y00
        marg["10"] += w * y10
        e_d += w * d
        e_d2 += w * d * d
    return e_d2 - e_d ** 2, marg, e_d


def serial_null():
    """The two-stage model fitted to three cells, predicting the fourth.

    P(correct | w,c) = e_w * q_c has three free quantities once scale is fixed,
    so Y00, Y01, Y10 determine Y11 = Y01*Y10/Y00 exactly. The interaction that
    chaining alone predicts is then whatever that leaves.
    """
    y11_pred = (Y01 * Y10) / Y00
    i_serial = y11_pred - Y10 - Y01 + Y00
    return y11_pred, i_serial


def main():
    ok = True
    main_w = Y10 - Y00
    main_c = Y01 - Y00
    interaction = Y11 - Y10 - Y01 + Y00
    total = Y11 - Y00

    print("=== 1. decomposition of the four measured cell means ===")
    print(f"  Y00 truncated+v1 {Y00:.3f}   Y01 truncated+v2 {Y01:.3f}")
    print(f"  Y10 full+v1      {Y10:.3f}   Y11 full+v2      {Y11:.3f}")
    print(f"  main effect, window     {main_w * 100:+6.1f} pp")
    print(f"  main effect, criterion  {main_c * 100:+6.1f} pp")
    print(f"  INTERACTION             {interaction * 100:+6.1f} pp   <- secondary estimand")
    print(f"  TOTAL                   {total * 100:+6.1f} pp   <- PRIMARY estimand")
    if abs((main_w + main_c + interaction) - total) > 1e-9:
        print("  ! decomposition does not close")
        ok = False
    else:
        print(f"  checks: {main_w * 100:.1f} + {main_c * 100:.1f} + "
              f"{interaction * 100:.1f} = {total * 100:.1f} pp")

    print("\n=== 2. the serial null — a positive interaction is not enough ===")
    y11_pred, i_serial = serial_null()
    print(f"  serial model predicts Y11 = {y11_pred:.4f}  -> interaction {i_serial * 100:+.1f} pp")
    print(f"  measured              Y11 = {Y11:.4f}  -> interaction {interaction * 100:+.1f} pp")
    print(f"  excess over serial chaining: {(interaction - i_serial) * 100:+.1f} pp "
          f"({interaction / i_serial:.0f}x)")
    print(f"  multiplicativity check: Y00*Y11 = {Y00 * Y11:.4f} vs "
          f"Y01*Y10 = {Y01 * Y10:.4f} (equal iff serial)")
    if interaction <= i_serial:
        print("  ! the measured interaction does not exceed serial chaining — "
              "the thesis has no room left")
        ok = False

    print("\n=== 3. Var(D): the exchangeable family, and why it is not an upper bound ===")
    print(f"  {'rho':>6} {'Var(D)':>9}")
    for rho in (0.0, 0.2, 0.4, 0.6):
        print(f"  {rho:6.1f} {var_d_exchangeable(rho):9.3f}")
    var_ex = var_d_exchangeable(0.0)
    var_cx, marg, e_d = var_d_codex_counterexample()
    print(f"\n  counterexample (gpt-6-astra, 2026-10-27): same marginals, different joint")
    print(f"    reproduces Y11={marg['11']:.3f} Y00={marg['00']:.3f} "
          f"Y10=Y01={marg['10']:.3f}, E[D]={e_d:.3f}")
    print(f"    Var(D) = {var_cx:.4f}  against the {var_ex:.3f} the draft called conservative")
    if var_cx <= var_ex:
        print("  ! the counterexample no longer bites")
        ok = False

    print("\n=== 4. what each candidate delta costs, alpha=0.03, power 0.80 ===")
    print(f"  {'delta':<34} {'Var=' + format(var_ex, '.3f'):>12} {'Var=' + format(var_cx, '.3f'):>12}")
    rows = [
        ("TOTAL effect (primary)", total),
        ("interaction vs 0", interaction),
        ("interaction vs serial null", interaction - i_serial),
    ]
    n_primary = None
    for label, d in rows:
        n_lo = n_required(d, var_ex, ALPHA_STAGE1)
        n_hi = n_required(d, var_cx, ALPHA_STAGE1)
        if label.startswith("TOTAL"):
            n_primary = n_lo
        flag = "" if n_lo <= CORPUS else "   <- does not fit in 500"
        print(f"  {label:<34} {n_lo:12.0f} {n_hi:12.0f}{flag}")

    print(f"\n=== 5. achieved power at the n the corpus allows (Var={var_ex:.3f}) ===")
    print(f"  {'n':>5} {'total effect':>14} {'interaction':>14} {'vs serial':>12}")
    for n in (196, 200, 240, CORPUS):
        print(f"  {n:5d} "
              f"{power_at(n, total, var_ex, ALPHA_STAGE1) * 100:13.1f}% "
              f"{power_at(n, interaction, var_ex, ALPHA_STAGE1) * 100:13.1f}% "
              f"{power_at(n, interaction - i_serial, var_ex, ALPHA_STAGE1) * 100:11.1f}%")

    print("\n=== 6. is an equivalence verdict reachable at all? ===")
    # This exists because the document once pre-set a 5 pp equivalence margin and called
    # an interval inside it "evidence of absence". No n this corpus allows produces an
    # interval that narrow, so the state was unreachable — and nothing here noticed,
    # because this script only ever checked POWER, which is about DETECTING an effect,
    # not about BOUNDING one. An adversarial pass (GLM-5.3, 2026-10-27) did the
    # arithmetic the gate was missing. A gate blind to the claim it should protect is
    # itself the defect.
    margin = 0.05
    print(f"  margin {margin * 100:.0f} pp, Var(D)={var_ex:.3f}")
    print(f"  {'n':>6}  {'SE':>8}  {'alpha':>6}  {'half-width':>11}  inside margin?")
    reachable_in_corpus = False
    for n in (200, CORPUS, 1000, 2000, 3000):
        for a in (ALPHA_STAGE1, ALPHA_STAGE2):
            se = (var_ex / n) ** 0.5
            hw = ND.inv_cdf(1 - a / 2) * se
            if hw < margin and n <= CORPUS:
                reachable_in_corpus = True
            print(f"  {n:>6}  {se * 100:>7.2f}pp  {a:>6}  {hw * 100:>10.2f}pp  "
                  f"{'yes' if hw < margin else 'no'}")
    n_equiv = var_ex * (ND.inv_cdf(1 - ALPHA_STAGE2 / 2) / margin) ** 2
    print(f"  an interval inside +/-{margin * 100:.0f} pp needs n={n_equiv:.0f}, "
          f"corpus has {CORPUS}")
    if reachable_in_corpus:
        print("  ! equivalence became reachable within the corpus — the decision tables "
              "should regain an absence state, and this note be re-examined")
        ok = False
    else:
        print("  -> not reachable: a CI containing 0 must be reported INCONCLUSIVE, "
              "never as absence")
        plan = (pathlib.Path(__file__).resolve().parent
                / "PREREGISTRATION-DRAFT.md").read_text(encoding="utf-8")
        for promise in ("evidence of absence at the pre-set margin",
                        "Equivalence margin, pre-set"):
            if promise in plan:
                print(f"  ! the plan still promises an absence verdict: {promise!r}")
                ok = False

    print("\n=== 7. the gate ===")
    n_inter = n_required(interaction, var_ex, ALPHA_STAGE1)
    print(f"  primary (total effect) needs n={n_primary:.0f}, corpus has {CORPUS}: "
          f"{'FITS' if n_primary <= CORPUS else 'DOES NOT FIT'}")
    print(f"  interaction needs n={n_inter:.0f}: "
          f"{'fits' if n_inter <= CORPUS else 'DOES NOT FIT — hence secondary'}")
    if n_primary > CORPUS:
        print("  ! the primary does not fit the corpus — the design cannot be confirmatory")
        ok = False
    if n_inter <= CORPUS:
        print("  ! the interaction now fits; it should be promoted back to primary "
              "and this script's premise re-examined")
        ok = False

    print(f"\n  {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
