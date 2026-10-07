#!/usr/bin/env python3
"""Parity check B-v2-rc14.md -> B-v2-rc15.md (Paper B, sprint 2026-10-04; rc15 2026-10-05).

rc15 applies the review of rc14 (`REVIEW-B-rc14-2026-10-05.md`: Codex C1-C6, Fable F1-F2), each
finding verified before it was applied (`APPLY-B-rc15.md`). C1 changes the analysis: the BCa
acceleration is computed arm by arm (v4, `out/ITT-REGISTRADO-v4-2026-10-05.json`), so every
reported BCa interval moves; the rest is text.

Checks (exit 1 if any fails):
  1. hunks: every hunk carries an ID. A hunk whose rc14 text, with the v4 substitutions applied,
     equals its rc15 text gets ID V4 automatically; any other hunk needs an anchor (ANCHORS).
  2. intervals traced to v4: SUBS, every (v3 string -> v4 string) pair the text can carry, is
     FORMATTED AT RUN TIME from the artifacts (v3/v4 JSON, checks-rc10/checks-rc15), never typed
     here; a space in a pair also matches a line break. SUBS is applied to the rc14 body (struck
     text masked); against the rc15 body, every numeric token REMOVED beyond that must be listed in
     JUSTIFIED_REMOVED with its exact count and edit, and every token ADDED must be in rc14, a leaf
     of an artifact read here, or derived (1 − 0.99^150; the v4 H2 bounds of rc9's analysis).
     After the substitution no v3 string may remain in the unstruck rc15 body outside the
     HISTORY contexts (text that records what an earlier version printed).
  3. invariants rc14 -> rc15 multiset-equal except declared deltas: § cross-references, code
     spans, italic quotations, citations, footnotes, DOIs, struck spans, image links (one image
     path, declared). Headings identical.
  4. working list and changelog: rc15's, with the declared insertions removed, is byte-identical
     to rc14's; the rc14 and rc15 changelog blocks are present and numbered 149 and 150-155.
  5. SHAM-JANELA: 10 blocks byte-identical to rc14.
  6. carried locks: `claims_rc13` (rc11 (a)-(f), rc12 (g)-(h), rc13 (i)-(l)) clean on rc15;
     NEW (m) the sweep classes of the review: no direction-of-error claim about the omitted
     uncertainty, no "instrument change", no categorical Monte-Carlo-noise claim, no "is rounded"
     header time, no "this failure is not that case", no "would not return all of its labels",
     no bootstrap that "resamples the first" (the assignment); (n) the status header names rc14
     and rc15; (o) C1's construction sentence, C2's independence condition, C3's two
     sentences, C4's sentence and F1's sentences present.
  7. qualifier set: (a) every LOCKED phrase of rc14 (its 38 qualifiers, 4 census marks and the
     headlines of rc11-rc13 recomputed with rc14's artifacts: 102 distinct) occurs in rc15 as
     many times as in rc14, except (i) headlines whose artifact value is a BCa interval, which
     must be replaced one for one by the same headline formatted from v4, and (ii) the deltas in
     JUSTIFIED_PHRASE, each tied to a reviewed finding; (b) hedge words (rc14's HEDGE) unchanged
     except JUSTIFIED_HEDGE.
  8. integrity: carried rc11 script integrity (on the frozen v3 script, which is what rc11 pinned),
     rc12 census record, rc13 B-censo paths (RESULTADO-v3.md read with the rc15 correction
     reverted, which must give rc13's file); NEW v4: the running script equals its frozen copy
     and the v4 provenance; v4 carries the arm-stratified construction and its v1/v2/v3 controls
     are identical; the acceleration test passed; checks-rc15 and the rc15 Figure B1 pin v4; v1,
     v2, v3 and checks-rc10 unchanged; every sha8 the manuscript cites for v4 is the file's.
  9. no REANALISE marker; bold balanced per paragraph.

Usage:  python3 parity-rc15.py | --report | --self-test     Reads; writes nothing.
"""
import collections
import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
OLD = SPRINT / "B-v2-rc14.md"
NEW = SPRINT / "B-v2-rc15.md"
RC14 = SPRINT / "B-rc14" / "parity-rc14.py"
RC14_SHA = "04e2dc01e536681298ea99bbceee0482d68cbea8bac89b3805a3fbe734ce43cd"

assert hashlib.sha256(RC14.read_bytes()).hexdigest() == RC14_SHA, \
    "parity-rc14.py changed: the locks carried from it are no longer the ones rc14 ran"
_spec = importlib.util.spec_from_file_location("parity_rc14", RC14)
R14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R14)
R13, R12, R11 = R14.R13, R14.R12, R14.R11

REG = SPRINT / "B-registered"
SCRIPT = P2 / "measurement" / "estimador_itt_registrado.py"
FROZEN_V3 = REG / "estimador_itt_registrado-v3-0aa9202b.py"
# rc11's checks read sha(R11.SCRIPT); the script rc11 pinned is the v3 one, now frozen
R11.SCRIPT = FROZEN_V3
ART = {
    "v1": P2 / "out" / "ITT-REGISTRADO-2026-10-05.json",
    "v2": P2 / "out" / "ITT-REGISTRADO-v2-2026-10-05.json",
    "v3": P2 / "out" / "ITT-REGISTRADO-v3-2026-10-05.json",
    "v4": P2 / "out" / "ITT-REGISTRADO-v4-2026-10-05.json",
    "c10": SPRINT / "B-rc10" / "checks-rc10.json",
    "c15": SPRINT / "B-rc15" / "checks-rc15.json",
    "c15py": SPRINT / "B-rc15" / "checks-rc15.py",
    "teste": REG / "teste-aceleracao-v4.json",
    "testepy": REG / "teste_aceleracao_v4.py",
    "fig4": SPRINT / "figures" / "figB1-h1a-inversao-registrado-v4.run.json",
    "fig4svg": SPRINT / "figures" / "figB1-h1a-inversao-registrado-v4.svg",
    "fig4py": P2 / "measurement" / "sprint-figB-h1a-inversao-registrado-v4.py",
    "res4": REG / "RESULTADO-v4.md",
}
PINNED = {  # sha256 of artifacts rc15 must not have touched
    "v1": None, "v2": None,  # filled from the v1/v2 controls recorded in v4 (their own sha)
    "v3": "41a0a0ee1f0e60716e8bda1c2280d3396a652bbaaa0009cbf71bb020efdd50f9",
    "c10": "b774e61c7c3a20f7af921dc7910f4abc9b66bbbb0586795fd9ef17d90040133a",
}
RESULTADO_RC15_NEW = ("control session. No standalone inferential interval or test is reported for this stratum. The\n"
                      "descriptive per-hour contrasts (6.00 / 321.43 and 139.96 / 321.43 in treatment against 0 / 54.00\n"
                      "in control) are reported in the manuscript (§4); H1c cannot be contrasted because control has no\n"
                      "eligible opportunities. They are listed,")
