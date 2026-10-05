#!/usr/bin/env python3
"""Parity check rc17 -> rc18 of Paper A after the Fable review of the rc17 diff.

Usage:
    python3 parity-rc18.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc18.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc18 applies the three low notes of `_sprint-2026-10-04/REVIEW-A-rc17-2026-10-05.md` (Fable, GO):
F18-1..F18-3, IDs as in `APPLY-A-rc18.md`. F18-2 (the measured quantity phrased as what the agent
sees or receives) is a class, so the whole manuscript was swept for it and the sweep edits are
declared under the same ID ("F18-2 sweep"). rc18 may change numbers, code spans, one heading and
one qualifier count, but only the ones a finding declares; no table row changes. The F-5
"Addendum, rc18" is cut out of NEW (between its header and "## Open items") before the delta
checks; the "addendum" check requires that it exists exactly once, right after the rc17 addendum
and right before "## Open items".

rc18 does not touch any earlier addendum: the F-5 addenda rc5..rc17 must be byte-identical. The
last sentence of the rc17 addendum ("so it does not touch the lower bounds on non-delivery") is
qualified by the rc18 addendum, not edited.

Checks, OLD vs NEW-without-the-rc18-addendum (the extractors come from A-rc17/parity-rc17.py,
which takes them from A-rc16 back to A-rc9, so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED (empty)
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings with the one DECLARED replacement (§8.3, F18-1) == NEW headings, in order
  tables      OLD table rows == NEW table rows, in order (no declared replacement)
  history     F-5 addenda rc5..rc17 byte-identical
  qualifiers  carried: every rc6-rc17 scope qualifier keeps its rc17 count (outside the addenda),
              except the one DECLARED delta ('no-record' +1, F18-3), and is >= 1; full scope clause in the Abstract and in §3.1;
              *no-record* defined exactly once, in §3.1
  classes     carried: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py occurs in NEW
              outside the F-5 addenda
  withdrawn   carried and extended: none of the 97 phrasings withdrawn in rc11..rc17, nor the 6
              rc17 phrasings withdrawn here, occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc17)
  addendum    the rc18 addendum exists exactly once, in place
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
DEFAULT_OLD = SPRINT / "A-v1.1-rc17.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc18.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "spare-capacity-narrow-surface-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc17", SPRINT / "A-rc17" / "parity-rc17.py")
_rc17 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc17)
FORBIDDEN = list(_rc17.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc17.extract, _rc17.norm, _rc17.outside_addenda, _rc17.prose_dashes
QUALIFIERS = list(_rc17.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc17.SCOPE_FULL, _rc17.NO_RECORD_DEF
section, declared_counter, delta = _rc17.section, _rc17.declared_counter, _rc17.delta
first_prose, sub_at, qualifier_counts = _rc17.first_prose, _rc17.sub_at, _rc17.qualifier_counts

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC16_ADDENDUM = "**Addendum, rc16 (2026-10-05)"
RC17_ADDENDUM = "**Addendum, rc17 (2026-10-05)"
RC18_ADDENDUM = "**Addendum, rc18 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD).
# F18-1 = §8.3 heading: "Pre-registration in systems CS" -> "Pre-registration, and what this paper
#         does not claim about it" (the body has not spoken about systems CS since rc17). No
#         cross-reference quotes the heading text outside the addenda.
# F18-2 = §1 gap bullet: "how many distinct items a system in production selects for an agent".
#         Sweep: §1 question ("what does the system select for the agent?"), §5.5 ("To move what
#         the brief selects"), §9 caveat ("what the brief selects for the agent"). No tokens.
# F18-3 = §3.1: the lower-bound reading of no-record also assumes the fail-open `brief_log` write
#         never failed (`brief.ts:1099-1101`); the code records no such failure.
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    ("F18-3 §3.1 '`brief.ts:1099-1101`'", "1099", +1),
    ("F18-3 §3.1 '`brief.ts:1099-1101`'", "1101", +1),
]
D_FOOTNOTES = []
D_REFS = []
D_CODE = [
    ("F18-3 §3.1 fail-open log write", "`brief.ts:1099-1101`", +1),
]
D_LINKS = []
OLD_83 = "### 8.3 Pre-registration in systems CS"
NEW_83 = "### 8.3 Pre-registration, and what this paper does not claim about it"
D_HEADINGS = [("F18-1", OLD_83, NEW_83)]
D_TABLES = []

# Declared qualifier deltas (rc18 - rc17), counted outside the addenda.
D_QUALIFIERS = {"no-record": (+1, "F18-3 §3.1 'The lower-bound reading of *no-record* (defined below)'")}

# Withdrawn phrasings: the 97 of rc11..rc17 (carried), plus the ones this review withdrew. None
# may come back outside the F-5 addenda (matching is whitespace-normalised and case-insensitive).
WITHDRAWN = list(_rc17.WITHDRAWN) + [
    ("F18-1", "Pre-registration in systems CS"),
    ("F18-2", "how many distinct items an agent in production sees"),
    ("F18-2", "an agent in production sees"),
    ("F18-2", "what does the agent receive?"),
    ("F18-2", "To move what the agent sees"),
    ("F18-2", "\"what the agent sees\" and \"what exists\""),
]
assert len(WITHDRAWN) == 103, f"expected 103 withdrawn phrasings, got {len(WITHDRAWN)}"


def cut_addendum(new):
    n = new.count(RC18_ADDENDUM)
    if n != 1:
        return new, f"rc18 addendum header occurs {n} times (expected 1)"
    a = new.find(RC18_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r17 = new.find(RC17_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc18 addendum"
    if r17 < 0 or r17 > a:
        return new, "rc18 addendum is not after the rc17 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc18 addendum and '## Open items'"
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

    # history: the addenda rc5..rc17 are byte-identical (rc18 corrects none of them)
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    ho, hn = region(old, ADDENDA_START, OPEN_ITEMS), region(stripped, ADDENDA_START, OPEN_ITEMS)
    bad = []
    if ho is None or hn is None or ho != hn:
        bad.append("F-5 addenda rc5..rc17 differ or not found")
    for hdr in (RC16_ADDENDUM, RC17_ADDENDUM):
        if stripped.count(hdr) != 1:
            bad.append(f"{hdr!r} occurs {stripped.count(hdr)} times (expected 1)")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc17 counts + declared delta must hold in rc18, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc17 has {co[q]}, declared delta "
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
C1_S31 = "`brief_log` records the items the brief selected, and it is written before the response is rendered"
C3_NOTE = "**Note:** the three constant items belong to the main pool in the reconstruction of §4.3.1,"
F2_GAP = "how many distinct items a system in\n  production selects for an agent, and which ones."
F2_Q = "include it: what does the system select for the agent?"
F2_55 = "To move what the brief selects beyond that bound"
F2_9 = 'boundary between "what the brief selects for the agent" and "what exists"'
F3_S31 = ("The lower-bound\nreading of *no-record* (defined below) also assumes that this log write never failed: the write is\n"
          "fail-open (`brief.ts:1099-1101`), so a failed write would deliver items with no row, and the code\n"
          "records no such failure.")


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
        ("declared number changed (F18-3: brief.ts:1099-1101 -> 1099-1102)", "numbers",
         lambda t: sub_at(t, "fail-open (`brief.ts:1099-1101`)", "fail-open (`brief.ts:1099-1102`)")),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("unit mutation is NOT caught (documented limit, as in rc17) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("declared heading not applied (F18-1 heading reverted)", "headings",
         lambda t: t.replace(NEW_83 + "\n", OLD_83 + "\n", 1)),
        ("§ reference (C17-2 sweep pointer §8.1 dropped in §9; undeclared in rc18)", "refs",
         lambda t: sub_at(t, "the metrics of the survey's taxonomy (§8.1). This", "the metrics of the survey's taxonomy. This")),
        ("§ reference (C17-3 pointer §4.3.1 -> §4.3.2; undeclared in rc18)", "refs",
         lambda t: sub_at(t, C3_NOTE, C3_NOTE.replace("reconstruction of §4.3.1,", "reconstruction of §4.3.2,"))),
        ("code span (F18-3 sentence removed from §3.1)", "code",
         lambda t: t.replace(" " + F3_S31, "", 1)),
        ("table row edited (no table change declared in rc18)", "tables",
         lambda t: t.replace("The check that replaced it uses only **recorded** quantities and is not a falsifier (§5.6) |",
                             "The check that replaced it uses **recorded** quantities and is not a falsifier (§5.6) |", 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc12 addendum edited", "history",
         lambda t: t.replace(rc12_line, rc12_line.replace("no wrong number", "no incorrect number"), 1)),
        ("history: rc17 addendum edited (now frozen; its last sentence is qualified, not edited)", "history",
         lambda t: t.replace("so it does not touch the lower bounds on non-delivery.",
                             "so it does not touch the lower bounds on non-delivery, provided the log write never failed.", 1)),
        ("history: rc17 addendum header duplicated", "history",
         lambda t: t.replace(RC18_ADDENDUM, RC17_ADDENDUM + " " + RC18_ADDENDUM, 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("undeclared qualifier delta ('phase 0' reworded; only 'no-record' +1 is declared in rc18)", "qualifiers",
         lambda t: sub_at(t, "where phase 0 selects them as pinned items. Their", "where the first phase selects them as pinned items. Their")),
        ("declared qualifier delta not seen (F18-3 '*no-record*' reworded)", "qualifiers",
         lambda t: sub_at(t, "reading of *no-record* (defined below)", "reading of the complement (defined below)")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R11-2 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("are what", "are taken by the high-pain floor, what"))),
        ("C17-1 withdrawn wording back in §3.1 (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, C1_S31, C1_S31.replace("`brief_log` records the items the brief selected, and it is",
                                                    "`brief_log` records what the brief returned. It is"))),
        ("F18-2 withdrawn wording back in the §1 gap bullet (no token changes)", "withdrawn",
         lambda t: t.replace(F2_GAP, "how many distinct items an agent in\n  production sees, and which ones.", 1)),
        ("F18-2 sweep: withdrawn question back in §1 (no token changes)", "withdrawn",
         lambda t: sub_at(t, F2_Q, "include it: what does the agent receive?")),
        ("F18-2 sweep: withdrawn wording back in §5.5 (no token changes)", "withdrawn",
         lambda t: sub_at(t, F2_55, "To move what the agent sees beyond that bound")),
        ("F18-2 sweep: withdrawn wording back in §9 (no token changes)", "withdrawn",
         lambda t: sub_at(t, F2_9, 'boundary between "what the agent sees" and "what exists"')),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc18 addendum removed", "addendum", lambda t: t.replace(RC18_ADDENDUM, "**Note, rc18 (2026-10-05)", 1)),
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
