#!/usr/bin/env python3
"""Bind every number in DATA-NOTE.md to the metric or README statement it reports.

    python3 parity.py numbers.json [DATA-NOTE.md]
    python3 parity.py --selftest numbers.json [DATA-NOTE.md]

Each entry of BINDINGS is a regular expression that matches one passage of the note and
captures its numbers, plus one source per captured group:

    ("k", key)          the value of numbers.json[key] (from analysis.py), compared at the
                        text's own rounding
    ("k", key, scale)   the same, multiplied by scale (1e6 for micro-USD)
    ("readme", value)   a statement of the dataset README that is not a function of the rows
                        (the defect count, the canary period, the cross-check row count...)
    ("lit", value)      an identifier or date of the note itself (version, status date)

A spelled-out number ("two dates") is captured as a word and compared as an integer.
CONDITIONS check facts the passage states in words ("all query embeddings").

The check fails if (a) a captured number differs from its source, (b) a binding no longer
matches the text (the passage changed), or (c) a number in the text is covered by no binding
and no entry of IGNORE. IGNORE holds only references that are not quantities: section, table,
figure and citation numbers, defect labels, clock times, block labels.

A non-zero decimal must show at least two significant digits; 0.1 for 0.0597 fails.
Spelled-out numbers are checked only where a binding names them; the others are not censused.
--selftest applies mutations that an earlier version of this script let pass (a value swapped
for another metric's value, a changed date, a changed spelled number) and fails unless every
one of them is caught.
"""
import json
import math
import re
import sys

WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "six": 6, "thirteen": 13}
N = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
D = r"(20\d\d-\d\d-\d\d)"
S = r"\s+"  # line breaks inside a passage


def k(key, scale=1.0):
    return ("k", key, scale)


def rd(v):
    return ("readme", v)


def lit(v):
    return ("lit", v)


def row(label, *keys, scales=None):
    cells = r" \| ".join(N for _ in keys)
    scales = scales or [1.0] * len(keys)
    return (r"\| " + label + r" \| " + cells + r" \|", [k(x, s) for x, s in zip(keys, scales)])


AMORT = [1.0, 1e6, 1.0, 1e6]  # Table 2: queries, micro-USD per query, queries, micro-USD per query

