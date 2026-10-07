#!/usr/bin/env python3
"""Parity check B-v2-rc8.md -> B-v2-rc9.md (Paper B, sprint 2026-10-04; rc9 2026-10-05).

rc9 applies the review of rc8 (`REVIEW-B-rc8-2026-10-05.md`: Codex C1-C5, Fable F1-F7), each
finding verified first (`APPLY-B-rc9.md`). The registered analysis is now the five-switch one
(`out/ITT-REGISTRADO-v2-2026-10-05.json`: the washout leaves the session-hour denominator).

The diff is cut into hunks (difflib on lines). Every hunk must carry at least one ID, assigned
by an anchor substring of the rc9 hunk (ANCHORS):
    ST status header · C1 washout in the denominator (v2 numbers) · C2 M10 renamed / not
    computable · C3 substitution rule attribution · C4F1 chronology of the two commitments ·
    C5 stopping disclosure · F2 multiplicity under both readings · F3 deposited stopping rules
    and safety abort · F4 promotable set at w = 4 · F5 the declaration's failure clause ·
    F6 unrounded distance · STRAD boundary-straddling sessions · FIG Figure B1 ·
    APPA / APPB appendices · CL working list and changelog.

Checks (exit 1 if any fails):
  1. hunks: every hunk has an ID.
  2. numbers: every numeric token ADDED in a hunk is (a) already in rc8, or (b) derived from an
     artifact read at run time (ITT-REGISTRADO-v2, checks-rc9, f4, f3, the rc9 figure's run.json,
     and, for values kept from rc8, ITT-REGISTRADO v1 and checks-rc8), in one of the paper's
     roundings, or (c) listed in LITERALS for one of the hunk's IDs with its source.
     --report prints, per ID, every added and removed number and the class that justifies it.
  3. headline values: strings formatted from the artifacts at run time must be present.
  4. claims, outside struck text and before the working list:
     (a) no sentence presents H1a as rejected;
     (b) NEW: no sentence presents H1 as rejecting (or as a rejection) without the word
         "deposited" in the same sentence (review F2: H1 rejects only under the deposited
         reading);
     (c) no sentence says the stopping condition "was met" without "planning" in it, and no
         sentence calls the correlation of §4.6 "M10" without "registered"/"called"/"label"
         (review F4, C2);
     (d) `1 195` is never called adjudicated.
  5. headings identical except the two renames in HEADINGS (§4.2, §4.6).
  6. citations unchanged and listed; footnotes defined; DOIs unchanged.
  7. no host, IP or personal path added.
  8. SHAM-JANELA: exactly 10 blocks, byte-identical to rc8's.
  9. no REANALISE marker.
 10. quotes: every *"..."* span added occurs verbatim (bold and whitespace normalized) in rc8 or
     in a declared source document.
 11. code spans: every added span that names a file resolves on disk; added snake_case
     identifiers occur in the artifacts or sources they name.
 12. bold balance: every paragraph has an even number of `**`.

Usage:  python3 parity-rc9.py              # check
        python3 parity-rc9.py --report     # per-ID numeric deltas with their justification
        python3 parity-rc9.py --self-test  # mutations of rc9 in memory; each must fail
Reads the two manuscripts and the artifacts named above. Writes nothing.
"""
import collections
import difflib
import glob
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
REPO = P2.parent
LASTRO = Path.home() / "Backups" / "paper2-ensaio-2026-09-21"
OLD = SPRINT / "B-v2-rc8.md"
NEW = SPRINT / "B-v2-rc9.md"
ART = {
    "ITT-REGISTRADO-v2": P2 / "out" / "ITT-REGISTRADO-v2-2026-10-05.json",
    "checks-rc9": HERE / "checks-rc9.json",
    "f4-w4": SPRINT / "B-registered" / "f4-promoviveis-w4.json",
    "f3-abort": SPRINT / "B-registered" / "f3-abort-ex-post.json",
    "figB1-v2": SPRINT / "figures" / "figB1-h1a-inversao-registrado-v2.run.json",
    "ITT-REGISTRADO-v1": P2 / "out" / "ITT-REGISTRADO-2026-10-05.json",
    "checks-rc8": SPRINT / "B-rc8" / "checks-rc8.json",
    "CONCENTRATION": P2 / "out" / "CONCENTRATION-2026-08-30.json",
}
QUOTE_SOURCES = [P2 / "PROSPECTIVE-ESTIMAND-2026-08-30.md", P2 / "PREREG-DRAFT.md",
                 P2 / "ASSIGN-SEED-2026-08-30.md"]

# ---------------------------------------------------------------- tokenization (as rc7)
SECREF = re.compile(r"§§?\s?(\d+(?:\.\d+)*[a-z]?)(?:\(\d+\))?(?:[–-]§?\d+(?:\.\d+)*[a-z]?)?")
CITE = re.compile(r"\[@[^\]]+\]")
LISTNUM = re.compile(r"^(\s*)\d+\.\s", re.M)
DATE = (r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?"
        r"|\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z?"
        r"|(?<![\d-])\d{2}-\d{2}(?![\d-])")
