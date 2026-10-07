#!/usr/bin/env python3
"""Parity check B-v2-rc15.md -> B-v2-rc16.md (Paper B, sprint 2026-10-04; rc16 2026-10-05).

rc16 applies the review of rc15 (`REVIEW-B-rc15-2026-10-05.md`: Codex K1-K4, Fable L1-L4 and an
optional note), each finding verified before it was applied (`APPLY-B-rc16.md`). No number of the
analysis moves: v4 and checks-rc15 are untouched. K4 changes one script, the acceleration test
(`B-registered/teste_aceleracao_v4.py`), which now makes the unrounded comparison its docstring
promised; it was rerun, and its rc15 bytes are kept beside it.

Checks (exit 1 if any fails):
  1. hunks: every hunk rc15 -> rc16 carries an ID from ANCHORS.
  2. numbers: every numeric token REMOVED from the body is listed in JUSTIFIED_REMOVED with its exact
     count and finding; every token ADDED is in rc15, a leaf of an artifact read here (v4,
     checks-rc15, the rc16 test output), or derived (DERIVED_RC16, each computed here).
  3. invariants rc15 -> rc16 multiset-equal except declared deltas: italic quotations, citations,
     footnotes, DOIs, image links fixed; struck spans +1 (`~~Twelve~~`, K1); headings identical.
  4. working list and changelog: rc16's, with the declared insertions removed, is byte-identical to
     rc15's; the changelog blocks after rc14's are numbered 149-160 and the rc16 block is present.
  5. SHAM-JANELA: 10 blocks byte-identical to rc15.
  6. carried locks: rc15's (claims_rc13 = rc11 (a)-(f), rc12 (g)-(h), rc13 (i)-(l); rc15's sweep (m),
     status (n) and presence (o)), with two declared changes: (i) the DEVIATION-COUNT LOCK of rc13
     (`appa_count`) is replaced, because K1 removes the dose-band item: the count word must now be
     the one after `~~Thirteen~~ ~~Twelve~~`, it must be Eleven, and it must equal the number of
     unstruck items (11 of 12); (ii) rc15's presence lock on C1's construction sentence is replaced by
     the same sentence with L4's scaling (the old wording is swept). NEW (p) sweep: the dose band
     read as registered not to move (K1), the absolute "no interval includes" / "in none of them" /
     "unbiased in expectation and heavy in the tail" (K2), "ceases to exist" (K3), "scaled by arm
     sample size" (L4), the zero-inclusion claim sourced to `controle_v3_registrado` alone (L1), "as
     rc8 reported them |" (L3); (q) presence of each reviewer's text; (r) status header names rc16.
  7. qualifier set: every LOCKED phrase of rc15 (rc14's qualifiers and census marks, and the
     headlines of rc11-rc13 recomputed with v4 and checks-rc15) occurs in rc16 as many times as in
     rc15, except JUSTIFIED_PHRASE; hedge words checked per hunk-ID group (JUSTIFIED_HEDGE) and summed
     to the body delta.
  8. integrity: carried rc11 script integrity (frozen v3), rc12 census record, rc13 B-censo paths
     (RESULTADO-v3 with rc15's correction reverted), rc15's v4 integrity with the acceleration test
     pinned to its frozen rc15 bytes (which RESULTADO-v4.md records); NEW: the frozen rc15 test bytes
     are exactly `bb9c3197…` / `ae9e8fe9…`; the rerun test passes 10/10 with every unrounded
     difference within its tolerance 1e-12 and every unrounded v4 value rounding to `acel`; every
     field the rc15 output had is unchanged; the script enforces the tolerance (static check); the
     sha8 of the new script and output and the largest difference are cited in rc16; v4, checks-rc15
     and RESULTADO-v4 are unchanged.
  9. no REANALISE marker; bold balanced per paragraph.

Usage:  python3 parity-rc16.py | --report | --self-test     Reads; writes nothing.
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
OLD = SPRINT / "B-v2-rc15.md"
NEW = SPRINT / "B-v2-rc16.md"
RC15 = SPRINT / "B-rc15" / "parity-rc15.py"
RC15_SHA = "df4f492b5c7d057fde79b93ec063b465542c34f5a7a4410b20952bff54d34e62"

assert hashlib.sha256(RC15.read_bytes()).hexdigest() == RC15_SHA, \
    "parity-rc15.py changed: the locks carried from it are no longer the ones rc15 ran"
_spec = importlib.util.spec_from_file_location("parity_rc15", RC15)
R15 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R15)
R14, R13, R12, R11 = R15.R14, R15.R13, R15.R12, R15.R11

REG = SPRINT / "B-registered"
TEST_PY, TEST_JSON = REG / "teste_aceleracao_v4.py", REG / "teste-aceleracao-v4.json"
FROZEN_TEST_PY = REG / "teste_aceleracao_v4-rc15-bb9c3197.py"
FROZEN_TEST_JSON = REG / "teste-aceleracao-v4-rc15-ae9e8fe9.json"
FROZEN_SHA = {"py": "bb9c31977ddfa7c65c6c056f703be47040cca774af28e4a15f13cda3c4cc6d58",
              "json": "ae9e8fe9e0f19c8186597906e54825006beada96314ba058b540bccbe482419c"}
PINNED = {  # sha256 of artifacts rc16 must not have touched (as rc15 left them; APPLY-B-rc15.md)
    "v4": "3ed7637e", "c15": "914d4fa0", "c15py": "603695e0", "res4": "d5b3b8b6",
}
TOL = 1e-12


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


flat, body, tail = R15.flat, R15.body, R15.tail


def load():
    """rc15's artifacts; `teste` is the rc16 output, `teste_rc15` the frozen rc15 output."""
    A = R15.load()
    A["teste_rc15"] = json.loads(FROZEN_TEST_JSON.read_text())
    return A


