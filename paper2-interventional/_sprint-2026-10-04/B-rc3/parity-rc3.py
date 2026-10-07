#!/usr/bin/env python3
"""Parity check B-v2-rc2.md -> B-v2-rc3.md (Paper B, sprint 2026-10-04).

Checks, each of which must pass (exit 0) or the script exits 1:
  1. numbers: every numeric token whose count changes between rc2 and rc3 is listed in
     JUSTIFIED with the exact signed change and a reason (finding ID of
     REVIEW-B-rc2-2026-10-04.md, SHAM for the sham integration, or CHANGELOG for the
     rc3 changelog block). A token that changes by a different amount, or that is not
     listed, fails; so does a listed token that no longer changes (stale justification).
  2. headings: the heading sequence is identical except for the renames in HEADINGS.
  3. section refs: every internal section reference of rc3 resolves to a heading, except
     the dangling references that already existed in rc2 (no new dangling refs).
  4. citations: every pandoc key [@key] used in the body is listed in References; none
     added or removed relative to rc2. Footnote markers [^x] are defined if used.
  5. no host, IP or personal path was added (tokens absent from rc2 only).

Usage:  python3 parity-rc3.py            # check
        python3 parity-rc3.py --report   # print the raw diff, no verdict
        python3 parity-rc3.py --self-test  # apply 3 mutations to rc3 in memory; each must fail
Reads only the two manuscripts. Writes nothing.
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RC2 = os.path.join(HERE, "..", "B-v2-rc2.md")
RC3 = os.path.join(HERE, "..", "B-v2-rc3.md")

# ---------------------------------------------------------------- tokenization
SECREF = re.compile(r"§§?\s?(\d+(?:\.\d+)*[a-z]?)(?:\(\d+\))?(?:[–-]§?\d+(?:\.\d+)*[a-z]?)?")
CITE = re.compile(r"\[@[^\]]+\]")
LISTNUM = re.compile(r"^(\s*)\d+\.\s", re.M)
DATE = (r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?"   # 2026-09-03T17:23:30Z
        r"|\d{2}:\d{2}(?::\d{2})?Z?"                            # 17:23:30Z
        r"|(?<![\d-])\d{2}-\d{2}(?![\d-])")                    # `09-14`, 09-12..16
TOK = re.compile(r"(?<![A-Za-z_\d.,])(" + DATE + r"|\d+(?:[.,]\d+)*)(?![A-Za-z_\d]|\.\d)")
HEADNUM = re.compile(r"^(#{1,6} )(?:Appendix )?[A-Z]?\.?\d+(?:\.\d+)*[a-z]?", re.M)
# section-number cells of the B.1 table ("| 4.1–4.3 |", "| Abstract, 4.0.2, 4.3 |")
SECCELL = re.compile(r"\|\s*(?:Abstract, )?\d+(?:\.\d+)*[a-z]?(?:\s*[,–]\s*\d+(?:\.\d+)*[a-z]?)*\s*(?=\|)")


def normalize(text):
    text = CITE.sub(" ", text)
    text = HEADNUM.sub(r"\1", text)
    text = SECCELL.sub("| ", text)
    text = SECREF.sub(" ", text)
    text = LISTNUM.sub(r"\1", text)
    prev = None
    while prev != text:  # "1 195" and "100 000" are one number each
        prev = text
        text = re.sub(r"(?<![\d.,])(\d{1,3}) (\d{3})(?![\d,])", r"\1\2", text)
    return text


def numbers(text):
    return collections.Counter(TOK.findall(normalize(text)))


# ---------------------------------------------------------------- justifications
# token: (signed change rc2 -> rc3, reason). Reasons name finding IDs (C1..C22) of
# REVIEW-B-rc2-2026-10-04.md, SHAM (sham integration, B-sham-v2/REPORT.md §7 and
# job-v2b/RESUMO.json) or CHANGELOG (the rc3 changelog block restating the same numbers).
JUSTIFIED = {}


def _J(token, delta, reason):
    assert token not in JUSTIFIED, token
    JUSTIFIED[token] = (delta, reason)


# ---- disappeared ----
_J("95", -1, "C3: abstract 'the observed 95% interval excludes total elimination' replaced by implied s.e.")
_J("12", -1, "C13: '12 pp' removed in §2 and §6 item 5 (-2); quoted once in the rc3 CHANGELOG (+1)")
_J("13.86", -1, "C14: '13.86 h long' removed from §4.6 prose; the M10 table keeps '13.86 h partial'")
# ---- power: C1, C2, C3, C20 ----
_J("80", +9, "C1/C2: 'not detectable at 80% power' (abstract, §1 table, §4.1 heading text, §4.1.1, §9) and C2 'detectable at 80%' (abstract, §4.1.1, CHANGELOG)")
_J("19", +5, "C2: 'the 19 clusters the calculation counted' (abstract, §1.1, §8.4, CHANGELOG); SHAM '19 non-designated items'")
_J("96.41", +3, "C2: effective size at 11T/9C, power-11T-9C-whole-epochs.json (§4.1.1, B.1, CHANGELOG)")
_J("95.26", +3, "C2: critical effective size, power-*.json (§4.1.1, B.1, CHANGELOG)")
_J("91.49", +3, "C2: fractional with 09-02, power-10.9375T-8.23375C-*.json (§4.1.1, B.1, CHANGELOG)")
_J("90.2", +2, "C2: the 11T/8C rerun reproduces the artifact (§4.1.1, B.1)")
_J("0.996", +2, "C2: relative MDE at 11T/9C (§4.1.1, B.1)")
_J("10.9375", +1, "C2: fractional treatment epochs (§4.1.1)")
_J("8.23375", +1, "C2: fractional control epochs (§4.1.1)")
_J("4.1", +3, "C2: 'verdict flips on a 4.1% drop in ICC' (§4.1.1, B.1, CHANGELOG)")
_J("0.0279", +2, "C3: abstract restates the §4.1.1 power bound; CHANGELOG")
_J("0.0165", +2, "C3: abstract restates the §4.1.1 bootstrap s.e.; CHANGELOG")
_J("9.991", +2, "C20: §1.1 excepts the 9.991 of §4.7; CHANGELOG")
_J("11", +5, "C2 '11 treatment' (abstract, §1.1, §4.1.1, CHANGELOG: +4); C10 B.1 '/ 11' (+1); C7 table row re-worded (-1 +1); SHAM claims paragraph re-worded around '11/11' (-2 +2)")
_J("8", +6, "C2: '8 control' (abstract, §1.1, CHANGELOG); C20 'working list 8'; SHAM 'a projected 8 h'; CHANGELOG 'working list 3, 8, 9'")
_J("9", +7, "C2: '9 control' (abstract, §4.1.1 x2); C10 B.1 '/ 9'; SHAM '9 S2', 'item 9' (working list 3, caveat); CHANGELOG")
_J("20", +22, "C2 '20 clusters' (abstract, §4.1.1, §8.4, §9, working list 13, CHANGELOG); SHAM '20 shams', 'K = 20', '20 of 20' throughout")
# ---- C4 dilution (checks.py on ITT-2026-09-21.json; 3.14% from H1C-POWER-REALIZADO) ----
_J("70.7", +5, "C4: H1 reduction, locked leg (abstract, §4.0.2, §4.3, B.1, CHANGELOG)")
_J("47.1", +4, "C4: H1 reduction without 09-14 (abstract, §4.3, B.1, CHANGELOG)")
_J("22.5", +5, "C4: 0.7073/0.0314 (abstract, §4.0.2, §4.3, B.1, CHANGELOG)")
_J("15.0", +2, "C4: 0.4713/0.0314 (§4.3, B.1)")
_J("10.3", +2, "C4: 0.7073/0.0685 (§4.3, B.1)")
_J("6.9", +4, "C4: 0.4713/0.0685 (abstract, §4.3, B.1, CHANGELOG)")
_J("6.85", +4, "C4: highest per-epoch share, already in §4.0.1b (abstract, §4.3, CHANGELOG); SHAM claims paragraph")
_J("2.83", +1, "SHAM: claims paragraph restates the §4.0.1b positive-control range 2.83-6.85%")
_J("3.14", +5, "C4: fracao_de_briefs_alterada 0.0314 (abstract, §4.0.2, §4.3, B.1, CHANGELOG)")
_J("6.050", +1, "C4: treatment H1, ITT-2026-09-21.json (§4.3)")
_J("20.672", +1, "C4: control H1, ITT-2026-09-21.json (§4.3)")
_J("30", +1, "C4: 'the registered 30% MDE' (§4.3)")
_J("955", +2, "C4: §4.3 'The 955% is the planning figure'; CHANGELOG")
_J("100", +4, "C4: 'more than 100%' (abstract x2, §4.0.2) and 'above 100%' (§4.3); net of C2 'saturated at 100%' unchanged")
_J("2026-08-30", +1, "C4: CHANGELOG '2026-08-30 demotion reason'")
# ---- C6 ----
_J("0.1603", +4, "C6: the null is the non-rejection p = 0.1603 (abstract, §4.1.1, §4.1.2, CHANGELOG)")
_J("22", +7, "C6 '22% relative reduction' (abstract, §4.1.1, CHANGELOG) and C6 B.1 '−22%' (+4); working list 14 and CHANGELOG '22 confirmed' (+2); SHAM dist row '22-state test', '22/22' and working list 3 '22/22' re-worded (-4 +5)")
# ---- C8 ----
_J("2026-09-10", +2, "C8: abstract and §3.0 re-worded around the same date (-2 +2, net 0); SHAM fd readings '2026-09-10 to 09-21' (+1); C4 B.1 row cites out/H1C-POWER-REALIZADO-2026-09-10.json (+1)")
# ---- C10 ----
_J("100.3", +3, "C10: treatment opportunities/epoch = 1103.75/11 (§7, B.1, CHANGELOG)")
_J("132.3", +3, "C10: control opportunities/epoch = 1191.14/9 (§7, B.1, CHANGELOG)")
_J("1103.75", +1, "C10: B.1 source of 100.3 (ITT-2026-09-21.json)")
_J("1191.14", +1, "C10: B.1 source of 132.3 (ITT-2026-09-21.json)")
_J("2026-09-21", +2, "C4 and C10 B.1 rows cite ITT-2026-09-21.json (+2)")
# ---- C11, C13, C14, C15 ----
_J("28", +2, "C11: 'those are the 28 losses of item 6' (§6 item 3, CHANGELOG)")
_J("6", +3, "C11 'item 6' (§6, CHANGELOG); SHAM overlap '6–14'")
_J("11.9", +3, "C13: 42.3 − 30.4 (§2, §6 item 5, CHANGELOG)")
_J("287", +3, "C14: 09-20 briefs after expiry, checks.py (§4.6, B.1, CHANGELOG)")
_J("385", +3, "C14: 09-20 briefs before expiry (§4.6, B.1, CHANGELOG)")
_J("98", +3, "C14: covered briefs before expiry (§4.6, B.1, CHANGELOG)")
_J("25.5", +3, "C14: 98/385 (§4.6, B.1, CHANGELOG)")
_J("09-20", +3, "C14: B.1 row and CHANGELOG name `09-20` (+2); B evidence row names the 09-20 coverage split (+1)")
_J("2026-08-26", +1, "C14: B.1 row cites DESIGNATION-2026-08-26.json")
_J("0", +5, "C14 '0 covered' (§4.6) and B.1 ', 0'; C2 '`p1 = 0`'; SHAM zero counts ('0 errors', shams >= real = 0 in both table rows); the 110-row and the sham-replayed row re-worded with the old value struck")
_J("672", +4, "C14 'all 672 briefs' (§4.6, CHANGELOG); SHAM '672/672 in each of the others'")
_J("1.5", +2, "C15: 'MC s.e. 1.5%' (Figure B2 caption, CHANGELOG)")
_J("1", +11, "C15 '1% of the deficit' x2; SHAM 'p = 1/21' and '(1 + #...)'; SHAM 'defect 1'")
_J("21", +14, "SHAM: '1/21', '21 runs', '2/21', '21–50%'")
_J("2", +2, "SHAM '2/21 = 0.095' (+1); working list 14 '2 rejected' (+1); C12 '2-2 tie' line and C22 caveat 'Items 2 and 3' re-worded (-3 +3)")
_J("3", +2, "C11 CHANGELOG '§6 item 3'; SHAM CHANGELOG 'working list 3'")
_J("5", +1, "C13 CHANGELOG '§6 item 5'")
_J("13", +1, "C2: CHANGELOG 'Working list 13, first half, closed'")
_J("14", +2, "SHAM overlap '6–14'; working list item 14 named in CHANGELOG")
_J("24", +1, "working list 14: '24 findings' of REVIEW-B-rc2")
_J("10", +2, "SHAM 'exceeds the largest sham by 10 states', '10 S1' (+2); C7 abstract '~10 clusters' and working list 8 '10 (ballast gap)' re-worded (-2 +2)")
_J("4", +15, "SHAM: 'w = 4' throughout the sham text (§4.0.1b, §4.0.1c, §7, §8.3, §8.5, working list)")
# ---- sham integration ----
_J("2,646", +22, "SHAM: 2,646 brief states (abstract, §4.0.1b, §4.0.1c, §7, B, B.1, working list, CHANGELOG)")
_J("0.0476", +6, "SHAM: p = 1/21 (§4.0.1b, §4.0.1c table x2 and text, B.1, CHANGELOG)")
_J("0.095", +1, "SHAM: p with one tied sham, 2/21")
_J("132", +9, "SHAM: real designation moves 132 states (§4.0.1b, §4.0.1c, B.1, working list, CHANGELOG)")
_J("146", +3, "SHAM: real total churn")
_J("81", +6, "SHAM: lowest sham `mexeu`, 81 (both doses)")
_J("122", +6, "SHAM: highest sham `mexeu`, 122 (both doses)")
_J("84", +2, "SHAM: lowest sham churn, 84")
_J("155", +3, "SHAM: real at w = 100 000 (positive control)")
_J("100000", +4, "SHAM: w = 100 000 (§4.0.1c, B.1)")
_J("110", +17, "SHAM: fidelity on the 110 states, 110/110 (§4.0.1c table, B, B.1, CHANGELOG)")
_J("36", +12, "SHAM: 36 boostable non-designated items (REPORT §2.1)")
_J("89", +6, "SHAM: 89 non-designated pool items")
_J("53", +2, "SHAM: 89 − 36 = 53 with no p2_verdict row (§4.0.1c, B.1)")
_J("0.301", +1, "SHAM: bonus mass 0.301·w (REPORT §2.1)")
_J("10.4", +1, "SHAM: mean pairwise sham overlap (REPORT §2.1)")
_J("50", +1, "SHAM: '21–50%' bonus mass of shams drawn from all 89")
_J("19,567", +2, "SHAM: whole-log states (REPORT §3)")
_J("11,865", +3, "SHAM: hash-verified trial-window states (REPORT §3)")
_J("8,000", +1, "SHAM: ~8k shadow states without identifiable corpus (REPORT §3)")
_J("60", +1, "SHAM: ≈60 h for the whole log (REPORT §3)")
_J("630", +2, "SHAM: 09-01 control 630/630 (RESUMO.json fidelidade_real)")
_J("09-01", +2, "SHAM: the four w = 4 epochs named")
_J("09-12", +1, "SHAM: the four w = 4 epochs named")
_J("09-14", +5, "C4: 'without `09-14`' (abstract x2 incl. CHANGELOG, §4.3 x2: +4); SHAM: the four w = 4 epochs named (+1)")
_J("09-15", +1, "SHAM: the four w = 4 epochs named")
_J("09-02", +3, "C2: §4.1.1 'fractional counting with `09-02`', B.1 and CHANGELOG (+3); §4.1.1 sentence re-worded (-1 +1)")
_J("09-08", +1, "SHAM: same file measured on 09-08 (DEVIATIONS §10.10)")
_J("09-21", +2, "SHAM: fd readings to 09-21")
_J("2026-09-03", +1, "SHAM: process start 2026-09-03 17:23:30Z")
_J("17:23:30Z", +1, "SHAM: process start time")
_J("2026-10-04", +20, "SHAM and CHANGELOG: run date / rc3 annotations")

# ---------------------------------------------------------------- headings
HEADINGS = {
    "### 3.0 The stopping rule, and a feasibility question we cannot yet answer":
        ("### 3.0 The stopping rule, and the feasibility question it raises", "C22"),
    "#### 4.0.1b The pre-committed instrument controls: two run, one not runnable":
        ("#### 4.0.1b The pre-committed instrument controls: all three run", "C22 + SHAM"),
    "#### 4.0.1c The specificity control: invalid as configured, runnable, not yet run":
        ("#### 4.0.1c The specificity control: invalid as first configured, then run", "SHAM"),
    "### 4.1 H1c: the primary outcome, null and undetectable":
        ("### 4.1 H1c: the primary outcome, null and not detectable at 80% power", "C1"),
}

# ---------------------------------------------------------------- forbidden additions
FORBIDDEN = [r"\b\d{1,3}(?:\.\d{1,3}){3}\b", r"/Users/", r"~/", r"/var/", r"/root/", r"/tmp/",
             r"\$NOX_", r"srv\d+", r"\.hostinger", r"@[a-z0-9-]+\.(?:com|br|ai)\b"]


def headings(text):
    return [l.rstrip() for l in text.splitlines() if re.match(r"^#{1,6} ", l)]


def heading_ids(text):
    ids = set()
    for h in headings(text):
        m = re.match(r"^#{1,6} (?:Appendix )?([A-Z]?\.?\d+(?:\.\d+)*[a-z]?|[A-Z])\b", h)
        if m:
            ids.add(m.group(1))
    return ids


EXTERNAL_CUE = re.compile(
    r"(spec|PREREG|DEVIATIONS|REPORT\.md|Paper A|pre-registration|registration|survey|"
    r"\.md|\.json|its own|TMLR|DECISIONS|HANDOFF|analysis specification)[^§]{0,40}$", re.I)


def dangling_refs(text):
    ids = heading_ids(text)
    out = collections.Counter()
    for m in SECREF.finditer(text):
        ref = m.group(1)
        before = text[max(0, m.start() - 60):m.start()]
        if EXTERNAL_CUE.search(before):
            continue
        if ref.startswith("10.") or ref.startswith("6") and "." not in ref and False:
            continue
        if ref in ids or ref.rstrip("abc") in ids:
            continue
        out[ref] += 1
    return out


def body_and_refs(text):
    i = text.find("\n## References")
    j = text.find("\n## Appendix A")
    return text[:i] + text[j:], text[i:j]


def check(rc2, rc3, verbose=True):
    fails = []
    # 1 numbers
    a, b = numbers(rc2), numbers(rc3)
    keys = set(a) | set(b)
    changed = {k: b[k] - a[k] for k in keys if b[k] != a[k]}
    for k, d in sorted(changed.items()):
        if k not in JUSTIFIED:
            fails.append(f"number: '{k}' changes by {d:+d}, not justified")
        elif JUSTIFIED[k][0] != d:
            fails.append(f"number: '{k}' changes by {d:+d}, justified for {JUSTIFIED[k][0]:+d}")
    for k, (d, _) in JUSTIFIED.items():
        if k not in changed:
            fails.append(f"number: justification for '{k}' ({d:+d}) is stale, token unchanged")
    # 2 headings
    h2, h3 = headings(rc2), headings(rc3)
    expected = [HEADINGS.get(h, (h, None))[0] for h in h2]
    if expected != h3:
        for x, y in zip(expected + [None] * 9, h3 + [None] * 9):
            if x != y:
                fails.append(f"heading: expected {x!r}, found {y!r}")
                break
    # 3 section refs
    d2, d3 = dangling_refs(rc2), dangling_refs(rc3)
    new = d3 - d2
    for ref, n in new.items():
        fails.append(f"section ref: new dangling §{ref} (x{n})")
    # 4 citations and footnotes
    for name, t in (("rc2", rc2), ("rc3", rc3)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        if name == "rc3":
            u2 = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body_and_refs(rc2)[0]))))
            if used != u2:
                fails.append(f"citation: key set changed: +{sorted(used - u2)} -{sorted(u2 - used)}")
        fm = set(re.findall(r"\[\^([^\]]+)\](?!:)", t))
        fd = set(re.findall(r"^\[\^([^\]]+)\]:", t, re.M))
        if fm - fd:
            fails.append(f"footnote ({name}): markers without definition {sorted(fm - fd)}")
    # 5 forbidden additions
    for pat in FORBIDDEN:
        n2, n3 = len(re.findall(pat, rc2)), len(re.findall(pat, rc3))
        if n3 > n2:
            fails.append(f"forbidden: pattern {pat!r} occurs {n3} times in rc3 against {n2} in rc2")
    if verbose:
        print(f"numeric tokens changed: {len(changed)} (justified entries: {len(JUSTIFIED)})")
        print(f"headings: {len(h3)} in rc3, {sum(1 for h in h2 if h in HEADINGS)} renamed (allowed)")
        print(f"dangling internal § refs: rc2 {sum(d2.values())}, rc3 {sum(d3.values())}, new {sum(new.values())}")
    return fails


def main():
    rc2, rc3 = open(RC2, encoding="utf-8").read(), open(RC3, encoding="utf-8").read()
    if "--report" in sys.argv:
        a, b = numbers(rc2), numbers(rc3)
        print("APPEARED", sorted((b - a).items()))
        print("DISAPPEARED", sorted((a - b).items()))
        print("DANGLING rc2", dict(dangling_refs(rc2)), "rc3", dict(dangling_refs(rc3)))
        return 0
    if "--self-test" in sys.argv:
        mutations = [
            ("number changed (96.41 -> 96.14 once)", rc3.replace("96.41", "96.14", 1)),
            ("heading renamed (§4.2)", rc3.replace("### 4.2 H1a:", "### 4.2 H1a (revised):", 1)),
            ("dangling § ref added", rc3.replace("(§4.0.1c); still not done", "(§4.0.1d); still not done", 1)),
        ]
        ok = True
        for name, mutated in mutations:
            assert mutated != rc3, f"mutation did not apply: {name}"
            f = check(rc2, mutated, verbose=False)
            print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0]}" if f else ""))
            ok &= bool(f)
        base = check(rc2, rc3, verbose=False)
        print(f"unmutated rc3: {'PASS' if not base else 'FAIL'}")
        return 0 if ok and not base else 1
    fails = check(rc2, rc3)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
