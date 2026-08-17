#!/usr/bin/env python3
"""claims_check.py — recompute every band-dependent claim and fail on divergence.

WHY THIS EXISTS
---------------
On 2026-08-17, one day after the pre-registration was deposited to Zenodo as an
immutable record, planning the implementation found a defect that five
adversarial reviewers and several mechanical censuses had walked past:

    PREREG-DRAFT.md:306 — "No locked dose reaches the main slots — the best case
    falls 0.0214 short. The entire treatment acts through the 2 coverage slots,
    never the 8 primary ones."

The `0.0214` was exact — for `w = 2.0`, S4, age 0: the top of the band as it
stood on 2026-07-29. The band was widened to `{2.0, 4.0, 7.5}` on 2026-08-16,
with the change itself documented carefully. The sentence derived from it was
not recomputed. Under the current band the best case *exceeds* the main cut by
0.2151.

A prose sentence stating a computed result is a CACHE WITH NO INVALIDATION.
Nothing links it to the parameter it depends on. A reviewer — human or model —
reads the sentence and checks whether it is COHERENT, not whether it is still
TRUE, and it was coherent, well written, and had been correct when written. A
mechanical census does not catch it either: `0.0214` is not a retired value that
survived, it is a value CORRECTLY COMPUTED under premises that changed.

So the fix cannot be discipline. It has to be a script.

WHAT IT DOES
------------
Two passes, and the second is the one that earns its keep.

1. RECOMPUTE. Every quantity the registration states about reach — `w_min` per
   severity and age, the age cliffs per dose, the excess over the main cut, the
   reachable shares — is derived here from the frozen constants alone. Change a
   constant, and the expected values change with it.

2. SWEEP. Walk every deposited document for the literal numbers and the phrase
   patterns that depend on the band, and require each occurrence to be either
   (a) consistent with pass 1, or (b) listed in KNOWN_STALE below as a dated
   record deliberately preserved. Anything else fails.

Pass 2 is what makes a NEW stale claim impossible rather than improbable. A
document that acquires `0.0214` tomorrow, in a context nobody registered as
historical, stops the check.

WHAT IT DOES NOT DO — stated because overclaiming here would be the same defect
this file exists to catch. The allowlist is per FILE, not per occurrence. A new
stale claim written into `PREREG-DRAFT.md` itself — the document most likely to
acquire one, since every correction note there quotes the text it corrects —
passes the sweep untouched. Narrowing the allowlist to line ranges was
considered and rejected: line numbers move with every edit, so the guard would
fail open on exactly the edits it is meant to police. Pass 1 still covers those
files, because it recomputes from the constants rather than reading the prose.
The residual exposure is therefore: a NEW prose claim, in an allowlisted file,
that is not one of the thirteen quantities pass 1 recomputes. Adding a claim to
`claims()` is the way to close that for any specific sentence worth the line.

USAGE
    python3 claims_check.py            # check, exit 1 on any failure
    python3 claims_check.py --show     # print the recomputed table and exit 0

No dependencies: standard library only, like every other canonical script here.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen constants. These are THE inputs; everything below is derived.
# Each carries the date it was locked and the document that locks it.
# ---------------------------------------------------------------------------

DELTA_CUT = 0.043  # LOCKED 2026-07-29 — PREREG-DRAFT.md §2
CUT_FRESH = 0.7342  # LOCKED 2026-08-17 — the coverage-slot cut
CUT_MAIN = 0.8524  # the 8 primary slots; boost does not reach here by design
BAND = (2.0, 4.0, 7.5)  # LOCKED 2026-08-16, replacing {0.5, 1.0, 2.0}

# Salience v2, additive: 0.55*importance + 0.15*recency + 0.10*pain + 0.20*access
W_IMPORTANCE, W_RECENCY, W_PAIN, W_ACCESS = 0.55, 0.15, 0.10, 0.20
IMPORTANCE_LESSON = 0.90  # IMPORTANCE_BY_TYPE['lesson']
RETENTION_LESSON = 180  # days; recency = 2^(-age/retention)

SEVERITY = {"S1": 0.25, "S2": 0.50, "S3": 0.75, "S4": 1.00}
SEVERITY_SHARE = {"S1": 0.6973, "S2": 0.2962, "S3": 0.0058, "S4": 0.0008}

# A written chunk is born with access_count = 0, so the access term contributes
# nothing; pain carries the severity. This is the `base` the registration uses.
BASE_CONST = W_IMPORTANCE * IMPORTANCE_LESSON  # 0.495


def base(sev: float, age_days: float) -> float:
    """Unboosted salience of a freshly written lesson chunk of the given severity."""
    return BASE_CONST + W_RECENCY * 2 ** (-age_days / RETENTION_LESSON) + W_PAIN * sev


def w_min(sev: float, age_days: float, cut: float = CUT_FRESH) -> float:
    """The dose multiplier that lifts such a chunk to `cut`. Independent of the band."""
    return (cut - base(sev, age_days)) / (DELTA_CUT * sev)


def max_age(sev: float, w: float, cut: float = CUT_FRESH) -> float | None:
    """Oldest age at which dose `w` still clears `cut`.

    None    -> never clears it, at any age (the boost is too small outright)
    math.inf -> clears it at every age (already above the cut before decay matters)
    """
    residual = cut - BASE_CONST - W_PAIN * sev - DELTA_CUT * w * sev
    if residual <= 0:
        return math.inf
    if residual > W_RECENCY:
        return None
    return -RETENTION_LESSON * math.log2(residual / W_RECENCY)


# ---------------------------------------------------------------------------
# The claims. Each is (label, computed value, tolerance) and each is asserted
# against the number the deposited documents actually print.
# ---------------------------------------------------------------------------


def claims() -> list[tuple[str, float, float, float]]:
    """(label, computed, published, tolerance)."""
    out: list[tuple[str, float, float, float]] = []
    a = out.append

    a(("w_min S1 @ age 0", w_min(0.25, 0), 5.97, 0.005))
    a(("w_min S1 @ 24 h", w_min(0.25, 1), 6.03, 0.005))
    a(("w_min S1 @ 30 d", w_min(0.25, 30), 7.49, 0.005))
    a(("w_min S2 @ age 0", w_min(0.50, 0), 1.82, 0.005))
    a(("w_min S2 @ 24 h", w_min(0.50, 1), 1.85, 0.005))
    a(("w_min S3 @ age 0", w_min(0.75, 0), 0.44, 0.005))

    a(("S2 age cliff at w = 2.0", max_age(0.50, 2.0), 6.66, 0.005))
    a(("S2 window at w = 4.0", max_age(0.50, 4.0), 97.11, 0.01))
    a(("S1 window at w = 7.5", max_age(0.25, 7.5), 30.12, 0.01))
    a(("S2 main-cut window at w = 7.5", max_age(0.50, 7.5, CUT_MAIN), 6.75, 0.01))

    # The claim that went stale, in both its forms.
    old_band_top = 2.0
    a((
        "old band shortfall at main cut (w = 2.0, S4)",
        CUT_MAIN - (base(1.0, 0) + DELTA_CUT * old_band_top * 1.0),
        0.0214,
        0.0001,
    ))
    a((
        "current band excess at main cut (w = 7.5, S4)",
        (base(1.0, 0) + DELTA_CUT * BAND[-1] * 1.0) - CUT_MAIN,
        0.2151,
        0.0001,
    ))

    # The margin that is too thin to be a design property, and is registered as such.
    a(("S1 margin at 30 d (7.5 - w_min)", BAND[-1] - w_min(0.25, 30), 0.0056, 0.0005))
    return out


# ---------------------------------------------------------------------------
# Pass 2: the sweep.
#
# Each entry is (regex, human-readable reason it is band-dependent). Any match
# outside KNOWN_STALE is a failure — the point is that a NEW occurrence, in a
# document nobody has marked as historical, stops the check.
# ---------------------------------------------------------------------------

BAND_DEPENDENT = [
    (r"0\.0214", "the old band's shortfall at the main cut"),
    (r"three times the top", "false: 6.0 is below the current top of 7.5"),
    (r"out of reach at every locked dose", "false at w = 7.5"),
    (r"no locked dose reaches the main slots", "false at w = 7.5"),
    (r"\{0\.5[ ,;·]+1\.0[ ,;·]+2\.0\}", "the superseded band written as a set"),
]

# Deliberately preserved occurrences: dated records, and the correction notes
# that quote the superseded text in order to correct it. Keyed by filename; a
# match in any OTHER file fails regardless of what it says.
KNOWN_STALE = {
    # The correction itself has to quote what it corrects.
    "PREREG-DRAFT.md": "carries the corrections; quoting the stale text is the point",
    "DEPOSIT-README.md": "same, on the deposit's front page",
    # Dated measurements, superseded-header'd rather than rewritten.
    "LINK-FEASIBILITY-2026-08-15.md": "2026-08-15 measurement, header marks it",
    "REACHABILITY-2026-08-16.md": "narrates the reviews that motivated the widening",
    "dose_reach.mjs": "must keep reproducing DOSE-REACH-2026-08-15.json byte for byte",
    "link_feasibility.mjs": "same",
    "DOSE-REACH-2026-08-15.json": "the output itself",
    "DISPLACEMENT-2026-08-16.txt": "raw output of the candidate-band run",
    "claims_check.py": "this file names the patterns in order to search for them",
}

SCAN_SUFFIXES = {".md", ".py", ".mjs", ".json", ".txt", ".jsonl"}


def sweep(root: Path) -> list[str]:
    failures = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if path.name in KNOWN_STALE:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern, reason in BAND_DEPENDENT:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                line = text.count("\n", 0, m.start()) + 1
                failures.append(
                    f"{path.name}:{line}: band-dependent claim outside the "
                    f"allowlist — {reason!r} (matched {m.group(0)!r})"
                )
    return failures


def show() -> None:
    print(f"band            w in {{{', '.join(str(w) for w in BAND)}}}")
    print(f"Delta_cut       {DELTA_CUT}")
    print(f"CUT_FRESH       {CUT_FRESH}   CUT_MAIN  {CUT_MAIN}")
    print()
    print("w_min against the coverage cut (independent of the band):")
    print(f"  {'sev':4}  {'age 0':>8}  {'24 h':>8}  {'30 d':>8}")
    for name, sev in SEVERITY.items():
        print(
            f"  {name:4}  {w_min(sev, 0):8.4f}  {w_min(sev, 1):8.4f}  {w_min(sev, 30):8.4f}"
        )
    print()
    for cut, label in ((CUT_FRESH, "coverage slots"), (CUT_MAIN, "primary slots")):
        print(f"oldest age still reached, {label} (cut {cut}):")
        for w in BAND:
            cells = []
            for name, sev in SEVERITY.items():
                age = max_age(sev, w, cut)
                if age is None:
                    cells.append(f"{name}=never")
                elif age == math.inf:
                    cells.append(f"{name}=always")
                else:
                    cells.append(f"{name}={age:.2f}d")
            print(f"  w={w:<4} " + "  ".join(cells))
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--show", action="store_true", help="print the recomputed table")
    ap.add_argument("--root", default=str(Path(__file__).parent))
    args = ap.parse_args()

    if args.show:
        show()
        return 0

    failures: list[str] = []

    for label, computed, published, tol in claims():
        if computed is None or computed == math.inf:
            failures.append(f"{label}: computed {computed}, expected a finite {published}")
        elif abs(computed - published) > tol:
            failures.append(
                f"{label}: computed {computed:.6f}, document says {published} "
                f"(tolerance {tol})"
            )

    failures.extend(sweep(Path(args.root)))

    if failures:
        print(f"FAIL — {len(failures)} divergence(s):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1

    n = len(claims())
    print(f"ok — {n} band-dependent claims recomputed and matched; sweep clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