RESULTADO_RC15_OLD = ("control session: no within-stratum inferential contrast (interval or test) is estimable, and H1c\n"
                      "cannot be contrasted because control has no opportunity; the descriptive per-hour differences\n"
                      "(6.00 / 321.43 and 139.96 / 321.43 in treatment against 0 / 54.00 in control) are given in the\n"
                      "manuscript (§4). They are listed,")
RESULTADO_RC15_NOTE = (" *(Corrected again 2026-10-05, rc15 (review of rc14, Codex C4): it read \"no within-stratum\n"
                       "inferential contrast (interval or test) is estimable\"; an interval or test is not reported, which\n"
                       "is not the same as not estimable. No number changed.)*")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def flat(t):
    return " ".join(t.split())


def body(t):
    return t[:t.find("\n## Working list")]


def tail(t):
    return t[t.find("\n## Working list"):]


def load():
    return {k: json.loads(p.read_text()) for k, p in ART.items() if p.suffix == ".json"}


# ---------------------------------------------------------------- 2: SUBS, formatted from the artifacts
def m(x):
    return x.replace("-", "−")


def f2(x):
    return m(f"{x:+.2f}")


def f3(x):
    return m(f"{x:+.3f}")


def f4(x):
    return m(f"{x:+.4f}")


def fint(x):
    s = f"{abs(round(x)):,}".replace(",", " ")
    return ("−" if x < 0 else "+") + s


def ci(a, f, sep="; "):
    return f"[{f(a[0])}{sep}{f(a[1])}]"


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def subs(A):
    """[(v3 string, v4 string, where)] — only pairs that differ; every string formatted here."""
    v3, v4, c10, c15 = A["v3"], A["v4"], A["c10"], A["c15"]
    out = []

    def add(a, b, where):
        if a != b and (a, b, where) not in out:
            out.append((a, b, where))
    for leg in ("registrado", "sens_registrado_sem_sessoes_atravessadas", "registrado_v2_equivalente",
                "registrado_v1_equivalente"):
        for h in ("H1", "H1a", "H1c"):
            fm = f4 if h == "H1c" else f2
            add(ci(v3["pernas"][leg]["hipoteses"][h]["ic95"], fm), ci(v4["pernas"][leg]["hipoteses"][h]["ic95"], fm),
                f"v3/v4 pernas.{leg}.{h}")
    for leg in ("registrado_precomprometida", "registrado_pos_hoc_sem_0914"):
        for h in ("H1", "H1a", "H1c"):
            fm = f4 if h == "H1c" else f2
            add(ci(c10["A_pernas_registradas"][leg][h]["ic95"], fm), ci(c15["A_pernas_registradas"][leg][h]["ic95"], fm),
                f"checks-rc10/rc15 A.{leg}.{h}")
    for k, row in c15["R_analises_rc8_rc9_em_v4"].items():
        if k == "sha256_checks":
            continue
        for h in ("H1", "H1a", "H1c"):
            fm = f4 if h == "H1c" else f2
            add(ci(row[h]["ic95_v3"], fm), ci(row[h]["ic95_v4"], fm), f"checks-rc15 R.{k}.{h}")
    h2a, h2b = v3["H2"]["registrado"], v4["H2"]["registrado"]
    add(ci(h2a["tempo_s"]["estimador_winsorizado"]["ic95"], f3), ci(h2b["tempo_s"]["estimador_winsorizado"]["ic95"], f3),
        "v3/v4 H2.registrado.tempo_s.winsorizado")
    add(ci(h2a["tempo_s"]["estimador_bruto"]["ic95"], f2), ci(h2b["tempo_s"]["estimador_bruto"]["ic95"], f2),
        "v3/v4 H2.registrado.tempo_s.bruto")
    add(ci(h2a["tokens"]["estimador_winsorizado"]["ic95"], fint), ci(h2b["tokens"]["estimador_winsorizado"]["ic95"], fint),
        "v3/v4 H2.registrado.tokens.winsorizado")
    add(ci(h2a["tokens"]["estimador_bruto"]["ic95"], fint), ci(h2b["tokens"]["estimador_bruto"]["ic95"], fint),
        "v3/v4 H2.registrado.tokens.bruto")
    # BCa adjusted quantiles and the replicate ranks of the upper bounds (checks block A)
    q3, q4 = c10["A_pernas_registradas"]["bca_quantis"], c15["A_pernas_registradas"]["bca_quantis"]
    from decimal import Decimal, ROUND_HALF_UP
    pc = lambda b, h: f"{(Decimal(str(b[h]['alfa_ajustado'][1])) * 100).quantize(Decimal('0.01'), ROUND_HALF_UP)}%"  # noqa: E731
    rk = lambda b, h: ordinal(b[h]["n"] - b[h]["indice_0_based"][1])  # noqa: E731
    add(f"({pc(q3, 'H1')} and {pc(q3, 'H1a')})", f"({pc(q4, 'H1')} and {pc(q4, 'H1a')})", "checks A.bca_quantis (§4)")
    add(f"{pc(q3, 'H1')} / {pc(q3, 'H1a')}", f"{pc(q4, 'H1')} / {pc(q4, 'H1a')}", "checks A.bca_quantis (B.1)")
    add(f"the {rk(q3, 'H1')} and {rk(q3, 'H1a')} largest", f"the {rk(q4, 'H1')} and {rk(q4, 'H1a')} largest",
        "checks A.bca_quantis ranks (B.1)")
    add(f"the {rk(q3, 'H1')} and the {rk(q3, 'H1a')} largest", f"the {rk(q4, 'H1')} and the {rk(q4, 'H1a')} largest",
        "checks A.bca_quantis ranks (§4)")
    add(f"is the {rk(q3, 'H1a')} largest of", f"is the {rk(q4, 'H1a')} largest of", "checks A.bca_quantis rank (§4.2)")
    return out


