#!/usr/bin/env python3
"""Parity check B-v2-rc3.md -> B-v2-rc4.md (Paper B, sprint 2026-10-04; rc4 2026-10-05).

Adapted from B-rc3/parity-rc3.py: same checks, the old file is rc3 and the new rc4
(variables OLD/NEW; labels renamed from the rc3 script on 2026-10-05, CHECK-A-rc4-B-rc4.md D-B3).

Checks, each of which must pass (exit 0) or the script exits 1:
  1. numbers: every numeric token whose count changes between rc3 and rc4 is listed in
     JUSTIFIED with the exact signed change and a reason (TITLE, POWER, SHAM, C12, B1,
     CHECK or CHANGELOG; see the comment above JUSTIFIED). A token that changes by a
     different amount, or that is not listed, fails; so does a listed token that no longer
     changes (stale justification).
  2. headings: the heading sequence is identical except for the renames in HEADINGS.
  3. section refs: every internal section reference of rc4 resolves to a heading, except
     the dangling references that already existed in rc3 (no new dangling refs).
  4. citations: every pandoc key [@key] used in the body is listed in References; none
     added or removed relative to rc3. Footnote markers [^x] are defined if used.
  5. no host, IP or personal path was added (tokens absent from rc3 only).

Usage:  python3 parity-rc4.py            # check
        python3 parity-rc4.py --report   # print the raw diff, no verdict
        python3 parity-rc4.py --self-test  # apply 3 mutations to rc4 in memory; each must fail
Reads only the two manuscripts. Writes nothing.
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "B-v2-rc3.md")
NEW = os.path.join(HERE, "..", "B-v2-rc4.md")

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


# token: (signed change rc3 -> rc4, reason). Reasons: TITLE, POWER (author decision 2 and 3:
# fractional counting governs; whole-epoch 11T/9C is a sensitivity; "projection-robust" holds
# only under the spec's cuts), SHAM (decision 4: whole-window replay running, source
# B-sham-v2/JANELA-LANCAMENTO.md), C12 (decision 5: out/C12-EMPATES-POR-BRACO-2026-10-05.json),
# B1 (Appendix B / B.1 rows), CHECK (fixes from CHECK-A-rc4-B-rc4.md, D-B1/D-B2, with
# out/C12-EMPATES-COMO-FAILURE-2026-10-05.json) and CHANGELOG (the rc4 changelog block, items 59-68).
_J("0", +1, "C12 B.1: '0 failures among those'")
_J("09-01", +4, "SHAM: `09-01` excluded from the whole-window replay (§4.0.1c, B.1, working list 15, CHANGELOG)")
_J("09-02", +2, "POWER: §4.1.1 'the ITT counts `09-02` as a control cluster' (+1, with the rewritten sentence net +1); CHANGELOG")
_J("1", +1, "CHANGELOG 63: 'p = 1/21' (rc3 sham result unchanged)")
_J("10", +5, "C12: '10 in treatment epochs' (§4, §7, B.1, CHANGELOG 64); CHANGELOG 63 'blocked by 10 and 15'")
_J("11", +12, "POWER: '11 treatment and 9 control' (abstract, §1.1 caveat, §9: +3); C12: '11 in control' and '11 that are opportunities' (§4 x2, §7 x2, B.1: +5); CHANGELOG 60 x2, 61, 64 (+4)")
_J("11,812", +7, "SHAM: whole-window states (STATUS, §4.0.1c, B.1, working list 15, CHANGELOG 63); JANELA-LANCAMENTO.md 'Relançamento'; CHECK D-B2: working list 9 (+1), CHANGELOG 68 (+1)")
_J("15", +5, "SHAM: working list 15 named in items 8 and 9 (+2); CHANGELOG 63 (+2); CHECK D-B2: CHANGELOG 68 'items 9 and 15' (+1)")
_J("18", +5, "SHAM: '18 epochs' (STATUS, §4.0.1c, B.1, working list 15, CHANGELOG 63)")
_J("19", +3, "§1.1 'all 19 items' (+1); POWER §4.1.1 '19 served epochs' (+1); §8.4 '19 clusters' removed (-1); B.1 84.8 row (+1); CHANGELOG 60 (+1)")
_J("20", +2, "POWER §4.1.1 rewrite (-1); App B '20 / 28 of §6 item 6' (+1); CHANGELOG 60 'ITT's 20', 65 'gains (20' (+2)")
_J("2026-09-09", +1, "§1.1 first list cites out/expiracao-designados-2026-09-09.json")
_J("2026-09-10", +3, "POWER: §4.1.1 cites out/H1C-POWER-FRACIONARIA-2026-09-10.json; B.1 row cites it and SPEC-ANALISE-2026-09-10.md")
_J("2026-09-21", +1, "C12 App B row: 'per-arm counts of ITT-2026-09-21.json'")
_J("2026-10-04", +2, "path `_sprint-2026-10-04/` in the new B.1 row and the rc4 changelog header")
_J("2026-10-05", +13, "rc4 date: STATUS; C12 artifact name (§4, §6, App B, B.1, CHANGELOG x2); working list 15; CHANGELOG header; CHECK D-B1: out/C12-EMPATES-COMO-FAILURE-2026-10-05.json in §4, §7, B.1, App B, CHANGELOG 67 (+5); D-B2: working list 15 'launched 2026-10-05' -> full timestamp (-1)")
_J("20260921", +2, "C12 B.1 row: `ensaio-20260921-*.jsonl`, `episodios-ensaio-20260921.jsonl`")
_J("21", +2, "C12 §4 'Of the 21 in the window'; CHANGELOG 63 'p = 1/21'")
_J("234", +1, "TITLE/POWER: §9 opening 'sized the trial for 234 epochs'")
_J("25", +2, "C12: 25 ties already not_failure (§6 item 3, CHANGELOG 65)")
_J("28", +11, "C12: 28 ties (§4 x2, §6 item 3, §6 item 6 definition, §7, App B, B.1, CHANGELOG 64, 65 x2); CHECK D-B1: §4 'Resolving all 28 ties' (+1)")
_J("3", +5, "C12: '3 of the 28 ties change a label' (§4, §6 item 3, B.1, CHANGELOG 65); CHANGELOG 65 '§6 item 3'")
_J("30", +1, "§1.1 first list: 'a 30-day window'")
_J("4", +8, "C12 '4 (treatment)' (§4, B.1, CHANGELOG 64); CHANGELOG 63 '`w = 4`'; CHECK D-B1: '4 treatment' (§4, §7, CHANGELOG 67: +3); D-B2: CHANGELOG 68 '`w = 4` set' (+1)")
_J("53", +6, "SHAM: 53 states with no reconstructible cut (§4.0.1c, B.1, working list 15, CHANGELOG 63); CHECK D-B2: §4.0.1c '(11,865 − 53)', CHANGELOG 68 (+2)")
_J("6", +4, "C12: '§6 item 6' / 'losses of item 6' (§6 item 3, App B, CHANGELOG 65 x2)")
_J("7", +10, "C12: '7 outside the window' and '7 (control)' (§4 x2, §7, B.1 x2, CHANGELOG 64 x2); CHECK D-B1: '7 control' (§4, §7, CHANGELOG 67: +3)")
_J("8", +2, "CHANGELOG 60 '11 treatment and 8 control'; CHANGELOG 63 'item 8'")
_J("84.8", +4, "POWER: fractional effective size over 19 served epochs, H1C-POWER-FRACIONARIA (§4.1.1, B.1 x2, CHANGELOG)")
_J("9", +9, "POWER: '9 control' (abstract, §1.1, §9, CHANGELOG 60 x2, 61: +6); §4.1.1 rewrite (-1); CHANGELOG 63 'item 9' (+1); B.1 '9 control epochs' (+1); CHECK D-B2: CHANGELOG 68 'items 9 and 15', 'Item 9's' (+2)")
_J("90.2", +1, "CHANGELOG 60: whole-epoch 11T/8C agrees (90.2)")
_J("91.49", +2, "POWER: §4.1.1 'at 91.49 the verdict flips' (+1); CHANGELOG 60 (+1)")
_J("95.26", +5, "POWER: critical effective size (abstract, §4.1.1, §9, CHANGELOG 60 x2)")
_J("96.4", +4, "POWER: the spec's own 9-control case, SPEC-ANALISE §3 '96,4' (§4.1.1, B.1 x2, CHANGELOG 60)")
_J("96.41", +3, "POWER: whole-epoch 11T/9C (abstract, §9, CHANGELOG 60)")

_J("0.0208", +4, "CHECK D-B1: four-vote H1c point difference under the paper's rule, C12-EMPATES-COMO-FAILURE (§4, §7, B.1, CHANGELOG 67)")
_J("0.0266", +5, "CHECK D-B1: the same with ties resolved as failure (§4 x2: measured and first order, §7, B.1, CHANGELOG 67)")
_J("11,865", +4, "CHECK D-B2: §4.0.1c '(11,865 − 53)'; CHANGELOG 68 x3 (struck item 9 text quoted, '11,865 − 53', '11,865 / 36 h')")
_J("2026-10-05T09:39:53Z", +5, "CHECK D-B2: job-janela2 relaunch, JANELA-LANCAMENTO.md 'Relançamento' (STATUS, §4.0.1c, working list 15, B.1, CHANGELOG 68)")
_J("2026-10-07T03:00Z", +5, "CHECK D-B2: job-janela2 ETA, JANELA-LANCAMENTO.md 'Relançamento' (STATUS, §4.0.1c, working list 15, B.1, CHANGELOG 68)")
_J("27.78", +4, "CHECK D-B1: treatment tied-opportunity HT weight, C12 por_braco.treatment.empates_oportunidade_peso (§4, §7, B.1, CHANGELOG 67)")
_J("36", +2, "CHECK D-B2: CHANGELOG 68 quotes 'about 36 h' and '11,865 / 36 h'")
_J("36.73", +4, "CHECK D-B1: control tied-opportunity HT weight 36.725, C12 por_braco.control.empates_oportunidade_peso (§4, §7, B.1, CHANGELOG 67)")

# ---------------------------------------------------------------- headings
HEADINGS = {
    "# Under-powered by construction: intention-to-treat results from a pre-registered interventional trial of agent-memory dosing":
        ("# A registration that outlived its intervention: a pre-registered randomized trial of memory dosing in a production agent fleet", "TITLE"),
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
    for name, t in (("rc3", old), ("rc4", new)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        if name == "rc4":
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
            fails.append(f"forbidden: pattern {pat!r} occurs {n3} times in rc4 against {n2} in rc3")
    if verbose:
        print(f"numeric tokens changed: {len(changed)} (justified entries: {len(JUSTIFIED)})")
        print(f"headings: {len(h3)} in rc4, {sum(1 for h in h2 if h in HEADINGS)} renamed (allowed)")
        print(f"dangling internal § refs: rc3 {sum(d2.values())}, rc4 {sum(d3.values())}, new {sum(added.values())}")
    return fails


def main():
    old, new = open(OLD, encoding="utf-8").read(), open(NEW, encoding="utf-8").read()
    if "--report" in sys.argv:
        a, b = numbers(old), numbers(new)
        print("APPEARED", sorted((b - a).items()))
        print("DISAPPEARED", sorted((a - b).items()))
        print("DANGLING rc3", dict(dangling_refs(old)), "rc4", dict(dangling_refs(new)))
        return 0
    if "--self-test" in sys.argv:
        mutations = [
            ("number changed (96.41 -> 96.14 once)", new.replace("96.41", "96.14", 1)),
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
        print(f"unmutated rc4: {'PASS' if not base else 'FAIL'}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
