#!/usr/bin/env python3
"""Two layout defects that pull in OPPOSITE directions, measured together.

A heading stranded at the foot of a page promises text that is not there. The
obvious cure — demand more free space before every heading — buys that at the
cost of pages left half empty. Neither number means anything alone, which is why
this gate reports both and why `\\needspace` in preamble-prereg.tex was calibrated
against the pair (4 -> 2 stranded / 5 short, 8 -> 1 / 6, 13 -> 0 / 5, 16 -> 0 / 7).

Headings are read from the MARKDOWN, not guessed from the PDF by a regex on
numbering: the first version of this probe matched "6. What would falsify each
claim" by its leading digits and reported zero problems on a PDF that had one.

Exit 1 if any heading is stranded. Short pages are reported, never fatal: some
are legitimate (a section that genuinely ends there).

  ./check-layout.py <pdf> <markdown>
"""
import re
import subprocess
import sys
from pathlib import Path

SHORT_PAGE = 0.80          # of the fullest page's line count


def headings(md_path):
    out, in_code = [], False
    for line in Path(md_path).read_text(encoding="utf-8").split("\n"):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            out.append((len(m.group(1)), re.sub(r"[*`_]", "", m.group(2)).strip()))
    return out


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def main(pdf, md):
    heads = {norm(t): lv for lv, t in headings(md)}
    text = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", pdf, "-"],
                          capture_output=True).stdout.decode()
    pages = [p for p in text.split("\f") if p.strip()]
    stranded, heights = [], []
    for i, page in enumerate(pages, 1):
        body = [l.rstrip() for l in page.split("\n")
                if l.strip() and not re.fullmatch(r"\s*\d+\s*", l)]
        heights.append(len(body))
        for pos, where in ((-1, "last"), (-2, "second-to-last")):
            if len(body) < abs(pos):
                continue
            n = norm(body[pos])
            for h, lv in heads.items():
                if n == h or (len(n) > 12 and h.startswith(n)):
                    stranded.append(f"page {i}, {where} line, H{lv}: {body[pos].strip()[:60]}")
                    break
    fullest = max(heights)
    short = [(i + 1, h) for i, h in enumerate(heights)
             if h < SHORT_PAGE * fullest and i + 1 != len(pages)]
    print(f"{len(heads)} headings · {len(pages)} pages · fullest page {fullest} lines")
    for s in stranded:
        print(f"  STRANDED  {s}")
    print(f"  short pages (under {SHORT_PAGE:.0%}, last page excluded): "
          f"{len(short)} {[f'p{i}:{h}' for i, h in short]}")
    print("PASS: no heading at a page foot" if not stranded else f"FAIL: {len(stranded)} stranded")
    return 1 if stranded else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