def mask_struck(t):
    keep = []

    def f(mo):
        keep.append(mo.group(0))
        return f"\x00{len(keep) - 1}\x00"
    return re.sub(r"~~.*?~~", f, t, flags=re.S), keep


def unmask(t, keep):
    return re.sub(r"\x00(\d+)\x00", lambda mo: keep[int(mo.group(1))], t)


def _flex(a):
    """regex for `a` in which every single space also matches a line break (wrapped prose)"""
    return re.compile(r"\s+".join(re.escape(x) for x in a.split(" ")))


def apply_subs(text, S):
    t, keep = mask_struck(text)
    n = {}
    for a, b, w in S:
        pa, pb = a.split(" "), b.split(" ")
        rx = _flex(a)
        cnt = 0

        def f(mo, pb=pb):
            ws = re.findall(r"\s+", mo.group(0))
            if len(ws) != len(pb) - 1:
                return mo.group(0)
            return "".join(x + y for x, y in zip(pb, ws + [""]))
        t, cnt = rx.subn(f, t)
        n[(a, b, w)] = cnt
    return unmask(t, keep), n


# text that records what an earlier version printed: a v3 string may stay here
HISTORY = [
    "the table read time +0.284",          # §5: rc9's printed H2 table
    "from +314.65 to +310.82",             # §4 Uncertainty: the correction names the move
]

# numeric tokens REMOVED beyond SUBS (after the substitution), each with its edit: token -> (count, edit, reason)
JUSTIFIED_REMOVED = {
    "78": (2, "C2", "'about 78% of the time' (§4 and B.1) replaced by the independence statement, 1 − 0.99^150 ≈ 0.779"),
    "0.22": (2, "C2", "'0.99^150 ≈ 0.22' (§4 and B.1) folded into 1 − 0.99^150 ≈ 0.779"),
    "99": (1, "C2", "'the lower bound of the 99/100 measurement' was in the withdrawn 'this failure is not that "
                    "case' sentence; the 99/100 measurement itself is still cited in the sentence before"),
    "100": (1, "C2", "same withdrawn sentence"),
}
# numeric tokens ADDED beyond SUBS must be in rc14, a leaf of an artifact read here, or DERIVED_RC15
def derived_rc15(A):
    cz_p0, n = 0.99, 150
    rules = (SPRINT / "B-censo" / "GATE-RULES-PREDECLARED.md").read_text()
    assert "0.99^150 ≈ 22%" in rules and "agreement ≥ 0.99" in rules, "rules file changed"
    out = {f"{1 - cz_p0 ** n:.3f}": "1 − 0.99^150 (rules file: the criterion and the pair count)"}
    v4 = A["v4"]["H2"]["registrado_v2_equivalente"]["tokens"]
    for e in ("estimador_winsorizado", "estimador_bruto"):
        for x in v4[e]["ic95"]:
            out[str(abs(round(x)))] = f"H2.registrado_v2_equivalente.tokens.{e} (v4), rounded to an integer"
    return out


def num_tok(t):
    return R11.numbers(t)


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc14 prepared 2026-10-05 (a writing pass"),
    ("ST", "2026-10-05 (review of rc14 applied: the BCa acceleration is computed arm by arm"),
    ("C3-ABS", "The interval's coverage has not been calibrated (a BCa"),
    ("F1-ABS", "its locked-leg interval excluded zero in every version that"),
    ("C1-EST", "in both cases under the BCa acceleration"),
    ("C1-UNC", "arm-stratified BCa bootstrap, with acceleration calculated from arm-specific"),
    ("C1-UNC", "**Correction (rc15).** Up to rc14 the acceleration pooled"),
    ("C5", "inconsistent with the file-system timestamp and, read literally"),
    ("C2", "fail by chance, and that each provider's Wilson interval would be reported"),
    ("C2", "adjudications of the 4 756 episodes with September"),
    ("C2-S7", "the October re-adjudication did not reproduce all of the"),
    ("C3", "does not explicitly propagate the stratum-B sampling (§4.1.2); some of that variation"),
    ("C3", "The cluster bootstrap resamples observed epochs within each arm,"),
    ("C3", "The bootstrap does not explicitly propagate adjudication-sampling or repeat-adjudication"),
    ("R-SRC", "the rc9 and rc8 rows, recomputed with"),
    ("C1-NOISE", "10 000 replicates (§4, *Uncertainty*), so it rests on the tail of the bootstrap distribution"),
    ("FIG", "![Figure B1](figures/figB1-h1a-inversao-registrado-v4.svg)"),
    ("FIG", "`ITT-REGISTRADO-v4` file (sha256), agrees with it on the registered leg"),
    ("FIG", "`figures/figB1-h1a-inversao-registrado-v2.svg`, and the rc8 figure,"),
    ("FIG", "`figures/figB1-h1a-inversao-registrado.svg`, are kept unchanged."),
    ("H2-HIST", "*(rc15: those are the"),
    ("F1-S9", "In every\nversion up to rc9 the only rejection"),
    ("F1-S9", "version up to rc9 the only rejection under the deposited decision rules was on the"),
    ("APPA", "Up to rc14 the\n  BCa acceleration was the one-sample formula"),
    ("APPA", "BCa acceleration was the one-sample formula over the pooled jackknife values"),
    ("APPA", "not in the registered analysis (v4)"),
    ("APPB", "| `out/ITT-REGISTRADO-v4-2026-10-05.json` · `measurement/estimador_itt_registrado.py` (six switches; arm-stratified"),
    ("APPB", "| `_sprint-2026-10-04/B-rc15/checks-rc15.py` · `checks-rc15.json` |"),
    ("B1", "BCa adjusted quantiles 99."),
    ("B1", "the 50th and 45th largest replicates"),
    ("B1", "(rc15; the same numbers, but the BCa intervals and ranks"),
    ("B1", "the rc8 rows of §4.2 as rc8 reported them"),
    ("B1", "| gate-2 rules, declared noise property (rc13; independence stated in rc15)"),
    ("B1", "and, with the panel (b) intervals of rc15"),
    ("BALLAST", "rc10, rc11, rc12 and rc15 (`ITT-PRELIMINAR.json`"),
    ("BALLAST", "script, `RESULTADO-v4.md`, the acceleration test"),
    ("SRC", "out/ITT-REGISTRADO-v4-2026-10-05.json"),
    ("SRC", "_sprint-2026-10-04/B-rc15/checks-rc15.json"),
    ("CL", "*(rc15)* also\n    `out/ITT-REGISTRADO-v4-2026-10-05.json`"),
    ("CL", "*(rc15: rc14, which\n    contains rc13"),
    ("CL", "*(rc15: the\n    78% holds only if"),
    ("CL", "**rc14: writing pass**"),
]