def sci(x):
    """1.4224732503009818e-16 -> '1.4×10⁻¹⁶' (the manuscript's style)"""
    mant, ex = f"{x:.1e}".split("e")
    sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return f"{mant}×10{str(int(ex)).translate(sup)}"


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "randomness, not explicitly propagated into the intervals (wording of rc16)"),
    ("ST", "rc16 prepared 2026-10-05 (review of rc15 applied:"),
    ("L4+L1", "(n_g − 1)/n_g, with n_g the arm's epoch count."),
    ("L4+L1", "changes whether it contains zero (`_sprint-2026-10-04/B-rc15/checks-rc15.json`, blocks V and R;"),
    ("K2", "weight 6.945; its contribution to estimator variance has not been quantified."),
    ("K2", "Repeat-adjudication\nuncertainty is not explicitly propagated"),
    ("K3", "repeat-attempt set coincides with the opportunity set: the nesting remains"),
    ("H2M", "The winsorized-time lower bound, +0.009913 s, clears"),
    ("K2-S7", "September labels. Repeat-adjudication uncertainty is not explicitly propagated; some realized"),
    ("K1", "~~Thirteen~~ ~~Twelve~~ Eleven (the struck item"),
    ("K1", "The dose band `{2.0, 4.0, 7.5}` was retained when the sizing formula was corrected."),
    ("K1", "the registration promises less, which rested on it."),
    ("K4", "*(rc16: the test also compares the unrounded accelerations, to 1e-12"),
    ("L3+GER", "its `gerado_em` timestamp, in UTC, falls on 2026-10-06"),
    ("L3+GER", "(points and session-hours as rc8 reported them; intervals recomputed in rc15)"),
    ("WL", "*(rc16)*\n    also the revised acceleration test"),
    ("WL", "*(rc16: rc15 had\n    two full reads"),
    ("CL", "**rc16: review of rc15 applied**"),
]
# a removal-only hunk has no new text to anchor: (rc15 text it removes, ID)
REMOVED_ANCHORS = [
    ("- the dose band `{2 · 4 · 7.5}` was registered among *\"what does not move, and could not\"*", "K1"),
]

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {  # token -> (count, finding, reason)
    "2": (1, "K1", "'{2 · 4 · 7.5}' in the withdrawn item; the note writes the band as '{2.0, 4.0, 7.5}', "
                   "as PREREG does"),
    "4": (1, "K1", "same"),
    "4.4": (1, "K1", "'saturating in (4.0; 4.4]' is not carried into the note (Codex's text)"),
}


