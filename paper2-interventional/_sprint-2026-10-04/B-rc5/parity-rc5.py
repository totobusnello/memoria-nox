#!/usr/bin/env python3
"""Parity check B-v2-rc4.md -> B-v2-rc5.md (Paper B, sprint 2026-10-04; rc5 2026-10-05).

Adapted from B-rc4/parity-rc4.py: same five checks, the old file is rc4 and the new rc5.

Checks, each of which must pass (exit 0) or the script exits 1:
  1. numbers: every numeric token whose count changes between rc4 and rc5 is listed in
     JUSTIFIED with the exact signed change and a reason (F1-F5, WL or CHANGELOG; see the
     comment above JUSTIFIED). A token that changes by a
     different amount, or that is not listed, fails; so does a listed token that no longer
     changes (stale justification).
  2. headings: the heading sequence is identical (HEADINGS is empty: rc5 renames nothing).
  3. section refs: every internal section reference of rc5 resolves to a heading, except
     the dangling references that already existed in rc4 (no new dangling refs).
  4. citations: every pandoc key [@key] used in the body is listed in References; none
     added or removed relative to rc4. Footnote markers [^x] are defined if used.
  5. no host, IP or personal path was added (pattern counts may not grow from rc4 to rc5).

Usage:  python3 parity-rc5.py            # check
        python3 parity-rc5.py --report   # print the raw diff, no verdict
        python3 parity-rc5.py --self-test  # apply 3 mutations to rc5 in memory; each must fail
Reads only the two manuscripts. Writes nothing.
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "B-v2-rc4.md")
NEW = os.path.join(HERE, "..", "B-v2-rc5.md")

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
JUSTIFIED = {}


def _J(token, delta, reason):
    assert token not in JUSTIFIED, token
    JUSTIFIED[token] = (delta, reason)


# token: (signed change rc4 -> rc5, reason). Every change comes from the Codex regression
# review of rc4 (2026-10-05; five findings, all confirmed; record in APPLY-B-rc5.md):
# F1 H1 ratios are proportional-dilution calculations, not causal bounds (abstract x2,
# §4.0.2, §4.3); F2 condition (i) described as implemented (§4); F3 sham claim limited to
# the 20 tested shams, rank not a calibrated randomization p-value (abstract, §4.0.1c, §7);
# F4 whole-epoch power: 80% only for reductions >= 99.6% (§4.1.1, §9, B.1); F5 C12 rerun and
# first-order values both stated (§4, B.1). WL = working list item 16; CHANGELOG = the rc5
# block (items 69-74) and the correction in item 67.
_J("0.026566", +3, "F5: first-order C12 difference, contrafactual_empate_como_failure.primeira_ordem.diferenca (§4, B.1, CHANGELOG 73)")
_J("0.026571", +3, "F5: rerun C12 difference, diferenca_4votos_empate_como_failure (§4, B.1, CHANGELOG 73)")
_J("0.996", +1, "F4: CHANGELOG 72 '(relative MDE 0.996)'")
_J("09-14", -1, "F1: §4.3 rewrite names 'without `09-14`' once instead of twice")
_J("1", +2, "F1: §4.3 'reading 1 above'; CHANGELOG 69 'reading 1'")
_J("10.3", +1, "F1: CHANGELOG 69 '10.3 / 6.9'")
_J("100", -2, "F1: 'more than 100%' / 'above 100%' removed from abstract x2, §4.0.2, §4.3 (-4); CHANGELOG 69 quotes both (+2)")
_J("11", +1, "F4: CHANGELOG 72 '11 treatment'")
_J("15.0", +1, "F1: CHANGELOG 69 '22.5 / 15.0'")
_J("16", +1, "WL: CHANGELOG 74 'item 16 added' (the list number itself is normalized away)")
_J("2026-10-04", +2, "path `_sprint-2026-10-04/APPLY-B-rc5.md` in WL 16 and the rc5 changelog header")
_J("2026-10-05", +2, "STATUS 'rc5 prepared 2026-10-05'; WL 16 'Done, 2026-10-05'")
_J("20", +5, "F3: abstract 'these 20 shams', §4.0.1c 'these 20', §7 'these 20 shams' and 'the 20 tested shams', CHANGELOG 71")
_J("22.5", +1, "F1: CHANGELOG 69 '22.5 / 15.0'")
_J("3.14", +2, "F1: §4.3 'by the 3.14% altered-brief share'; CHANGELOG 69")
_J("5", +2, "WL 16: '5 findings, 5 confirmed'")
_J("6.9", +1, "F1: CHANGELOG 69 '10.3 / 6.9'")
_J("67", +1, "F5: CHANGELOG 73 'item 67 is corrected'")
_J("73", +1, "F5: CHANGELOG 67 '(corrected in rc5, item 73)'")
_J("80", +4, "F4: '80% power' in §4.1.1, §9, B.1, CHANGELOG 72")
_J("9", +1, "F4: CHANGELOG 72 '9 control'")
_J("99.6", +4, "F4: 1 - mde_relativo_h1c 0.996 of power-11T-9C-whole-epochs.json (§4.1.1, §9, B.1, CHANGELOG 72)")

# ---------------------------------------------------------------- headings
HEADINGS = {}  # rc5 renames no heading

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


def check(old, new, verbose=True):
    fails = []
    # 1 numbers
    a, b = numbers(old), numbers(new)
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
    h2, h3 = headings(old), headings(new)
    expected = [HEADINGS.get(h, (h, None))[0] for h in h2]
    if expected != h3:
        for x, y in zip(expected + [None] * 9, h3 + [None] * 9):
            if x != y:
                fails.append(f"heading: expected {x!r}, found {y!r}")
                break
    # 3 section refs
    d2, d3 = dangling_refs(old), dangling_refs(new)
    added = d3 - d2
    for ref, n in added.items():
        fails.append(f"section ref: new dangling §{ref} (x{n})")
    # 4 citations and footnotes
    for name, t in (("rc4", old), ("rc5", new)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        if name == "rc5":
            u2 = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body_and_refs(old)[0]))))
            if used != u2:
                fails.append(f"citation: key set changed: +{sorted(used - u2)} -{sorted(u2 - used)}")
        fm = set(re.findall(r"\[\^([^\]]+)\](?!:)", t))
        fd = set(re.findall(r"^\[\^([^\]]+)\]:", t, re.M))
        if fm - fd:
            fails.append(f"footnote ({name}): markers without definition {sorted(fm - fd)}")
    # 5 forbidden additions
    for pat in FORBIDDEN:
        n2, n3 = len(re.findall(pat, old)), len(re.findall(pat, new))
        if n3 > n2:
            fails.append(f"forbidden: pattern {pat!r} occurs {n3} times in rc5 against {n2} in rc4")
    if verbose:
        print(f"numeric tokens changed: {len(changed)} (justified entries: {len(JUSTIFIED)})")
        print(f"headings: {len(h3)} in rc5, {sum(1 for h in h2 if h in HEADINGS)} renamed (allowed)")
        print(f"dangling internal § refs: rc4 {sum(d2.values())}, rc5 {sum(d3.values())}, new {sum(added.values())}")
    return fails


def main():
    old, new = open(OLD, encoding="utf-8").read(), open(NEW, encoding="utf-8").read()
    if "--report" in sys.argv:
        a, b = numbers(old), numbers(new)
        print("APPEARED", sorted((b - a).items()))
        print("DISAPPEARED", sorted((a - b).items()))
        print("DANGLING rc4", dict(dangling_refs(old)), "rc5", dict(dangling_refs(new)))
        return 0
    if "--self-test" in sys.argv:
        mutations = [
            ("number changed (99.6 -> 96.6 once)", new.replace("99.6%", "96.6%", 1)),
            ("heading renamed (§4.2)", new.replace("### 4.2 H1a:", "### 4.2 H1a (revised):", 1)),
            ("dangling § ref added", new.replace("(§4.0.1c); still not done", "(§4.0.1d); still not done", 1)),
        ]
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            f = check(old, mutated, verbose=False)
            print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False)
        print(f"unmutated rc5: {'PASS' if not base else 'FAIL'}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