# ---------------------------------------------------------------- 3: declared deltas of the other invariants
DECL_INV = {
    # invariant -> {item: delta}; anything else must be unchanged
    "image links": {"![Figure B1](figures/figB1-h1a-inversao-registrado-v3.svg)": -1,
                    "![Figure B1](figures/figB1-h1a-inversao-registrado-v4.svg)": +1},
}
INV_FREE = {"code spans", "path-like tokens", "§ cross-references", "straight-quoted strings", "table lines"}
# These change with the edits (paths now point to v4 and checks-rc15; new cross-references in new sentences;
# new App. B rows). Their deltas are printed in --report and covered by the hunk IDs; the four invariants
# below must not move at all.
INV_FIXED = {"italic quotations", "citations", "footnote markers", "DOIs", "struck spans"}

# ---------------------------------------------------------------- 4: tail insertions (working list, changelog)
TAIL_INSERTS = [
    """; *(rc15)* also
    `out/ITT-REGISTRADO-v4-2026-10-05.json` with the frozen v4 script
    (`B-registered/estimador_itt_registrado-v4-b3095740.py`), `B-registered/RESULTADO-v4.md`,
    `B-registered/teste_aceleracao_v4.py` with `teste-aceleracao-v4.json`,
    `B-rc15/checks-rc15.json` with its script, and the rc15 Figure B1 with its script""",
    """ *(rc15: rc14, which
    contains rc13, had two full reads (`REVIEW-B-rc14-2026-10-05.md`): Fable GO, Codex NO-GO
    with three MEDIUM and three LOW, and Fable two LOW; all verified and applied in rc15. rc15
    itself, including the arm-stratified acceleration, has not been reviewed.)*""",
    """ *(rc15: the
    78% holds only if the 150 agreement indicators are independent, and "this failure is not
    that case" is withdrawn: the Wilson intervals are evidence against 0.99, not proof of a
    changed model or of lower reliability than in September; item 152.)*""",
]

# ---------------------------------------------------------------- 6: sweep locks (m) and presence (o)
SWEEP_LOCK = [  # (pattern, finding) — searched in the unstruck body
    (r"\binstrument change\b", "C2: an instrument change is not established"),
    (r"\btoo narrow\b", "C3: direction of the omitted uncertainty not established"),
    (r"pushes the intervals toward", "C3"),
    (r"resamples the first with the other two frozen", "C3: the bootstrap does not resample the assignment"),
    (r"so this failure is not that case", "C2: evidence, not proof"),
    (r"would fail on noise alone about \d+% of the time if each pair truly agreed", "C2: independence unstated"),
    (r"would not return all of its labels", "C2/§7"),
    (r"is rounded and, read literally", "C5"),
    (r"carry visible Monte-Carlo noise", "C1 sweep: categorical noise claim"),
    (r"least stable number", "C1 sweep: categorical noise claim"),
    (r"no inferential contrast is, and", "C4"),
    (r"its intervals excluded zero while sessions were split", "F1"),
    (r"and its intervals and H1a's excluded zero on every registered leg", "F1"),
    (r"The interval may be too narrow", "C3 sweep (abstract)"),
    (r"Where either acts, it makes the interval", "C3 sweep (§4.1.1)"),
]
PRESENT = [  # (text, finding) — must occur in the unstruck body (whitespace-normalized)
    ("The analysis uses an arm-stratified BCa bootstrap, with acceleration calculated from arm-specific "
     "leave-one-epoch-out jackknife influences, centered within arm and scaled by arm sample size.", "C1"),
    ("If the 150 agreement indicators were independent Bernoulli draws with agreement probability 0.99, the "
     "all-agree criterion would fail with probability 1 − 0.99^150 ≈ 0.779.", "C2"),
    ("marginal Wilson intervals exclude 0.99 under the binomial model, providing evidence against that agreement "
     "probability on these episodes. The comparison does not establish a change in model weights or a "
     "deterioration from September reliability, which was not measured for these providers. The declared point "
     "criteria nevertheless fail.", "C2"),
    ("despite observed test–retest disagreement; whether the instrument's response distribution changed is "
     "unresolved.", "C2"),
    ("the October re-adjudication did not reproduce all of the September labels", "C2 §7"),
    ("The cluster bootstrap resamples observed epochs within each arm, holding arm membership, arm sizes, the "
     "adjudication sample and its labels fixed. It does not redraw the constrained assignment; the separate "
     "re-randomization test does that.", "C3"),
    ("The bootstrap does not explicitly propagate adjudication-sampling or repeat-adjudication uncertainty. Some "
     "realized variation enters through between-epoch differences, but the resulting coverage error, including its "
     "direction and magnitude, has not been calibrated", "C3"),
    ("No standalone inferential interval or test is reported for this stratum. The descriptive per-hour contrasts "
     "are reported in §4; H1c cannot be contrasted because control has no eligible opportunities.", "C4"),
    ("is inconsistent with the file-system timestamp and, read literally, falls after the first call", "C5"),
    ("In every version up to rc9 the only rejection under the deposited decision rules was on the hypothesis "
     "demoted, in the undeposited revision, as requiring a 955% effect at the calibration share of altered briefs; "
     "its intervals excluded zero on every leg in every version, and H1a's excluded zero on every registered leg "
     "in rc9 (on the locked leg only in the sensitivity analysis, and not on rc8's post-hoc leg; §4.2).", "F1"),
    ("its locked-leg interval excluded zero in every version that split sessions across epochs, all three legs did "
     "in rc9, and every leg contains zero once they are not", "F1"),
]
STATUS_MARKS = ["rc14 prepared 2026-10-05", "rc15 prepared\n> 2026-10-05 (review of rc14 applied"]