def derived_rc16(A):
    t = A["teste"]
    out = {}
    m = sci(t["max_dif_cru"])  # 1.4×10⁻¹⁶
    for tok in R11.numbers(m):
        out[tok] = f"rc16 test output: max_dif_cru {t['max_dif_cru']!r} -> {m}"
    for tok in R11.numbers(f"{t['tolerancia_cru']:.0e}"):  # 1e-12
        out.setdefault(tok, f"rc16 test output: tolerancia_cru {t['tolerancia_cru']}")
    g = A["v4"]["gerado_em"]
    assert g.startswith("2026-10-06T"), g
    for tok in R11.numbers(g[:10]):
        out.setdefault(tok, f"v4 gerado_em {g} (UTC date)")
    lo = A["v4"]["H2"]["registrado"]["tempo_s"]["estimador_winsorizado"]["ic95"][0]
    out.setdefault(f"{lo:.6f}", "v4 H2.registrado.tempo_s.estimador_winsorizado.ic95[0] at six decimals "
                                "(R11.forms stops at five)")
    for tok in R11.numbers("2026-08-17"):
        out.setdefault(tok, "PREREG-DRAFT.md: the design-effect correction block is dated 2026-08-17")
    return out


# ---------------------------------------------------------------- 3: declared deltas of the invariants
DECL_INV = {"struck spans": {"~~Twelve~~": +1}}
INV_FREE = {"code spans", "path-like tokens", "§ cross-references", "straight-quoted strings", "table lines"}
INV_FIXED = {"italic quotations", "citations", "footnote markers", "DOIs", "image links"}

# ---------------------------------------------------------------- 4: tail insertions
TAIL_INSERTS = [
    """; *(rc16)*
    also the revised acceleration test (`B-registered/teste_aceleracao_v4.py` with
    `teste-aceleracao-v4.json`) and the rc15 bytes kept beside it""",
    """ *(rc16: rc15 had
    two full reads (`REVIEW-B-rc15-2026-10-05.md`): Fable GO with four LOW and an optional
    note, Codex NO-GO with two MEDIUM and two LOW; all verified and applied in rc16. rc16
    itself has not been reviewed.)*""",
]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC16 = [  # (pattern, finding) — searched in the unstruck, flattened body
    (r"dose band `\{2 · 4 · 7\.5\}` was registered among", "K1: the band read as registered not to move"),
    (r"registration promises less than what was measured", "K1"),
    (r"The two items where the registration promises \*less\* matter most", "K1"),
    (r"unbiased in expectation", "K2"),
    (r"heavy in the tail", "K2"),
    (r"in none of them", "K2"),
    (r"no interval includes", "K2 (§7 and the status header)"),
    (r"It is not negligible: a single sampled failure", "K2"),
    (r"ceases to exist", "K3"),
    (r"scaled by arm sample size", "L4"),
    (r"contains zero, and no p-value changes \(`out/ITT-REGISTRADO-v4", "L1: zero inclusion is not in the v3 control"),
    (r"as rc8 reported them \|", "L3"),
]
PRESENT_RC16 = [
    ("The analysis uses an arm-stratified BCa bootstrap, with acceleration calculated from arm-specific "
     "leave-one-epoch-out jackknife influences, centred within arm and scaled by (n_g − 1)/n_g, with n_g the "
     "arm's epoch count.", "L4 (replaces rc15's C1 presence lock)"),
    ("no interval changes whether it contains zero (`_sprint-2026-10-04/B-rc15/checks-rc15.json`, blocks V and R; "
     "`_sprint-2026-10-04/B-registered/RESULTADO-v4.md`), and no p-value or point estimate changes "
     "(`out/ITT-REGISTRADO-v4-2026-10-05.json`, field `controle_v3_registrado`)", "L1"),
    ("A sampled stratum-B failure carries weight 6.945; its contribution to estimator variance has not been "
     "quantified.", "K2"),
    ("Repeat-adjudication uncertainty is not explicitly propagated; some realized variation may enter through "
     "between-epoch differences, and its contribution to interval coverage has not been quantified.", "K2 §4.1.2"),
    ("September labels. Repeat-adjudication uncertainty is not explicitly propagated; some realized variation may "
     "enter through between-epoch differences, and its contribution to interval coverage has not been quantified "
     "(§4.1.2).", "K2 §7"),
    ("the repeat-attempt set coincides with the opportunity set: the nesting remains, but H1b no longer provides "
     "the intended intermediate distinction.", "K3"),
    ("The dose band `{2.0, 4.0, 7.5}` was retained when the sizing formula was corrected. The later calibration "
     "replay changed 11/15/17 of 350 states; this does not contradict that commitment.", "K1"),
    ("the rc8 rows of §4.2 (points and session-hours as rc8 reported them; intervals recomputed in rc15)", "L3"),
    ("The winsorized-time lower bound, +0.009913 s, clears zero by less than 0.01 s, and its Monte-Carlo error "
     "was not measured.", "Fable optional (H2 margin)"),
    ("its `gerado_em` timestamp, in UTC, falls on 2026-10-06", "review note (gerado_em)"),
]
# rc15's presence lock that L4 rewrites (the rest of rc15's PRESENT is carried as is)
PRESENT_REPLACED = {R15.PRESENT[0][0]: "L4"}
assert "centered within arm and scaled by arm sample size" in R15.PRESENT[0][0]
STATUS_MARKS_RC16 = R15.STATUS_MARKS + ["rc16 prepared 2026-10-05 (review of rc15 applied:"]
STATUS_LOCK = [(r"randomness that no interval includes", "K2: status header (rc13 clause)")]

