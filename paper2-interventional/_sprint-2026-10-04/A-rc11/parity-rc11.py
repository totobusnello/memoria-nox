#!/usr/bin/env python3
"""Parity check rc10 -> rc11 of Paper A after the Fable regression review of rc10.

Usage:
    python3 parity-rc11.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc11.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc11 applies the eight findings of `_sprint-2026-10-04/REVIEW-A-rc10-2026-10-05.md` (numbered
1-8 there; "R10-n" here). Like rc10 it may change numbers, references, code spans and one table
row, but only the ones a finding declares. The F-5 "Addendum, rc11" is cut out of NEW (between its
header and "## Open items") before the delta checks; the "addendum" check requires that it exists
exactly once, right after the rc10 addendum and right before "## Open items".

Checks, OLD vs NEW-without-the-rc11-addendum (the extractors are imported from
A-rc10/parity-rc10.py, which imports them from A-rc9/parity-rc9.py, so the tokenisation cannot
drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings == NEW headings, in order (no heading changes in rc11)
  tables      OLD table rows with the DECLARED replacement applied == NEW table rows, in order
  history     F-5 addenda rc5..rc9 byte-identical; the rc10 addendum byte-identical after the one
              declared R10-7 replacement
  qualifiers  carried from parity-rc10: every rc6-rc10 scope qualifier keeps its rc10 count
              (outside the addenda) plus the DECLARED delta (one: R10-2 adds a "not established")
              and is >= 1; full scope clause in the Abstract and in §3.1;
              *no-record* defined exactly once, in §3.1
  classes     carried from parity-rc10: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py
              occurs in NEW outside the F-5 addenda
  withdrawn   new in rc11: none of the 8 rc10 phrasings that the review withdrew occurs in NEW
              outside the F-5 addenda (wording regressions that change no token)
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc10)
  addendum    the rc11 addendum exists exactly once, in place
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
DEFAULT_OLD = SPRINT / "A-v1.1-rc10.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc11.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "MANUSCRIPT-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc10", SPRINT / "A-rc10" / "parity-rc10.py")
_rc10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc10)
FORBIDDEN = list(_rc10.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc10.extract, _rc10.norm, _rc10.outside_addenda, _rc10.prose_dashes
QUALIFIERS = list(_rc10.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc10.SCOPE_FULL, _rc10.NO_RECORD_DEF
section, declared_counter, delta = _rc10.section, _rc10.declared_counter, _rc10.delta
first_prose, sub_at = _rc10.first_prose, _rc10.sub_at

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC10_ADDENDUM = "**Addendum, rc10 (2026-10-05)"
RC11_ADDENDUM = "**Addendum, rc11 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD). Net, because a token can be removed by
# one finding and added by another; the justification says who did what.
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    ("R10-2 'diagnosed on 2026-08-22' -1, '2026-08-22 epoch' +1; R10-7 '2026-09-03 and 2026-09-07' +2; "
     "R10-1 table row 'mismatch of 2026-08-22' +1", "2026", +3),
    ("R10-2 -1 (diagnosed on) +1 (08-21) +1 (08-22) +1 (part of 08-23) +1 (epoch); R10-1 +1", "08", +4),
    ("R10-2 -1 (diagnosed on) +1 (08-22 in the slot list) +1 (epoch); R10-1 +1", "22", +2),
    ("R10-2 '285042 in that slot on 08-21'", "21", +1),
    ("R10-2 'part of 08-23'", "23", +1),
    ("R10-7 09-03, 09-07", "09", +2),
    ("R10-7 09-03", "03", +1),
    ("R10-7 09-07", "07", +1),
    ("R10-2 'production served 285042 ... kept 285042' (one already there)", "285042", +2),
    ("R10-2 the first criterion, now stated twice (first and stricter)", "85.8%", +1),
    ("R10-2 the first criterion, now stated twice (first and stricter)", "85.7%", +1),
    ("R10-2 stricter criterion on 2026-08-23 (472/560)", "84.3%", +1),
    ("R10-3 §9 'ranks 1, 3 and 4'", "1", +1),
    ("R10-3 §9 'ranks 1, 3 and 4'", "3", +1),
    ("R10-3 §9 'ranks 1, 3 and 4'", "4", +1),
    ("R10-4 '112241 and 116467 stay'", "112241", +1),
    ("R10-4 '112241 and 116467 stay'", "116467", +1),
    ("R10-4 'for one of the three'", "three", +1),
    ("R10-5 §1 pointer to §4.3.2", "4.3.2", +1),
    ("R10-6 Open items 5 '(§5.6)'", "5.6", +1),
    ("R10-6 Open items 5 'carries the 10 entries'", "10", +1),
    ("R10-6 Open items 5 `ts-350.txt` named a second time", "350", +1),
    ("R10-8 'The two sentences' -> 'The capacity figure and the 83.78%'", "two", -1),
    ("R10-8 'The two sentences' -> 'The capacity figure and the 83.78%'", "83.78%", +1),
]
D_FOOTNOTES = []
D_REFS = [
    ("R10-5 §1 pointer", "§4.3.2", +1),
    ("R10-6 Open items 5 pointer", "§5.6", +1),
]
D_CODE = [
    ("R10-1 Appendix D enumeration + table row", "`A-filters-disaggregation/diag-out.txt`", +2),
    ("R10-1 table row: the script that produced it", "`diag-residual-mismatch.py`", +1),
    ("R10-7 rc10 addendum 'where `fresh_added` is null'", "`fresh_added`", +1),
    ("R10-6 Open items 5", "`ts-350.txt`", +1),
]
D_LINKS = []
D_HEADINGS = []
D_TABLES = [
    ("R10-1 Appendix D row of the filter disaggregation",
     "| main-pool filter disaggregation, and the served main set from the log (§4.3.1) | `sprint-desagrega-filtros-pool-principal.py` (`--log-only` for the log census) | `A-filters-disaggregation/out-ord0826.json` · `A-filters-disaggregation/observed-main-from-log.json` |",
     "| main-pool filter disaggregation, and the served main set from the log (§4.3.1) | `sprint-desagrega-filtros-pool-principal.py` (`--log-only` for the log census) | `A-filters-disaggregation/out-ord0826.json` · `A-filters-disaggregation/observed-main-from-log.json` · `A-filters-disaggregation/diag-out.txt` (the residual mismatch of 2026-08-22, `diag-residual-mismatch.py`) |"),
]
R7_OLD = "  id-for-id test passes in 94.3–97.9% of the briefs of each day, and every failure comes from\n"
R7_NEW = ("  id-for-id test passes in 94.3–97.9% of the briefs of each day except 2026-09-03 and "
          "2026-09-07, where `fresh_added` is null, and every failure comes from\n")

# Declared qualifier deltas (rc11 - rc10), with the finding that justifies each.
D_QUALIFIERS = {
    "not established": (+1, "R10-2: 'why production kept 285042 after the access is not established'"),
}

# rc10 phrasings the review withdrew. None may come back outside the F-5 addenda.
WITHDRAWN = [
    ("R10-2", "for briefs served before that access"),
    ("R10-2", "diagnosed on 2026-08-22"),
    ("R10-2", "Under the same criterion those"),
    ("R10-3", "keep their slots only through"),
    ("R10-4", "and it is measured as necessary:"),
    ("R10-5", "placed there by the high-pain floor"),
    ("R10-6", "The next deposit must"),
    ("R10-8", "The two sentences change universe"),
]


def cut_addendum(new):
    n = new.count(RC11_ADDENDUM)
    if n != 1:
        return new, f"rc11 addendum header occurs {n} times (expected 1)"
    a = new.find(RC11_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r10 = new.find(RC10_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc11 addendum"
    if r10 < 0 or r10 > a:
        return new, "rc11 addendum is not after the rc10 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc11 addendum and '## Open items'"
    return new[:a].rstrip("\n") + "\n" + new[b:], None


def qualifier_counts(text):
    qn = norm(outside_addenda(text)[0])
    return {q: len(re.findall(re.escape(q), qn, re.I)) for q, _, _ in QUALIFIERS}


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

    # history
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    bad = []
    ho, hn = region(old, ADDENDA_START, RC10_ADDENDUM), region(stripped, ADDENDA_START, RC10_ADDENDUM)
    if ho is None or ho != hn:
        bad.append("F-5 addenda rc5..rc9 differ or not found")
    r10o, r10n = region(old, RC10_ADDENDUM, OPEN_ITEMS), region(stripped, RC10_ADDENDUM, OPEN_ITEMS)
    if r10o is None or r10o.count(R7_OLD) != 1:
        bad.append("R10-7: the rc10 line to replace is not in OLD once")
    elif r10o.replace(R7_OLD, R7_NEW).rstrip("\n") != (r10n or "").rstrip("\n"):
        bad.append("rc10 addendum differs from OLD + the declared R10-7 replacement")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc10 counts must survive in rc11, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc10 has {co[q]}, declared delta "
                       f"{D_QUALIFIERS.get(q, (0, 'none'))[0]:+d}: {D_QUALIFIERS.get(q, (0, 'no rc11 finding'))[1]})")
    abstract = norm(section(stripped, "## Abstract", "## 1. Introduction"))
    s31 = norm(section(stripped, "### 3.1 ", "### 3.2 "))
    if SCOPE_FULL not in abstract:
        bad.append("full scope clause missing from the Abstract")
    if SCOPE_FULL not in s31:
        bad.append("full scope clause missing from §3.1")
    if stripped.count(NO_RECORD_DEF) != 1 or NO_RECORD_DEF not in section(stripped, "### 3.1 ", "### 3.2 "):
        bad.append("no-record is not defined exactly once, in §3.1")
    results["qualifiers"] = (not bad, len(QUALIFIERS), "; ".join(bad))

    # classes (carried) and withdrawn (new), both outside the F-5 addenda
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
    rc9_line = "`_sprint-2026-10-04/A-rc9/parity-rc9.py` checks, against rc8: the multisets of"
    row_new = D_TABLES[0][2]
    mutations = [
        ("declared number changed (R10-2: 84.3% -> 84.4%)", "numbers", lambda t: sub_at(t, "85.7% and 84.3%", "85.7% and 84.4%")),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("unit mutation is NOT caught (documented limit, as in rc10) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("§ reference in prose (R10-5 pointer)", "refs",
         lambda t: sub_at(t, "already placed in the brief (§4.3.2)", "already placed in the brief (§4.3.3)")),
        ("code span (R10-2 artifact path)", "code",
         lambda t: sub_at(t, "`A-filters-disaggregation/diag-out.txt`,", "`A-filters-disaggregation/diag-out.json`,")),
        ("table row: R10-1 reverted", "tables", lambda t: t.replace(row_new, D_TABLES[0][1], 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc9 addendum edited", "history",
         lambda t: t.replace(rc9_line, rc9_line.replace("checks, against rc8", "checks, against rc7"), 1)),
        ("history: R10-7 replacement reverted", "history", lambda t: t.replace(R7_NEW, R7_OLD, 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("R10-2 'not established' dropped (declared +1 not seen)", "qualifiers",
         lambda t: t.replace("after the access is not\nestablished)", "after the access is unknown)", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R10-2 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "so the reconstruction ranks 298048 above 285042, while",
                          "so for briefs served before that access the reconstruction ranks 298048 above 285042, while")),
        ("R10-3 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "the three constant chunks hold ranks 1, 3 and 4 by salience only through",
                          "the three constant chunks keep their slots only through ranks 1, 3 and 4 by salience")),
        ("R10-5 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "held there by the high-pain pin", "placed there by the high-pain floor")),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc11 addendum removed", "addendum", lambda t: t.replace(RC11_ADDENDUM, "**Note, rc11 (2026-10-05)", 1)),
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
    bit = not res["deposit"][0] and all(g for k, (g, _, _) in res.items() if k != "deposit")
    print(f"SELFTEST mutation 'deposit copy diverges': fails on "
          f"{sorted(k for k, (g, _, _) in res.items() if not g)} (expect deposit) -> {'BITES' if bit else 'MISSED'}")
    ok &= bit
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