# ---------------------------------------------------------------- 7: qualifier deltas
# phrase -> (delta, finding, reason). Headlines with a BCa interval are handled by the one-for-one rule.
JUSTIFIED_PHRASE = {
    ("did not reproduce", +2): ("C2 §7", "'a re-adjudication … would not return all of its labels' became 'the October "
                                "re-adjudication did not reproduce all of the September labels' (reviewer's text), "
                                "and changelog item 152 records it"),
    ("contains zero", +3): ("C1, F1", "§4 Uncertainty and changelog 150: 'no interval changes whether it contains zero'; "
                            "the abstract's F1 sentence: 'every leg contains zero once they are not'"),
    ("contain zero", -1): ("F1", "the abstract's '… contain zero once they are not' became '… every leg contains zero …'"),
    ("not been established", +1): ("C3", "changelog item 153: 'the direction of the resulting coverage error has not "
                                   "been established'"),
    ("post-hoc", +1): ("F1", "§9: 'and not on rc8's post-hoc leg' (Fable's text)"),
    ("in the sensitivity analysis", +1): ("F1", "§9: 'on the locked leg only in the sensitivity analysis' (Fable's text)"),
    ("which adds an instrument change to the sampling deviation", -1):
        ("C2", "rc12 headline withdrawn: an instrument change is not established (§7 says the record cannot tell "
               "non-determinism from a changed model); replaced by the reviewer's 'whether the instrument's response "
               "distribution changed is unresolved'"),
    ("H1c cannot be contrasted because control has no eligible opportunities", +1):
        ("C4", "Appendix B now carries the reviewer's sentence, which contains this rc11 headline"),
    ("`_sprint-2026-10-04/B-registered/estimador_itt_registrado-v3-0aa9202b.py`", +1):
        ("C1", "the v3 row of Appendix B names its frozen script in its first cell, because "
               "`measurement/estimador_itt_registrado.py` is now the v4 script"),
    # rc13 headlines rewritten by reviewed findings (the old text must be gone; the new text is in PRESENT)
    ("it neither re-draws the stratum-B sample nor re-adjudicates the episodes", -1):
        ("C3 sweep", "the abstract's direction claim rewritten; the two omitted layers are named as not propagated"),
    ("is rounded and, read literally, falls after the first call; it is not evidence of the order, which rests on "
     "the file-system creation time alone, and a checkout rewrites that time", -1):
        ("C5", "'is rounded' → 'is inconsistent with the file-system timestamp'; the rest of the sentence is kept"),
    ("would fail on noise alone about 78% of the time if each pair truly agreed with probability 0.99 (0.99^150 ≈ "
     "0.22 is the chance of zero changes)", -1):
        ("C2", "the noise property is restated under its independence condition (0.779)"),
    ("both point estimates lie below the lower bound of the 99/100 measurement, so this failure is not that case", -1):
        ("C2", "withdrawn: evidence against 0.99, not proof"),
    ("The cluster bootstrap resamples the first with the other two frozen.", -1):
        ("C3", "the bootstrap resamples observed epochs within arm; it does not redraw the assignment"),
}
# hedge-word delta of the hunks carrying each ID set (body, struck text removed) -> (delta, reason)
JUSTIFIED_HEDGE = {
    "ST": ({"no": 3}, "status header: rc14 'no claim moves'; rc15 'changes no zero-inclusion conclusion and "
                      "no p-value'"),
    "C3-ABS": ({"not": 3, "neither": -1, "nor": -1, "may": -1},
               "abstract (C3 sweep): 'may be too narrow' and 'neither re-draws … nor re-adjudicates' replaced by 'has not "
               "been calibrated', 'does not explicitly propagate', 'is not established'; 'may under-cover' kept"),
    "F1-ABS": ({"all": 1, "every": 2}, "abstract (F1, Fable's text): 'in every version …, all three legs did in rc9, "
                                      "and every leg contains zero'"),
    "C1-EST": ({"except": 1, "every": 2}, "§4 Estimator (C1): the v3 control 'every BCa interval of rc10 to rc14' and "
                                         "'every field except its timestamp'"),
    "C1-UNC+SRC": ({"not": 2, "no": 2, "registered": 1}, "§4 Uncertainty (C1): 'was not measured', 'H1c's "
                                                          "registered lower bound does not move', 'no interval changes "
                                                          "…, and no p-value'"),
    "C2": ({"not": 1, "about": -1, "alone": -1}, "§4 census (C2, reviewer's text): 'does not establish'; 'about 78%' "
                                                 "and 'on noise alone' replaced by the independence statement"),
    "C2-S7": ({"would": -1}, "§7 (C2): 'would not return all of its labels' → 'did not reproduce all of the September "
                             "labels'"),
    "C3": ({"may": -1, "either": -1, "not": 2}, "§4.1.1 table and §4.1.2 (C3, reviewer's text): 'may be "
                                                "under-represented. Where either acts, it makes the interval too narrow' "
                                                "→ 'does not explicitly propagate', 'has not been calibrated'"),
    "C1-NOISE": ({"not": 1}, "§4.2 sources (C1 sweep): 'its Monte-Carlo error was not measured' replaces 'the least "
                             "stable number in the table'"),
    "F1-S9": ({"not": 1, "only": 1, "sensitivity": 1, "every": 3}, "§9 (F1, Fable's text): 'every leg in every "
                                                                    "version', 'every registered leg', 'on the locked "
                                                                    "leg only in the sensitivity analysis, and not on "
                                                                    "rc8's post-hoc leg'"),
    "APPA": ({"not": 1, "no": 2}, "Appendix A (C1): 'does not match', 'no zero-inclusion conclusion and no p-value'"),
    "APPB+SRC": ({"not": 3, "no": 1, "cannot": 1, "registered": 6, "except": 1, "without": 2, "every": 5, "only": 1,
                  "unless": 4}, "Appendix B: the v4 row, the checks-rc15 row and the rc15 Figure B1 row (new artifacts, "
                                "their abort conditions 'unless …'), and C4's sentence ('No standalone inferential "
                                "interval …', 'cannot be contrasted', 'no eligible opportunities')"),
    "B1": ({"would": 1, "about": -1, "alone": -1}, "B.1 noise-property row (C2): 'fails on noise alone about 78%' → "
                                                   "'would fail with probability … 0.779' under independence"),
    "B1+SRC": ({"every": 1}, "B.1 first row: 'every number but the BCa intervals … equal to v3'"),
}


