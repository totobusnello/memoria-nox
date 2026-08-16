#!/usr/bin/env python3
"""Epoch -> arm assignment for the Paper 2 interventional study.

This is the script Sec. 2 registers pre-hoc ("the assignment script, with its
commit hash").  It is deterministic: given the seed derived from the drand
beacon and the list of epochs, it produces one assignment sequence, and any
third party can reproduce it bit-for-bit.

It also implements the *same* scheme in permutation mode, because Sec. 5's
sharp-null test re-randomizes "under the same balancing constraints".  Having
one implementation serve both is the point: a permutation test that draws from
a different distribution than the assignment did is not a valid null.

--------------------------------------------------------------------------
WHAT IS REGISTERED HERE, AND WHAT WAS ONLY IMPLIED BEFORE
--------------------------------------------------------------------------

Sec. 2 locks: 174 epochs, fleet-wide, 24 h, "assigned to arm by constrained
randomization balancing weekday/weekend and calendar halves".  Three things
that sentence needs in order to be executable were never written down, and are
fixed here:

1.  **The dose allocation.**  `sizing.py` powers a TWO-arm contrast at K = 87
    per arm.  Sec. 2 also locks a dose band `w in {2.0, 4.0, 7.5}` and calls it
    "a real gradient, not three labels for one brief", with a dose-response
    reading rule predicting a step at 2.0->4.0 and another at 4.0->7.5.  Those
    two facts only coexist under one allocation:

        control  87 epochs
        w = 2.0  29 epochs   |
        w = 4.0  29 epochs   |-- 87 treatment epochs
        w = 7.5  29 epochs   |

    The primary contrast pools the three doses as "treatment", which is what
    the 87/87 power calculation assumes and leaves every locked number intact.
    The dose-response reading rule is secondary and runs at 29 per dose --
    stated plainly because 29 is a much weaker instrument than 87, and a
    reader is entitled to know that before the result exists.

    87 = 29 x 3 exactly, so the allocation needs no remainder rule at the top
    level.

2.  **The randomization scheme.**  Stratified block randomization over four
    strata:

        (first calendar half | second calendar half) x (weekday | weekend)

    Within each stratum, group counts are allocated by largest remainder and
    the labels are then shuffled by a seeded Fisher-Yates.  This satisfies both
    registered constraints BY CONSTRUCTION rather than by rejection, so there
    is no acceptance rate to depend on and no failure mode where the sampler
    quietly relaxes a constraint after N tries.

3.  **The tolerance.**  For every group `g` and stratum `s`, the realized count
    obeys

        | n(g,s) - |g|*|s|/N |  <  1

    i.e. each cell lands on the floor or the ceiling of its exact share.  This
    is the tightest tolerance any integer allocation can meet, and it is a
    property of the scheme, not a check performed afterwards.  `verify` re-
    asserts it anyway, because a registered tolerance that is never tested is
    a claim rather than a constraint.

--------------------------------------------------------------------------
RANDOMNESS
--------------------------------------------------------------------------

Python's `random` is NOT used.  Seeding it reproducibly across versions and
languages is a promise this study cannot keep, and "re-run the committed
script" has to mean re-run it in any language.  Instead the entropy stream is
counter-mode SHA-256:

    block_i = SHA256(seed_bytes || b"|" || ascii(i))

read as a big-endian integer stream.  Uniform draws in [0, n) use rejection on
the top multiple of n, so the result is exactly uniform and the rejection rule
is explicit rather than implementation-defined.

The seed itself follows Sec. 2:  seed = SHA256(randomness_hex(R)), where
`randomness_hex` is hashed as LOWERCASE ASCII TEXT, not as decoded bytes.  Sec.
2 spells this out because the two differ and leaving it implicit would make
third-party verification a coin flip.

--------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------

    # derive the seed from a drand round and assign
    python3 assign_arms.py assign --round 30800000 --start 2026-09-01 \
        --epochs 174 --out ASSIGNMENT.json

    # or supply the seed directly (offline / testing)
    python3 assign_arms.py assign --seed <64-hex> --start 2026-09-01

    # check a published assignment against its inputs
    python3 assign_arms.py verify --assignment ASSIGNMENT.json

    # permutation draws for the Sec. 5 sharp-null test
    python3 assign_arms.py permute --assignment ASSIGNMENT.json --n 10000

No network access is required except for `--round`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass, asdict

# ---------------------------------------------------------------------------
# Locked design constants.  Changing any of these is an amendment, not a fix.
# ---------------------------------------------------------------------------

N_EPOCHS = 174                    # LOCKED 2026-08-15, sizing.py
DOSES = (2.0, 4.0, 7.5)           # LOCKED 2026-08-16, Sec. 2 designation block
CONTROL = "control"
GROUPS = (CONTROL,) + tuple(f"w{d:g}" for d in DOSES)

DRAND_CHAIN = "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971"
DRAND_API = "https://api.drand.sh/{chain}/public/{rnd}"   # v1: has `randomness`

# Weekend = Saturday and Sunday in the epoch-boundary timezone (BRT), which is
# the timezone the 06:00 boundary is defined in.  The epoch is labelled by the
# calendar date on which it starts.
WEEKEND = {5, 6}                  # Python weekday(): Mon=0 .. Sun=6


# ---------------------------------------------------------------------------
# Entropy: counter-mode SHA-256.  Language-agnostic and verifiable.
# ---------------------------------------------------------------------------

class HashStream:
    """Deterministic uniform integers from a seed, portable across languages."""

    def __init__(self, seed_hex: str):
        self._seed = bytes.fromhex(seed_hex)
        self._counter = 0
        self._buf = b""

    def _more(self) -> None:
        block = hashlib.sha256(
            self._seed + b"|" + str(self._counter).encode("ascii")
        ).digest()
        self._counter += 1
        self._buf += block

    def _take(self, nbytes: int) -> int:
        while len(self._buf) < nbytes:
            self._more()
        chunk, self._buf = self._buf[:nbytes], self._buf[nbytes:]
        return int.from_bytes(chunk, "big")

    def below(self, n: int) -> int:
        """Uniform in [0, n).  Rejection on the top multiple of n -- exact.

        NOTE FOR REIMPLEMENTERS.  `limit` is computed in Python's
        arbitrary-precision integers, where `(2**64 // n) * n` is exact and
        can equal 2**64 itself (when n divides 2**64, in which case no draw is
        ever rejected -- correctly, since the space divides evenly).  In a
        language with fixed-width 64-bit integers that expression OVERFLOWS to
        0 for such n, and every draw would then be rejected forever.  Compute
        the limit as `2**64 - (2**64 % n)` in unsigned arithmetic, or in
        128-bit.  The study itself runs at n <= 174 and is unaffected either
        way; this matters only for the portability the docstring promises.

        (An adversarial review of 2026-08-16 reported the overflow as a defect
        *in this file*.  It is not -- Python integers do not overflow, and the
        zero-rejection case at n = 2**32 is exact rather than accidental.  The
        real and narrower point is the one recorded above: a reimplementation
        in a fixed-width language needs care here.)
        """
        if n <= 0:
            raise ValueError("n must be positive")
        if n == 1:
            return 0
        limit = 2 ** 64 - (2 ** 64) % n     # == (2**64 // n) * n, overflow-safe
        while True:
            x = self._take(8)
            if x < limit:
                return x % n

    def shuffle(self, seq: list) -> list:
        """Fisher-Yates, descending, drawing j in [0, i]."""
        out = list(seq)
        for i in range(len(out) - 1, 0, -1):
            j = self.below(i + 1)
            out[i], out[j] = out[j], out[i]
        return out


# ---------------------------------------------------------------------------
# Seed derivation (Sec. 2)
# ---------------------------------------------------------------------------

def fetch_randomness_hex(rnd: int, chain: str = DRAND_CHAIN) -> str:
    url = DRAND_API.format(chain=chain, rnd=rnd)
    with urllib.request.urlopen(url, timeout=30) as r:
        payload = json.load(r)
    if "randomness" not in payload:
        raise SystemExit(
            f"no `randomness` field at {url} -- this must be the v1 API; "
            "the v2 endpoint returns only round and signature."
        )
    return payload["randomness"].strip().lower()


def seed_from_randomness_hex(randomness_hex: str) -> str:
    """SHA256 of the lowercase ASCII hex STRING, per Sec. 2 -- not the bytes."""
    return hashlib.sha256(randomness_hex.encode("ascii")).hexdigest()


# ---------------------------------------------------------------------------
# Strata and allocation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Epoch:
    index: int          # 0-based position in the study
    date: str           # YYYY-MM-DD, the calendar date the epoch starts on

    def weekday(self) -> int:
        return dt.date.fromisoformat(self.date).weekday()


def build_epochs(start: str, n: int) -> list[Epoch]:
    d0 = dt.date.fromisoformat(start)
    return [Epoch(i, (d0 + dt.timedelta(days=i)).isoformat()) for i in range(n)]


def stratum_of(e: Epoch, n: int) -> str:
    half = "h1" if e.index < n / 2 else "h2"
    kind = "wknd" if e.weekday() in WEEKEND else "wkdy"
    return f"{half}:{kind}"


def group_sizes(n: int) -> dict[str, int]:
    """87 control, 29 per dose, at N = 174.  Scales proportionally otherwise.

    The proportional fallback exists so the script can be exercised on short
    test horizons; the study itself runs at N_EPOCHS and the exact split is the
    one registered above.
    """
    n_control = n // 2
    per_dose, extra = divmod(n - n_control, len(DOSES))
    sizes = {CONTROL: n_control}
    for i, d in enumerate(DOSES):
        sizes[f"w{d:g}"] = per_dose + (1 if i < extra else 0)
    return sizes


def controlled_round(
    sizes: dict[str, int], strat_sizes: dict[str, int], n: int, rng: HashStream
) -> dict[tuple[str, str], int]:
    """Round the exact group x stratum table so BOTH marginals stay exact.

    The exact cell value is `x(g,s) = sizes[g] * strat_sizes[s] / n`.  We need
    an integer table whose row sums are `sizes`, whose column sums are
    `strat_sizes`, and every cell of which is floor(x) or ceil(x) -- the last
    condition is what makes the registered tolerance |n - x| < 1 a property of
    the construction rather than a hope.

    This is the classical two-way controlled-rounding problem.  An earlier
    version of this script instead apportioned per stratum and then "repaired"
    the group marginals by moving labels, which is the natural thing to write
    and is wrong: every repair move perturbs a cell that was already correct.
    Measured on the first test seed it produced a deviation of 1.17 against a
    tolerance of 1.0.  The failure is recorded here rather than quietly fixed,
    because "by construction" was asserted in the docstring before it was true.

    With |GROUPS| x |strata| = 16 cells the feasible set is small enough to
    enumerate exactly, so there is no heuristic and no acceptance rate.  The
    choice among feasible tables is uniform, drawn from the same seeded stream.
    """
    keys = [(g, s) for g in GROUPS for s in sorted(strat_sizes)]
    exact = {k: sizes[k[0]] * strat_sizes[k[1]] / n for k in keys}
    base = {k: int(exact[k]) for k in keys}

    # Cells already integral must not be bumped: a +1 there would land exactly
    # on the tolerance rather than inside it.
    free = [k for k in keys if exact[k] != base[k]]

    need_row = {g: sizes[g] - sum(base[(g, s)] for s in strat_sizes)
                for g in GROUPS}
    need_col = {s: strat_sizes[s] - sum(base[(g, s)] for g in GROUPS)
                for s in strat_sizes}

    feasible = []
    for mask in range(1 << len(free)):
        bump = {free[i] for i in range(len(free)) if mask >> i & 1}
        if all(sum(1 for s in strat_sizes if (g, s) in bump) == need_row[g]
               for g in GROUPS) and \
           all(sum(1 for g in GROUPS if (g, s) in bump) == need_col[s]
               for s in strat_sizes):
            feasible.append(bump)

    if not feasible:
        raise SystemExit(
            "no controlled rounding exists for this horizon under the "
            "floor/ceil constraint -- the design cannot be balanced at this "
            "N and start date; do not relax the tolerance silently."
        )

    chosen = feasible[rng.below(len(feasible))]
    return {k: base[k] + (1 if k in chosen else 0) for k in keys}


def assign(epochs: list[Epoch], seed_hex: str) -> dict[str, str]:
    """Stratified block randomization.  Returns {epoch_date: group}."""
    n = len(epochs)
    sizes = group_sizes(n)

    strata: dict[str, list[Epoch]] = {}
    for e in epochs:
        strata.setdefault(stratum_of(e, n), []).append(e)
    strat_sizes = {s: len(m) for s, m in strata.items()}

    rng = HashStream(seed_hex)
    table = controlled_round(sizes, strat_sizes, n, rng)

    out: dict[str, str] = {}
    for name in sorted(strata):
        labels: list[str] = []
        for g in GROUPS:
            labels += [g] * table[(g, name)]
        for e, g in zip(rng.shuffle(strata[name]), labels):
            out[e.date] = g

    return out


# ---------------------------------------------------------------------------
# Balance report and the registered tolerance
# ---------------------------------------------------------------------------

def balance(epochs: list[Epoch], mapping: dict[str, str]) -> dict:
    n = len(epochs)
    strata: dict[str, list[Epoch]] = {}
    for e in epochs:
        strata.setdefault(stratum_of(e, n), []).append(e)

    sizes = group_sizes(n)
    cells, worst = {}, 0.0
    for s, members in sorted(strata.items()):
        row = {}
        for g in GROUPS:
            got = sum(1 for e in members if mapping[e.date] == g)
            ideal = sizes[g] * len(members) / n
            row[g] = {"n": got, "ideal": round(ideal, 4),
                      "dev": round(got - ideal, 4)}
            worst = max(worst, abs(got - ideal))
        cells[s] = row

    return {
        "grupos": {g: sum(1 for v in mapping.values() if v == g)
                   for g in GROUPS},
        "grupos_esperados": sizes,
        "celulas": cells,
        "desvio_maximo": round(worst, 4),
        "tolerancia": 1.0,
        "dentro_da_tolerancia": worst < 1.0,
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_assign(a) -> None:
    if a.seed and a.round:
        raise SystemExit("give --seed or --round, not both")
    if a.round:
        rhex = fetch_randomness_hex(a.round, a.chain)
        seed = seed_from_randomness_hex(rhex)
    elif a.seed:
        rhex, seed = None, a.seed.strip().lower()
        if len(seed) != 64:
            raise SystemExit("--seed must be 64 hex characters")
    else:
        raise SystemExit("need --seed or --round")

    epochs = build_epochs(a.start, a.epochs)
    mapping = assign(epochs, seed)
    bal = balance(epochs, mapping)
    if not bal["dentro_da_tolerancia"]:
        raise SystemExit(
            f"tolerance violated (max dev {bal['desvio_maximo']}) -- "
            "this should be impossible by construction; do not publish."
        )

    doc = {
        "esquema": "stratified block randomization; strata = calendar-half x "
                   "weekday/weekend; largest-remainder apportionment; seeded "
                   "Fisher-Yates within stratum",
        "chain": a.chain,
        "round": a.round,
        "randomness_hex": rhex,
        "seed": seed,
        "regra_da_semente": "seed = SHA256(ascii(randomness_hex))",
        "start": a.start,
        "n_epochs": a.epochs,
        "grupos": list(GROUPS),
        "doses": list(DOSES),
        "atribuicao": mapping,
        "balanceamento": bal,
        "script_sha256": _self_sha256(),
    }
    _emit(doc, a.out)


def cmd_verify(a) -> None:
    doc = json.load(open(a.assignment))
    epochs = build_epochs(doc["start"], doc["n_epochs"])

    problems = []
    if doc.get("randomness_hex"):
        want = seed_from_randomness_hex(doc["randomness_hex"])
        if want != doc["seed"]:
            problems.append(f"seed mismatch: derived {want}, file {doc['seed']}")

    redone = assign(epochs, doc["seed"])
    if redone != doc["atribuicao"]:
        diff = [d for d in redone if redone[d] != doc["atribuicao"].get(d)]
        problems.append(f"assignment mismatch on {len(diff)} epochs: {diff[:5]}")

    bal = balance(epochs, doc["atribuicao"])
    if not bal["dentro_da_tolerancia"]:
        problems.append(f"tolerance violated: max dev {bal['desvio_maximo']}")

    if doc.get("script_sha256") and doc["script_sha256"] != _self_sha256():
        problems.append(
            "script hash differs from the one recorded in the assignment -- "
            "the file that produced it is not this file"
        )

    print(json.dumps({
        "ok": not problems,
        "problemas": problems,
        "balanceamento": bal,
    }, indent=1, ensure_ascii=False))
    sys.exit(1 if problems else 0)


def cmd_permute(a) -> None:
    """Re-randomizations under the SAME scheme, for the Sec. 5 sharp null.

    Draw `i` uses seed SHA256(assignment_seed || "|perm|" || i), so the whole
    permutation set is reproducible from the published assignment alone.
    """
    doc = json.load(open(a.assignment))
    epochs = build_epochs(doc["start"], doc["n_epochs"])
    base = doc["seed"]

    rows = []
    for i in range(a.n):
        s = hashlib.sha256(
            bytes.fromhex(base) + b"|perm|" + str(i).encode("ascii")
        ).hexdigest()
        rows.append(assign(epochs, s))

    if a.out:
        with open(a.out, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")
        print(f"{len(rows)} permutations -> {a.out}")
    else:
        distinct = len({json.dumps(r, sort_keys=True) for r in rows})
        identical = sum(1 for r in rows if r == doc["atribuicao"])
        print(json.dumps({
            "n": len(rows),
            "distintas": distinct,
            "iguais_a_observada": identical,
        }, indent=1))


def _self_sha256() -> str:
    return hashlib.sha256(open(__file__, "rb").read()).hexdigest()


def _emit(doc: dict, out: str | None) -> None:
    text = json.dumps(doc, indent=1, ensure_ascii=False)
    if out:
        open(out, "w").write(text + "\n")
        print(f"-> {out}")
        print(json.dumps(doc["balanceamento"], indent=1, ensure_ascii=False))
    else:
        print(text)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("assign", help="produce the assignment sequence")
    a.add_argument("--seed", help="64-hex seed (offline / testing)")
    a.add_argument("--round", type=int, help="drand round R")
    a.add_argument("--chain", default=DRAND_CHAIN)
    a.add_argument("--start", required=True, help="first epoch date, YYYY-MM-DD")
    a.add_argument("--epochs", type=int, default=N_EPOCHS)
    a.add_argument("--out")
    a.set_defaults(func=cmd_assign)

    v = sub.add_parser("verify", help="recompute and check a published sequence")
    v.add_argument("--assignment", required=True)
    v.set_defaults(func=cmd_verify)

    m = sub.add_parser("permute", help="permutation draws under the same scheme")
    m.add_argument("--assignment", required=True)
    m.add_argument("--n", type=int, default=10000)
    m.add_argument("--out")
    m.set_defaults(func=cmd_permute)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
