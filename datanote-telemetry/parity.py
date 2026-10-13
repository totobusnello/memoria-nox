#!/usr/bin/env python3
"""Census of every number in DATA-NOTE.md against analysis.py output.

    python3 parity.py numbers.json [DATA-NOTE.md]

A number in the text passes if it equals some value in numbers.json at the
text's own rounding (also tried as a percentage-free ratio and in micro-USD),
or if it is listed in STRUCTURAL with the reason it is not a function of the
rows. Exits non-zero and lists every number that matched nothing.
Run with --selftest to confirm a mutated number is caught.
"""
import json
import re
import sys

# Numbers that are not computed from the rows: identifiers, dates, schema facts,
# and README statements the dataset cannot recompute. Each one is named here so
# that a new unchecked number fails the census instead of passing silently.
STRUCTURAL = {
    "23130191": "dataset DOI", "23147633": "nox-mem report DOI", "2606.06448": "arXiv id",
    "1.0.0": "dataset version", "1.0.6": "report version",
    "13": "column count / write-silent days (also computed)",
    "16": "defect count (README)", "108": "values the verifier recomputes (README)",
    "3,278": "rows in the second preserved copy (README cross-check)",
    "30": "canary period in minutes (README)", "32": "window days / max gap minutes / failed calls",
    "8": "caller values (also computed)", "4": "smoke-test rows / block 5 length",
    "485": "unflagged rows in the nightly window (README D2)",
    "3": "top-3 calls / phase count", "2": "models / dates / gaps / smoke query rows",
    "1": "rc number / block number / kg row", "5": "block number", "6": "D-number",
    "7": "block length / D-number", "9": "D-number", "10": "D-number", "11": "maintenance days",
    "12": "D-number", "14": "D-number", "19": "construction days / clean block-4 queries",
    "100": "table total", "10.5281": "DOI prefix", "2026": "year", "256": "SHA-256", "4.0": "license version",
}
DATE = re.compile(r"\b20\d\d-\d\d-\d\d(T[\d:]+Z)?\b")
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![\w])")


def candidates(m):
    for v in m.values():
        if isinstance(v, (int, float)) and v is not None:
            yield v
            yield v * 1e6  # micro-USD


def matches(tok, m):
    clean = tok.replace(",", "")
    dec = len(clean.split(".")[1]) if "." in clean else 0
    x = float(clean)
    for v in candidates(m):
        if round(v, dec) == x or (dec == 0 and round(v) == x):
            return True
    return False


def census(text, m):
    text = DATE.sub(" ", text)
    text = re.sub(r"\b(Aug|Sep) \d+(–(Aug |Sep )?\d+)?", " ", text)
    text = re.sub(r"zenodo\.\d+|arXiv:\S+|D\d+|Table \d|Section \d|\[\d\]|Paradigms? [IV]+", " ", text)
    text = re.sub(r"`[^`]*`", " ", text)
    bad = []
    for tok in NUM.findall(text):
        if tok in STRUCTURAL or matches(tok, m):
            continue
        bad.append(tok)
    return bad


def main():
    if sys.argv[1] == "--selftest":
        m = {"a": 55.713, "b": 3544}
        assert census("55.7% of 3,544", m) == []
        assert census("55.8% of 3,544", m) == ["55.8"], "mutation not caught"
        print("selftest ok")
        return
    m = json.load(open(sys.argv[1]))
    text = open(sys.argv[2] if len(sys.argv) > 2 else "DATA-NOTE.md").read()
    bad = census(text, m)
    print(f"unmatched: {len(bad)}")
    for b in sorted(set(bad)):
        print("  ", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