def headlines(A, cz, which):
    """rc11's headlines from the given artifacts (v3+checks-rc10 for rc14, v4+checks-rc15 for rc15), and rc12's
    and rc13's from the census record. R11.SCRIPT is pinned to the frozen v3 script in both cases."""
    itt = json.loads(R12.ART["ITT-2026-09-21"].read_text())
    f4 = json.loads(R12.ART["f4-w4"].read_text())
    f3 = json.loads(R12.ART["f3-abort"].read_text())
    reg, chk = (A["v3"], A["c10"]) if which == "rc14" else (A["v4"], A["c15"])
    heads = dict(R11.headline(reg, chk, f4, f3, itt))
    heads.update({"rc12 " + k: v for k, v in R12.headline_rc12(cz).items() if k != "drift §7"})
    heads.update({"rc13 " + k: v for k, v in R13.headline_rc13(cz).items()})
    return heads


# ---------------------------------------------------------------- 8: v4 integrity
def v4_integrity(A, new, files=None):
    fails = []
    files = files or {k: p.read_bytes() for k, p in ART.items()}
    h = lambda k: hashlib.sha256(files[k]).hexdigest()  # noqa: E731
    s_script = sha(SCRIPT)
    frozen = REG / f"estimador_itt_registrado-v4-{s_script[:8]}.py"
    if not frozen.exists() or sha(frozen) != s_script:
        fails.append("v4: no frozen copy of the running script under its sha8")
    v4 = A["v4"]
    if v4["proveniencia"]["script"]["sha256"] != s_script:
        fails.append("v4: provenance does not record the running script's sha256")
    if "bca_aceleracao" not in v4:
        fails.append("v4: the artifact does not declare the arm-stratified acceleration")
    for k in ("controle_v1_registrado", "controle_v2_registrado", "controle_v3_registrado"):
        if v4.get(k, {}).get("identico") is not True:
            fails.append(f"v4: {k} is not identical")
    if not all(x["identico"] for x in v4["controle_reproducao"].values()):
        fails.append("v4: the locked files are not rebuilt byte for byte")
    for leg in ("registrado", "sens_registrado_sem_sessoes_atravessadas"):
        for hh in ("H1", "H1a", "H1c"):
            if v4["pernas"][leg]["hipoteses"][hh]["bca"].get("aceleracao") != v4["bca_aceleracao"]["construcao"]:
                fails.append(f"v4: {leg}.{hh} not built with the arm-stratified acceleration")
    if v4["controle_v3_registrado"]["sha256"] != PINNED["v3"] or h("v3") != PINNED["v3"]:
        fails.append("v4: v3 artifact changed, or the v3 control read another file")
    if h("c10") != PINNED["c10"]:
        fails.append("v4: checks-rc10.json changed")
    for k, ck in (("v1", "controle_v1_registrado"), ("v2", "controle_v2_registrado")):
        if v4[ck]["sha256"] != h(k):
            fails.append(f"v4: {k} artifact differs from the one the v4 control read")
    t = A["teste"]
    if t.get("ok") is not True or len(t.get("dados_reais", [])) != 10 or not all(x["confere"] for x in t["dados_reais"]):
        fails.append("v4: the acceleration test did not pass on all 10 real cases")
    c = A["c15"]
    if c.get("sha256_ITT_REGISTRADO_v4") != h("v4") or c.get("sha256_script") != h("c15py"):
        fails.append("v4: checks-rc15.json does not pin the v4 artifact or its own script")
    if c["V_v3_para_v4"].get("sha256_checks_rc10") != PINNED["c10"]:
        fails.append("v4: checks-rc15 block V did not read checks-rc10.json")
    f = A["fig4"]
    if f["fonte"]["ITT-REGISTRADO"] != h("v4") or f["fonte"]["checks-rc15.json"] != h("c15"):
        fails.append("v4: Figure B1 (rc15) does not pin v4 and checks-rc15")
    # every sha8 the manuscript cites for v4
    for what, k in (("script", None), ("artifact", "v4")):
        s8 = (s_script if k is None else h(k))[:8]
        if f"`{s8}…`" not in new:
            fails.append(f"v4: the manuscript does not cite the {what} sha8 `{s8}…`")
    res = files["res4"].decode()
    for s8 in (s_script[:8], h("v4")[:8], h("testepy")[:8], h("teste")[:8], h("fig4py")[:8], h("fig4svg")[:8]):
        if s8 not in res:
            fails.append(f"v4: RESULTADO-v4.md does not record {s8}…")
    return fails


def resultado_reverted(st):
    r = st["resultado"].decode()
    fails = []
    if r.count(RESULTADO_RC15_NEW) != 1 or r.count(RESULTADO_RC15_NOTE) != 1:
        fails.append("resultado: RESULTADO-v3.md does not carry the rc15 correction exactly once")
        return st, fails
    r = r.replace(RESULTADO_RC15_NOTE, "").replace(RESULTADO_RC15_NEW, RESULTADO_RC15_OLD)
    return dict(st, resultado=r.encode()), fails