TOK = re.compile(r"(?<![A-Za-z_\d.,])(" + DATE + r"|\d+(?:[.,]\d+)*)(?![A-Za-z_\d]|\.\d)")
HEADNUM = re.compile(r"^(#{1,6} )(?:Appendix )?[A-Z]?\.?\d+(?:\.\d+)*[a-z]?", re.M)
SECCELL = re.compile(r"\|\s*(?:Abstract, )?\d+(?:\.\d+)*[a-z]?(?:\s*[,–]\s*\d+(?:\.\d+)*[a-z]?)*\s*(?=\|)")
CODE = re.compile(r"`([^`\n]+)`")
QUOTE = re.compile(r"(?<!\*)\*\".*?\"\*(?!\*)", re.S)
DOI = re.compile(r"10\.\d{4,9}/[^\s`)]+")
S_OPEN, S_CLOSE = "<!-- SHAM-JANELA: pending -->", "<!-- /SHAM-JANELA -->"
R_ANY = re.compile(r"<!-- (?:REANALISE(?:: rewrite)?|/REANALISE) -->")
EXPECTED_SHAM = 10
EXPECTED_R = 108


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


# ---------------------------------------------------------------- hunk IDs
ANCHORS = [
    ("ST", "rc9 prepared 2026-10-05 (review of rc8 applied"),
    ("F2", "and we report the deposited primary beside it. Under the deposited"),
    ("C1", "H1a has the smallest unadjusted p-value, 0.0168"),
    ("C3", "The reported analysis combines deposited analysis provisions"),
    ("C1", "quantities *do* return intervals excluding zero, `H1a` and `H1`"),
    ("C1", "and 16.1 times at the share realized in the trial"),
    ("C4F1", "Two commitments made before the seed were not kept. One, a stopping rule"),
    ("F2", "three legs, and its test rejects under the deposited reading"),
    ("C1", "§4.2)*~~ ~~excludes zero on the locked and the"),
    ("C1", "excludes zero on all three legs once the washout leaves the denominator"),
    ("C1", "held for the percentile interval of earlier versions, not for the registered BCa; §4.2)*~~"),
    ("F1", "appended a retraction section to `ASSIGN-SEED-2026-08-30.md`"),
    ("F5", "The declaration also fixed its own consequence"),
    ("F2", "the registered test rejects under the deposited reading (alone at α = 0.05)"),
    ("F2", "under the deposited reading, H1 is the primary, tested alone"),
    ("F4", "promotable at `w = 4` re-derived from the calibration replay"),
    ("F2", "the primary: under that deposited reading it rejects"),
    ("C1", "**Washout.** Two hours from the epoch boundary. A session that starts inside it"),
    ("C2", "| **coverage and the designated-presence correlation"),
    ("F3", "**The deposited stopping rules (rc9).**"),
    ("F4", "in the planning corpus, and 44.4%"),
    ("F4", "names was met under the planning definition"),
    ("F4", "**Under the dose Epoch 1 was served at, the condition was not met (rc9).**"),
    ("C1", "measured with the washout still in the denominator"),
    ("C1", "(`out/ITT-REGISTRADO-v2-2026-10-05.json`). It imports the same blocks"),
    ("C1", "**The washout in the denominator (rc9).**"),
    ("C1", "and H1a (0.056% and 0.053%)"),
    ("C1", "| **H1a** | **0.0168**; 0.0855"),
    ("F2", "yes under the deposited reading (primary, alone at α = 0.05); no under the switch"),
    ("C1", "the offsets of the partial epochs and the washout's removal"),
    ("C1", "first threshold is 0.01 (0.0125 without H1b); 0.0168"),
    ("C1", "0.0168 against 0.05 would apply"),
    ("F2", "`H1` rejects under the deposited reading in both analyses"),
    ("C1", "(73.5% on the locked leg; 70.7% in the sensitivity analysis)"),
    ("F2", "We report it as an unexplained rejection,"),
    ("STRAD", "On the registered sensitivity that drops the sessions"),
    ("F2", "Artifacts: `out/ITT-REGISTRADO-v2-2026-10-05.json` (field `multiplicidade` holds"),
    ("C1", "(`out/ITT-REGISTRADO-v2-2026-10-05.json` for the locked leg"),
    ("C1", "*(rc9: with the"),
    ("F6", "computed from the unrounded bound −0.056038"),
    ("C2", "(H1, H1a, H1c; not the correlation of §4.6)"),
    ("C1", "### 4.2 H1a: excludes zero on every registered leg"),
    ("C1", "**Correction (rc8).** ~~The struck sentences"),
    ("C1", "**Correction (rc9).** The rc8 correction"),
    ("STRAD", "the registered\nsensitivity that drops the four sessions"),
    ("C1", "| session-hours, treatment / control | 10.75 / 3.25"),
    ("C1", "Sources: the registered locked leg from `out/ITT-REGISTRADO-v2-2026-10-05.json`"),
    ("C1", "(unadjusted `p = 0.0168`, Holm-adjusted 0.0840), and neither"),
    ("C1", "Measured under the registered window and washout"),
    ("STRAD", "the four sessions with episodes in more than one epoch (§5)"),
    ("C1", "the first two lie"),
    ("C1", "on the locked leg only, on a denominator dominated by one sparse session.~~ ~~that the"),
    ("C1", "interval it does not.)*~~ that the registered decision rule does not reject H1a."),
    ("FIG", "![Figure B1](figures/figB1-h1a-inversao-registrado-v2.svg)"),
    ("FIG", "**Figure B1. H1a's intervals exclude zero on every registered leg"),
    ("FIG", "inside the registered exposure windows and without the sessions"),
    ("C1", "`H1` returns −19.85, BCa CI"),
    ("F2", "and the registered test rejects under the deposited\nreading (`p = 0.0302`"),
    ("C1", "(`_sprint-2026-10-04/B-rc9/checks-rc9.json`, block A). This is an algebraic"),
    ("C1", "(0.396 treatment against 0.406"),
    ("C1", "observed reduction is 73.5% on the locked leg"),
    ("C1", "share gives 23.4 and 13.7 times"),
    ("C1", "16.1 and 9.4 times"),
    ("C1", "We also owe a note on our own criterion. §4.2 discards `H1a` because the registered"),
    ("C2", "### 4.6 Exploratory arm–designated-item-presence correlation"),
    ("C2", "These correlations measure designated-item presence"),
    ("C2", "was not computed for this correlation"),
    ("C2", "| **M10 as registered**"),
    ("STRAD", "| **boundary-straddling sessions**"),
    ("C1", "field `H2` (identical"),
    ("C3", "the substitute-only rule"),
    ("F4", "declared for Epoch 1 was met under its planning definition"),
    ("C1", "**Denominator.** §4.2. The exposure measure counts idleness, and long sessions"),
    ("C5", "**A stopping rule that may have been met and was not executed.**"),
    ("F1", "retracted in writing the same evening, before Epoch 1."),
    ("F4", "a declared feasibility stop, met under its planning definition"),
    ("C4F1", "that was not deposited; under H1, tested alone as the deposited reading"),
    ("F2", "only rejection under the deposited decision rules"),
    ("APPA", "omission of H2 and H3 until rc7, the washout kept in the denominator until rc8"),
    ("APPA", "~~Nine~~ Twelve"),
    ("F2", "rejects under the deposited reading (`p = 0.0302`, tested alone)"),
    ("C1", "Up to rc8 the"),
    ("C5", "reconstructed Epoch-1 coverage was below the threshold under the planning definition"),
    ("F3", "the deposited mechanical safety abort (arm-blind"),
    ("F5", "The retraction is in `ASSIGN-SEED-2026-08-30.md`, filed the"),
    ("C2", "- the registered M10 (arm × session-level"),
    ("STRAD", "- boundary-straddling sessions are not assigned"),
    ("APPB", "| `out/ITT-REGISTRADO-v2-2026-10-05.json` · `measurement/estimador_itt_registrado.py` (five switches)"),
    ("C2", "the designated-presence correlation of §4.6 with its four legs"),
    ("APPB", "| `_sprint-2026-10-04/B-rc9/checks-rc9.py` · `checks-rc9.json` |"),
    ("C2", "the whole of the correlation then called M10"),
    ("APPB", "| registered analysis: H1, H1a, H1c, every BCa interval and re-randomization p-value of the locked leg; session-hours 10.75 / 3.25"),
    ("APPB", "| the ten signatures promotable at `w = 4`"),
    ("APPB", "| 7.13 h at `09-14` with the washout in, 6.79 h without"),
    ("C2", "| `r` and all four legs of the designated-presence correlation"),
    ("APPB", "`out/ITT-REGISTRADO-v2-2026-10-05.json` (unchanged from rc8)"),
    ("APPB", "| Figure B1 (rc9): 10.75 / 3.25 h"),
    ("APPB", "The artifacts added in rc7, rc8 and rc9"),
    ("CL", "*(rc9: the correlation of"),
    ("CL", "script; *(rc9)* also `out/ITT-REGISTRADO-v2-2026-10-05.json`"),
    ("CL", "20. ~~**Review of rc8**"),
    ("CL", "been reviewed by any voice.~~ → **Done, 2026-10-05**: two full reads (Codex, Fable), both"),
    ("CL", "**rc9: review of rc8 applied**"),
    ("F4", "**Correction (rc8, qualified in rc9): a declared stopping rule was met in Epoch 1 under its planning definition"),
    ("F2", "remains an unexplained rejection under the deposited reading."),
]