# deviation-count lock (rc13's appa_count), replaced: K1 removes one item
DEV_COUNT = 11
DEV_COUNT_JUSTIFIED = ("K1: the dose band is not a deviation — PREREG's 'What does not move, and could not' "
                       "(the 2026-08-17 design-effect correction) names the parameters that correction left "
                       "unchanged; it does not say the dose cannot change briefs. 12 -> 11 unstruck items.")
DOSE_ITEM = re.compile(r"\n- the dose band\b")


def appa_count_rc16(new):
    appa = R13.section(new, "\n## Appendix A", "\n## Appendix B")
    m = re.search(r"~~Twelve~~ ~~Thirteen~~ ~~Twelve~~ (\w+) \(the struck item below is no longer a deviation\) "
                  r"that a reader", appa)
    if not m:
        return ["App A: count sentence (~~Thirteen~~ ~~Twelve~~ <word>) not found"]
    end = appa.find("\n\nThe dose band `{2.0, 4.0, 7.5}` was retained", m.end())
    if end < 0:
        return ["App A: the list's closing note (K1) not found"]
    lst = appa[m.end():end]
    items = re.split(r"\n- ", "\n" + lst.strip())[1:]
    live = [x for x in items if not x.lstrip().startswith("~~")]
    want = R13.WORDS.get(m.group(1).lower())
    fails = []
    if want != len(live):
        fails.append(f"App A: the count word says {m.group(1)}, the list has {len(live)} unstruck items of {len(items)}")
    if want != DEV_COUNT:
        fails.append(f"App A: the count is {m.group(1)}, the locked count is {DEV_COUNT} ({DEV_COUNT_JUSTIFIED[:40]}…)")
    if DOSE_ITEM.search("\n" + lst.strip()):
        fails.append("App A: the dose band is listed as a deviation again (K1)")
    return fails


R13.appa_count = appa_count_rc16  # claims_rc13 looks it up in its module at call time