BINDINGS = [
    # Status block
    (r"Status \(" + D + r"\)", [lit("2026-10-13")]),
    (r"Busnello, L\. A\. \((2026)\)", [lit(2026)]),
    (r"\(" + N + r"-day window, " + D + r" to " + D + r"\)",
     [k("days_with_rows"), rd("2026-08-07"), rd("2026-09-08")]),
    (r"version\s*>?\s*(1\.0\.0), Zenodo", [lit("1.0.0")]),
    # Abstract
    (r"public dataset of " + N + r" external", [k("raw_calls")]),
    (r"recorded over " + N + r" days", [k("days_with_rows")]),
    (r"Construction is " + N + r"% of calls and " + N + r"% of estimated cost",
     [k("raw_construction_pct_calls"), k("raw_construction_pct_cost")]),
    (r"costs about " + N + r" times as much", [k("construction_to_query_cost_ratio")]),
    (r"stays" + S + r"between " + N + r"% and " + N + r"% whether",
     [k("raw_construction_pct_cost"), k("clean_construction_pct_cost")]),
    (r"instrument\. " + N + r"% of query calls", [k("query_annotated_pct")]),
    (r"a " + N + r"-day stretch" + S + r"with no recorded", [k("write_silent_days")]),
    (r"estimated USD " + N + r", which is USD " + N + r" per day",
     [k("raw_cost"), k("usd_per_day")]),
    (r"dataset's" + S + N + r" documented defects", [rd(16)]),
    # Specifications
    (r"Raw \(" + N + r" columns\)", [k("columns")]),
    (r"UTC, " + N + r" days", [k("days_with_rows")]),
    (r"host migration on " + D, [rd("2026-08-23")]),
    # 1. Data description
    (N + r" rows," + S + N + r" columns\)", [k("raw_calls"), k("columns")]),
    (r"the " + N + r" known defects", [rd(16)]),
    (r"recomputes " + N + r" values", [rd(108)]),
    (r", " + N + r" values\)", [k("callers")]),
    (r"for " + N + r"% of rows", [k("tokens_estimated_pct")]),
    (r"(Two) models occur", [k("models")]),
    # 2. Methods
    (r"deployed on " + D, [k("first_row_date")]),
    (r"\(" + N + r" rows\)\.\s*\n\n\*Annotations", [rd(3278)]),
    (r"smoke test \(" + N + r" rows\)", [k("smoke_rows")]),
    (r"monitoring canary \(" + N + r" rows\)", [k("query_canary")]),
    (r"window on " + D + r" \(" + N + r" rows\)", [rd("2026-08-10"), k("query_aug10")]),
    (N + r" rows arrive about every " + N + r" s", [k("aug10_other_rows"), rd(30)]),
    (r"and " + N + r" form a burst", [k("aug10_burst_rows")]),
    (r"means all " + N + r" rows and \*unflagged\*" + S + r"means the " + N + r" rows",
     [k("raw_calls"), k("clean_calls")]),
    # 3. First reading
    (r"flagged rows are " + N + r" calls and " + N + r"% of" + S + r"estimated cost",
     [k("annotated_rows"), k("annotated_cost_pct")]),
    row("construction", "raw_construction_calls", "raw_construction_pct_calls", "raw_construction_pct_cost",
        "clean_construction_calls", "clean_construction_pct_calls", "clean_construction_pct_cost"),
    row("query", "raw_query_calls", "raw_query_pct_calls", "raw_query_pct_cost",
        "clean_query_calls", "clean_query_pct_calls", "clean_query_pct_cost"),
    row("maintenance", "raw_maintenance_calls", "raw_maintenance_pct_calls", "raw_maintenance_pct_cost",
        "clean_maintenance_calls", "clean_maintenance_pct_calls", "clean_maintenance_pct_cost"),
    (r"\| total \| " + N + r" \| \| USD " + N + r" \| " + N + r" \| \| USD " + N + r" \|",
     [k("raw_calls"), k("raw_cost"), k("clean_calls"), k("clean_cost")]),
    (r"costs USD " + N + r" on average and a query call USD " + N + r"," + S + r"a ratio of about " + N,
     [k("usd_per_construction_call"), k("usd_per_query_call"), k("construction_to_query_cost_ratio")]),
    (r"reads " + N + r" input tokens on average and a query call" + S + N + r", a ratio of about " + N,
     [k("mean_tin_construction"), k("mean_tin_query"), k("input_token_ratio")]),
    (r"prices: " + N + r" of the " + N + r" query calls are embeddings",
     [k("query_embed_calls"), k("raw_query_calls")]),
    (r"The (three) most expensive" + S + r"calls, all digest builds, account for " + N + r"%",
     [k("top3_digest_calls"), k("top3_pct_cost")]),
    (r"falls from " + N + r"% to " + N + r"%", [k("raw_construction_pct_cost"),
                                             k("construction_pct_cost_without_top3")]),
    (r"sits in " + N + r" calls, which is " + N + r"% of the series",
     [k("calls_for_half_cost"), k("pct_calls_for_half_cost")]),
    (r"on " + N + r" of the " + N + r" days with construction, its cost" + S + r"exceeds " + N +
     r" milli-USD, and those " + N + r" days hold " + N + r"% of construction cost",
     [k("construction_days_over_10musd"), k("days_construction"), lit(10),
      k("construction_days_over_10musd"), k("construction_cost_pct_on_those_days")]),
    (r"Shaded:" + S + D + r" to " + D + r", the " + N + r" days",
     [k("write_silent_first"), k("write_silent_last"), k("write_silent_days")]),
    (r"It is " + N + r"% of calls and " + N + r"% of" + S + r"cost, and it ran on " + N + r" of the " + N + r" days",
     [k("raw_maintenance_pct_calls"), k("raw_maintenance_pct_cost"), k("days_maintenance"), k("days_with_rows")]),
    (r"inside" + S + r"the " + N + r"-day stretch with no recorded construction", [k("write_silent_days")]),
    (r"so its ratio is (zero)", [k("amort_raw_block4")]),
    (r"ratio is " + N + r" or " + N + r" µUSD per query",
     [k("amort_raw_block2", 1e6), k("amort_clean_block2", 1e6)]),
    row(r"1 \(Aug 7–13\)", "amort_raw_block1_queries", "amort_raw_block1",
        "amort_clean_block1_queries", "amort_clean_block1", scales=AMORT),
    row(r"2 \(Aug 14–20\)", "amort_raw_block2_queries", "amort_raw_block2",
        "amort_clean_block2_queries", "amort_clean_block2", scales=AMORT),
    row(r"3 \(Aug 21–27\)", "amort_raw_block3_queries", "amort_raw_block3",
        "amort_clean_block3_queries", "amort_clean_block3", scales=AMORT),
    row(r"4 \(Aug 28–Sep 3\)", "amort_raw_block4_queries", "amort_raw_block4",
        "amort_clean_block4_queries", "amort_clean_block4", scales=AMORT),
    row(r"5 \(Sep 4–7\)", "amort_raw_block5_queries", "amort_raw_block5",
        "amort_clean_block5_queries", "amort_clean_block5", scales=AMORT),
    (r"USD " + N + r" in total, for one shared store serving (six)" + S + r"agents: USD " + N +
     r" per day over the " + N + r" days, of which the first covers only " + N + r" hours",
     [k("raw_cost"), rd(6), k("usd_per_day"), k("days_with_rows"), k("first_day_hours_covered")]),
    # 4. Second reading
    (r"breaks down the " + N + r" query rows\." + S + N + r" of them, or " + N +
     r"%, carry a flag; the canary signature alone accounts for " + N + r", or " + N + r"%\." + S +
     r"That leaves " + N + r" unflagged query rows, " + N + r"% of the phase",
     [k("raw_query_calls"), k("query_annotated"), k("query_annotated_pct"), k("query_canary"),
      k("query_canary_pct"), k("query_unannotated"), k("query_unannotated_pct")]),
    (N + r" of them fall between 02:00 and 02:59 UTC on " + N + r" dates",
     [k("nightly_unflagged_query_rows"), k("nightly_dates")]),
    row("canary signature", "query_canary", "query_canary_pct"),
    (r"\| " + D + r" night window \| " + N + r" \| " + N + r" \|",
     [rd("2026-08-10"), k("query_aug10"), k("query_aug10_pct")]),
    row("smoke test", "query_smoke", "query_smoke_pct"),
    row("unflagged", "query_unannotated", "query_unannotated_pct"),
    (r"\| total \| " + N + r" \| " + N + r" \|", [k("raw_query_calls"), lit(100)]),
    (r"\*(Thirteen) days with no recorded writes", [k("write_silent_days")]),
    (r"From " + D + r" to " + D + r", " + N + r" days", [k("write_silent_first"), k("write_silent_last"),
                                                       k("write_silent_days")]),
    (r"and " + N + r"% of them match the" + S + r"canary", [k("write_silent_canary_pct")]),
    (r"occurs on " + N + r" of the " + N + r" days and maintenance on " + N,
     [k("days_construction"), k("days_with_rows"), k("days_maintenance")]),
    (r"holds exactly (one) ", [k("kg_extract_rows")]),
    (r"it fires every " + N + r" minutes, and no gap between consecutive rows exceeds " + N +
     r" minutes" + S + r"except (two)", [rd(30), lit(32), k("gaps_over_32min")]),
    (N + r" calls failed, all query embeddings, on (two) dates", [k("failed_calls"), k("failed_dates")]),
    (r"only from " + N + r"% to " + N + r"%, and cuts the query" + S + r"call count from " + N + r" to " + N,
     [k("raw_construction_pct_cost"), k("clean_construction_pct_cost"), k("raw_query_calls"),
      k("clean_query_calls")]),
    # 5 and back matter
    (r"one provider and " + N + r" days", [k("days_with_rows")]),
    (r"full list of " + N + r" defects", [rd(16)]),
    (r"version (1\.0\.6)\. Zenodo", [lit("1.0.6")]),
    (r"cites version (1\.0\.2)", [rd("1.0.2")]),
]