# ---------------------------------------------------------------- the check
def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    fails, rep = [], []
    S = subs(A)
    ob, nb = body(old), body(new)
    # 2 intervals traced to v4
    ob_sub, counts = apply_subs(ob, S)
    used = {k: v for k, v in counts.items() if v}
    dn = num_tok(nb)
    do = num_tok(ob_sub)
    delta = {k: dn[k] - do[k] for k in set(dn) | set(do) if dn[k] != do[k]}
    removed = {k: -d for k, d in delta.items() if d < 0}
    for k in sorted(set(removed) | set(JUSTIFIED_REMOVED)):
        if removed.get(k, 0) != JUSTIFIED_REMOVED.get(k, (0,))[0]:
            fails.append(f"numbers: token {k!r} removed {removed.get(k, 0)}x after the v4 substitutions; "
                         f"JUSTIFIED_REMOVED declares {JUSTIFIED_REMOVED.get(k, (0,))[0]}x")
    allowed = dict(R11.artifact_numbers())
    for name in ("v4", "c15", "teste"):
        for v in R11.leaves(A[name]):
            for fm in R11.forms(v):
                allowed.setdefault(fm, name)
    der = derived_rc15(A)
    old_nums = num_tok(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        elif old_nums[k]:
            src_add[k] = "in rc14"
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc14, nor an artifact leaf, nor derived")
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for a, b, w in S:
        for mo in re.finditer(re.escape(flat(a)), fn_unstruck):
            ctx = fn_unstruck[max(0, mo.start() - 120):mo.end() + 40]
            if not any(hh in ctx for hh in HISTORY):
                fails.append(f"v3 value left in the body: {a} ({w}) in …{ctx[60:200]!r}")
    rep.append(f"v4 substitutions formatted from the artifacts: {len(S)} pairs, {len(used)} used in rc14, "
               f"{sum(used.values())} occurrences")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = []
        o_sub, _ = apply_subs(h["old"], S)
        if h["old"] and o_sub == h["new"]:
            ids.append("V4")
        for aid, anc in ANCHORS:
            if anc in h["new"] and aid not in ids:
                ids.append(aid)
        h["ids"] = ids
        if not ids:
            fails.append(f"hunk rc14 {h['rc10']} rc15 {h['rc11']} has no ID: {h['new'][:80]!r}")
    # 3 invariants
    inv = {
        "§ cross-references": (collections.Counter(mo.group(0) for mo in R11.SECREF.finditer(ob)),
                               collections.Counter(mo.group(0) for mo in R11.SECREF.finditer(nb))),
        "code spans": (collections.Counter(R11.CODE.findall(ob)), collections.Counter(R11.CODE.findall(nb))),
        "italic quotations": (collections.Counter(R11.QUOTE.findall(ob)), collections.Counter(R11.QUOTE.findall(nb))),
        "straight-quoted strings": (collections.Counter(R14.STRAIGHT.findall(ob)), collections.Counter(R14.STRAIGHT.findall(nb))),
        "path-like tokens": (collections.Counter(R14.PATHLIKE.findall(ob)), collections.Counter(R14.PATHLIKE.findall(nb))),
        "citations": (collections.Counter(R11.CITE.findall(ob)), collections.Counter(R11.CITE.findall(nb))),
        "footnote markers": (collections.Counter(R14.FOOT.findall(ob)), collections.Counter(R14.FOOT.findall(nb))),
        "DOIs": (collections.Counter(R11.DOI.findall(ob)), collections.Counter(R11.DOI.findall(nb))),
        "struck spans": (collections.Counter(R14.STRUCK.findall(ob)), collections.Counter(R14.STRUCK.findall(nb))),
        "table lines": (collections.Counter(R14.TABLE.findall(ob)), collections.Counter(R14.TABLE.findall(nb))),
        "image links": (collections.Counter(R14.IMG.findall(ob)), collections.Counter(R14.IMG.findall(nb))),
    }
    for name, (a, b) in inv.items():
        d = {k: b[k] - a[k] for k in set(a) | set(b) if a[k] != b[k]}
        if name in DECL_INV:
            if d != DECL_INV[name]:
                fails.append(f"invariant: {name} delta {d} is not the declared {DECL_INV[name]}")
        elif name in INV_FIXED:
            if d:
                fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and name in INV_FREE:
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:60]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed")
    # table lines: every changed table line must be V4-only or anchored (covered by hunk IDs above)
    # 4 tail
    to, tn = tail(old), tail(new)
    t = tn
    for ins in TAIL_INSERTS:
        if t.count(ins) != 1:
            fails.append(f"tail: declared insertion not found exactly once: {ins.strip()[:60]!r}")
        t = t.replace(ins, "")
    i = t.find("\n**rc14: writing pass**")
    blocks = t[i:] if i >= 0 else ""
    t = t[:i] if i >= 0 else t
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertions removed, is not byte-identical to rc14")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", blocks, re.M)]
    if nums != list(range(149, 156)):
        fails.append(f"tail: rc14/rc15 changelog items are {nums}, expected 149..155")
    if "**rc15: review of rc14 applied**" not in blocks:
        fails.append("tail: the rc15 changelog block is missing")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc15 and {len(so)} in rc14, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc14")
    # 6 carried locks + (m) sweep + (n) status + (o) presence
    fails += R13.claims_rc13(new, cz)
    for pat, why in SWEEP_LOCK:
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS:
        if mk not in head:
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for txt, why in PRESENT:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    # 7 qualifier set
    h_old, h_new = headlines(A, cz, "rc14"), headlines(A, cz, "rc15")
    fo, fnn = flat(old), flat(new)
    locked = list(dict.fromkeys(R14.QUALIFIERS + R14.CENSUS_MARKS + [flat(v) for v in h_old.values()]))
    moved = {flat(h_old[k]): flat(h_new[k]) for k in h_old if flat(h_old[k]) != flat(h_new[k])}
    pdeltas = {}
    for ph in locked:
        a, b = fo.count(ph), fnn.count(ph)
        if ph in moved:
            nw = moved[ph]
            if b != 0 or fnn.count(nw) != a + fo.count(nw):
                fails.append(f"headline (BCa, v4): {ph[:50]!r} {a}x in rc14 must become {nw[:50]!r} one for one; "
                             f"rc15 has old {b}x, new {fnn.count(nw)}x")
            continue
        if a != b:
            pdeltas[ph] = b - a
            if (ph, b - a) not in JUSTIFIED_PHRASE:
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc15 against {a}x in rc14, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in JUSTIFIED_PHRASE if d < 0 and fnn.count(ph) == 0}
    for k, v in h_new.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc15")
    if report:
        lines_new = new.splitlines()
        for ph, d in pdeltas.items():
            where = [i + 1 for i, l in enumerate(lines_new) if ph.split(" ")[0] in l and ph in flat(" ".join(lines_new[max(0, i - 1):i + 2]))]
            rep.append(f"  phrase {d:+d} {ph[:60]!r} near rc15 lines {where[:12]}")
    ho, hn = R14.hedge_counts(old), R14.hedge_counts(new)
    hd = {w: hn[w] - ho[w] for w in R14.HEDGE if hn[w] != ho[w]}
    # per edit: the hedge delta of the hunks carrying each ID set (body only, struck text removed)
    def hc(t):
        w = collections.Counter(re.findall(r"[a-z][a-z\-]*", R11.strip_struck(t).lower()))
        return {x: w.get(x, 0) for x in R14.HEDGE}
    per = collections.defaultdict(collections.Counter)
    cut = len(body(new).splitlines())
    for h in hs:
        if h["rc11"][0] > cut:
            continue
        a_, b_ = hc(h["old"]), hc(h["new"])
        key = "+".join(h["ids"]) or "?"
        for w in R14.HEDGE:
            if b_[w] != a_[w]:
                per[key][w] += b_[w] - a_[w]
    per = {k: {w: d for w, d in v.items() if d} for k, v in per.items()}
    per = {k: v for k, v in per.items() if v}
    for k in sorted(set(per) | set(JUSTIFIED_HEDGE)):
        if per.get(k, {}) != JUSTIFIED_HEDGE.get(k, ({}, ""))[0]:
            fails.append(f"hedge: hunks [{k}] move hedge words by {per.get(k, {})}; JUSTIFIED_HEDGE declares "
                         f"{JUSTIFIED_HEDGE.get(k, ({}, ''))[0]}")
    tot = collections.Counter()
    for v in per.values():
        tot.update(v)
    if {w: d for w, d in tot.items() if d} != hd:
        fails.append(f"hedge: per-hunk deltas {dict(tot)} do not add up to the body delta {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    rep.append(f"locked phrases: {len(locked)} (rc14's); moved one-for-one to v4: {len(moved)}; "
               f"justified deltas: {pdeltas}; hedge deltas: {hd}")
    # 8 integrity
    fails += R11.script_integrity(**R11.load_integrity_inputs())
    fails += R12.census_integrity(cz)
    st2, f_res = resultado_reverted(st)
    fails += f_res
    f15, warns = R13.paths_integrity(st2)
    fails += f15
    fails += v4_integrity(A, new, files)
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc15")
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)} "
              f"({sorted({i for h in hs for i in h['ids']})})")
        for r in rep:
            print(r)
        print(f"headings: {len(R11.headings(new))}, unchanged: {R11.headings(old) == R11.headings(new)}")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc14: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc14 {len(old.split())} (body {len(body(old).split())}), "
              f"rc15 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nSUBS used (v3 -> v4, occurrences in rc14, source):")
        for (a, b, w), n in counts.items():
            if n:
                print(f"  {a} -> {b}  ×{n}  [{w}]")
        print("\nnumeric tokens added after SUBS (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed after SUBS:", removed)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc14 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc15 l.{h['rc11'][0]}-{h['rc11'][1]}")
            print("  - " + "\n  - ".join(h["old"].splitlines()[:6]))
            print("  + " + "\n  + ".join(h["new"].splitlines()[:6]))
    return fails


