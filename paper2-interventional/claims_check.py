#!/usr/bin/env python3
"""claims_check.py — recompute every band-dependent claim and fail on divergence.

WHY THIS EXISTS
---------------
On 2026-08-17, roughly two hours after the pre-registration was deposited to
Zenodo as an immutable record, planning the implementation found a defect that
five adversarial reviewers and several mechanical censuses had walked past:

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
Three passes. The first is arithmetic, the second and third are the ones that
earn their keep.

1. RECOMPUTE (`claims`). Every quantity the registration DERIVES about reach --
   `w_min` per severity and age, the age cliffs per dose, the excess over the
   main cut -- is recomputed here from the frozen constants alone and compared
   against a literal typed in this file. Change a constant and the comparison
   breaks. It does NOT read the documents; see the note above `claims()`.

2. SWEEP (`sweep`). Walk every file in the package, recursively, for the literal
   numbers AND the phrase patterns that depend on the band, in both languages
   the package is written in. An occurrence is allowed only in a file that is
   both named in KNOWN_STALE and carries a correction marker -- the name alone
   is not enough, because two different files here are called `README.md`.

3. CROSS-CHECK (`cross_check`, `doc_check`). Parse the band declaration out of
   the other scripts and compare it to BAND, because a stale literal is not a
   stale string and no regex distinguishes a superseded tuple quoted in a
   correction comment from a live one. Then read the MEASURED reach figures out
   of the JSON artifact and require the prose to still state them, so a
   measurement cannot be dropped instead of updated.

Pass 2 is what makes a NEW stale claim impossible rather than improbable. A
document that acquires `0.0214` tomorrow, in a context nobody registered as
historical, stops the check.

WHAT IT DOES NOT DO -- stated because overclaiming here would be the same defect
this file exists to catch, and because an earlier version of this section DID
overclaim, in two ways that an external review found before I did.

The allowlist is per FILE, not per occurrence. A new stale claim written into
`PREREG-DRAFT.md` itself -- the document most likely to acquire one, since every
correction note there quotes the text it corrects -- passes the sweep, provided
it is not one of the quantities pass 1 or 3 covers. Narrowing the allowlist to
line ranges was considered and rejected: line numbers move with every edit, so
the guard would fail open on exactly the edits it is meant to police. Requiring
a correction marker in the file is the weaker but stable substitute.

The phrase list is a LIST. It catches the four claims that went stale on
2026-08-16 and their translations; it does not catch a fifth way of saying the
same thing that nobody has written yet. Every pattern here was added after a
defect, not before one. Read the "ok" as "none of the known failure shapes are
present", never as "the package is consistent".

USAGE
    python3 claims_check.py            # check, exit 1 on any failure
    python3 claims_check.py --show     # print the recomputed table and exit 0

No dependencies: standard library only, like every other canonical script here.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import hashlib
import subprocess
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
# The claims.
#
# ⚠️ WHAT THIS COMPARES, precisely — an earlier version of this comment said each
# claim is "asserted against the number the deposited documents actually print",
# which was false and is the exact defect this file exists to catch, committed
# inside the file itself. `claims()` compares a value RECOMPUTED from the frozen
# constants against a literal TYPED HERE. If a document silently changed the
# number it prints, this pass would not notice; what it notices is a constant
# changing underneath a number that was once right. `doc_check()` below closes
# the other half for the measured quantities, by reading them out of the JSON
# artifacts and grepping the documents for disagreement.
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
    # Added 2026-08-17 after `reachable_share.py` was found defaulting to the old
    # band under the comment "the locked band". An earlier review called excluding
    # the tuple form defensible, on the grounds that the sweep targets prose; the
    # script that produces the reach numbers is exactly where it was not.
    (r"\(0\.5,\s*1\.0,\s*2\.0\)", "the superseded band written as a tuple"),
    # These were among the four original stale claims and the first version of
    # this sweep did not look for any of them. That is how the OSF abstract and
    # the repository README kept theirs: the numeric patterns above do not appear
    # in a sentence that says "about 30% of failures" in words.
    #
    # ⚠️ BILINGUAL, and this was not an afterthought — it was a hole. The package
    # is written in two languages: the registration and the deposited documents
    # in English, and the working documents that route the project in Portuguese,
    # including `OSF-SUBMISSION.md`, whose abstract becomes the permanent public
    # OSF registration. The first version of these three patterns was
    # English-only, so the sweep was structurally blind to the half of the corpus
    # where two of the surviving stale claims actually lived. A positive-control
    # run caught it: a synthetic "~30% dos failures" passed cleanly.
    (r"(?:about|~|approximately|cerca de|aproximadamente|em torno de)\s*30\s*%\s*(?:of|dos|das|de)\s+(?:the\s+|os\s+|as\s+)?(?:failures|falhas)",
     "reach is 30% only at w = 2.0; 100% at w = 7.5"),
    (r"(?:only\s+at\s+severity|apenas\s+(?:a\s+)?severidade|s[oó]\s+(?:a\s+)?severidade)\s*S2\s+(?:and above|e acima|ou acima|para cima)",
     "true at w = 2.0 only; S1 is reachable at w = 7.5"),
    (r"S1[^.\n]{0,40}(?:never|nunca)[^.\n]{0,40}(?:locked dose|dose travada)",
     "S1 needs w = 5.97 and the band's top is 7.5"),
]

# Deliberately preserved occurrences: dated records, and the correction notes
# that quote the superseded text in order to correct it. Keyed by filename; a
# match in any OTHER file fails regardless of what it says.
KNOWN_STALE = {
    # The correction itself has to quote what it corrects.
    "PREREG-DRAFT.md": "carries the corrections; quoting the stale text is the point",
    "DEPOSIT-README.md": "same, on the deposit's front page",
    # The same file, under the name it carries INSIDE the deposit. Both keys are
    # needed and the omission was caught by this check on its first real run:
    # the deposit renames DEPOSIT-README.md to README.md, so an allowlist keyed
    # on the repository name fails open in the repository and closed in the
    # deposit — the direction that at least announces itself, but still wrong.
    # ⚠️ Keyed by name, and two DIFFERENT files are called README.md: the
    # deposit's front page (DEPOSIT-README.md renamed) and the repository's own
    # navigation index. Exempting the name exempted both, and the repository
    # README was carrying a stale "~30% of failures" that the sweep therefore
    # never reported. The exemption now requires the file to CARRY a correction
    # marker, so a file that merely shares the name is still swept.
    "README.md": "DEPOSIT-README.md under its in-deposit name",
    # Dated measurements, superseded-header'd rather than rewritten.
    "LINK-FEASIBILITY-2026-08-15.md": "2026-08-15 measurement, header marks it",
    "REACHABILITY-2026-08-16.md": "narrates the reviews that motivated the widening",
    "dose_reach.mjs": "must keep reproducing DOSE-REACH-2026-08-15.json byte for byte",
    "link_feasibility.mjs": "same",
    "DOSE-REACH-2026-08-15.json": "the output itself",
    "DISPLACEMENT-2026-08-16.txt": "raw output of the candidate-band run",
    "claims_check.py": "this file names the patterns in order to search for them",
    # Allowlisted for the REGEX only, and only because `cross_check` below reads
    # its band declaration structurally and compares it to BAND. That is the
    # right layering: the file quotes the superseded tuple inside a correction
    # comment, which no regex can distinguish from a live one, while the thing
    # that actually matters — what the script will USE — is checked by parsing
    # rather than by matching. Removing cross_check would silently downgrade this
    # entry from "checked a better way" to "not checked".
    "reachable_share.py": "correction comment quotes the old tuple; cross_check covers the real value",
}

SCAN_SUFFIXES = {".md", ".py", ".mjs", ".json", ".txt", ".jsonl"}

# An allowlist entry only takes effect if the file actually says, somewhere, that
# it is preserving superseded text on purpose. Without this, exempting a NAME
# exempts every file that happens to carry it.
MARKERS = ("SUPERSEDED", "CORRECTED", "superseded", "corrected 2026", "the old band",
           "band then in force", "LOCKED when this ran", "locked when this ran")


def _is_marked(path: Path) -> bool:
    try:
        return any(m in path.read_text(encoding="utf-8") for m in MARKERS)
    except (UnicodeDecodeError, OSError):
        return True  # binary or unreadable: nothing to sweep anyway


def sweep(root: Path) -> list[str]:
    failures = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if "__pycache__" in path.parts or ".git" in path.parts:
            continue
        if path.name in KNOWN_STALE and _is_marked(path):
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


def doc_check(root: Path) -> list[str]:
    """Check the MEASURED quantities against the artifact, not against a literal.

    `claims()` recomputes from constants, which covers the arithmetic but not the
    measurements: the reachable shares come out of a run over the corpus and
    cannot be derived from `DELTA_CUT` and friends. Those numbers travel through
    the documents as typed percentages, so they can drift from the JSON that
    produced them exactly the way the prose drifted from the band.

    So: read them out of `REACHABILITY-TOP1-2026-08-16.json`, and require that
    each still appears somewhere in the prose. A number that vanishes is as much
    a defect as a number that changes -- it means a document was rewritten and
    the measurement it rested on was dropped rather than updated.
    """
    failures = []
    art = root / "REACHABILITY-TOP1-2026-08-16.json"
    if not art.exists():
        return [f"{art.name}: missing — the measured reach figures cannot be checked"]
    data = json.loads(art.read_text(encoding="utf-8"))

    corpus = {
        p.name: p.read_text(encoding="utf-8", errors="ignore")
        for p in root.rglob("*.md")
        if "__pycache__" not in p.parts
    }

    for key, label in (
        ("fracao_alcancavel_por_dose", "reachable share"),
        ("teto_de_efeito_incondicional_por_dose", "unconditional ceiling"),
    ):
        for dose, frac in sorted(data[key].items()):
            if float(dose) not in BAND:
                continue
            pct = f"{frac * 100:.2f}"
            if not any(pct in text for text in corpus.values()):
                failures.append(
                    f"{art.name}: {label} at w = {dose} is {pct}%, and no document "
                    f"in the package states it — dropped rather than updated?"
                )
    return failures


def cross_check(root: Path) -> list[str]:
    """Assert that the OTHER scripts agree with the band declared here.

    A regex sweep catches a stale value written as text. It does not catch a
    stale value that is simply a different literal — `reachable_share.py` held
    `DOSES = (0.5, 1.0, 2.0)` for a day after the band moved, and would have gone
    on holding `(1.0, 3.0, 5.0)` just as quietly. This reads the declaration out
    of each script that carries one and compares it to BAND.
    """
    failures = []
    targets = {
        "reachable_share.py": r"^DOSES\s*=\s*\(([^)]*)\)",
    }
    for name, pattern in targets.items():
        path = root / name
        if not path.exists():
            failures.append(f"{name}: expected to be present and carry a band declaration")
            continue
        m = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
        if not m:
            failures.append(f"{name}: no band declaration found — did it move or get renamed?")
            continue
        declared = tuple(float(x) for x in m.group(1).split(",") if x.strip())
        if declared != BAND:
            failures.append(
                f"{name}: declares the band as {declared}, this file locks {BAND}"
            )
    return failures


# --- sizing, locked 2026-08-17 (amendment v1.11) ---------------------------
# These are not band-dependent, so they are checked by a separate pass. They are
# here because the defect that produced them is the same one this file exists to
# catch: `N` = 174 was a computed result quoted in prose across the package, and
# it stayed quoted after the formula that produced it was found to be wrong.
SIZING_INPUTS = dict(
    r_hat=29.838403, p0_hat=0.111813, icc=0.18141, mde=0.30,
    hours_per_epoch=5.1867, session_hours_per_epoch=50.4667, cv2=0.3833,
)
N_EPOCHS_LOCKED = 234
DESIGN_EFFECT_LOCKED = 13.482928
CV2_LOCKED = 0.3833
ALLOCATION_LOCKED = {"control": 117, "w2": 39, "w4": 39, "w7.5": 39}


def sizing_check(root: Path) -> list[str]:
    """Re-run `sizing.py` and `assign_arms.py` and assert the locked outputs.

    This is a RUN, not a regex: the point of the 2026-08-17 amendment is that a
    formula was wrong while every number derived from it reproduced perfectly.
    Only executing the current code can catch the next instance of that.

    Limit, stated because it is real: this asserts that the deposited scripts
    still produce the locked values. It does NOT assert that the formula inside
    them is the right one for the design — that is a question about applicability,
    which no self-check can answer, and which is exactly how the 174 survived
    eleven versions and five adversarial voices.
    """
    failures = []
    sizing = root / "sizing.py"
    if not sizing.exists():
        return [f"sizing.py not found under {root}"]

    argv = [sys.executable, str(sizing)]
    for key, val in SIZING_INPUTS.items():
        argv += [f"--{key.replace('_', '-')}", str(val)]
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        return [f"sizing.py exited {proc.returncode}: {proc.stderr.strip()[:200]}"]
    out = json.loads(proc.stdout)

    got_n = out["N_epochs_total"]
    if got_n != N_EPOCHS_LOCKED:
        failures.append(f"N_epochs: sizing.py returns {got_n}, this file locks {N_EPOCHS_LOCKED}")
    got_de = out["intermediarios"]["design_effect"]
    if abs(got_de - DESIGN_EFFECT_LOCKED) > 1e-6:
        failures.append(f"design effect: sizing.py returns {got_de}, locked {DESIGN_EFFECT_LOCKED}")
    got_cv2 = out["inputs"].get("cv2")
    if got_cv2 != CV2_LOCKED:
        failures.append(f"cv2: sizing.py echoes {got_cv2}, locked {CV2_LOCKED}")

    # The equal-cluster formula is the defect itself; assert it is gone by
    # checking that cv2 actually changes the answer. If a future edit dropped the
    # term, every number above would still reproduce at cv2=0 and the check would
    # pass while the design effect was wrong again.
    argv_zero = [a for a in argv]
    argv_zero[argv_zero.index("--cv2") + 1] = "0.0"
    zero = json.loads(subprocess.run(argv_zero, capture_output=True, text=True).stdout)
    if zero["intermediarios"]["design_effect"] >= got_de:
        failures.append(
            "design effect does not increase with cv2 — the unequal-cluster term "
            "is not being applied, which is the 2026-08-17 defect returning"
        )

    assign = root / "assign_arms.py"
    if not assign.exists():
        failures.append(f"assign_arms.py not found under {root}")
        return failures
    src = assign.read_text(encoding="utf-8")
    m = re.search(r"^N_EPOCHS\s*=\s*(\d+)", src, re.MULTILINE)
    if not m:
        failures.append("assign_arms.py: no N_EPOCHS declaration found")
    elif int(m.group(1)) != N_EPOCHS_LOCKED:
        failures.append(
            f"assign_arms.py declares N_EPOCHS = {m.group(1)}, sizing locks {N_EPOCHS_LOCKED}"
        )
    else:
        seed = hashlib.sha256(b"claims_check").hexdigest()
        proc = subprocess.run(
            [sys.executable, str(assign), "assign", "--seed", seed, "--start", "2026-09-01"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            failures.append(f"assign_arms.py exited {proc.returncode}")
        else:
            bal = json.loads(proc.stdout)["balanceamento"]
            if bal["grupos"] != ALLOCATION_LOCKED:
                failures.append(
                    f"allocation: assign_arms.py gives {bal['grupos']}, locked {ALLOCATION_LOCKED}"
                )
            if not bal["dentro_da_tolerancia"]:
                failures.append("assign_arms.py: balance outside the registered tolerance")
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
    failures += sizing_check(Path(args.root))

    for label, computed, published, tol in claims():
        if computed is None or computed == math.inf:
            failures.append(f"{label}: computed {computed}, expected a finite {published}")
        elif abs(computed - published) > tol:
            failures.append(
                f"{label}: computed {computed:.6f}, document says {published} "
                f"(tolerance {tol})"
            )

    failures.extend(sweep(Path(args.root)))
    failures.extend(cross_check(Path(args.root)))
    failures.extend(doc_check(Path(args.root)))

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