# Facts the text states in words, checked against numbers.json.
CONDITIONS = [
    (r"all query embeddings, on two dates", "failed_not_query_embed", 0),
    (r"it is the smoke test", "kg_extract_non_smoke", 0),
    (r"all digest builds", "top3_digest_calls", 3),
    (r"Phase is derived from the call site", "phase_rule_mismatches", 0),
    (r"so its ratio is zero", "amort_clean_block4", 0),
]

IGNORE = [
    r"Table \d", r"Figure \d", r"Section \d", r"\[\d\]", r"^#+ \d\.", r"\bD\d+\b", r"\d\d:\d\d",
    r"SHA-256", r"CC BY 4\.0", r"arXiv:\d+\.\d+", r"[Bb]locks? \d(–\d)?", r"\| [1-5] \((?:Aug|Sep)[^)]*\)",
    r"rc2", r"\b2026\.(?=\s)",
]
TOKEN = re.compile(r"(?<![\w.])(20\d\d-\d\d-\d\d|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)*)(?![\w])")


def mask(text):
    """Blank out code spans, URLs and pandoc attributes; keep offsets."""
    for pat in (r"`[^`]*`", r"https?://\S+", r"\{width=[^}]*\}"):
        text = re.sub(pat, lambda m: " " * len(m.group(0)), text)
    return text