# (c) literals: numbers added that are neither in rc8 nor in an artifact, with their source
LITERALS = {
    "ST": {"2026-10-05": "date of rc9"},
    "C1": {"2": "the two-hour washout (PREREG §2)", "1007": "checks-rc9 W episodios_removidos_pelo_washout",
           "6": "BCa lower bound rank (checks-rc9 bca_quantis rank 6)", "9.4": "0.430672 / 0.0455782 = 9.449",
           "5": "five switches", "0.0128": "so_washout_in_denominator H1a p_rerand",
           "0.94": "checks-rc9 outros_max 0.9393", "1.1": "figB1-v2 sessoes_ocupadas span 1.11 min",
           "8.0": "figB1-v2 sessoes_ocupadas span 8.03 min", "2026-09-08": "d37a5964 first episode (checks-rc9 S)",
           "7.149": "checks-rc9 H1_t 7.149362", "27.003": "checks-rc9 H1_c 27.003259",
           "0.056": "BCa alfa_ajustado H1 0.000561 (as %)", "0.053": "BCa alfa_ajustado H1a 0.000526 (as %)",
           "4": "four sessions / four switches", "0.0302": "v2 H1 p_rerand", "0.0168": "v2 H1a p_rerand"},
    "C2": {"5": "PREREG §5", "0.15": "TOST band", "30": "K >= 30", "95": "coverage floor 95%",
           "19": "K = 19"},
    "C3": {"10.31": "DEVIATIONS §10.31", "695": "PREREG l.695"},
    "C4F1": {"3e1c259": "commit", "2026-08-30": "retraction date", "24": "24 min 38 s", "38": "24 min 38 s",
             "52": "f4 epoch_1_inteiro cobertas w4", "37.4": "f4 0.3741", "10": "ten signatures (f4 n_promoviveis 4)",
             "7": "seven signatures", "2": "w = 2", "4": "w = 4"},
    "C5": {"2026-08-21": "abort-check run (SHADOW-ARMED)", "14": "14-day gate", "20": "epoch boundaries"},
    "F1": {"24": "24 min 38 s", "38": "24 min 38 s"},
    "F2": {"0.0302": "v2 H1 p_rerand", "6": "m = 6", "5": "m = 5", "0.0083": "0.05/6", "0.01": "0.05/5",
           "0.151": "v2 Holm m6 H1", "0.1208": "v2 Holm m5 H1", "0.0906": "v2 Holm m4 sem H1c",
           "0.0762": "atual Holm m6 H1", "0.0635": "atual Holm m5 H1", "1": "H1b as p = 1",
           "0.05": "alpha"},
    "F3": {"234": "registered N", "2026-08-21": "deployment date", "2026-08-23": "crontab snapshot",
           "2026-08-31": "crontab snapshot", "2026-09-09": "cron inventory", "14": "14-day gate",
           "3": "three epochs / three times", "20": "epoch boundaries", "696": "f3 substituicao adjudicados",
           "10": "f3 algum_painelista_S3", "1": "f3 algum_painelista_S4", "4": "S4", "7": "seven days / seven cron lines"},
    "F4": {"350": "dose-350-v3 states", "52": "f4", "37.4": "f4 0.3741", "29.8": "f4 wilson", "45.7": "f4 wilson",
           "40.6": "f4 0.4059", "48.0": "f4 0.48", "65.1": "f4 0.6514", "44.4": "f4 0.4436", "677": "f4 cobertas_w4",
           "36.7": "PROSPECTIVE threshold", "10": "ten signatures", "7": "seven", "2": "w = 2", "4": "w = 4"},
    "F5": {"2026-09-01": "Epoch 1 start"},
    "F6": {"0.056038": "atual H1c ic95 lower (unrounded)", "0.089552": "atual control H1c_prop (unrounded)",
           "0.0336": "0.0896 − 0.0560 (rounded values)"},
    "STRAD": {"0.1957": "diag leg H1 p_rerand", "4": "four sessions"},
    "FIG": {"2": "two-hour washout", "1.1": "figB1-v2", "8.0": "figB1-v2"},
    "APPA": {"2": "two-hour washout", "2026-08-21": "abort-check run", "14": "14-day gate", "20": "boundaries",
             "37.4": "f4", "32.4": "checks-rc8 D", "36.7": "threshold", "0.0302": "v2", "95": "coverage floor",
             "0.151": "v2 Holm m6", "0.1208": "v2 Holm m5"},
    "APPB": {"0.151": "v2 Holm m6", "0.1208": "v2 Holm m5", "0.0906": "v2 Holm m4", "0.0762": "atual Holm m6",
             "0.0635": "atual Holm m5", "0.056": "BCa alfa (as %)", "0.053": "BCa alfa (as %)", "6": "rank",
             "9.4": "dilution ratio", "1007": "checks-rc9 W", "638": "checks-rc9 W treatment",
             "369": "checks-rc9 W control", "2026-09-08": "d37a5964 start", "1.1": "figB1-v2", "8.0": "figB1-v2",
             "c28b064f": "v1 script sha prefix", "0.94": "outros_max 0.9393", "10": "f3", "1": "f3", "3": "S3",
             "4": "S4 / four sessions", "5": "m = 5", "0.0840": "Holm m5", "0.0672": "Holm m4",
             "0.0302": "v2", "0.0168": "v2", "2026-10-05": "date"},
    "CL": {"2026-10-05": "date", "12": "findings C1-C5 + F1-F7", "0.0302": "v2", "0.0168": "v2",
           "0.0840": "v2", "0.0672": "v2", "0.151": "v2", "0.1208": "v2", "6": "m", "5": "m", "37.4": "f4",
           "0.0335": "rc8 value", "0.0336": "rounded", "22": "working list item", "21": "working list item",
           "24": "24 min 38 s", "38": "24 min 38 s", "4": "w = 4", "95": "95% coverage"},
}