# ---------------------------------------------------------------- 7: qualifier deltas
JUSTIFIED_PHRASE = {
    # rc13 headlines that K2 withdraws (the new text is in PRESENT_RC16)
    ("The September labels are held fixed in every interval, so this variation is in none of them", -1):
        ("K2", "§4.1.2: replaced by the reviewer's 'Repeat-adjudication uncertainty is not explicitly propagated …'"),
    ("no interval includes that variation (§4.1.2)", -1):
        ("K2", "§7: same replacement"),
    # rc13's deviation-count headline: K1 removes the dose-band item
    ("~~Thirteen~~ Twelve (the struck item below is no longer a deviation)", -1):
        ("K1", "'~~Thirteen~~ Twelve' → '~~Thirteen~~ ~~Twelve~~ Eleven'"),
}
# hedge-word delta of the body hunks carrying each ID set -> (delta, reason)
JUSTIFIED_HEDGE = {
    "ST": ({"not": 5, "could": 1, "every": 1},
           "status header: the rc16 clause ('is no longer listed', 'did not say the dose could not change briefs', "
           "'not quantified, not as absent from every interval') and the rc13 clause ('not explicitly propagated')"),
    "K1": ({"not": 2, "could": 1, "registered": -1, "no": -1},
           "Appendix A: the withdrawn item ('was registered among', its quotation) and paragraph ('no reason to "
           "correct'); the note (Codex's 'does not contradict', the quotation again, 'the dose could not change briefs')"),
    "K2": ({"not": 2, "may": 1, "every": -1, "none": -1},
           "§4.1.2 (reviewer's text): 'It is not negligible' and 'held fixed in every interval, … in none of them' "
           "replaced by 'has not been quantified' (×2), 'is not explicitly propagated', 'may enter'"),
    "K2-S7": ({"not": 2, "no": -1, "may": 1},
              "§7 (reviewer's text): 'no interval includes that variation' replaced by 'is not explicitly "
              "propagated; some realized variation may enter …, has not been quantified'"),
    "K3": ({"no": 1}, "§4.4 (reviewer's text): 'H1b no longer provides the intended intermediate distinction'"),
    "H2M": ({"not": 1}, "§5 (Fable, optional): 'its Monte-Carlo error was not measured', as in §4 Uncertainty"),
}


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    fails, rep = [], []
    ob, nb = body(old), body(new)
    # 2 numbers
    dn, do = R11.numbers(nb), R11.numbers(ob)
    delta = {k: dn[k] - do[k] for k in set(dn) | set(do) if dn[k] != do[k]}
    removed = {k: -d for k, d in delta.items() if d < 0}
    for k in sorted(set(removed) | set(JUSTIFIED_REMOVED)):
        if removed.get(k, 0) != JUSTIFIED_REMOVED.get(k, (0,))[0]:
            fails.append(f"numbers: token {k!r} removed {removed.get(k, 0)}x; JUSTIFIED_REMOVED declares "
                         f"{JUSTIFIED_REMOVED.get(k, (0,))[0]}x")
    allowed = dict(R11.artifact_numbers())
    for name in ("v4", "c15", "teste"):
        for v in R11.leaves(A[name]):
            for fm in R11.forms(v):
                allowed.setdefault(fm, name)
    der = derived_rc16(A)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc15"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc15, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc15 {h['rc10']} rc16 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:40]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed")
    # 4 tail
    to, tn = tail(old), tail(new)
    t = tn
    for ins in TAIL_INSERTS:
        if t.count(ins) != 1:
            fails.append(f"tail: declared insertion not found exactly once: {ins.strip()[:60]!r}")
        t = t.replace(ins, "")
    i16 = t.find("\n\n**rc16: review of rc15 applied**")
    blocks16 = t[i16:] if i16 >= 0 else ""
    t = t[:i16] + "\n" if i16 >= 0 else t
    if i16 < 0:
        fails.append("tail: the rc16 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertions and the rc16 block removed, "
                     "is not byte-identical to rc15")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 161)):
        fails.append(f"tail: rc14-rc16 changelog items are {nums}, expected 149..160")
    if not re.search(r"^156\. Appendix A \(Codex K1\)", blocks16, re.M):
        fails.append("tail: changelog item 156 (K1) missing")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc16 and {len(so)} in rc15, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc15")
    # 6 carried locks (rc13 deviation count replaced, see appa_count_rc16) + rc15 (m)(n)(o) + rc16 (p)(q)(r)
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in R15.SWEEP_LOCK + SWEEP_LOCK_RC16:
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC16:
        if mk not in head:
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    for txt, why in [p for p in R15.PRESENT if p[0] not in PRESENT_REPLACED] + PRESENT_RC16:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    # 7 qualifier set (rc15's locked phrases: the same artifacts on both sides, so no headline moves)
    h15 = R15.headlines(A, cz, "rc15")
    fo, fnn = flat(old), flat(new)
    locked = list(dict.fromkeys(R14.QUALIFIERS + R14.CENSUS_MARKS + [flat(v) for v in h15.values()]))
    pdeltas = {}
    for ph in locked:
        a, b = fo.count(ph), fnn.count(ph)
        if a != b:
            pdeltas[ph] = b - a
            if (ph, b - a) not in JUSTIFIED_PHRASE:
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc16 against {a}x in rc15, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R15.JUSTIFIED_PHRASE) if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc16")
    ho, hn = R14.hedge_counts(old), R14.hedge_counts(new)
    hd = {w: hn[w] - ho[w] for w in R14.HEDGE if hn[w] != ho[w]}

    def hc(t_):
        w = collections.Counter(re.findall(r"[a-z][a-z\-]*", R11.strip_struck(t_).lower()))
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
    rep.append(f"locked phrases: {len(locked)} (rc15's); justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: carried
    fails += R11.script_integrity(**R11.load_integrity_inputs())
    fails += R12.census_integrity(cz)
    st2, f_res = R15.resultado_reverted(st)
    fails += f_res
    f15, warns = R13.paths_integrity(st2)
    fails += f15
    # rc15's v4 integrity, with the acceleration test pinned to the frozen rc15 bytes RESULTADO-v4.md records
    files = files or {k: p.read_bytes() for k, p in R15.ART.items()}
    files15 = files15 or {"py": FROZEN_TEST_PY.read_bytes(), "json": FROZEN_TEST_JSON.read_bytes()}
    A15 = dict(A, teste=json.loads(files15["json"]))
    f15b = dict(files, testepy=files15["py"], teste=files15["json"])
    fails += R15.v4_integrity(A15, new, f15b)
    fails += test_integrity(A, new, files, files15)
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc16")
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
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc15: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc15 {len(old.split())} (body {len(body(old).split())}), "
              f"rc16 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc15 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc16 l.{h['rc11'][0]}-{h['rc11'][1]}")
            print("  - " + "\n  - ".join(h["old"].splitlines()[:6]))
            print("  + " + "\n  + ".join(h["new"].splitlines()[:6]))
    return fails


