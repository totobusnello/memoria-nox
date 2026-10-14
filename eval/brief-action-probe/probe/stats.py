"""Statistics for the 7b probe (spec §4, §5.4, §6). Stdlib only."""
import math
import random


def stratum_estimate(by_cluster):
    means = [sum(v) / len(v) for v in by_cluster.values() if v]
    return sum(means) / len(means)


def cluster_bootstrap(by_cluster, n_draws=10000, seed=0):
    """Resample clusters with replacement; each draw = mean of cluster means."""
    rng = random.Random(seed)
    means = [sum(v) / len(v) for v in by_cluster.values() if v]
    k = len(means)
    return [sum(means[rng.randrange(k)] for _ in range(k)) / k for _ in range(n_draws)]


def one_sided_p(draws):
    return (1 + sum(1 for d in draws if d <= 0)) / (1 + len(draws))


def percentile_ci(draws, level=0.95):
    s = sorted(draws)
    lo = (1 - level) / 2
    return s[int(math.floor(lo * (len(s) - 1)))], s[int(math.ceil((1 - lo) * (len(s) - 1)))]


def holm(pvals):
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def _hyper_pmf(a, r1, c1, n):
    return math.comb(c1, a) * math.comb(n - c1, r1 - a) / math.comb(n, r1)


def fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact test for [[a, b], [c, d]]."""
    r1, c1, n = a + b, a + c, a + b + c + d
    if n == 0:
        return 1.0
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    p_obs = _hyper_pmf(a, r1, c1, n)
    total = 0.0
    for x in range(lo, hi + 1):
        p = _hyper_pmf(x, r1, c1, n)
        if p <= p_obs * (1 + 1e-7):
            total += p
    return min(1.0, total)


def _binom_logpmf(k, n, p):
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log(1 - p))


def tost_proportion(k, n, p0=0.5, margin=0.10, alpha=0.05):
    """Exact binomial TOST: is the proportion k/n equivalent to p0 within ±margin?"""
    p_low = sum(math.exp(_binom_logpmf(x, n, p0 - margin)) for x in range(k, n + 1))
    p_high = sum(math.exp(_binom_logpmf(x, n, p0 + margin)) for x in range(0, k + 1))
    return (p_low < alpha and p_high < alpha), p_low, p_high


def simulate_mde(pilot_units, dist, cluster_sizes, q_grid, n_sim=200, n_boot=1000, alpha=0.0125, seed=0):
    """§5.4. pilot_units: list of replica-id lists (4 each) for one stratum; dist(i, j) -> divergence.

    Each simulated unit takes a random pilot unit as base; each arm's two replicas are drawn without
    replacement from the base's replicas. With probability q, the comparison arm's replicas come from a
    different pilot unit. Δ = D(B1, X) − mean A/A over the three arms, as in §6.1.
    """
    rng = random.Random(seed)
    curve = []
    for q in q_grid:
        deltas, hits = [], 0
        for _ in range(n_sim):
            by_cluster = {}
            for ci, size in enumerate(cluster_sizes):
                vals = []
                for _ in range(size):
                    u = rng.randrange(len(pilot_units))
                    b1 = rng.sample(pilot_units[u], 2)
                    third = rng.sample(pilot_units[u], 2)
                    if rng.random() < q:
                        v = rng.choice([x for x in range(len(pilot_units)) if x != u])
                        cmp_ = rng.sample(pilot_units[v], 2)
                    else:
                        cmp_ = rng.sample(pilot_units[u], 2)
                    aa = (dist(*b1) + dist(*cmp_) + dist(*third)) / 3
                    d = sum(dist(x, y) for x in b1 for y in cmp_) / 4
                    vals.append(d - aa)
                by_cluster[ci] = vals
            deltas.append(stratum_estimate(by_cluster))
            draws = cluster_bootstrap(by_cluster, n_boot, rng.randrange(2 ** 31))
            hits += one_sided_p(draws) < alpha
        curve.append({"q": q, "mean_delta": sum(deltas) / len(deltas), "power": hits / n_sim})
    return curve


def mde_from_curve(curve, power=0.8):
    ok = [c["mean_delta"] for c in curve if c["power"] >= power]
    return min(ok) if ok else None
