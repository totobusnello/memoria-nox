#!/usr/bin/env python3
"""Parity check rc8 -> rc9 of Paper A after a prose-only writing pass (avoid-ai-writing).

Usage:
    python3 parity-rc9.py [OLD] [NEW]            # default: A-v1.1-rc8.md vs A-v1.1-rc9.md
    python3 parity-rc9.py --selftest [OLD] [NEW]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc9 is a writing pass: it may reword prose and nothing else. The only content it adds is the
F-5 "Addendum, rc9 (writing pass ...)" paragraph, which is cut out of NEW (between its header and
"## Open items") before every check below; the "addendum" check requires that it exists exactly
once, right after the rc8 addendum and right before "## Open items".

Checks, all OLD vs NEW-without-the-rc9-addendum (modelled on A-rc3/parity-rc3.py):

  numbers     multiset of numeric tokens + cardinal number words two..twenty/hundred/...
  footnotes   multiset of [^x] markers and correction back-references (↩ F-x)
  refs        multiset of §n(.n)*, Appendix X / F-n, App. X, Table/Figure/Proposition/Corollary n
  code        multiset of inline backtick spans, and fenced code blocks byte for byte
  links       multiset of markdown link targets, bare URLs and DOIs
  headings    ordered list of heading lines, byte for byte (the title included)
  tables      ordered list of table rows, byte for byte
  history     the F-5 addenda rc5..rc8 (from "**Addendum, rc5" to the rc9 addendum) byte-identical
  qualifiers  whitespace-normalized count of every rc6-rc8 scope qualifier is unchanged
  classes     none of the forbidden phrasings of A-rc8/parity-rc8.py (imported, not copied, so the
              list cannot drift; 33 inherited from rc6/rc7 + 2 from rc8) occurs in NEW outside the
              F-5 addenda, which quote them as history
  dashes      em dashes in running prose, outside the carve-outs (table rows, headings, fences,
              blockquotes, quoted spans "..." / *"..."*, F-3 run-in labels), must be <= PROSE_DASH_MAX
  addendum    the rc9 addendum exists exactly once, in place

--selftest first requires OLD vs NEW to pass, then applies one mutation per check to NEW (or to
OLD for none) and requires each mutated copy to FAIL on the expected check.
"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OLD = HERE.parent / "A-v1.1-rc8.md"
DEFAULT_NEW = HERE.parent / "A-v1.1-rc9.md"

# --- the rc8 class list, imported from the rc8 gate ------------------------------------------
_spec = importlib.util.spec_from_file_location("parity_rc8", HERE.parent / "A-rc8" / "parity-rc8.py")
_rc8 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc8)
FORBIDDEN = list(_rc8.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 33 + 2 forbidden phrasings from parity-rc8, got {len(FORBIDDEN)}"

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC8_ADDENDUM = "**Addendum, rc8 (2026-10-05)"
RC9_ADDENDUM = "**Addendum, rc9 (writing pass"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# Scope qualifiers added in rc6-rc8 (and eligibility/pinning wording) that must survive unchanged.
QUALIFIERS = [
    "lower bound on non-delivery by the brief and by tracked search",
    "lower bound on non-delivery by the brief and tracked search",
    "non-delivery across all agent-facing search is not established",
    "not established",
    "in the measured regime",
    "in that regime",
    "holding eligibility fixed",
    "with eligibility held fixed",
    "within `last_served` ties",
    "path patterns, the importance/pain floor and age windows",
    "path patterns, an importance floor and age windows",
    "two path patterns, an importance floor and an age",
    "the importance/pain floor",
    "whoever initiated",
    "phase 0",
    "phase 1",
    "before the F6 quota pass",
    "after the pinned",
    "toward `mainTarget`",
]

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
QUOTED_RE = re.compile(r'\*"[^"]*"\*|"[^"\n]*"|«[^»]*»')


def split_fences(text):
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


def cut_rc9_addendum(new):
    """Return (new_without_rc9_addendum, problem_or_None)."""
    n = new.count(RC9_ADDENDUM)
    if n != 1:
        return new, f"rc9 addendum header occurs {n} times (expected 1)"
    a = new.find(RC9_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r8 = new.find(RC8_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc9 addendum"
    if r8 < 0 or r8 > a:
        return new, "rc9 addendum is not after the rc8 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc9 addendum and '## Open items'"
    stripped = new[:a].rstrip("\n") + "\n" + new[b:]
    return stripped, None


def history(text):
    a = text.find(ADDENDA_START)
    b = text.find(OPEN_ITEMS, a)
    return text[a:b] if a >= 0 and b >= 0 else None


def outside_addenda(text):
    a = text.find(ADDENDA_START)
    b = text.find(OPEN_ITEMS, a) if a >= 0 else -1
    if a < 0 or b < 0:
        return text, False
    return text[:a] + text[b:], True


def prose_dashes(text):
    hits, fence = [], False
    for i, line in enumerate(text.split("\n"), 1):
        s = line.lstrip()
        if s.startswith("```"):
            fence = not fence
            continue
        if fence or s.startswith(("|", "#", ">")):
            continue
        body = QUOTED_RE.sub("", line)
        body = re.sub(r"^\*\*F-\d+(?:\.\d+)?\b[^*]*\*\*", "", body.strip())
        for _ in range(body.count("—")):
            hits.append(i)
    return hits


def norm(s):
    return re.sub(r"\s+", " ", s)


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


def compare(old, new):
    """Return {check: (ok, size, detail)}."""
    results = {}
    stripped, problem = cut_rc9_addendum(new)
    results["addendum"] = (problem is None, 1, problem or "")
    a, b = extract(old), extract(stripped)
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
    # history: addenda rc5..rc8 untouched
    ho, hn = history(old), history(stripped)
    results["history"] = (ho is not None and ho == hn, len(ho or ""),
                          "" if ho is not None and ho == hn else "F-5 addenda rc5..rc8 differ or not found")
    # qualifiers: same normalized count, outside the addenda (they quote phrasings as history)
    qo, qn = norm(outside_addenda(old)[0]), norm(outside_addenda(stripped)[0])
    bad = []
    for q in QUALIFIERS:
        co = len(re.findall(re.escape(q), qo, re.I))
        cn = len(re.findall(re.escape(q), qn, re.I))
        if co == 0:
            bad.append(f"{q!r}: absent from OLD (qualifier list is stale)")
        elif co != cn:
            bad.append(f"{q!r}: {co} -> {cn}")
    results["qualifiers"] = (not bad, len(QUALIFIERS), "; ".join(bad))
    # classes: inherited forbidden phrasings, outside the F-5 addenda of NEW (full NEW, addendum incl.)
    body, found = outside_addenda(new)
    residual = []
    if not found:
        residual.append("F-5 addenda region not found; cannot exclude quoted history")
    for fid, pat in FORBIDDEN:
        for m in re.finditer(pat, body, re.I):
            ln = body.count("\n", 0, m.start()) + 1
            residual.append(f"{fid} /{pat}/ at body line {ln}: {m.group(0)!r}")
    results["classes"] = (not residual, len(FORBIDDEN), "; ".join(residual))
    # dashes: running-prose em dashes outside carve-outs
    d = prose_dashes(stripped)
    results["dashes"] = (len(d) <= PROSE_DASH_MAX, len(d),
                         "" if len(d) <= PROSE_DASH_MAX else f"{len(d)} > {PROSE_DASH_MAX} at lines {d[:10]}")
    return results


def report(results, label):
    print(f"== {label}")
    for key, (ok, size, detail) in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key:<10} n={size}" + (f"  {detail[:400]}" if detail else ""))
    allok = all(ok for ok, _, _ in results.values())
    print(f"  => {'PARITY OK' if allok else 'PARITY BROKEN'}")
    return allok


def stats(text, label):
    words = len(re.findall(r"\S+", text))
    total = text.count("—")
    print(f"{label}: {words} words, {total} em dashes in all, {len(prose_dashes(text))} in running prose "
          f"outside carve-outs")


def first_prose(text, needle):
    """Replace position of the first occurrence of needle on a prose line (not table/heading/fence)."""
    fence, pos = False, 0
    for line in text.split("\n"):
        s = line.lstrip()
        if s.startswith("```"):
            fence = not fence
        elif not fence and not s.startswith(("|", "#")) and needle in line:
            return pos + line.find(needle)
        pos += len(line) + 1
    raise SystemExit(f"selftest: {needle!r} not on any prose line")


def sub_at(text, needle, repl):
    i = first_prose(text, needle)
    return text[:i] + repl + text[i + len(needle):]


def main(argv):
    selftest = "--selftest" in argv
    paths = [a for a in argv if not a.startswith("--")]
    old_p = Path(paths[0]) if paths else DEFAULT_OLD
    new_p = Path(paths[1]) if len(paths) > 1 else DEFAULT_NEW
    try:
        old, new = old_p.read_text(), new_p.read_text()
    except OSError as e:
        print(e)
        return 2
    print(f"OLD {old_p}\nNEW {new_p}")
    stats(old, "OLD")
    stats(cut_rc9_addendum(new)[0], "NEW (rc9 addendum cut)")
    base_ok = report(compare(old, new), "baseline OLD vs NEW")
    if not selftest:
        return 0 if base_ok else 1
    if not base_ok:
        print("SELFTEST: baseline does not pass; mutations not meaningful")
        return 1
    rc8_line = "proposed two §1 sentences, and both are taken verbatim."
    mutations = [
        ("number in prose", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("heading changed", "headings",
         lambda t: t.replace("## 7. Threats to validity", "## 7. Threats to the validity", 1)),
        ("title changed", "headings",
         lambda t: t.replace("what a production agent-memory system actually surfaces",
                             "what a production agent-memory system surfaces", 1)),
        ("§ reference in prose", "refs", lambda t: sub_at(t, "§4.3.1", "§4.3.2")),
        ("code span", "code", lambda t: sub_at(t, "`pickDedup`", "`pickDedupe`")),
        ("table row", "tables", lambda t: t.replace("| positive search counter (live) | 9,755 |",
                                                    "| positive search counter, live | 9,755 |", 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc8 addendum edited", "history",
         lambda t: t.replace(rc8_line, rc8_line.replace("taken verbatim", "taken literally"), 1)),
        ("qualifier dropped", "qualifiers",
         lambda t: sub_at(t, "which it exhausted in the measured regime", "which it exhausted")),
        ("qualifier dropped: holding eligibility fixed", "qualifiers",
         lambda t: sub_at(t, "corpus grew outside the configured path patterns. Holding eligibility fixed, an",
                          "corpus grew outside the configured path patterns. Then an")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("rc7 class 'set by eligibility' reintroduced", "classes",
         lambda t: sub_at(t, "This is a separate result,", "This is a separate result, set by eligibility,")),
        ("rc6 class 'immune' reintroduced", "classes",
         lambda t: sub_at(t, "The symmetry.** The two channels", "The symmetry.** The two immune channels")),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc9 addendum removed", "addendum",
         lambda t: t.replace(RC9_ADDENDUM, "**Note, rc9 (writing pass", 1)),
    ]
    ok = True
    for name, expect, mut in mutations:
        m = mut(new)
        if m == new:
            print(f"SELFTEST mutation '{name}': did not apply -> MISSED")
            ok = False
            continue
        res = compare(old, m)
        bit = not res[expect][0]
        failed = sorted(k for k, (good, _, _) in res.items() if not good)
        print(f"SELFTEST mutation '{name}': fails on {failed} (expect {expect}) -> {'BITES' if bit else 'MISSED'}")
        ok &= bit
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
