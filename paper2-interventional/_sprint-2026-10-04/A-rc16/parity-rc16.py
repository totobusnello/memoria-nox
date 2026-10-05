#!/usr/bin/env python3
"""Parity check rc15 -> rc16 of Paper A after the Codex and Fable reviews of rc15.

Usage:
    python3 parity-rc16.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc16.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc16 applies the findings of `_sprint-2026-10-04/REVIEW-A-rc15-2026-10-05.md`: Codex CX-A..CX-D,
Fable FB-A, FB-B and the Fable nit (FB-nit), IDs as in `APPLY-A-rc16.md`. CX-A and CX-B are
residues of classes rc15 fixed elsewhere (a check called a falsifier; a policy called better or
worse without measured utility), so the whole manuscript was swept for both and the sweep edits
are declared under the same IDs ("CX-A sweep", "CX-B sweep"). rc16 may change numbers,
references, code spans, one heading and one table row, but only the ones a finding declares. The
F-5 "Addendum, rc16" is cut out of NEW (between its header and "## Open items") before the delta
checks; the "addendum" check requires that it exists exactly once, right after the rc15 addendum
and right before "## Open items".

Unlike rc15, rc16 does not touch any earlier addendum: the F-5 addenda rc5..rc15 must be
byte-identical.

Checks, OLD vs NEW-without-the-rc16-addendum (the extractors come from A-rc15/parity-rc15.py,
which takes them from A-rc14 back to A-rc9, so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings == NEW headings, in order, except the 1 DECLARED replacement (§5.6)
  tables      OLD table rows == NEW table rows, in order, except the 1 DECLARED replacement
  history     F-5 addenda rc5..rc15 byte-identical
  qualifiers  carried: every rc6-rc15 scope qualifier keeps its rc15 count (outside the addenda),
              no declared delta, and is >= 1; full scope clause in the Abstract and in §3.1;
              *no-record* defined exactly once, in §3.1
  classes     carried: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py occurs in NEW
              outside the F-5 addenda
  withdrawn   carried and extended: none of the 55 phrasings withdrawn in rc11..rc15, nor the 17
              rc15 phrasings withdrawn here, occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc15)
  addendum    the rc16 addendum exists exactly once, in place
  deposit     deposit/paperA-v1.1/spare-capacity-narrow-surface-v1.1.md is byte-identical to NEW

Every DECLARED entry carries the finding ID that justifies it. A delta that is not declared, or a
declared delta that did not happen, fails the check.

--selftest first requires OLD vs NEW to pass, then applies one mutation per check to NEW (or to
the deposit copy) and requires each mutated copy to FAIL on the expected check.
"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
DEFAULT_OLD = SPRINT / "A-v1.1-rc15.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc16.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "spare-capacity-narrow-surface-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc15", SPRINT / "A-rc15" / "parity-rc15.py")
_rc15 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc15)
FORBIDDEN = list(_rc15.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc15.extract, _rc15.norm, _rc15.outside_addenda, _rc15.prose_dashes
QUALIFIERS = list(_rc15.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc15.SCOPE_FULL, _rc15.NO_RECORD_DEF
section, declared_counter, delta = _rc15.section, _rc15.declared_counter, _rc15.delta
first_prose, sub_at, qualifier_counts = _rc15.first_prose, _rc15.sub_at, _rc15.qualifier_counts

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC14_ADDENDUM = "**Addendum, rc14 (2026-10-05)"
RC15_ADDENDUM = "**Addendum, rc15 (2026-10-05)"
RC16_ADDENDUM = "**Addendum, rc16 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD).
# CX-A  = §1 no longer calls §5.6 the test that could have killed the prediction: "All 20 entries
#         observed at saturation ... not a falsifier of Proposition 1 (§5.2, §5.6)".
#         Sweep: §5.6 heading; §6 row on the reconstructed pool ("the valid test").
# CX-B  = Appendix F-1: no "worse policy"; utility not measured. Sweep: F-1 "including a correct
#         one" x2; title note "the corpus that is starved" (no tokens).
# CX-C  = §5.7.1: "unreachability" withdrawn; loss of sensitivity, with the log evidence.
# CX-D  = §4.3.2: `clamp01` in the access term; non-decreasing and capped at 0.20.
# FB-A  = §4.3.1 and status block: the 10,899 `sessions/%` count flagged as without artifact.
# FB-B  = Appendix D: four `out/` artifacts dated 2026-10-05, not three.
# FB-nit= §4.3.1: the 285 cites `DEVIATIONS-FOR-PAPER.md` §10.11.
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    # CX-A §1: 'All 20 entries observed at saturation ... (§5.2, §5.6)'; 'Proposition 1' added in
    # §1 and removed from the CX-C bullet ('It is Proposition 1 biting ...'): '1' net 0
    ("CX-A §1 'All 20 entries observed at saturation'", "20", +1),
    ("CX-A §1 pointer '§5.2' (Proposition 1)", "5.2", +1),
    ("CX-A §1 'Proposition 1' +1, CX-C bullet 'Proposition 1' -1", "1", 0),
    # CX-B F-1: '3,231 chunks of type `daily`' removed
    ("CX-B F-1 'In a corpus with ... 3,231 chunks of type `daily`' removed", "3,231", -1),
    # CX-C §5.7.1: 'the three lost states' removed; 'the two states have zero churn'; the two
    # selected ids of the hour control
    ("CX-C §5.7.1 'As measured, the three lost states' removed", "three", -1),
    ("CX-C §5.7.1 'the two states have zero churn'", "two", +1),
    ("CX-C §5.7.1 '`308222`'", "308222", +1),
    ("CX-C §5.7.1 '`308240`'", "308240", +1),
    # CX-D §4.3.2: '(`serving-salience.ts:227-234`)', 'capped at 0.20'
    ("CX-D §4.3.2 '`serving-salience.ts:227-234`'", "227", +1),
    ("CX-D §4.3.2 '`serving-salience.ts:227-234`'", "234", +1),
    ("CX-D §4.3.2 'capped at 0.20'", "0.20", +1),
    # FB-A: 'The 10,899 `sessions/%` count' in §4.3.1 and in the status block
    ("FB-A §4.3.1 and status block 'the 10,899 `sessions/%` count'", "10,899", +2),
    # FB-B Appendix D: 'the three dated' -> 'the four cited here that are dated'
    ("FB-B Appendix D 'three' -> 'four'", "three", -1),
    ("FB-B Appendix D 'three' -> 'four'", "four", +1),
    # FB-nit §4.3.1: '`DEVIATIONS-FOR-PAPER.md` §10.11'
    ("FB-nit §4.3.1 '§10.11'", "10.11", +1),
]
D_FOOTNOTES = []
D_REFS = [
    ("CX-A §1 '(§5.2, §5.6)'", "§5.2", +1),
    ("CX-A §1 'Proposition 1' added; CX-C 'It is Proposition 1 biting' removed", "Proposition 1", 0),
    ("FB-nit §4.3.1 '§10.11'", "§10.11", +1),
]
D_CODE = [
    ("CX-B F-1 '`daily`' removed with the sentence", "`daily`", -1),
    ("CX-C §5.7.1 hour control artifact", "`out/gran3-hora.json`", +1),
    ("CX-C §5.7.1 selected id", "`308222`", +1),
    ("CX-C §5.7.1 selected id", "`308240`", +1),
    ("CX-C §5.7.1 classifier", "`granularidade-do-teto.py`", +1),
    ("CX-D §4.3.2 old formula", "`0.20 · log1p(access_count)/log(1000)`", -1),
    ("CX-D §4.3.2 new formula", "`0.20 · clamp01(log1p(access_count)/log(1000))`", +1),
    ("CX-D §4.3.2 line cite", "`serving-salience.ts:227-234`", +1),
    ("FB-A §4.3.1 and status block", "`sessions/%`", +2),
    ("FB-nit §4.3.1", "`DEVIATIONS-FOR-PAPER.md`", +1),
]
D_LINKS = []
D_HEADINGS = [
    ("CX-A sweep §5.6 heading",
     "### 5.6 The test this derivation has to pass",
     "### 5.6 A same-stratum matching check on recorded quantities"),
]
_ROW_HEAD = ("| **test of a derivation on a RECONSTRUCTED pool** (the coverage pool is not returned by any "
             "exported function) | classified 25 states as alterable against 17 real ones, and only **1 of "
             "the 17** fell in the class; 24 violations of the prefix assumption were the symptom. ")
D_TABLES = [
    ("CX-A sweep §6 row on the reconstructed pool",
     _ROW_HEAD + "The valid test uses only **recorded** quantities (§5.6) |",
     _ROW_HEAD + "The check that replaced it uses only **recorded** quantities and is not a falsifier "
                 "(§5.6) |"),
]

# Declared qualifier deltas (rc16 - rc15), counted outside the addenda: none.
D_QUALIFIERS = {}

# Withdrawn phrasings: the 55 of rc11..rc15 (carried), plus the ones this review withdrew. None
# may come back outside the F-5 addenda.
WITHDRAWN = list(_rc15.WITHDRAWN) + [
    ("CX-A", "the test that could have killed it"),
    ("CX-A", "confirmed it for the wrong reason"),
    ("CX-A", "The test this derivation has to pass"),
    ("CX-A", "The valid test uses only"),
    ("CX-B", "it would be the *worse* policy"),
    ("CX-B", "would mean serving obsolete digests"),
    ("CX-B", "including a correct one"),
    ("CX-B", "It is the corpus that is starved"),
    ("CX-C", "**unreachability:**"),
    ("CX-C", "drops below the selection cut"),
    ("CX-C", "Proposition 1 biting in the opposite"),
    ("CX-C", "split into opposite mechanisms"),
    ("CX-D", "rises and never falls"),
    ("CX-D", "`0.20 · log1p(access_count)/log(1000)`"),
    ("FB-A", "(The 20.5 days, the 1,971 and the 10,926 have no preserved artifact.)"),
    ("FB-A", "the 5.6× partial-day reading and the 1,971, 10,926 and 20.5 days"),
    ("FB-B", "including the three dated 2026-10-05"),
]
assert len(WITHDRAWN) == 72, f"expected 72 withdrawn phrasings, got {len(WITHDRAWN)}"


def cut_addendum(new):
    n = new.count(RC16_ADDENDUM)
    if n != 1:
        return new, f"rc16 addendum header occurs {n} times (expected 1)"
    a = new.find(RC16_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r15 = new.find(RC15_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc16 addendum"
    if r15 < 0 or r15 > a:
        return new, "rc16 addendum is not after the rc15 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc16 addendum and '## Open items'"
    return new[:a].rstrip("\n") + "\n" + new[b:], None


def compare(old, new, deposit=None):
    results = {}
    stripped, problem = cut_addendum(new)
    results["addendum"] = (problem is None, 1, problem or "")
    eo, en = extract(old), extract(stripped)
    for key, decl in (("numbers", D_NUMBERS), ("footnotes", D_FOOTNOTES), ("refs", D_REFS),
                      ("code", D_CODE), ("links", D_LINKS)):
        actual = delta(eo[key], en[key])
        want = Counter({k: v for k, v in declared_counter(decl).items() if v})
        ok = actual == want
        detail = ""
        if not ok:
            undeclared = {k: v for k, v in actual.items() if want.get(k) != v}
            missing = {k: v for k, v in want.items() if actual.get(k) != v}
            detail = f"undeclared/other={undeclared} declared-not-seen={missing}"
        results[key] = (ok, len(decl), detail)
    for key, decl in (("headings", D_HEADINGS), ("tables", D_TABLES)):
        expect, bad = list(eo[key]), []
        for fid, o, n in decl:
            if expect.count(o) != 1:
                bad.append(f"{fid}: OLD line occurs {expect.count(o)} times")
                continue
            expect[expect.index(o)] = n
        if expect != en[key]:
            diffs = [(i, x[:80], y[:80]) for i, (x, y) in enumerate(zip(expect, en[key])) if x != y][:3]
            bad.append(f"len {len(expect)}->{len(en[key])}; first diffs {diffs}")
        results[key] = (not bad, len(decl), "; ".join(bad))

    # history: the addenda rc5..rc15 are byte-identical (rc16 corrects none of them)
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    ho, hn = region(old, ADDENDA_START, OPEN_ITEMS), region(stripped, ADDENDA_START, OPEN_ITEMS)
    bad = []
    if ho is None or hn is None or ho != hn:
        bad.append("F-5 addenda rc5..rc15 differ or not found")
    for hdr in (RC14_ADDENDUM, RC15_ADDENDUM):
        if stripped.count(hdr) != 1:
            bad.append(f"{hdr!r} occurs {stripped.count(hdr)} times (expected 1)")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc15 counts + declared delta must hold in rc16, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc15 has {co[q]}, declared delta "
                       f"{D_QUALIFIERS.get(q, (0, 'none'))[0]:+d})")
    abstract = norm(section(stripped, "## Abstract", "## 1. Introduction"))
    s31 = norm(section(stripped, "### 3.1 ", "### 3.2 "))
    if SCOPE_FULL not in abstract:
        bad.append("full scope clause missing from the Abstract")
    if SCOPE_FULL not in s31:
        bad.append("full scope clause missing from §3.1")
    if stripped.count(NO_RECORD_DEF) != 1 or NO_RECORD_DEF not in section(stripped, "### 3.1 ", "### 3.2 "):
        bad.append("no-record is not defined exactly once, in §3.1")
    results["qualifiers"] = (not bad, len(QUALIFIERS), "; ".join(bad))

    # classes (carried) and withdrawn (carried + extended), both outside the F-5 addenda
    body, found = outside_addenda(new)
    residual = [] if found else ["F-5 addenda region not found"]
    for fid, pat in FORBIDDEN:
        for m in re.finditer(pat, body, re.I):
            residual.append(f"{fid} /{pat}/ at body line {body.count(chr(10), 0, m.start()) + 1}: {m.group(0)!r}")
    results["classes"] = (not residual, len(FORBIDDEN), "; ".join(residual))
    nbody = norm(body)
    back = [f"{fid}: {p!r}" for fid, p in WITHDRAWN if norm(p).lower() in nbody.lower()]
    results["withdrawn"] = (not back and found, len(WITHDRAWN), "; ".join(back))

    d = prose_dashes(stripped)
    results["dashes"] = (len(d) <= PROSE_DASH_MAX, len(d),
                         "" if len(d) <= PROSE_DASH_MAX else f"{len(d)} > {PROSE_DASH_MAX} at lines {d[:10]}")
    if deposit is None:
        results["deposit"] = (False, 0, "deposit copy not found")
    else:
        same = deposit == new
        results["deposit"] = (same, len(deposit), "" if same else "deposit copy differs from NEW")
    return results


def report(results, label):
    print(f"== {label}")
    for key, (ok, size, detail) in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key:<10} n={size}" + (f"  {detail[:500]}" if detail else ""))
    allok = all(ok for ok, _, _ in results.values())
    print(f"  => {'PARITY OK' if allok else 'PARITY BROKEN'}")
    return allok


R2_SLOTS = "the 3 shared slots are what `mainTarget` leaves after the agent quota"
CX7_S1 = "concentrate. Uniform serving is used only as a capacity reference; its effect on agent utility"
CXA_S1 = "All 20 entries observed at saturation had an exit in the same stratum. That matching check is an"
CXB_F1 = "produces ≫ 1, whatever its effect on agent utility. A ratio near 1 would indicate little"
CXC_OPEN = "arms. The recorded outputs distinguish the following cases:"
CXD_ACC = "counter: it is non-decreasing and capped at 0.20."
FBA_S431 = "10,899 `sessions/%` count, the 20.5 days, the 1,971 and the 10,926 have no preserved artifact.)"


def main(argv):
    selftest = "--selftest" in argv
    dep_p = DEFAULT_DEPOSIT
    args = []
    it = iter(argv)
    for a in it:
        if a == "--deposit":
            dep_p = Path(next(it))
        elif not a.startswith("--"):
            args.append(a)
    old_p = Path(args[0]) if args else DEFAULT_OLD
    new_p = Path(args[1]) if len(args) > 1 else DEFAULT_NEW
    try:
        old, new = old_p.read_text(), new_p.read_text()
    except OSError as e:
        print(e)
        return 2
    deposit = dep_p.read_text() if dep_p.exists() else None
    print(f"OLD {old_p}\nNEW {new_p}\nDEPOSIT {dep_p}")
    base_ok = report(compare(old, new, deposit), "baseline OLD vs NEW")
    if not selftest:
        return 0 if base_ok else 1
    if not base_ok:
        print("SELFTEST: baseline does not pass; mutations not meaningful")
        return 1
    rc12_line = "review found no wrong number in rc11. What changed:"
    mutations = [
        ("declared number changed (FB-B: four -> five in Appendix D)", "numbers",
         lambda t: sub_at(t, "(including the four cited here", "(including the five cited here")),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("CX-D cap dropped (declared 0.20 not seen)", "numbers",
         lambda t: sub_at(t, CXD_ACC, "counter: it is non-decreasing and capped.")),
        ("unit mutation is NOT caught (documented limit, as in rc15) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("heading reverted (CX-A sweep, §5.6)", "headings",
         lambda t: t.replace("### 5.6 A same-stratum matching check on recorded quantities",
                             "### 5.6 The test this derivation has to pass", 1)),
        ("§ reference in prose (DS3 pointer §3.1 -> §3.2)", "refs",
         lambda t: sub_at(t, "the absence of a record in both (§3.1),", "the absence of a record in both (§3.2),")),
        ("§ reference (CX-A pointer §5.2 dropped)", "refs",
         lambda t: sub_at(t, "not a falsifier of Proposition 1 (§5.2, §5.6).",
                          "not a falsifier of Proposition 1 (§5.6).")),
        ("code span (CX-C hour-control artifact dropped)", "code",
         lambda t: sub_at(t, "remain outside the control (`out/gran3-hora.json`). These",
                          "remain outside the control. These")),
        ("code span (CX-D formula reverted)", "code",
         lambda t: sub_at(t, "`0.20 · clamp01(log1p(access_count)/log(1000))`",
                          "`0.20 · log1p(access_count)/log(1000)`")),
        ("table row reverted (CX-A sweep, §6 'the valid test')", "tables",
         lambda t: t.replace("The check that replaced it uses only **recorded** quantities and is not a falsifier (§5.6) |",
                             "The valid test uses only **recorded** quantities (§5.6) |", 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc12 addendum edited", "history",
         lambda t: t.replace(rc12_line, rc12_line.replace("no wrong number", "no incorrect number"), 1)),
        ("history: rc15 addendum edited (now frozen)", "history",
         lambda t: t.replace("`churn` (CX6) counts the treated-only ids", "`churn` (CX6) counts the treated ids", 1)),
        ("history: rc15 addendum header duplicated", "history",
         lambda t: t.replace(RC16_ADDENDUM, RC15_ADDENDUM + " " + RC16_ADDENDUM, 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("qualifier dropped: 'with eligibility held fixed'", "qualifiers",
         lambda t: sub_at(t, "with eligibility held fixed, other designations", "with eligibility fixed, other designations")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R11-2 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("are what", "are taken by the high-pain floor, what"))),
        ("DS6 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, "they fill the three shared main-pool slots", "they fill the three corpus-wide slots")),
        ("CX7 (rc15) withdrawn wording back in §1 (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, CX7_S1, CX7_S1.replace("concentrate. Uniform", "concentrate; serving memory at random would be worse. Uniform"))),
        ("CX-A withdrawn wording back in §1 (no token changes)", "withdrawn",
         lambda t: sub_at(t, CXA_S1, CXA_S1.replace("All 20 entries", "The prediction survived the test that could have killed it. All 20 entries"))),
        ("CX-B withdrawn wording back in F-1 (no token changes)", "withdrawn",
         lambda t: sub_at(t, CXB_F1, CXB_F1.replace("whatever its effect on agent utility", "including a correct one"))),
        ("CX-B sweep withdrawn wording back in the title note (no token changes)", "withdrawn",
         lambda t: t.replace("It is the corpus that largely goes without an exposure record, not the coverage channel,",
                             "It is the corpus that is starved, not the coverage,", 1)),
        ("CX-C withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, CXC_OPEN, "arms. As measured, the lost states split into opposite mechanisms:")),
        ("CX-D withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, CXD_ACC, "counter: it rises and never falls, capped at 0.20.")),
        ("FB-A flag reverted in §4.3.1", "withdrawn",
         lambda t: sub_at(t, FBA_S431, "20.5 days, the 1,971 and the 10,926 have no preserved artifact.)")),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc16 addendum removed", "addendum", lambda t: t.replace(RC16_ADDENDUM, "**Note, rc16 (2026-10-05)", 1)),
    ]
    ok = True
    for name, expect, mut in mutations:
        m = mut(new)
        if m == new:
            print(f"SELFTEST mutation '{name}': did not apply -> MISSED")
            ok = False
            continue
        res = compare(old, m, m)
        failed = sorted(k for k, (good, _, _) in res.items() if not good)
        if expect is None:
            good = not failed
            print(f"SELFTEST mutation '{name}': fails on {failed} -> {'AS DOCUMENTED' if good else 'UNEXPECTED'}")
        else:
            good = expect in failed
            print(f"SELFTEST mutation '{name}': fails on {failed} (expect {expect}) -> {'BITES' if good else 'MISSED'}")
        ok &= good
    dep_mut = new.replace("reserved before deposit; the record is published", "reserved at deposit; the record is published", 1)
    res = compare(old, new, dep_mut)
    bit = dep_mut != new and not res["deposit"][0] and all(g for k, (g, _, _) in res.items() if k != "deposit")
    print(f"SELFTEST mutation 'deposit copy diverges': fails on "
          f"{sorted(k for k, (g, _, _) in res.items() if not g)} (expect deposit) -> {'BITES' if bit else 'MISSED'}")
    ok &= bit
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
