#!/usr/bin/env python3
"""Parity check B-v2-rc5.md -> B-v2-rc6.md (Paper B, sprint 2026-10-04; rc6 2026-10-05).

rc6 does two things to rc5 and nothing else:
  LASTRO-10  the ballast text of `LASTRO-B-item10.md` §4-§5 (working list 1, 8, 10; the
             Appendix B manifest row, the † marks, the ITT-SENSIB row, the B caveat), plus
             its bookkeeping (STATUS header, changelog items 75-78);
  PROSE      an avoid-ai-writing pass (em dashes, bold, pivots, closers) that may change
             wording only.
It also wraps the passages that depend on the whole-window sham in
`<!-- SHAM-JANELA: pending -->` ... `<!-- /SHAM-JANELA -->`, wording unchanged.

Checks (exit 1 if any fails):
  1. numbers: every numeric token whose count changes is in JUSTIFIED with the exact signed
     change and a LASTRO-10 reason; unlisted or stale justifications fail. PROSE may move
     no number.
  2. headings: identical sequence (rc6 renames nothing).
  3. section refs: no new dangling internal § ref; the multiset of § refs is unchanged.
  4. citations: [@key] set unchanged and listed in References; footnotes defined.
  5. no host, IP or personal path added.
  6. SHAM-JANELA: markers balanced, not nested, exactly EXPECTED_BLOCKS blocks, none in
     rc5; each block's content (between its markers) occurs byte-identically exactly once
     in rc5.
  7. identifiers and quotes: the multiset of `code spans` changes only by CODE_JUSTIFIED
     (LASTRO-10); quoted spans *"..."* and DOIs are unchanged.
  8. bold balance: every paragraph has an even number of `**` (the unbold pass broke none).

Usage:  python3 parity-rc6.py              # check
        python3 parity-rc6.py --report     # raw numeric and code-span diff, no verdict
        python3 parity-rc6.py --self-test  # 8 mutations of rc6 in memory; each must fail
Reads only the two manuscripts. Writes nothing.
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "B-v2-rc5.md")
NEW = os.path.join(HERE, "..", "B-v2-rc6.md")

# ---------------------------------------------------------------- tokenization (as rc5)
SECREF = re.compile(r"§§?\s?(\d+(?:\.\d+)*[a-z]?)(?:\(\d+\))?(?:[–-]§?\d+(?:\.\d+)*[a-z]?)?")
CITE = re.compile(r"\[@[^\]]+\]")
LISTNUM = re.compile(r"^(\s*)\d+\.\s", re.M)
DATE = (r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?"
        r"|\d{2}:\d{2}(?::\d{2})?Z?"
        r"|(?<![\d-])\d{2}-\d{2}(?![\d-])")
TOK = re.compile(r"(?<![A-Za-z_\d.,])(" + DATE + r"|\d+(?:[.,]\d+)*)(?![A-Za-z_\d]|\.\d)")
HEADNUM = re.compile(r"^(#{1,6} )(?:Appendix )?[A-Z]?\.?\d+(?:\.\d+)*[a-z]?", re.M)
SECCELL = re.compile(r"\|\s*(?:Abstract, )?\d+(?:\.\d+)*[a-z]?(?:\s*[,–]\s*\d+(?:\.\d+)*[a-z]?)*\s*(?=\|)")
CODE = re.compile(r"`([^`\n]+)`")
QUOTE = re.compile(r"(?<!\*)\*\".*?\"\*(?!\*)", re.S)
DOI = re.compile(r"10\.\d{4,9}/[^\s`)]+")
SECALL = re.compile(r"§§?\s?\d+(?:\.\d+)*[a-z]?(?:\(\d+\))?")
S_OPEN, S_CLOSE = "<!-- SHAM-JANELA: pending -->", "<!-- /SHAM-JANELA -->"
EXPECTED_BLOCKS = 10


def normalize(text):
    text = CITE.sub(" ", text)
    text = HEADNUM.sub(r"\1", text)
    text = SECCELL.sub("| ", text)
    text = SECREF.sub(" ", text)
    text = LISTNUM.sub(r"\1", text)
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"(?<![\d.,])(\d{1,3}) (\d{3})(?![\d,])", r"\1\2", text)
    return text


def numbers(text):
    return collections.Counter(TOK.findall(normalize(text)))


# ---------------------------------------------------------------- justifications
# Every numeric change is LASTRO-10. Locations: WL10 = the struck item 10 and its "Done"
# text (LASTRO §4); WL1 = item 1 "closed 2026-10-05"; ROW = Appendix B manifest row
# ("(2026-10-04)" dropped, LASTRO §5.1); CAV = the B caveat's first two sentences (LASTRO
# §5.4); CAV2 = its "Done" sentence ("and again 2026-10-05 13:03Z after item 10 ... 16/16");
# ST = STATUS "rc6 prepared 2026-10-05"; CL = changelog items 75-78 (LASTRO §5.5 and the
# bookkeeping of this rc). Each count was verified against MANIFESTO-LASTRO-P2.json
# (sha256 172c5382…) before writing; see APPLY-B-rc6.md.
JUSTIFIED = {}


def _J(token, delta, reason):
    assert token not in JUSTIFIED, token
    JUSTIFIED[token] = (delta, "LASTRO-10: " + reason)


_J("1", +1, "CL 76 \"item 1's caveat closed\"")
_J("10", +4, "WL10 '2026-09-09/10'; CAV2 'after item 10'; CL 75 'working list 10', CL 76 'Working list 10'")
_J("12", -1, "CAV 'copies the 12 that live outside' replaced by 'the 16' (12/12 in CAV2 kept)")
_J("13:03Z", +1, "CAV2 'again 2026-10-05 13:03Z' (RECIBO-ITEM10B-20261005T130316Z.txt)")
_J("15", +1, "WL10 'The whole-window sham (item 15)'")
_J("158", +3, "WL10 '= 158 MiB'; CAV '158 MiB'; CL 76 '158 MiB' (165 473 805 B / 2^20 = 157.8)")
_J("16", +8, "WL10 '16/16'; CAV 'the 16'; CAV2 'then 16/16' x2; CL 76 '16 copied' (12 + 4 copied)")
_J("165473", +1, "WL10 '165 473 805 bytes' = manifest bytes_totais (normalizer splits after 6 digits)")
_J("805", +1, "WL10 '165 473 805 bytes', tail group")
_J("2026-09-09", +1, "WL10 'the five out/ rows of 2026-09-09/10'")
_J("2026-09-21", +1, "CAV 'hashed the first 20 (154 MiB) on 2026-09-21' (manifest gerado_em)")
_J("2026-10-04", +1, "ROW drops '(2026-10-04)' (-1); CL header path `_sprint-2026-10-04/` x2 (+2)")
_J("2026-10-05", +5, "WL10 'Done, 2026-10-05'; WL1 'closed 2026-10-05'; CAV 'on 2026-10-05'; CAV2 'again 2026-10-05'; ST 'rc6 prepared 2026-10-05'")
_J("24", +1, "WL10 'the 24 † rows' (extensoes[0].adicionados)")
_J("26", +3, "WL10 'The other 26 are versioned, 26/26' (20 item10 + 6 item10-b)")
_J("30", +2, "WL10 '30 entries'; CAV 'appended 30 more' (24 + 6)")
_J("34", +2, "CAV 'the other 34'; CL 76 '34 versioned' (8 + 26)")
_J("4", +1, "WL10 'The 4 new ones that live outside the repository'")
_J("50", +4, "WL10 '**50** artifacts'; CAV 'for 50 artifacts'; CL 75 '50 artifacts', CL 76 '50 artifacts' (n_artefatos)")

# code spans added by LASTRO-10 text and the changelog; none may disappear
CODE_JUSTIFIED = {
    "ITT-SENSIB-PRECOMPROMETIDA.json": (+1, "WL10 'The 4 new ones … (`ITT-SENSIB-PRECOMPROMETIDA.json` and the three C12 files)'"),
    "out/": (+1, "WL10 'the five `out/` rows'"),
    "B-sham-v2/RESUMO.txt": (+1, "WL10"),
    "172c5382…": (+1, "WL10 manifest sha256"),
    "RECIBO-ITEM10-20261005T125933Z.txt": (+1, "WL10 receipt"),
    "RECIBO-ITEM10B-20261005T130316Z.txt": (+1, "WL10 receipt"),
    "origin/main": (+1, "WL10 git leg"),
    "JANELA-LANCAMENTO.md": (+1, "WL10 'not yet in it'"),
    "scripts/estende-lastro-p2.py": (+1, "CAV"),
    "_sprint-2026-10-04/LASTRO-B-item10.md": (+1, "CL header"),
    "avoid-ai-writing": (+1, "CL header"),
    "_sprint-2026-10-04/APPLY-B-rc6.md": (+1, "CL header"),
    "LASTRO-B-item10.md": (+1, "CL 75 (LASTRO §5.5 text)"),
    "job-janela2": (+1, "CL 77"),
    "<!-- SHAM-JANELA -->": (+1, "CL 77"),
    "APPLY-B-rc6.md": (+1, "CL 77"),
}

HEADINGS = {}
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
        if ref in ids or ref.rstrip("abc") in ids:
            continue
        out[ref] += 1
    return out


def body_and_refs(text):
    i = text.find("\n## References")
    j = text.find("\n## Appendix A")
    return text[:i] + text[j:], text[i:j]


def sham_blocks(text):
    """Return (blocks, errors). A block is the text strictly between its two markers."""
    blocks, errs, pos = [], [], 0
    while True:
        i = text.find(S_OPEN, pos)
        j = text.find(S_CLOSE, pos)
        if i < 0 and j < 0:
            break
        if i < 0 or (0 <= j < i):
            errs.append(f"sham: closing marker without opening at offset {j}")
            break
        k = text.find(S_CLOSE, i)
        n2 = text.find(S_OPEN, i + len(S_OPEN))
        if k < 0:
            errs.append(f"sham: opening marker at offset {i} never closed")
            break
        if 0 <= n2 < k:
            errs.append(f"sham: nested opening marker at offset {n2}")
            break
        blocks.append(text[i + len(S_OPEN):k])
        pos = k + len(S_CLOSE)
    return blocks, errs


def check(old, new, verbose=True):
    fails = []
    # 1 numbers
    a, b = numbers(old), numbers(new)
    changed = {k: b[k] - a[k] for k in set(a) | set(b) if b[k] != a[k]}
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
    for ref, n in (d3 - d2).items():
        fails.append(f"section ref: new dangling §{ref} (x{n})")
    s2, s3 = collections.Counter(SECALL.findall(old)), collections.Counter(SECALL.findall(new))
    if s2 != s3:
        fails.append(f"section ref: multiset changed: +{dict(s3 - s2)} -{dict(s2 - s3)}")
    # 4 citations and footnotes
    for name, t in (("rc5", old), ("rc6", new)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        if name == "rc6":
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
            fails.append(f"forbidden: pattern {pat!r} occurs {n3} times in rc6 against {n2} in rc5")
    # 6 SHAM-JANELA blocks
    if S_OPEN in old or S_CLOSE in old:
        fails.append("sham: rc5 already contains a marker")
    blocks, errs = sham_blocks(new)
    fails += errs
    if len(blocks) != EXPECTED_BLOCKS:
        fails.append(f"sham: {len(blocks)} blocks, expected {EXPECTED_BLOCKS}")
    for i, blk in enumerate(blocks, 1):
        n = old.count(blk)
        if n != 1:
            fails.append(f"sham: block {i} ({blk.strip()[:50]!r}…) occurs {n} times in rc5, must be exactly 1 (byte-identical)")
    # 7 identifiers, quotes, DOIs
    c2, c3 = collections.Counter(CODE.findall(old)), collections.Counter(CODE.findall(new))
    cdiff = {k: c3[k] - c2[k] for k in set(c2) | set(c3) if c3[k] != c2[k]}
    for k, d in sorted(cdiff.items()):
        if k not in CODE_JUSTIFIED or CODE_JUSTIFIED[k][0] != d:
            fails.append(f"code span: `{k}` changes by {d:+d}, not justified as such")
    for k, (d, _) in CODE_JUSTIFIED.items():
        if k not in cdiff:
            fails.append(f"code span: justification for `{k}` is stale")
    if collections.Counter(QUOTE.findall(old)) != collections.Counter(QUOTE.findall(new)):
        q2, q3 = collections.Counter(QUOTE.findall(old)), collections.Counter(QUOTE.findall(new))
        fails.append(f"quote: quoted spans changed: {[x[:60] for x in (q2 - q3)]} -> {[x[:60] for x in (q3 - q2)]}")
    if collections.Counter(DOI.findall(old)) != collections.Counter(DOI.findall(new)):
        fails.append("doi: DOI multiset changed")
    # 8 bold balance per paragraph (fenced code excluded)
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"numeric tokens changed: {len(changed)} (justified entries: {len(JUSTIFIED)}, all LASTRO-10)")
        print(f"headings: {len(h3)} in rc6, identical to rc5: {h2 == h3}")
        print(f"dangling internal § refs: rc5 {sum(d2.values())}, rc6 {sum(d3.values())}, new {sum((d3 - d2).values())}")
        print(f"SHAM-JANELA blocks: {len(blocks)} (expected {EXPECTED_BLOCKS}), byte-identical to rc5: "
              f"{sum(1 for x in blocks if old.count(x) == 1)}")
        print(f"code spans changed: {len(cdiff)} (justified: {len(CODE_JUSTIFIED)})")
        print(f"em dashes: rc5 {old.count('—')}, rc6 {new.count('—')}; "
              f"bold spans: rc5 {len(re.findall(r'[*][*].+?[*][*]', old, re.S))}, "
              f"rc6 {len(re.findall(r'[*][*].+?[*][*]', new, re.S))}")
    return fails


def main():
    old, new = open(OLD, encoding="utf-8").read(), open(NEW, encoding="utf-8").read()
    if "--report" in sys.argv:
        a, b = numbers(old), numbers(new)
        print("APPEARED", sorted((b - a).items()))
        print("DISAPPEARED", sorted((a - b).items()))
        c2, c3 = collections.Counter(CODE.findall(old)), collections.Counter(CODE.findall(new))
        print("CODE+", dict(c3 - c2), "CODE-", dict(c2 - c3))
        return 0
    if "--self-test" in sys.argv:
        blocks, _ = sham_blocks(new)
        mutations = [
            ("number changed (99.6% -> 96.6% once)", new.replace("99.6%", "96.6%", 1)),
            ("heading renamed (§4.2)", new.replace("### 4.2 H1a:", "### 4.2 H1a (revised):", 1)),
            ("dangling § ref added", new.replace("(§4.1.1). What remains", "(§4.1.9). What remains", 1)),
            ("word changed inside a SHAM-JANELA block (§4.0.1c)",
             new.replace("**Our error, stated.**", "**Our error.**", 1)),
            ("SHAM-JANELA closing marker dropped", new.replace(S_CLOSE, "", 1)),
            ("code identifier renamed outside the blocks",
             new.replace("`estimador_itt.py`, which is", "`estimador_itt2.py`, which is", 1)),
            ("quote reworded", new.replace("it underestimates failures\"*", "it may underestimate failures\"*", 1)),
            ("bold left unbalanced", new.replace("**Washout.**", "**Washout.", 1)),
        ]
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            f = check(old, mutated, verbose=False)
            print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False)
        print(f"unmutated rc6: {'PASS' if not base else 'FAIL'}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
