#!/usr/bin/env python3
"""Parity check rc11 -> rc12 of Paper A after the Fable review of rc11.

Usage:
    python3 parity-rc12.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc12.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc12 applies the findings of `_sprint-2026-10-04/REVIEW-A-rc11-2026-10-05.md` (numbered 2-4 there;
"R11-n" here). Finding 3 touches only the package manifest (build-package.py), not the text. Like
rc11, rc12 may change numbers, references, code spans and one table row, but only the ones a
finding declares. The F-5 "Addendum, rc12" is cut out of NEW (between its header and
"## Open items") before the delta checks; the "addendum" check requires that it exists exactly
once, right after the rc11 addendum and right before "## Open items".

Checks, OLD vs NEW-without-the-rc12-addendum (the extractors come from A-rc11/parity-rc11.py,
which takes them from A-rc10 and A-rc9, so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings == NEW headings, in order (no heading changes in rc12)
  tables      OLD table rows with the DECLARED replacement applied == NEW table rows, in order
  history     F-5 addenda rc5..rc11 byte-identical (no addendum edit in rc12)
  qualifiers  carried: every rc6-rc11 scope qualifier keeps its rc11 count (outside the addenda)
              and is >= 1; full scope clause in the Abstract and in §3.1; *no-record* defined
              exactly once, in §3.1
  classes     carried: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py occurs in NEW
              outside the F-5 addenda
  withdrawn   carried and extended: none of the 8 rc10 phrasings withdrawn in rc11, nor the 2 rc11
              phrasings withdrawn here, occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc11)
  addendum    the rc12 addendum exists exactly once, in place
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
DEFAULT_OLD = SPRINT / "A-v1.1-rc11.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc12.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "spare-capacity-narrow-surface-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc11", SPRINT / "A-rc11" / "parity-rc11.py")
_rc11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc11)
FORBIDDEN = list(_rc11.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc11.extract, _rc11.norm, _rc11.outside_addenda, _rc11.prose_dashes
QUALIFIERS = list(_rc11.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc11.SCOPE_FULL, _rc11.NO_RECORD_DEF
section, declared_counter, delta = _rc11.section, _rc11.declared_counter, _rc11.delta
first_prose, sub_at, qualifier_counts = _rc11.first_prose, _rc11.sub_at, _rc11.qualifier_counts

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC11_ADDENDUM = "**Addendum, rc11 (2026-10-05)"
RC12_ADDENDUM = "**Addendum, rc12 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD).
# R11-2 = §4.3.1 "3 + 6 agents x 5" sentence; R11-4a = Appendix D "two sprint scripts";
# R11-4b = Appendix D table row; R11-4c = §9 rank order (42, 90 and 30: a reorder, no net delta).
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    ("R11-2 '(8 - 5)'", "8", +1),
    ("R11-2 '(8 - 5)'", "5", +1),
    ("R11-2 'placed in phase 0'", "0", +1),
    ("R11-2 'the same 3 slots go to'", "3", +1),
    ("R11-2 'the three pinned chunks' and 'top three'", "three", +2),
    ("R11-2 '227328 replaces 116107'", "227328", +1),
    ("R11-2 '227328 replaces 116107'", "116107", +1),
    ("R11-2 pointer '(§4.3.2)'", "4.3.2", +1),
    ("R11-4a 'the two sprint scripts'", "two", +1),
    ("R11-4b 'a 2026-09-08 run and the 2026-08-28 control' +2; the full path "
     "`_sprint-2026-10-04/...` +1 (numbers inside code spans are tokens)", "2026", +3),
    ("R11-4b the full path `_sprint-2026-10-04/...`", "10", +1),
    ("R11-4b the full path `_sprint-2026-10-04/...`", "04", +1),
    ("R11-4b 2026-09-08, 2026-08-28", "08", +2),
    ("R11-4b 2026-09-08", "09", +1),
    ("R11-4b 2026-08-28", "28", +1),
]
D_FOOTNOTES = []
D_REFS = [
    ("R11-2 pointer to §4.3.2 (where 227328 replaces 116107)", "§4.3.2", +1),
]
D_CODE = [
    ("R11-2 '`mainTarget` leaves'", "`mainTarget`", +1),
    ("R11-2 'the `scope=global` sub-pool'", "`scope=global`", +1),
    ("R11-4b table row: short name replaced by the full path", "`diag-residual-mismatch.py`", -1),
    ("R11-4b table row: full path of the script",
     "`_sprint-2026-10-04/A-filters-disaggregation/diag-residual-mismatch.py`", +1),
]
D_LINKS = []
D_HEADINGS = []
D_TABLES = [
    ("R11-4b Appendix D row of the filter disaggregation",
     "| main-pool filter disaggregation, and the served main set from the log (§4.3.1) | `sprint-desagrega-filtros-pool-principal.py` (`--log-only` for the log census) | `A-filters-disaggregation/out-ord0826.json` · `A-filters-disaggregation/observed-main-from-log.json` · `A-filters-disaggregation/diag-out.txt` (the residual mismatch of 2026-08-22, `diag-residual-mismatch.py`) |",
     "| main-pool filter disaggregation, and the served main set from the log (§4.3.1) | `sprint-desagrega-filtros-pool-principal.py` (`--log-only` for the log census) | `A-filters-disaggregation/out-ord0826.json` · `A-filters-disaggregation/observed-main-from-log.json` · `A-filters-disaggregation/diag-out.txt` (the residual mismatch of 2026-08-22, produced by `_sprint-2026-10-04/A-filters-disaggregation/diag-residual-mismatch.py`; the file also holds a 2026-09-08 run and the 2026-08-28 control) |"),
]

# Declared qualifier deltas (rc12 - rc11), with the finding that justifies each.
D_QUALIFIERS = {
    "phase 0": (+1, "R11-2: 'placed in phase 0 before the quota pass'"),
}

# Withdrawn phrasings: the 8 of rc11 (carried), plus the 2 that this review withdrew. None may come
# back outside the F-5 addenda. Both new ones are reverts that change no token.
WITHDRAWN = list(_rc11.WITHDRAWN) + [
    ("R11-2", "the 3 shared slots are taken by the high-pain floor"),
    ("R11-4c", "last accessed 90, 30, and 42 days"),
]
assert len(WITHDRAWN) == 10, f"expected 10 withdrawn phrasings, got {len(WITHDRAWN)}"


def cut_addendum(new):
    n = new.count(RC12_ADDENDUM)
    if n != 1:
        return new, f"rc12 addendum header occurs {n} times (expected 1)"
    a = new.find(RC12_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r11 = new.find(RC11_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc12 addendum"
    if r11 < 0 or r11 > a:
        return new, "rc12 addendum is not after the rc11 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc12 addendum and '## Open items'"
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

    # history: the addenda rc5..rc11 are byte-identical (rc12 edits none of them)
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    ho, hn = region(old, ADDENDA_START, OPEN_ITEMS), region(stripped, ADDENDA_START, OPEN_ITEMS)
    bad = []
    if ho is None or hn is None or ho.rstrip("\n") != hn.rstrip("\n"):
        bad.append("F-5 addenda rc5..rc11 differ or not found")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc11 counts must survive in rc12, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc11 has {co[q]}, declared delta "
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


R2_NEW = "where 227328 replaces 116107 (§4.3.2),"
R2_SLOTS = "the 3 shared slots are what `mainTarget` leaves after the agent quota"


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
    rc11_line = "with the wording the review proposed. What changed:"
    row_new = D_TABLES[0][2]
    mutations = [
        ("declared number changed (R11-2: 227328 -> 227329)", "numbers",
         lambda t: sub_at(t, R2_NEW, "where 227329 replaces 116107 (§4.3.2),")),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("unit mutation is NOT caught (documented limit, as in rc11) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("§ reference in prose (R11-2 pointer)", "refs",
         lambda t: sub_at(t, R2_NEW, "where 227328 replaces 116107 (§4.3.1),")),
        ("code span (R11-2 `mainTarget`)", "code",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("`mainTarget`", "`main_target`"))),
        ("table row: R11-4b reverted", "tables", lambda t: t.replace(row_new, D_TABLES[0][1], 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc11 addendum edited", "history",
         lambda t: t.replace(rc11_line, rc11_line.replace("the review proposed", "the reviewer proposed"), 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("R11-2 'phase 0' dropped (declared +1 not seen)", "qualifiers",
         lambda t: sub_at(t, "placed in phase 0 before the quota pass", "placed first, before the quota pass")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R10-5 withdrawn wording back (carried from rc11)", "withdrawn",
         lambda t: sub_at(t, "held there by the high-pain pin", "placed there by the high-pain floor")),
        ("R11-2 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("are what", "are taken by the high-pain floor, what"))),
        ("R11-4c §9 rank order reverted (no token changes)", "withdrawn",
         lambda t: t.replace("last accessed 42, 90 and\n30 days before the window closed",
                             "last accessed 90, 30, and\n42 days before the window closed", 1)),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc12 addendum removed", "addendum", lambda t: t.replace(RC12_ADDENDUM, "**Note, rc12 (2026-10-05)", 1)),
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