def main():
    old, new = OLD.read_text(encoding="utf-8"), NEW.read_text(encoding="utf-8")
    if "--report" in sys.argv:
        f = check(old, new, verbose=True, report=True)
        print("\n" + ("\n".join("FAIL " + x for x in f) or "no failures"))
        return 0
    if "--self-test" in sys.argv:
        return self_test(old, new)
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


def self_test(old, new):
    cz, st, A = R13.load_rc13(), R13.load_paths(), load()
    files = {k: p.read_bytes() for k, p in ART.items()}
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("abstract H1 interval back to v3", rep1("`H1` −1.27 [−28.36; +23.15]", "`H1` −1.27 [−28.15; +23.50]")),
        ("v4 bound altered in the §4.2 table", rep1("CI [−373.70; +310.82] · **contains zero**", "CI [−373.70; +310.83] · **contains zero**")),
        ("rc8 row left at the v3 interval", rep1("CI [−146.19; +2.11] · contains zero", "CI [−146.22; +1.95] · contains zero")),
        ("H2 raw tokens back to v3", rep1("+5 533 [+749; +12 308]", "+5 533 [+740; +12 282]")),
        ("BCa rank not updated (§4.2)", rep1("is the 45th largest of", "is the 30th largest of")),
        ("'may under-cover' dropped (§4.1.1)", rep1("on 11 and 9) may under-cover;", "on 11 and 9) under-covers;")),
        ("'instrument change' reintroduced (C2)", rep1("whether the\ninstrument's response distribution changed is unresolved.",
                                                       "which adds an\ninstrument change to the sampling deviation.")),
        ("direction claim reintroduced (C3)", rep1("has not been calibrated |", "makes the interval **too narrow** |")),
        ("independence dropped (C2)", rep1("If the 150 agreement indicators were independent Bernoulli draws",
                                          "If the 150 agreement indicators were Bernoulli draws")),
        ("'this failure is not that case' restored (C2)", rep1("The declared point criteria\nnevertheless fail.",
                                                              "So this failure is not that case.")),
        ("categorical noise claim restored (C1 sweep)", rep1("its Monte-Carlo error was not measured.",
                                                             "so it is the least stable number in the table.")),
        ("F1 sentence reverted", rep1("its locked-leg interval excluded zero in every version that",
                                      "its intervals excluded zero while sessions were split; in every version that")),
        ("status header without rc15", rep1("rc15 prepared\n> 2026-10-05 (review of rc14 applied", "rc15 drafted\n> 2026-10-05 (review of rc14 applied")),
        ("changelog block 155 removed", rep1("\n155. §9 and the abstract (Fable F1)", "\n§9 and the abstract (Fable F1)")),
        ("old changelog line edited", rep1("**rc13: review of rc12 applied**", "**rc13: review of rc12 applied (edited)**")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("hedge 'not' removed in Appendix A (C1)", rep1("which does\n  not match the arm-stratified bootstrap",
                                                        "which matches the arm-stratified bootstrap")),
        ("hedge 'not' removed", rep1("The comparison\ndoes not establish a change", "The comparison\nestablishes a change")),
        ("carried rc11: H1a presented as rejected", rep1("and it is not rejected. Sources:", "and it is rejected. Sources:")),
        ("carried rc13: abstract back to two commitments", rep1("Three commitments made before the seed", "Two commitments made before the seed")),
        ("citation removed", rep1(" [@kaplan2015nullnhlbi]", "")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    # integrity mutations (in memory)
    A2 = copy.deepcopy(A)
    A2["c15"]["sha256_ITT_REGISTRADO_v4"] = "0" * 64
    A3 = copy.deepcopy(A)
    A3["v4"]["controle_v3_registrado"]["identico"] = False
    A4 = copy.deepcopy(A)
    A4["teste"]["dados_reais"][0]["confere"] = False
    st2 = dict(st, resultado=st["resultado"].replace(RESULTADO_RC15_NEW.encode(), RESULTADO_RC15_OLD.encode()))
    files2 = dict(files, res4=files["res4"].replace(sha(SCRIPT)[:8].encode(), b"deadbeef"))
    integ = [("checks-rc15 does not pin v4", dict(A=A2)), ("v3 control not identical", dict(A=A3)),
             ("acceleration test failed on a real case", dict(A=A4)),
             ("RESULTADO-v3 rc15 correction reverted", dict(st=st2)),
             ("RESULTADO-v4 does not record the script sha8", dict(files=files2))]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files)
    print(f"unmutated rc15: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