HEADINGS = {
    "### 4.2 H1a: excludes zero on a denominator dominated by one epoch, is not rejected, and bears no weight":
        ("### 4.2 H1a: excludes zero on every registered leg, is not rejected under the registered rule, and bears no weight", "C1"),
    "### 4.6 M10: arm × coverage correlation, reported unconditionally":
        ("### 4.6 Exploratory arm–designated-item-presence correlation", "C2"),
}
FORBIDDEN = [r"\b\d{1,3}(?:\.\d{1,3}){3}\b", r"/Users/", r"~/", r"/var/", r"/root/", r"/tmp/",
             r"\$NOX_", r"srv\d+", r"\.hostinger", r"@[a-z0-9-]+\.(?:com|br|ai)\b"]
EXPECTED_SHAM = 10

# ---------------------------------------------------------------- artifact-derived numbers
def leaves(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from leaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from leaves(v)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield float(o)


def forms(v):
    out = set()
    for x in (abs(v), abs(v) * 100):
        for d in range(0, 5):
            t = f"{x:.{d}f}"
            out.add(t)
            if "." in t:
                out.add(t.rstrip("0").rstrip(".") if d else t)
        if float(x).is_integer():
            out.add(str(int(x)))
    return out


def artifact_numbers():
    allowed = {}
    for name, p in ART.items():
        d = json.loads(p.read_text())
        for v in leaves(d):
            for f in forms(v):
                allowed.setdefault(f, name)
    return allowed


# ---------------------------------------------------------------- helpers
def headings(text):
    return [l.rstrip() for l in text.splitlines() if re.match(r"^#{1,6} ", l)]


def body_and_refs(text):
    i = text.find("\n## References")
    j = text.find("\n## Appendix A")
    return text[:i] + text[j:], text[i:j]


def sham_spans(text):
    spans, errs, pos = [], [], 0
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
        spans.append(text[i + len(S_OPEN):k])
        pos = k + len(S_CLOSE)
    return spans, errs


def reanalise_lines(text):
    """rc7 REANALISE blocks as (id, first line, last line), 1-based, in order."""
    out, stack, i = [], None, 0
    for m in R_ANY.finditer(text):
        ln = text.count("\n", 0, m.start()) + 1
        if m.group(0) != "<!-- /REANALISE -->":
            stack = ln
        else:
            i += 1
            out.append((f"R{i:02d}", stack, ln))
            stack = None
    return out


def hunks(old, new):
    a, b = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    rb = reanalise_lines(old)
    out = []
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal":
            continue
        ids = [r for r, s, e in rb if s <= i2 and e >= i1 + 1]
        texto8 = "\n".join(b[j1:j2])
        for aid, anc in ANCHORS:
            if anc in texto8 and aid not in ids:
                ids.append(aid)
        out.append(dict(rc7=(i1 + 1, i2), rc8=(j1 + 1, j2), ids=ids,
                        old="\n".join(a[i1:i2]), new=texto8))
    return out, rb


def strip_struck(text):
    return re.sub(r"~~.*?~~", " ", text, flags=re.S)


def fmt4(x):
    return f"{x:+.4f}".replace("-", "−") if x else "0"


def hunks(old, new):
    a, b = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal":
            continue
        texto = "\n".join(b[j1:j2])
        ids = []
        for aid, anc in ANCHORS:
            if anc in texto and aid not in ids:
                ids.append(aid)
        out.append(dict(rc8=(i1 + 1, i2), rc9=(j1 + 1, j2), ids=ids, old="\n".join(a[i1:i2]), new=texto))
    return out


def strip_struck(text):
    return re.sub(r"~~.*?~~", " ", text, flags=re.S)


def fmt2(x, sinal=False):
    t = f"{x:+.2f}" if sinal else f"{x:.2f}"
    return t.replace("-", "−")


def fmt4(x):
    return f"{x:+.4f}".replace("-", "−") if x else "0"


def headline(reg, chk, f4, f3):
    r = reg["pernas"]["registrado"]["hipoteses"]
    m = reg["multiplicidade"]["registrado"]
    dep = m["leitura_depositada"]["holm_H1a_H1b_H1c_H2x2"]
    tro = m["leitura_da_troca"]["holm_H1_H1a_H1b_H1c_H2x2_m6_m5"]
    lo, hi = r["H1c"]["ic95"]
    d = reg["pernas"]["diag_registrado_sem_sessoes_atravessadas"]["hipoteses"]["H1"]
    e4 = f4["epoch_1"]["4"]["epoch_1_inteiro"]
    return {
        "H1 p (deposited)": f"`p = {r['H1']['p_rerand']}`",
        "H1 point and BCa CI": f"{fmt2(r['H1']['dif_pontual'])}, BCa CI [{fmt2(r['H1']['ic95'][0])}; {fmt2(r['H1']['ic95'][1])}]",
        "H1a point and BCa CI": f"{fmt2(r['H1a']['dif_pontual'])} · CI [{fmt2(r['H1a']['ic95'][0])}; {fmt2(r['H1a']['ic95'][1])}]",
        "H1c p": f"`p = {r['H1c']['p_rerand']}`",
        "H1a raw p": f"{r['H1a']['p_rerand']}",
        "H1a Holm m=5": f"{dep['A_familia_registada_inavaliaveis_como_p1']['p_ajustado']['H1a']:.4f}",
        "H1a Holm m=4": f"{dep['B_so_membros_avaliaveis']['p_ajustado']['H1a']:.4f}",
        "H1 Holm switch m=6": f"{tro['A_familia_registada_inavaliaveis_como_p1']['p_ajustado']['H1']}",
        "H1 Holm switch m=5": f"{tro['B_so_membros_avaliaveis']['p_ajustado']['H1']}",
        "H1c CI": f"[{fmt4(lo)}; {fmt4(hi)}]",
        "hours v2": f"{reg['pernas']['registrado']['por_braco']['treatment']['horas_sessao']} / "
                    f"{reg['pernas']['registrado']['por_braco']['control']['horas_sessao']}",
        "washout episodes": f"{chk['W_washout']['episodios_removidos_pelo_washout']:,}".replace(",", " "),
        "straddle H1 CI": f"[{fmt2(d['ic95'][0])}; {fmt2(d['ic95'][1], True)}]",
        "w=4 coverage": f"{100 * e4['cobertura']:.1f}% ({e4['cobertas']} of {e4['oportunidades']}",
        "abort adjudicated": f"{f3['substituicao']['total']['adjudicados']} episodes",
    }


HYP = re.compile(r"\bH1[abc]?\b|\bH2\b")
NEG = re.compile(r"\b(?:not|no|nor|never|neither|without|cannot|stops|only)\b")
REJ = re.compile(r"\b(?:rejects?|rejected|rejection)\b")


def sentences(corpo):
    return re.split(r"(?<=[.])\s+|\s*\|\s*", corpo)


def claims(new):
    fails = []
    corpo = strip_struck(new[:new.find("\n## Working list")])
    for sent in sentences(corpo):
        for m in REJ.finditer(sent):
            antes = list(HYP.finditer(sent[:m.start()]))
            if not antes:
                continue
            sujeito = antes[-1].group(0)
            ini = max(sent.rfind(c, 0, m.start()) for c in ",;:()")
            clause = sent[ini + 1:m.end() + 12]
            negado = bool(re.search(r"\b(?:not|no|nor|never|neither|without|cannot|stops)\b", clause))
            if sujeito == "H1a" and not negado:
                fails.append(f"claim: H1a presented as rejected: {clause.strip()[:90]!r}")
            if sujeito == "H1" and not negado and "deposited" not in sent:
                fails.append(f"claim: H1 presented as rejecting without 'deposited': {sent.strip()[:110]!r}")
    for sent in sentences(corpo):
        if re.search(r"\b(?:condition|rule)\b[^.]*\bwas met\b", sent) and "planning" not in sent \
                and "not met" not in sent and "Whether" not in sent:
            fails.append(f"claim: stopping condition 'was met' without the planning qualifier: {sent.strip()[:110]!r}")
    sec46 = corpo[corpo.find("### 4.6"):corpo.find("### 4.7")]
    for sent in sentences(sec46):
        if "M10" in sent and not re.search(r"registered|called|label", sent):
            fails.append(f"claim: §4.6 calls the correlation M10: {sent.strip()[:110]!r}")
    if re.search(r"\b1 195 (?:episodes )?(?:were |are )?adjudicated", corpo):
        fails.append("claim: 1 195 called adjudicated (it is the number submitted)")
    return fails


def check(old, new, verbose=True, report=False):
    fails = []
    reg = json.loads(ART["ITT-REGISTRADO-v2"].read_text())
    chk = json.loads(ART["checks-rc9"].read_text())
    f4 = json.loads(ART["f4-w4"].read_text())
    f3 = json.loads(ART["f3-abort"].read_text())
    allowed_art = artifact_numbers()
    rc8_nums = numbers(old)
    hs = hunks(old, new)
    # 1 hunks
    for h in hs:
        if not h["ids"]:
            fails.append(f"hunk rc8 {h['rc8']} rc9 {h['rc9']} has no ID: {h['new'][:70]!r}")
    # 2 numbers per hunk
    rep = collections.defaultdict(lambda: dict(added=[], removed=[]))
    for h in hs:
        add = numbers(h["new"]) - numbers(h["old"])
        rem = numbers(h["old"]) - numbers(h["new"])
        key = "+".join(h["ids"]) or "?"
        for tok, n in sorted(add.items()):
            why = None
            if tok in rc8_nums:
                why = "rc8"
            elif tok in allowed_art:
                why = "artifact:" + allowed_art[tok]
            else:
                for i in h["ids"]:
                    if tok in LITERALS.get(i, {}):
                        why = f"literal[{i}]: " + LITERALS[i][tok]
                        break
            rep[key]["added"].append((tok, n, why))
            if why is None:
                fails.append(f"number '{tok}' (+{n}) added in hunk {key} (rc9 l.{h['rc9'][0]}) is not justified")
        for tok, n in sorted(rem.items()):
            rep[key]["removed"].append((tok, n))
    # 3 headline values
    for k, v in headline(reg, chk, f4, f3).items():
        if v not in new:
            fails.append(f"headline: {k} — expected text {v!r} (from the artifact) not found in rc9")
    # 4 claims
    fails += claims(new)
    # 5 headings
    h8, h9 = headings(old), headings(new)
    expected = [HEADINGS.get(h, (h, None))[0] for h in h8]
    if expected != h9:
        for x, y in zip(expected + [None] * 9, h9 + [None] * 9):
            if x != y:
                fails.append(f"heading: expected {x!r}, found {y!r}")
                break
    # 6 citations and footnotes
    for name, t in (("rc8", old), ("rc9", new)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        fm = set(re.findall(r"\[\^([^\]]+)\](?!:)", t))
        fd = set(re.findall(r"^\[\^([^\]]+)\]:", t, re.M))
        if fm - fd:
            fails.append(f"footnote ({name}): markers without definition {sorted(fm - fd)}")
    c9 = collections.Counter(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body_and_refs(new)[0]))))
    c8 = collections.Counter(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body_and_refs(old)[0]))))
    if c9 != c8:
        fails.append(f"citation: occurrences changed: +{dict(c9 - c8)} -{dict(c8 - c9)}")
    if collections.Counter(DOI.findall(old)) != collections.Counter(DOI.findall(new)):
        fails.append("doi: DOI multiset changed")
    # 7 forbidden additions
    for pat in FORBIDDEN:
        if len(re.findall(pat, new)) > len(re.findall(pat, old)):
            fails.append(f"forbidden: pattern {pat!r} added")
    # 8 SHAM-JANELA
    so, eo = sham_spans(old)
    sn, en = sham_spans(new)
    fails += eo + en
    if len(sn) != EXPECTED_SHAM or len(so) != EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc9 and {len(so)} in rc8, expected {EXPECTED_SHAM}")
    for i, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {i} ({y.strip()[:50]!r}…) is not byte-identical to rc8")
    # 9 no REANALISE comment marker
    if R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc9")
    # 10 quotes
    def nq(x):
        return " ".join(x.replace("**", "").split())
    fontes = nq(old) + " " + " ".join(nq(p.read_text()) for p in QUOTE_SOURCES)
    q8, q9 = collections.Counter(QUOTE.findall(old)), collections.Counter(QUOTE.findall(new))
    for q in (q9 - q8):
        if nq(q[2:-2]) not in fontes:
            fails.append(f"quote: {q[:70]!r} is not verbatim in rc8 or a declared source")
    for q in (q8 - q9):
        fails.append(f"quote removed: {q[:70]!r}")
    # 11 code spans
    c8s, c9s = collections.Counter(CODE.findall(old)), collections.Counter(CODE.findall(new))
    roots = [P2, SPRINT, P2 / "out", REPO, LASTRO, SPRINT / "B-rc8", HERE, P2 / "measurement",
             SPRINT / "figures", SPRINT / "B-registered"]
    idsrc = "".join(p.read_text() for p in (ART["ITT-REGISTRADO-v2"], ART["checks-rc9"],
                                            P2 / "measurement" / "estimador_itt_registrado.py",
                                            P2 / "ASSIGN-SEED-2026-08-30.md", P2 / "serving-brief.ts",
                                            P2 / "PREREG-DRAFT.md"))
    for span in (c9s - c8s):
        s = span.strip()
        if re.search(r"\.(?:py|json|md|svg|png|ndjson|jsonl|sh|tgz|txt|ts)\b|/$|\.\*$|\{", s) and " " not in s:
            pats = [s]
            m = re.search(r"\{([^}]+)\}", s)
            if m:
                pats = [s[:m.start()] + x + s[m.end():] for x in m.group(1).split(",")]
            for pat in pats:
                pat = pat.replace("…", "*")
                if not any(glob.glob(str(r / pat)) for r in roots):
                    fails.append(f"code span: `{span}` names no file on disk")
        elif re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", s):
            if s not in idsrc:
                fails.append(f"code span: identifier `{span}` occurs in none of the named sources")
    # 12 bold balance
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)}")
        na = sum(len(v['added']) for v in rep.values())
        print(f"numeric tokens added across hunks: {na}; justified by rc8 / artifact / literal: "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] == 'rc8')} / "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] and t[2].startswith('artifact'))} / "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] and t[2].startswith('literal'))}")
        print(f"headings: {len(h9)}; renamed: {sum(1 for x, y in zip(h8, h9) if x != y)} (allowed {len(HEADINGS)})")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc8: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"quotes added: {sum((q9 - q8).values())}; code spans added: {sum((c9s - c8s).values())}")
    if report:
        for key, v in rep.items():
            print(f"\n[{key}]")
            for tok, n, why in v["added"]:
                print(f"  + {tok} x{n}  <- {why}")
            if v["removed"]:
                print("  - " + ", ".join(f"{t} x{n}" for t, n in v["removed"]))
    return fails


