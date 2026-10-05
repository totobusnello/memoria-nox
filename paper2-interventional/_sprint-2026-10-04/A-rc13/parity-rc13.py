#!/usr/bin/env python3
"""Parity check rc12 -> rc13 of Paper A after the Codex and DeepSeek reviews of rc12.

Usage:
    python3 parity-rc13.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc13.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc13 applies the findings of `_sprint-2026-10-04/REVIEW-A-rc12-2026-10-05.md`: Codex C1, C2 and
DeepSeek DS1..DS6 (IDs as in `APPLY-A-rc13.md`). rc13 may change numbers, references, code spans
and one table row, but only the ones a finding declares. The F-5 "Addendum, rc13" is cut out of
NEW (between its header and "## Open items") before the delta checks; the "addendum" check
requires that it exists exactly once, right after the rc12 addendum and right before
"## Open items".

Checks, OLD vs NEW-without-the-rc13-addendum (the extractors come from A-rc12/parity-rc12.py,
which takes them from A-rc11, A-rc10 and A-rc9, so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings == NEW headings, in order (no heading changes in rc13)
  tables      OLD table rows with the DECLARED replacement applied == NEW table rows, in order
  history     F-5 addenda rc5..rc12 byte-identical (no addendum edit in rc13)
  qualifiers  carried: every rc6-rc12 scope qualifier keeps its rc12 count (outside the addenda)
              and is >= 1; full scope clause in the Abstract and in §3.1; *no-record* defined
              exactly once, in §3.1
  classes     carried: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py occurs in NEW
              outside the F-5 addenda
  withdrawn   carried and extended: none of the 10 phrasings withdrawn in rc11/rc12, nor the 10
              rc12 phrasings withdrawn here, occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc12)
  addendum    the rc13 addendum exists exactly once, in place
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
DEFAULT_OLD = SPRINT / "A-v1.1-rc12.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc13.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "MANUSCRIPT-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc12", SPRINT / "A-rc12" / "parity-rc12.py")
_rc12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc12)
FORBIDDEN = list(_rc12.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc12.extract, _rc12.norm, _rc12.outside_addenda, _rc12.prose_dashes
QUALIFIERS = list(_rc12.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc12.SCOPE_FULL, _rc12.NO_RECORD_DEF
section, declared_counter, delta = _rc12.section, _rc12.declared_counter, _rc12.delta
first_prose, sub_at, qualifier_counts = _rc12.first_prose, _rc12.sub_at, _rc12.qualifier_counts

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC12_ADDENDUM = "**Addendum, rc12 (2026-10-05)"
RC13_ADDENDUM = "**Addendum, rc13 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD).
# DS1 = the frozen set: §1 calendar item, §1 "that batch belongs to the second", §2 bullet,
#       §4.3.1 sentence on the batch (BATCH-CYCLE-2026-08-29.json);
# DS5 = §1 parenthesis naming the two sub-pools; DS2 = Abstract; DS6 = §1 slots sentence;
# DS3 = §2 no-record sentence; DS4 = §4.3.1 table header and note; C1 = §4.3.2 (no token);
# C1-sweep = §9 pin sentence; C2 = §4.3.1 fidelity sentence.
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    # DS2 Abstract: 'lifting it removes only one of the three from the main set (§4.3.2)'
    ("DS2 'one of the three'", "three", +1),
    ("DS2 pointer '(§4.3.2)'", "4.3.2", +1),
    # DS6 §1: 'the three shared main-pool slots' / 'one of the three' replace 'all three corpus-wide'
    ("DS6 §1 slots sentence", "three", +1),
    # DS5 §1: 'on 2026-08-26 to 08-29 its per-agent sub-pool held 0 eligible chunks and its
    # global sub-pool 108, §4.3.1'
    ("DS5 '2026-08-26 to 08-29'", "2026", +1),
    ("DS5 '2026-08-26 to 08-29'", "08", +2),
    ("DS5 '2026-08-26'", "26", +1),
    ("DS5 '08-29'", "29", +1),
    ("DS5 'held 0 eligible chunks'", "0", +1),
    ("DS5 'global sub-pool 108'", "108", +1),
    ("DS5 pointer '§4.3.1'", "4.3.1", +1),
    # DS1 §1: 'the batch of 2026-08-21 to 08-22 was served at 108 distinct chunks a day (109 on
    # 2026-08-26), ... from 2026-08-23 to 2026-08-29 (`BATCH-CYCLE-2026-08-29.json`)'; and
    # 'five consecutive days' / 'the five-day observation' withdrawn
    ("DS1 §1 four dates + the file name in code", "2026", +5),
    ("DS1 §1 four dates + the file name in code", "08", +6),
    ("DS1 §1 '2026-08-21'", "21", +1),
    ("DS1 §1 '08-22'", "22", +1),
    ("DS1 §1 '2026-08-23'", "23", +1),
    ("DS1 §1 '2026-08-26'", "26", +1),
    ("DS1 §1 '2026-08-29' + file name", "29", +2),
    ("DS1 §1 '108 distinct chunks a day'", "108", +1),
    ("DS1 §1 '(109 on 2026-08-26)'", "109", +1),
    ("DS1 §1 'five consecutive days' and 'the five-day observation' removed", "five", -2),
    # DS1 §2: 'The frozen days that §1 cites (2026-08-23 to 2026-08-29)'
    ("DS1 §2 two dates", "2026", +2),
    ("DS1 §2 two dates", "08", +2),
    ("DS1 §2 '2026-08-23'", "23", +1),
    ("DS1 §2 '2026-08-29'", "29", +1),
    ("DS1 §2 'The five consecutive days' removed", "five", -1),
    # DS1 §4.3.1: 'the batch of 2026-08-21 to 08-22 was served at 108 distinct chunks a day from
    # 2026-08-22 to 2026-08-29 (109 on 2026-08-26), and its minimum served age rose by exactly
    # +1.00 per day, from 0.92 on 2026-08-23 to 6.92 on 2026-08-29 (`BATCH-CYCLE-...`)'
    ("DS1 §4.3.1 six dates + the file name in code", "2026", +7),
    ("DS1 §4.3.1 seven 08s + the file name in code", "08", +8),
    ("DS1 §4.3.1 '2026-08-21'", "21", +1),
    ("DS1 §4.3.1 '08-22', '2026-08-22'", "22", +2),
    ("DS1 §4.3.1 '2026-08-23'", "23", +1),
    ("DS1 §4.3.1 '2026-08-26'", "26", +1),
    ("DS1 §4.3.1 '2026-08-29' x2 + file name", "29", +3),
    ("DS1 §4.3.1 '108 distinct chunks a day'", "108", +1),
    ("DS1 §4.3.1 '(109 on 2026-08-26)'", "109", +1),
    ("DS1 §4.3.1 '+1.00 per day'", "1.00", +1),
    ("DS1 §4.3.1 'from 0.92'", "0.92", +1),
    ("DS1 §4.3.1 'to 6.92'", "6.92", +1),
    ("DS1 §4.3.1 'the five days without new items' removed", "five", -1),
    # DS3 §2: 'the absence of a record in both (§3.1)'
    ("DS3 pointer '(§3.1)'", "3.1", +1),
    # DS4 note: 'every 672-brief day from 2026-08-24 to 2026-09-07 ...; on 2026-09-03 (441 briefs)
    # the rows that read 672 read 441 and F5 reads 126'
    ("DS4 note three dates", "2026", +3),
    ("DS4 note '2026-08-24'", "08", +1),
    ("DS4 note '2026-08-24'", "24", +1),
    ("DS4 note '2026-09-07', '2026-09-03'", "09", +2),
    ("DS4 note '2026-09-07'", "07", +1),
    ("DS4 note '2026-09-03'", "03", +1),
    ("DS4 note '672-brief day', 'read 672'", "672", +2),
    ("DS4 note '(441 briefs)', 'read 441'", "441", +2),
    ("DS4 note 'F5 reads 126'", "126", +1),
    # C2 §4.3.1: '9 or 10 ids. On 2026-09-03 and 2026-09-07, ... all 10 served ids'
    ("C2 '9 or 10 ids', 'all 10 served ids'", "10", +2),
    ("C2 '2026-09-03 and 2026-09-07'", "2026", +2),
    ("C2 '2026-09-03 and 2026-09-07'", "09", +2),
    ("C2 '2026-09-03'", "03", +1),
    ("C2 '2026-09-07'", "07", +1),
    # C1-sweep §9: 'for one of the three (§4.3.2)'
    ("C1-sweep §9 'one of the three'", "three", +1),
    ("C1-sweep §9 pointer '(§4.3.2)'", "4.3.2", +1),
]
D_FOOTNOTES = []
D_REFS = [
    ("DS2 Abstract pointer to §4.3.2 (lifting the pin removes one of the three)", "§4.3.2", +1),
    ("C1-sweep §9 pointer to §4.3.2", "§4.3.2", +1),
    ("DS5 §1 pointer to §4.3.1 (the sub-pool table)", "§4.3.1", +1),
    ("DS3 §2 pointer to §3.1 (no-record)", "§3.1", +1),
]
D_CODE = [
    ("DS1 §1 artifact", "`BATCH-CYCLE-2026-08-29.json`", +1),
    ("DS1 §4.3.1 artifact", "`BATCH-CYCLE-2026-08-29.json`", +1),
    ("C2 'treated `fresh_added`' / 'null `fresh_added`' (one span replaced, two added)", "`fresh_added`", +1),
    ("DS4 note artifact", "`out-ord0826.json`", +1),
    ("DS4 note field", "`leave_one_out`", +1),
]
D_LINKS = []
D_HEADINGS = []
D_TABLES = [
    ("DS4 §4.3.1 filter table header",
     "| lifted | briefs whose main set changes (of 672) | distinct main chunks per day |",
     "| lifted | briefs whose main set changes (of a 672-brief day) | distinct main chunks per day |"),
]

# Declared qualifier deltas (rc13 - rc12): none.
D_QUALIFIERS = {}

# Withdrawn phrasings: the 10 of rc12 (carried), plus the 10 that this review withdrew. None may
# come back outside the F-5 addenda.
WITHDRAWN = list(_rc12.WITHDRAWN) + [
    ("DS1", "five consecutive days with zero new items"),
    ("DS1", "the five-day observation belongs to the first"),
    ("DS1", "The five consecutive days that §1 cites"),
    ("DS5", "the pool is empty and the channel serves"),
    ("DS6", "corpus-wide slots"),
    ("DS2", "The high-pain pin keeps them in every brief"),
    ("DS3", '"Never exposed" is therefore a verifiable property'),
    ("C1", "Search traffic is one condition of their rank"),
    ("C2", "so the subtraction leaves 9 ids ("),
    ("C1-sweep", "the high-pain pin holds in every brief what that score placed there"),
]
assert len(WITHDRAWN) == 20, f"expected 20 withdrawn phrasings, got {len(WITHDRAWN)}"


def cut_addendum(new):
    n = new.count(RC13_ADDENDUM)
    if n != 1:
        return new, f"rc13 addendum header occurs {n} times (expected 1)"
    a = new.find(RC13_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r12 = new.find(RC12_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc13 addendum"
    if r12 < 0 or r12 > a:
        return new, "rc13 addendum is not after the rc12 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc13 addendum and '## Open items'"
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

    # history: the addenda rc5..rc12 are byte-identical (rc13 edits none of them)
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    ho, hn = region(old, ADDENDA_START, OPEN_ITEMS), region(stripped, ADDENDA_START, OPEN_ITEMS)
    bad = []
    if ho is None or hn is None or ho.rstrip("\n") != hn.rstrip("\n"):
        bad.append("F-5 addenda rc5..rc12 differ or not found")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc12 counts must survive in rc13, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc12 has {co[q]}, declared delta "
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
DS1_43 = "2026-08-23 to 6.92 on 2026-08-29 (`BATCH-CYCLE-2026-08-29.json`)."


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
    row_new = D_TABLES[0][2]
    mutations = [
        ("declared number changed (DS1: 6.92 -> 6.93)", "numbers",
         lambda t: sub_at(t, DS1_43, DS1_43.replace("6.92", "6.93"))),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("C2 reverted to '9 ids' (declared '10' not seen)", "numbers",
         lambda t: sub_at(t, "so the subtraction leaves 9 or 10 ids.", "so the subtraction leaves 9 ids.")),
        ("unit mutation is NOT caught (documented limit, as in rc12) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("§ reference in prose (DS3 pointer §3.1 -> §3.2)", "refs",
         lambda t: sub_at(t, "the absence of a record in both (§3.1),", "the absence of a record in both (§3.2),")),
        ("code span (DS1 §4.3.1 artifact name)", "code",
         lambda t: sub_at(t, DS1_43, DS1_43.replace("`BATCH-CYCLE-2026-08-29.json`", "`BATCH-CYCLE.json`"))),
        ("table row: DS4 header reverted", "tables", lambda t: t.replace(row_new, D_TABLES[0][1], 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc12 addendum edited", "history",
         lambda t: t.replace(rc12_line, rc12_line.replace("no wrong number", "no incorrect number"), 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("qualifier dropped: phase 0 (carried)", "qualifiers",
         lambda t: sub_at(t, "placed in phase 0 before the quota pass", "placed first, before the quota pass")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R10-5 withdrawn wording back (carried)", "withdrawn",
         lambda t: sub_at(t, "places them first, in the three shared main-pool slots",
                          "placed there by the high-pain floor, in the three shared main-pool slots")),
        ("R11-2 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("are what", "are taken by the high-pain floor, what"))),
        ("DS2 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "The high-pain pin places them first in every brief",
                          "The high-pain pin keeps them in every brief")),
        ("DS6 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "in the three shared main-pool slots", "in the three corpus-wide slots")),
        ("C1 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: t.replace("Tracked search traffic is necessary for their observed salience ranks in the measured\n"
                             "counterfactual.", "Search traffic is one condition of their rank.", 1)),
        ("C1-sweep §9 withdrawn wording back", "withdrawn",
         lambda t: sub_at(t, "The high-pain pin, which places them first in every brief, protects what that score placed there",
                          "The high-pain pin holds in every brief what that score placed there")),
        ("DS1 withdrawn wording back", "withdrawn",
         lambda t: sub_at(t, "and that batch belongs to the second.",
                          "and the five-day observation belongs to the first.")),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc13 addendum removed", "addendum", lambda t: t.replace(RC13_ADDENDUM, "**Note, rc13 (2026-10-05)", 1)),
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
