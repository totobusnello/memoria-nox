#!/usr/bin/env python3
"""Build the anonymized supplementary files S1-S3 for the IP&M submission.

S1 = technical report v1.0.6 (paper/paper-tecnico-nox-mem.md), S2 = Wave 2 closure and
cross-backbone analysis, S3 = operational appendices (the numbering of the manuscript). The text is copied as it stands; the only changes are
the replacements listed in RULES (author, ORCID, e-mail, DOIs, repository links, host paths,
platform and agent names) and a short header per file. Nothing is condensed or rewritten.

    python3 -I build_supplements.py           # write supplement/S1..S3
    python3 -I build_supplements.py --check   # exit 1 if the files are stale or an identifier remains
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAPER = HERE.parents[1]
OUT = HERE / "supplement"

SOURCES = {
    "S1-technical-report.md": (PAPER / "paper-tecnico-nox-mem.md",
                               "Supplementary material S1: the full technical report (anonymized)"),
    "S2-wave2-and-cross-backbone.md": (PAPER / "publication" / "supplement-wave2-and-cross-backbone.md",
                                       "Supplementary material S2: Wave 2 closure and cross-backbone analysis (anonymized)"),
    "S3-operational-appendices.md": (PAPER / "publication" / "supplement-operational-appendices.md",
                                     "Supplementary material S3: operational appendices C to G (anonymized)"),
}

HEADER = """# {title}

> Anonymized copy prepared for double-anonymized review. The author's name and identifiers, e-mail
> address, DOIs, repository links, host paths and the agents' names are replaced by neutral
> placeholders; no other word or number is changed. Inside S1, references to "supplement
> §S..." point to S2 (Wave 2 and cross-backbone analysis) and S3 (operational appendices).

"""

AGENTS = {"Nox": "Agent A", "Boris": "Agent B", "Forge": "Agent C",
          "Atlas": "Agent D", "Cipher": "Agent E", "Lex": "Agent F"}

RULES = [
    # S1 front matter: author block, DOI line and code link (lines 3-9 of the report)
    (re.compile(r"\A# (.+?)\n\n\*\*Luiz Antonio Busnello\*\*\n.*?\n---\n", re.S),
     lambda m: f"*Original title:* {m.group(1)}\n\n**Version** v1.0.6 (2026-10-04)\n\n---\n"),
    (re.compile(r"\*\*Repository:\*\* github\.com/totobusnello/memoria-nox"), "**Repository:** [withheld for review]"),
    (re.compile(r"\[?(https?://)?github\.com/totobusnello/[\w./-]*\]?(\([^)]*\))?"), "[repository withheld for review]"),
    (re.compile(r"\[?(https?://doi\.org/)?10\.5281/zenodo\.\d+\]?(\([^)]*\))?"), "[DOI withheld for review]"),
    (re.compile(r"/root/[^\s`)]*"), "<host path>"),
    (re.compile(r"TotoClaw Command Center"), "operator dashboard"),
    (re.compile(r"\b(" + "|".join(AGENTS) + r")\b"), lambda m: AGENTS[m.group(1)]),
]

FORBIDDEN = re.compile(
    r"Busnello|\bToto|Totó|\bLuiz\b|ORCID|0009-0007|generantis|nuvini|labf|totobusnello|zenodo|10\.5281"
    r"|/root/|srv\d{4,}|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    r"|[\w.+-]+@[\w-]+\.(com|br|org|ai|io)\b", re.I)
AGENT_NAMES = re.compile(r"\b(" + "|".join(AGENTS) + r")\b")  # case-sensitive: "nox-mem" is the system


def build():
    out = {}
    for name, (src, title) in SOURCES.items():
        text = src.read_text()
        for pat, rep in RULES:
            text = pat.sub(rep, text)
        out[name] = HEADER.format(title=title) + text
    return out


def residual(text):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in list(FORBIDDEN.finditer(line)) + list(AGENT_NAMES.finditer(line)):
            # section numbers like 5.1.8.1 are not IP addresses
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", m.group(0)) and re.search(r"(§|S|#)\s*" + re.escape(m.group(0)) + r"|\b" + re.escape(m.group(0)) + r" ", line):
                continue
            hits.append((i, m.group(0), line.strip()[:120]))
    return hits


def main():
    files = build()
    bad = 0
    for name, text in files.items():
        for i, tok, ctx in residual(text):
            print(f"{name}:{i}: identifier {tok!r}: {ctx}")
            bad += 1
    if "--check" in sys.argv:
        for name, text in files.items():
            p = OUT / name
            if not p.exists() or p.read_text() != text:
                print(f"{name}: stale, rerun build_supplements.py")
                bad += 1
        sys.exit(1 if bad else 0)
    if bad:
        sys.exit(f"{bad} identifier(s) remain; nothing written")
    OUT.mkdir(exist_ok=True)
    for name, text in files.items():
        (OUT / name).write_text(text)
        print(f"wrote supplement/{name} ({len(text.split()):,} words)")


if __name__ == "__main__":
    main()