def main():
    old, new = OLD.read_text(encoding="utf-8"), NEW.read_text(encoding="utf-8")
    if "--report" in sys.argv:
        f = check(old, new, verbose=True, report=True)
        print("\n" + ("\n".join("FAIL " + x for x in f) or "no failures"))
        return 0
    if "--self-test" in sys.argv:
        mutations = [
            ("word changed inside a SHAM-JANELA block", new.replace("**Our error, stated.**", "**Our error.**", 1)),
            ("REANALISE marker inserted", new.replace("`p = 0.434`", "<!-- REANALISE -->`p = 0.434`<!-- /REANALISE -->", 1)),
            ("H1 p changed (0.0302 -> 0.0320)", new.replace("`p = 0.0302`", "`p = 0.0320`")),
            ("H1a Holm-adjusted changed (0.0840 -> 0.0804)", new.replace("0.0840", "0.0804")),
            ("switch Holm for H1 changed (0.151 -> 0.115)", new.replace("0.151", "0.115")),
            ("H1 rejects without 'deposited'", new.replace(
                "`H1` rejects under the deposited reading in both analyses, and under the switch's Holm\nrule in neither (§1).",
                "`H1` rejects in both analyses (§1).", 1)),
            ("H1 rejection without 'deposited' (abstract)", new.replace(
                "We report H1 as a rejection conditional on the deposited\nreading, and as unexplained (§4.0.2).",
                "We report H1 as an unexplained rejection (§4.0.2).", 1)),
            ("H1a presented as rejected", new.replace("`H1a` is not rejected\nunder the registered Holm rule;",
                                                      "`H1a` is rejected\nunder the registered Holm rule;", 1)),
            ("stopping condition 'was met' unqualified", new.replace(
                "names was met under the planning definition, and the arm was not closed.",
                "names was met, and the arm was not closed.", 1)),
            ("§4.6 calls the correlation M10", new.replace("**The sign flips.**", "**The M10 sign flips.**", 1)),
            ("w = 4 coverage changed (37.4% -> 34.7%)", new.replace("37.4%", "34.7%")),
            ("v2 session-hours changed (10.75 -> 10.57)", new.replace("10.75 / 3.25", "10.57 / 3.25")),
            ("1 195 called adjudicated", new.replace("All 1 195 were submitted to the", "All 1 195 were adjudicated by the", 1)),
            ("heading renamed without justification", new.replace("### 4.3 H1: an interval", "### 4.3 H1 (rc9): an interval", 1)),
            ("quote fabricated", new.replace('*"esta declaração falhou e o estudo\nnão começa"*', '*"esta declaração vale e o estudo\ncomeça"*', 1)),
            ("code span names a missing file", new.replace("`_sprint-2026-10-04/B-registered/f3-abort-ex-post.json`",
                                                           "`_sprint-2026-10-04/B-registered/f3-abort-ex-ante.json`", 1)),
            ("IP address added", new.replace("Every\n> number below is measured", "Every\n> number below (10.1.2.3) is measured", 1)),
            ("citation removed", new.replace("[@cameron2008bootstrap; @webb2014reworking] motivates", "motivates", 1)),
            ("bold left unbalanced", new.replace("**The washout in the denominator (rc9).**", "**The washout in the denominator (rc9).*", 1)),
            ("unmapped hunk with a new number", new.replace("**Benchmarks compare systems on fixed tasks.**",
                                                            "We ran 4217 extra checks.\n\n**Benchmarks compare systems on fixed tasks.**", 1)),
            ("headline interval changed", new.replace("[−0.0445; +0.0125]", "[−0.0445; +0.0152]")),
        ]
        PELA_CLAIM = {"H1 rejects without 'deposited'", "H1 rejection without 'deposited' (abstract)",
                      "H1a presented as rejected", "stopping condition 'was met' unqualified",
                      "§4.6 calls the correlation M10", "1 195 called adjudicated"}
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            f = claims(mutated) if name in PELA_CLAIM else check(old, mutated, verbose=False)
            via = "claim check" if name in PELA_CLAIM else "full check"
            print(f"mutation [{name}] ({via}): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False)
        print(f"unmutated rc9: {'PASS' if not base else 'FAIL'}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
