#!/usr/bin/env python3
"""Mechanical parity check, paper v1.0.3 baseline vs v1.0.4 (writing pass).

Usage: parity-v104.py BASELINE.md NEW.md
Exit 0 only if every invariant matches. The version line on the first page is
the one intended non-prose change: it is removed from both texts before the
comparison and checked separately (format kept, v1.0.3 -> v1.0.4).
"""
import re, sys, collections, pathlib

VERSION_RE = re.compile(r'^\*\*Version\*\* v(\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\) — changelog in `paper/CHANGELOG\.md`$', re.M)

def strip_version(t):
    m = VERSION_RE.search(t)
    if not m:
        return t, None
    return t[:m.start()] + '<<VERSION>>' + t[m.end():], m.groups()

CHECKS = {
    'numeric tokens (multiset, sign/% attached)': lambda t: re.findall(r'[+\-−±]?\d+(?:[.,]\d+)*%?', t),
    'numeric tokens (multiset, digits only)':     lambda t: re.findall(r'\d+(?:[.,]\d+)*', t),
    'footnote markers [^x] (multiset)':           lambda t: re.findall(r'\[\^[^\]\s]+\]', t),
    'footnote definitions (lines, byte-exact)':   lambda t: re.findall(r'^\[\^[^\]]+\]:.*$', t, re.M),
    '§ references (multiset)':                    lambda t: re.findall(r'§\s?\d+(?:\.\d+)*', t),
    'backtick spans (multiset)':                  lambda t: re.findall(r'`[^`\n]+`', t),
    # The manuscript writes links as bare host/path text (no scheme, no [..](..)),
    # so the check also catches host-like targets, DOIs and arXiv ids.
    'link targets (multiset)':                    lambda t: (re.findall(r'\]\(([^)\s]+)\)', t)
                                                             + re.findall(r'https?://[^\s)>\]`"]+', t)
                                                             + re.findall(r'(?<![\w/.])(?:[a-z0-9-]+\.)+(?:com|org|io|ai|net|dev|co|edu)/[^\s)>\]`",;]*', t, re.I)
                                                             + re.findall(r'\b10\.\d{4,9}/[^\s)>\]`",;]+', t)
                                                             + re.findall(r'arxiv[:.][^\s)>\]`",;]+', t, re.I)),
}
ORDERED = {
    'headings (ordered list, byte-exact)': lambda t: [l for l in t.split('\n') if re.match(r'^#{1,6} ', l)],
}
COUNTS = {
    'table rows (lines starting with |)': lambda t: sum(1 for l in t.split('\n') if l.lstrip().startswith('|')),
    'tables (header separator rows)':     lambda t: sum(1 for l in t.split('\n') if re.match(r'^\s*\|[\s:\-|]+\|\s*$', l)),
}

def main(a, b):
    A = pathlib.Path(a).read_text(); B = pathlib.Path(b).read_text()
    A2, va = strip_version(A); B2, vb = strip_version(B)
    out = []; ok = True
    out.append(f'baseline: {a}\nnew:      {b}\n')
    out.append(f'version line: baseline {va}  new {vb}')
    if not (va and vb and va[0] == '1.0.3' and vb[0] == '1.0.4'):
        ok = False; out.append('  FAIL version line missing or not 1.0.3 -> 1.0.4')
    else:
        out.append('  ok (format kept; excluded from the checks below)')
    for name, f in CHECKS.items():
        ca, cb = collections.Counter(f(A2)), collections.Counter(f(B2))
        same = ca == cb
        ok &= same
        out.append(f'{"ok  " if same else "FAIL"} {name}: baseline {sum(ca.values())} ({len(ca)} distinct) / new {sum(cb.values())} ({len(cb)} distinct)')
        if not same:
            for k in sorted(set(ca) | set(cb), key=str):
                if ca[k] != cb[k]:
                    out.append(f'       {k!r}: baseline {ca[k]} new {cb[k]}')
    for name, f in ORDERED.items():
        la, lb = f(A2), f(B2); same = la == lb; ok &= same
        out.append(f'{"ok  " if same else "FAIL"} {name}: baseline {len(la)} / new {len(lb)}')
        if not same:
            for x, y in zip(la, lb):
                if x != y: out.append(f'       - {x}\n       + {y}')
    for name, f in COUNTS.items():
        na, nb = f(A2), f(B2); same = na == nb; ok &= same
        out.append(f'{"ok  " if same else "FAIL"} {name}: baseline {na} / new {nb}')
    # references block must be byte-identical
    ka = A2.find('\n## References and Footnotes'); kb = B2.find('\n## References and Footnotes')
    same = ka >= 0 and kb >= 0 and A2[ka:] == B2[kb:]; ok &= same
    out.append(f'{"ok  " if same else "FAIL"} references/footnotes block byte-identical ({len(A2)-ka if ka>=0 else -1} bytes)')
    # descriptive (not invariants)
    out.append('')
    out.append('descriptive (not invariants):')
    for lab, rx in (('em-dashes', '—'), ('bold markers **', r'\*\*')):
        out.append(f'  {lab}: baseline {len(re.findall(rx, A2))} / new {len(re.findall(rx, B2))}')
    out.append(f'  words: baseline {len(A2.split())} / new {len(B2.split())}')
    out.append(f'  lines: baseline {A.count(chr(10))} / new {B.count(chr(10))}')
    out.append('')
    out.append('RESULT: ' + ('PASS — all invariants identical' if ok else 'FAIL'))
    print('\n'.join(out))
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
