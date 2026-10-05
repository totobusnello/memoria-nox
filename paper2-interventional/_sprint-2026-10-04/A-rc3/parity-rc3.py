#!/usr/bin/env python3
"""Parity check between two manuscript versions after a prose-only writing pass.

Usage:
    python3 parity-rc3.py [OLD] [NEW]          # default: A-v1.1-rc2.md vs A-v1.1-rc3.md
    python3 parity-rc3.py --selftest [OLD] [NEW]

Exit 0 = parity holds; exit 1 = at least one check differs; exit 2 = usage/IO error.

What must be identical between OLD and NEW (a writing pass may reword prose, nothing else):

  numbers      multiset of numeric tokens (digits, with sign, decimal/thousands separators, %)
               plus the multiset of cardinal number words two..twenty / hundred / thousand /
               million / billion. ("one" is excluded: it is also a pronoun.)
  footnotes    multiset of footnote markers [^x] and of correction back-references (↩ F-x)
  refs         multiset of cross-references: §n(.n)*, Appendix X / Appendix F-n / App. X,
               F-n(.n) labels, Table n, Figure n, Proposition n, Corollary n
  code         multiset of inline backtick spans, and the fenced code blocks, byte for byte
  links        multiset of markdown link targets, bare URLs and DOIs
  headings     ordered list of heading lines, byte for byte
  tables       ordered list of table rows, byte for byte

--selftest proves the checker bites: it first requires OLD vs NEW to pass, then applies three
mutations to NEW in memory (a number in prose, a heading, a § reference in prose) and requires
each mutated copy to FAIL on the expected check. Exit 0 only if the baseline passes and all
three mutations are caught.
"""
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OLD = HERE.parent / "A-v1.1-rc2.md"
DEFAULT_NEW = HERE.parent / "A-v1.1-rc3.md"

NUM_RE = re.compile(r"(?<![\w.,])[−-]?\d+(?:[.,]\d+)*%?")
NUM_WORDS = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
             "fifteen sixteen seventeen eighteen nineteen twenty hundred thousand million billion").split()
NUM_WORD_RE = re.compile(r"\b(" + "|".join(NUM_WORDS) + r")\b", re.I)
FOOT_RE = re.compile(r"\[\^[^\]]+\]|↩\s*[A-Z]-[\w.]+")
REF_RE = re.compile(
    r"§\s?\d+(?:\.\d+)*"
    r"|\bAppendix(?:es)?\s+[A-H](?:-\d+(?:\.\d+)?)?\b"
    r"|\bApp\.\s*[A-H]\b"
    r"|\bF-\d+(?:\.\d+)?\b"
    r"|\b(?:Table|Figure|Proposition|Corollary)\s+\d+\b"
)
TICK_RE = re.compile(r"`[^`\n]+`")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)|(https?://[^\s)>\]]+)|(10\.\d{4,9}/[^\s`)\]]+)")


def split_fences(text):
    """Return (text_without_fences, list_of_fenced_blocks)."""
    blocks, out, cur, inside = [], [], [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if inside:
                cur.append(line)
                blocks.append("\n".join(cur))
                cur, inside = [], False
            else:
                inside, cur = True, [line]
            continue
        (cur if inside else out).append(line)
    if cur:
        blocks.append("\n".join(cur))
    return "\n".join(out), blocks


def extract(text):
    body, fences = split_fences(text)
    lines = body.split("\n")
    return {
        "numbers": Counter(NUM_RE.findall(text)) + Counter(w.lower() for w in NUM_WORD_RE.findall(text)),
        "footnotes": Counter(FOOT_RE.findall(text)),
        "refs": Counter(re.sub(r"\s+", " ", r) for r in REF_RE.findall(text)),
        "code": Counter(TICK_RE.findall(body)) + Counter(("FENCE", b) for b in fences),
        "links": Counter(next(g for g in m if g) for m in LINK_RE.findall(text)),
        "headings": [l for l in lines if re.match(r"#{1,6}\s", l)],
        "tables": [l for l in lines if l.lstrip().startswith("|")],
    }


def compare(old_text, new_text):
    a, b = extract(old_text), extract(new_text)
    results = {}
    for key in a:
        if isinstance(a[key], Counter):
            lost, gained = a[key] - b[key], b[key] - a[key]
            ok = not lost and not gained
            detail = "" if ok else f"lost={dict(lost)} gained={dict(gained)}"
            size = sum(a[key].values())
        else:
            ok = a[key] == b[key]
            detail = ""
            if not ok:
                diffs = [(i, x, y) for i, (x, y) in enumerate(zip(a[key], b[key])) if x != y][:3]
                detail = f"len {len(a[key])}->{len(b[key])}; first diffs {diffs}"
            size = len(a[key])
        results[key] = (ok, size, detail)
    return results


def report(results, label):
    print(f"== {label}")
    for key, (ok, size, detail) in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key:<9} n={size}" + (f"  {detail[:400]}" if detail else ""))
    allok = all(ok for ok, _, _ in results.values())
    print(f"  => {'PARITY OK' if allok else 'PARITY BROKEN'}")
    return allok


def first_prose_line(text, pred):
    lines = text.split("\n")
    fence = False
    for i, l in enumerate(lines):
        if l.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence or l.lstrip().startswith(("|", "#")):
            continue
        if pred(l):
            return i
    raise SystemExit("selftest: no line matches the mutation predicate")


def mutate(text, kind):
    lines = text.split("\n")
    if kind == "number":
        i = first_prose_line(text, lambda l: "83.78%" in l)
        lines[i] = lines[i].replace("83.78%", "83.87%", 1)
        expect = "numbers"
    elif kind == "heading":
        i = next(i for i, l in enumerate(lines) if l.startswith("### 4.4 "))
        lines[i] = lines[i] + " (revised)"
        expect = "headings"
    elif kind == "reference":
        i = first_prose_line(text, lambda l: "§4.3.1" in l)
        lines[i] = lines[i].replace("§4.3.1", "§4.3.2", 1)
        expect = "refs"
    else:
        raise ValueError(kind)
    return "\n".join(lines), expect, i + 1


def main(argv):
    selftest = "--selftest" in argv
    paths = [a for a in argv if not a.startswith("--")]
    old = Path(paths[0]) if len(paths) > 0 else DEFAULT_OLD
    new = Path(paths[1]) if len(paths) > 1 else DEFAULT_NEW
    try:
        old_text, new_text = old.read_text(), new.read_text()
    except OSError as e:
        print(e)
        return 2
    print(f"OLD {old}\nNEW {new}")
    base_ok = report(compare(old_text, new_text), "baseline OLD vs NEW")
    if not selftest:
        return 0 if base_ok else 1
    caught = 0
    for kind in ("number", "heading", "reference"):
        mtext, expect, lineno = mutate(new_text, kind)
        res = compare(old_text, mtext)
        bit = not res[expect][0]
        caught += bit
        report(res, f"mutation '{kind}' at NEW line {lineno} (expect FAIL on {expect})")
        print(f"  mutation {kind}: {'CAUGHT' if bit else 'MISSED'}")
    print(f"selftest: baseline {'ok' if base_ok else 'BROKEN'}, mutations caught {caught}/3")
    return 0 if (base_ok and caught == 3) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
