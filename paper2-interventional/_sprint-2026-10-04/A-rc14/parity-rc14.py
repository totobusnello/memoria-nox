#!/usr/bin/env python3
"""Parity check rc13 -> rc14 of Paper A after the Codex review of rc13.

Usage:
    python3 parity-rc14.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc14.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc14 applies the findings of `_sprint-2026-10-04/REVIEW-A-rc13-2026-10-05.md`: Codex CR1, CR2
(IDs as in `APPLY-A-rc14.md`), plus V10, the correction of where the withdrawn five-day series
lived (the rc13 addendum said "the v1.0 text"; it was a pre-deposit draft, and v1.0 carried the
statement in §1 and a pointer in §2). rc14 may change numbers, references and code spans, but only
the ones a finding declares. The F-5 "Addendum, rc14" is cut out of NEW (between its header and
"## Open items") before the delta checks; the "addendum" check requires that it exists exactly
once, right after the rc13 addendum and right before "## Open items".

The rc13 addendum is part of the same unpublished version (v1.1 draft), so rc14 corrects two of
its items in place; those edits are inside the delta checks and are declared like any other.

Checks, OLD vs NEW-without-the-rc14-addendum (the extractors come from A-rc13/parity-rc13.py,
which takes them from A-rc12, A-rc11, A-rc10 and A-rc9, so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings == NEW headings, in order (no heading changes in rc14)
  tables      OLD table rows == NEW table rows, in order (no table changes in rc14)
  history     F-5 addenda rc5..rc12 byte-identical; the rc13 addendum occurs exactly once
  qualifiers  carried: every rc6-rc13 scope qualifier keeps its rc13 count (outside the addenda)
              plus the DECLARED delta, and is >= 1; full scope clause in the Abstract and in
              §3.1; *no-record* defined exactly once, in §3.1
  classes     carried: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py occurs in NEW
              outside the F-5 addenda
  withdrawn   carried and extended: none of the 20 phrasings withdrawn in rc11..rc13, nor the 8
              rc13 phrasings withdrawn here, occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc13)
  addendum    the rc14 addendum exists exactly once, in place
  deposit     deposit/paperA-v1.1/MANUSCRIPT-v1.1.md is byte-identical to NEW

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
DEFAULT_OLD = SPRINT / "A-v1.1-rc13.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc14.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "MANUSCRIPT-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc13", SPRINT / "A-rc13" / "parity-rc13.py")
_rc13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc13)
FORBIDDEN = list(_rc13.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc13.extract, _rc13.norm, _rc13.outside_addenda, _rc13.prose_dashes
QUALIFIERS = list(_rc13.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc13.SCOPE_FULL, _rc13.NO_RECORD_DEF
section, declared_counter, delta = _rc13.section, _rc13.declared_counter, _rc13.delta
first_prose, sub_at, qualifier_counts = _rc13.first_prose, _rc13.sub_at, _rc13.qualifier_counts

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC13_ADDENDUM = "**Addendum, rc13 (2026-10-05)"
RC14_ADDENDUM = "**Addendum, rc14 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD).
# CR1 = two measurements kept apart: §1 calendar item, §2 bullet, §4.3.1 sentence, rc13 addendum
#       DS1 item (COVERAGE-SET-FROM-LOG for the coverage set; BATCH-CYCLE for serves across both
#       channels, with the 109 exception);
# CR2 = "selects them in phase 0, before the quota pass": Abstract, §1, §9, rc13 addendum C1 item;
# V10 = rc13 addendum DS1 item: where v1.0 carried the withdrawn statement (§1, and §2's pointer
#       to §4.3.1), and that the table was in a pre-deposit draft, not in v1.0.
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    # CR2: 'phase 0' in the Abstract, §1, §9 and the rc13 addendum's C1 item
    ("CR2 Abstract 'selects them in phase 0'", "0", +1),
    ("CR2 §1 'selects them in phase 0'", "0", +1),
    ("CR2 §9 'which selects them in phase 0 of every brief'", "0", +1),
    ("CR2 rc13 addendum 'The pin selects them in phase 0'", "0", +1),
    # CR1 §1: 'the same 108 coverage-side ids on every day from 2026-08-23 to 2026-08-29
    # (`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`). Separately, ... contributed 108 distinct
    # chunks a day from 2026-08-22 to 2026-08-29, except 109 on 2026-08-26, ... reported to two
    # decimal places, rose from 0.92 to 6.92 days in daily increments of 1.00'
    ("CR1 §1 dates '2026-08-22', '2026-08-29' (log sentence + batch range) and the COVERAGE file", "2026", +3),
    ("CR1 §1 '2026-08-22', one extra '2026-08-29'", "08", +2),
    ("CR1 §1 'from 2026-08-22'", "22", +1),
    ("CR1 §1 extra '2026-08-29'", "29", +1),
    ("CR1 §1 'the same 108 coverage-side ids'", "108", +1),
    ("CR1 §1 'from 0.92'", "0.92", +1),
    ("CR1 §1 'to 6.92 days'", "6.92", +1),
    ("CR1 §1 'two decimal places'", "two", +1),
    ("CR1 §1 COVERAGE file name '2026-10-04'", "10", +1),
    ("CR1 §1 COVERAGE file name '2026-10-04'", "04", +1),
    # CR1 §2: '(`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`)'
    ("CR1 §2 COVERAGE file name", "2026", +1),
    ("CR1 §2 COVERAGE file name", "10", +1),
    ("CR1 §2 COVERAGE file name", "04", +1),
    # CR1 §4.3.1: 'the same 108 coverage-side ids on every day from 2026-08-23 to 2026-08-29';
    # 'reported to two decimal places'
    ("CR1 §4.3.1 'the same 108 coverage-side ids'", "108", +1),
    ("CR1 §4.3.1 '2026-08-23 to 2026-08-29'", "2026", +2),
    ("CR1 §4.3.1 '2026-08-23 to 2026-08-29'", "08", +2),
    ("CR1 §4.3.1 '2026-08-23'", "23", +1),
    ("CR1 §4.3.1 '2026-08-29'", "29", +1),
    ("CR1 §4.3.1 'two decimal places'", "two", +1),
    # CR1 rc13 addendum DS1 item: the coverage set (108 ids, COVERAGE file) and the batch serves
    # across both channels ('except 109 on 2026-08-26', 'from 0.92 to 6.92 days'); 'two
    # measurements'
    ("CR1 rc13 addendum COVERAGE file + '2026-08-26'", "2026", +2),
    ("CR1 rc13 addendum '2026-08-26'", "08", +1),
    ("CR1 rc13 addendum '2026-08-26'", "26", +1),
    ("CR1 rc13 addendum 'the same 108 coverage-side ids'", "108", +1),
    ("CR1 rc13 addendum 'except 109 on 2026-08-26'", "109", +1),
    ("CR1 rc13 addendum 'from 0.92'", "0.92", +1),
    ("CR1 rc13 addendum 'to 6.92 days'", "6.92", +1),
    ("CR1 rc13 addendum COVERAGE file name", "10", +1),
    ("CR1 rc13 addendum COVERAGE file name", "04", +1),
    ("CR1 rc13 addendum 'two measurements'", "two", +1),
    # V10 rc13 addendum: 'v1.0 stated it in §1, item 1 of the coverage channel's two reasons, and
    # its §2 said that §4.3.1 showed five consecutive days without an eligible candidate, which
    # v1.0's §4.3.1 does not show'
    ("V10 '§1, item 1'", "1", +2),
    ("V10 'its §2'", "2", +1),
    ("V10 '§4.3.1 showed', 'v1.0's §4.3.1'", "4.3.1", +2),
    ("V10 'two reasons'", "two", +1),
    ("V10 'five consecutive days without an eligible candidate'", "five", +1),
]
D_FOOTNOTES = []
D_REFS = [
    ("V10 rc13 addendum 'v1.0 stated it in §1'", "§1", +1),
    ("V10 rc13 addendum 'its §2 said'", "§2", +1),
    ("V10 rc13 addendum '§4.3.1 showed', 'v1.0's §4.3.1'", "§4.3.1", +2),
]
D_CODE = [
    ("CR1 §1 coverage-set artifact", "`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`", +1),
    ("CR1 §2 coverage-set artifact", "`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`", +1),
    ("CR1 rc13 addendum coverage-set artifact", "`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`", +1),
    ("CR1 §4.3.1 the query that does not attribute serves to a channel", "`ciclo-do-lote.py`", +1),
]
D_LINKS = []
D_HEADINGS = []
D_TABLES = []

# Declared qualifier deltas (rc14 - rc13), counted outside the addenda.
D_QUALIFIERS = {
    "phase 0": (+3, "CR2: Abstract, §1 and §9 now say the pin selects them in phase 0"),
}

# Withdrawn phrasings: the 20 of rc11..rc13 (carried), plus the 8 that this review withdrew. None
# may come back outside the F-5 addenda.
WITHDRAWN = list(_rc13.WITHDRAWN) + [
    ("CR2", "places them first"),
    ("CR2", "The high-pain pin places them first in every brief"),
    ("CR2", "which places them first in every brief"),
    ("CR1", "that batch belongs to the second"),
    ("CR1", "was served at 108 distinct chunks a day"),
    ("CR1", "rising by exactly +1.00 per day"),
    ("CR1", "rose by exactly +1.00 per day"),
    ("CR1", "the signature of a frozen set"),
]
assert len(WITHDRAWN) == 28, f"expected 28 withdrawn phrasings, got {len(WITHDRAWN)}"


def cut_addendum(new):
    n = new.count(RC14_ADDENDUM)
    if n != 1:
        return new, f"rc14 addendum header occurs {n} times (expected 1)"
    a = new.find(RC14_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r13 = new.find(RC13_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc14 addendum"
    if r13 < 0 or r13 > a:
        return new, "rc14 addendum is not after the rc13 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc14 addendum and '## Open items'"
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

    # history: the addenda rc5..rc12 are byte-identical; the rc13 addendum (same unpublished
    # version) may be corrected, but must still occur exactly once
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    ho, hn = region(old, ADDENDA_START, RC13_ADDENDUM), region(stripped, ADDENDA_START, RC13_ADDENDUM)
    bad = []
    if ho is None or hn is None or ho != hn:
        bad.append("F-5 addenda rc5..rc12 differ or not found")
    if stripped.count(RC13_ADDENDUM) != 1:
        bad.append(f"rc13 addendum header occurs {stripped.count(RC13_ADDENDUM)} times (expected 1)")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc13 counts + declared delta must hold in rc14, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc13 has {co[q]}, declared delta "
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
CR1_43 = "6.92 on 2026-08-29 in daily increments of 1.00 (`BATCH-CYCLE-2026-08-29.json`)."
CR2_ABS = "The high-pain pin selects them in phase 0, before the quota"
CR2_S1 = "selects them in phase 0, before the quota pass, and they fill the three shared main-pool slots"
CR2_S9 = "The high-pain pin, which selects them in phase 0 of every brief, before the quota pass, protects"


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
        ("declared number changed (CR1: 6.92 -> 6.93 in §4.3.1)", "numbers",
         lambda t: sub_at(t, CR1_43, CR1_43.replace("6.92", "6.93"))),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("CR1 109 exception dropped from §4.3.1 (declared '109' not seen)", "numbers",
         lambda t: sub_at(t, "2026-08-29, except 109 on 2026-08-26,", "2026-08-29,")),
        ("unit mutation is NOT caught (documented limit, as in rc13) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("§ reference in prose (DS3 pointer §3.1 -> §3.2)", "refs",
         lambda t: sub_at(t, "the absence of a record in both (§3.1),", "the absence of a record in both (§3.2),")),
        ("code span (CR1 §4.3.1 artifact name)", "code",
         lambda t: sub_at(t, CR1_43, CR1_43.replace("`BATCH-CYCLE-2026-08-29.json`", "`BATCH-CYCLE.json`"))),
        ("code span (CR1 §2 coverage-set artifact removed)", "code",
         lambda t: sub_at(t, "(`A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json`), not days without a candidate",
                          "not days without a candidate")),
        ("table row edited", "tables",
         lambda t: t.replace("| lifted | briefs whose main set changes (of a 672-brief day) |",
                             "| lifted | briefs whose main set changes (of 672) |", 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc12 addendum edited", "history",
         lambda t: t.replace(rc12_line, rc12_line.replace("no wrong number", "no incorrect number"), 1)),
        ("history: rc13 addendum header duplicated", "history",
         lambda t: t.replace(RC14_ADDENDUM, RC13_ADDENDUM + " " + RC14_ADDENDUM, 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("CR2 qualifier dropped: §9 'phase 0' (declared +3 not reached)", "qualifiers",
         lambda t: sub_at(t, CR2_S9, CR2_S9.replace("in phase 0 of every brief", "in stage 0 of every brief"))),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R11-2 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("are what", "are taken by the high-pain floor, what"))),
        ("DS6 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, "they fill the three shared main-pool slots", "they fill the three corpus-wide slots")),
        ("CR2 withdrawn wording back in the Abstract", "withdrawn",
         lambda t: sub_at(t, CR2_ABS, "The high-pain pin places them first in every brief, before the quota")),
        ("CR2 withdrawn wording back in §1", "withdrawn",
         lambda t: sub_at(t, CR2_S1, CR2_S1.replace("selects them in phase 0, before the quota pass, and they fill",
                                                    "places them first in phase 0, before the quota pass, and they fill"))),
        ("CR2 withdrawn wording back in §9", "withdrawn",
         lambda t: sub_at(t, CR2_S9, CR2_S9.replace("which selects them in phase 0 of every brief",
                                                    "which places them first in phase 0 of every brief"))),
        ("CR1 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "and the coverage-served portion of that batch belongs to the global sub-pool.",
                          "and that batch belongs to the second, the global sub-pool.")),
        ("CR1 withdrawn wording back: 'the signature of a frozen set'", "withdrawn",
         lambda t: sub_at(t, CR1_43, CR1_43[:-1] + ", the signature of a frozen set.")),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc14 addendum removed", "addendum", lambda t: t.replace(RC14_ADDENDUM, "**Note, rc14 (2026-10-05)", 1)),
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