# ---------------------------------------------------------------- 8: the acceleration test (K4)
def test_integrity(A, new, files, files15):
    fails = []
    h = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    if h(files15["py"]) != FROZEN_SHA["py"] or h(files15["json"]) != FROZEN_SHA["json"]:
        fails.append("test: the frozen rc15 test bytes are not bb9c3197… / ae9e8fe9…")
    for k, s8 in PINNED.items():
        if not h(files[k]).startswith(s8):
            fails.append(f"test: {k} changed in rc16 (rc15 left {s8}…)")
    t, t15 = A["teste"], A["teste_rc15"]
    reais = t.get("dados_reais", [])
    if t.get("ok") is not True or t.get("falhas") or len(reais) != 10:
        fails.append("test: the rc16 test did not pass on 10 real cases")
    if t.get("tolerancia_cru") != TOL:
        fails.append(f"test: tolerance {t.get('tolerancia_cru')} is not {TOL}")
    for x in reais:
        if not (x.get("confere") and x.get("confere_cru") and x.get("confere_arredondado")):
            fails.append(f"test: {x['perna']}.{x['h']} does not pass both comparisons")
        if not (isinstance(x.get("dif_cru"), float) and x["dif_cru"] <= TOL
                and abs(x["a_v4_cru"] - x["a_scipy"]) == x["dif_cru"] and round(x["a_v4_cru"], 6) == x["a_v4"]):
            fails.append(f"test: {x['perna']}.{x['h']} unrounded difference {x.get('dif_cru')!r} out of tolerance "
                         f"or inconsistent with its values")
    if reais and t.get("max_dif_cru") != max(x["dif_cru"] for x in reais):
        fails.append("test: max_dif_cru is not the largest unrounded difference")
    # every field of the rc15 output is unchanged
    for k in ("scipy", "numpy", "caso_a_mao"):
        if t.get(k) != t15.get(k):
            fails.append(f"test: field {k} differs from the rc15 output")
    if len(t15["dados_reais"]) != len(reais):
        fails.append("test: the rc16 output has a different number of real cases")
    for a, b in zip(t15["dados_reais"], reais):
        for k, v in a.items():
            if b.get(k) != v:
                fails.append(f"test: {a['perna']}.{a['h']} field {k} differs from rc15 ({v!r} -> {b.get(k)!r})")
    # the script enforces the tolerance and its docstring says what it does
    src = files["testepy"].decode()
    for needle, why in (('x["dif_cru"] <= TOL_CRU', "the tolerance is not enforced"),
                        ("TOL_CRU = 1e-12", "the tolerance constant is not 1e-12"),
                        ("if not x[\"confere_cru\"]:\n        falhas.append", "an unrounded failure is not recorded"),
                        ("unrounded, to\n     1e-12", "the docstring does not state the unrounded comparison")):
        if needle not in src:
            fails.append(f"test: {why}")
    if "(to 1e-12 before\n     rounding; to the 6th decimal after)" in src:
        fails.append("test: the rc15 docstring promise is still there")
    # the manuscript cites the new bytes and the largest difference
    for what, s8 in (("script", h(files["testepy"])[:8]), ("output", h(files["teste"])[:8])):
        if f"`{s8}…`" not in new:
            fails.append(f"test: rc16 does not cite the {what} sha8 `{s8}…`")
    if reais and sci(t["max_dif_cru"]) not in new:
        fails.append(f"test: rc16 does not cite the largest difference {sci(t['max_dif_cru'])}")
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
    files = {k: p.read_bytes() for k, p in R15.ART.items()}
    files15 = {"py": FROZEN_TEST_PY.read_bytes(), "json": FROZEN_TEST_JSON.read_bytes()}
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("K1: dose-band item restored", rep1(
            "- the designation was recorded as an open defect",
            "- the dose band `{2 · 4 · 7.5}` was registered among *\"what does not move, and could not\"*\n"
            "  and moves: 11/15/17 states of 350, monotone, saturating in `(4.0; 4.4]`. The\n"
            "  registration promises less than what was measured;\n- the designation was recorded as an open defect")),
        ("K1: count word left at Twelve", rep1("~~Thirteen~~ ~~Twelve~~ Eleven (the struck", "~~Thirteen~~ Twelve (the struck")),
        ("K1: count word says Twelve over eleven items", rep1("~~Twelve~~ Eleven (the struck", "~~Twelve~~ Twelve (the struck")),
        ("K1: 'promises less' paragraph restored", rep1(
            "commitment. Up to rc15 this list",
            "commitment.\n\nThe two items where the registration promises *less* matter most: an error that favours\n"
            "its authors is one they have no reason to correct unprompted. Up to rc15 this list")),
        ("K2: 'heavy in the tail' restored", rep1("its contribution to estimator variance has not been quantified.",
                                                  "which is unbiased in expectation and heavy in the tail.")),
        ("K2: 'in none of them' restored (§4.1.2)", rep1(
            "by 6.945. Repeat-adjudication\nuncertainty is not explicitly propagated;",
            "by 6.945. The September labels are held fixed in every interval, so this variation is in none of them;"
            " Repeat-adjudication\nuncertainty is not explicitly propagated;")),
        ("K2: §7 'no interval includes' restored", rep1("coverage has not been quantified (§4.1.2).",
                                                       "coverage has not been quantified, and no interval includes that variation (§4.1.2).")),
        ("K2: status header reverted", rep1("randomness, not explicitly propagated into the intervals (wording of rc16)",
                                            "randomness that no interval includes")),
        ("K3: 'ceases to exist' restored", rep1("the nesting remains, but H1b no longer\nprovides the intended intermediate distinction.",
                                                "the nesting ceases to exist.")),
        ("L4: 'scaled by arm sample size' restored", rep1("scaled by\n(n_g − 1)/n_g, with n_g the arm's epoch count.",
                                                         "scaled by arm sample\nsize.")),
        ("L1: zero inclusion sourced to the v3 control again", rep1(
            "contains zero (`_sprint-2026-10-04/B-rc15/checks-rc15.json`, blocks V and R;\n"
            "`_sprint-2026-10-04/B-registered/RESULTADO-v4.md`), and no p-value or point estimate changes\n",
            "contains zero, and no p-value changes\n")),
        ("L3: 'as rc8 reported them' restored", rep1(
            "the rc8 rows of §4.2 (points and session-hours as rc8 reported them; intervals recomputed in rc15) |",
            "the rc8 rows of §4.2 as rc8 reported them |")),
        ("H2 margin sentence dropped", rep1("The winsorized-time lower bound, +0.009913 s, clears\nzero by less than 0.01 s, "
                                            "and its Monte-Carlo error was not measured. ", "")),
        ("K4: new test sha8 not cited", rep1("script sha256 `d4d960db…`", "script sha256 `bb9c3197…`")),
        ("status header without rc16", rep1("rc16 prepared 2026-10-05 (review of rc15 applied:", "rc16 drafted 2026-10-05 (review of rc15 applied:")),
        ("changelog item 159 removed", rep1("\n159. `B-registered/teste_aceleracao_v4.py`", "\n`B-registered/teste_aceleracao_v4.py`")),
        ("old changelog line edited", rep1("**rc15: review of rc14 applied**", "**rc15: review of rc14 applied (edited)**")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("hedge 'not' removed (K2)", rep1("its contribution to estimator variance has not been quantified.",
                                          "its contribution to estimator variance has been quantified.")),
        ("carried rc15: 'instrument change' reintroduced", rep1(
            "whether the\ninstrument's response distribution changed is unresolved.",
            "which adds an\ninstrument change to the sampling deviation.")),
        ("carried rc13: abstract back to two commitments", rep1("Three commitments made before the seed",
                                                               "Two commitments made before the seed")),
        ("carried rc11: H1a presented as rejected", rep1("and it is not rejected. Sources:", "and it is rejected. Sources:")),
        ("italic quotation removed", rep1("reading\n*\"what does not move, and could not\"* (PREREG", "reading\nthe phrase (PREREG")),
        ("citation removed", rep1(" [@kaplan2015nullnhlbi]", "")),
        ("unsourced number added", rep1("the day after the date in the file name;", "the day after the date in the file name (0.7311);")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    # integrity mutations (in memory)
    A2 = copy.deepcopy(A)
    A2["teste"]["dados_reais"][3]["dif_cru"] = 2e-12
    A3 = copy.deepcopy(A)
    A3["teste"]["dados_reais"][0]["a_v3"] = 0.153026
    A4 = copy.deepcopy(A)
    A4["c15"]["sha256_ITT_REGISTRADO_v4"] = "0" * 64
    files_tol = dict(files, testepy=files["testepy"].replace(b'x["dif_cru"] <= TOL_CRU', b'x["dif_cru"] <= 1.0'))
    files_res = dict(files, res4=files["res4"].replace(b"bb9c3197", b"deadbeef"))
    files15_bad = dict(files15, py=files15["py"] + b"\n")
    integ = [("an unrounded difference above the tolerance", dict(A=A2)),
             ("an rc15 field of the test output changed", dict(A=A3)),
             ("carried rc15: checks-rc15 does not pin v4", dict(A=A4)),
             ("the test no longer enforces the tolerance", dict(files=files_tol)),
             ("RESULTADO-v4 no longer records the rc15 test sha8", dict(files=files_res)),
             ("the frozen rc15 test copy altered", dict(files15=files15_bad))]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15)
    print(f"unmutated rc16: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