def same(tok, value):
    if isinstance(value, str):
        return tok == value
    t = tok.replace(",", "")
    if t.lower() in WORDS:
        return WORDS[t.lower()] == value
    dec = len(t.split(".")[1]) if "." in t else 0
    if dec and float(t) != 0 and len(t.replace(".", "").lstrip("0")) < 2:
        return False  # a decimal shown with one significant digit hides the value (0.1 for 0.06)
    return math.isclose(round(value, dec), float(t), abs_tol=10 ** -(dec + 6))


def source_value(src, m):
    if src[0] == "k":
        v = m[src[1]]
        return v * src[2] if isinstance(v, (int, float)) and src[2] != 1.0 else v
    return src[1]


def census(text, m):
    t = mask(text)
    errors, covered = [], []
    for pat, srcs in BINDINGS:
        hits = list(re.finditer(pat.replace(" ", r"\s+"), t, flags=re.M))  # a space may be a line break
        if not hits:
            errors.append(f"binding no longer matches the text: {pat[:70]}")
            continue
        for h in hits:
            assert len(h.groups()) == len(srcs), pat
            for i, src in enumerate(srcs, 1):
                want = source_value(src, m)
                if not same(h.group(i), want):
                    errors.append(f"{h.group(i)!r} should be {want!r} ({src[0]}:{src[1]})  in: "
                                  + " ".join(h.group(0).split())[:90])
                covered.append(h.span(i))
    for pat, key, val in CONDITIONS:
        if not re.search(pat, t):
            errors.append(f"condition passage missing: {pat}")
        elif m[key] != val:
            errors.append(f"'{pat}' requires {key} == {val}, got {m[key]}")
    ign = [h.span() for p in IGNORE for h in re.finditer(p, t, flags=re.M)]
    for h in TOKEN.finditer(t):
        a, b = h.span(1)
        if any(x <= a and b <= y for x, y in covered + ign):
            continue
        ctx = " ".join(t[max(0, a - 40):b + 20].split())
        errors.append(f"unbound number {h.group(1)!r}  in: {ctx}")
    return errors


MUTATIONS = [  # (old, new): each must make the census fail
    ("55.7% of estimated cost", "30.5% of estimated cost"),
    ("32 calls failed", "13 calls failed"),
    ("a query call USD 0.0000123", "a query call USD 12.3026559"),
    ("serving six", "serving nine"),
    ("96.3% of them match", "92.0% of them match"),
    ("From 2026-08-25 to", "From 2026-08-24 to"),
    ("on two dates", "on three dates"),
    ("| smoke test | 2 | 0.060 |", "| smoke test | 2 | 0.1 |"),
    ("maintenance on 11.", "maintenance on 13."),
    ("ratio of about 67", "ratio of about 55"),
]


def main():
    args = sys.argv[1:]
    selftest = bool(args) and args[0] == "--selftest"
    if selftest:
        args = args[1:]
    m = json.load(open(args[0]))
    text = open(args[1] if len(args) > 1 else "DATA-NOTE.md").read()
    errors = census(text, m)
    if selftest:
        assert not errors, "the unmutated note must pass first:\n" + "\n".join(errors)
        missed = []
        for old, new in MUTATIONS:
            assert text.count(old) == 1, f"mutation anchor not unique: {old}"
            if not census(text.replace(old, new), m):
                missed.append(f"{old} -> {new}")
        print(f"selftest: {len(MUTATIONS) - len(missed)}/{len(MUTATIONS)} mutations caught")
        for x in missed:
            print("   MISSED:", x)
        sys.exit(1 if missed else 0)
    print(f"bindings: {len(BINDINGS)}  conditions: {len(CONDITIONS)}  errors: {len(errors)}")
    for e in errors:
        print("  ", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
