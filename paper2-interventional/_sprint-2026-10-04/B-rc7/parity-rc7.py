#!/usr/bin/env python3
"""Parity check B-v2-rc6.md -> B-v2-rc7.md (Paper B, sprint 2026-10-04; rc7 2026-10-05).

rc7 applies the review of rc6 (`REVIEW-B-rc6-2026-10-05.md`: Codex 1-11, Fable HIGH-1..LOW-12)
that does not depend on the registered re-analysis, and wraps every number and sentence that
the re-analysis will replace in `<!-- REANALISE -->` ... `<!-- /REANALISE -->` (a value, still
the rc6 value) or `<!-- REANALISE: rewrite -->` ... `<!-- /REANALISE -->` (a sentence that
describes what the analysis of this version does, to be rewritten). Finding IDs used below:
C1..C11 (Codex), FH1, FH2 (Fable HIGH), FM3..FM7 (Fable MEDIUM), FL8..FL12 (Fable LOW),
SW (the sweep of the review's classes), CL (status header, working list, changelog).

Checks (exit 1 if any fails):
  1. numbers: every numeric token whose count changes is in JUSTIFIED with the exact signed
     change and a finding ID; unlisted or stale justifications fail.
  2. headings: identical sequence except the two renames in HEADINGS (C4, C1).
  3. section refs: no new dangling internal § ref; the multiset of § refs changes exactly by
     SECREF_JUSTIFIED.
  4. citations: [@key] set unchanged and listed in References; footnotes defined.
  5. no host, IP or personal path added.
  6. SHAM-JANELA: markers balanced, not nested, exactly 10 blocks, and the sequence of block
     contents is byte-identical to rc6's.
  7. REANALISE: markers balanced, not nested, none inside a SHAM-JANELA block, none in rc6;
     exactly EXPECTED_REANALISE value blocks and EXPECTED_REWRITE rewrite blocks; a value
     block holds a number and a rewrite block a sentence; each block is listed with its
     line (--list).
  8. identifiers and quotes: the multiset of `code spans` changes only by CODE_JUSTIFIED;
     quoted spans *"..."* and DOIs are unchanged.
  9. bold balance: every paragraph has an even number of `**`.

Usage:  python3 parity-rc7.py              # check
        python3 parity-rc7.py --report     # raw numeric, code-span and § diff, no verdict
        python3 parity-rc7.py --list       # the REANALISE blocks, with line and kind
        python3 parity-rc7.py --self-test  # mutations of rc7 in memory; each must fail
Reads only the two manuscripts. Writes nothing.
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(HERE, "..", "B-v2-rc6.md")
NEW = os.path.join(HERE, "..", "B-v2-rc7.md")

# ---------------------------------------------------------------- tokenization (as rc6)
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
R_VAL, R_REW, R_CLOSE = "<!-- REANALISE -->", "<!-- REANALISE: rewrite -->", "<!-- /REANALISE -->"
R_ANY = re.compile(r"<!-- (?:REANALISE(?:: rewrite)?|/REANALISE) -->")
EXPECTED_BLOCKS = 10
EXPECTED_REANALISE = 85
EXPECTED_REWRITE = 23


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


JUSTIFIED = {}


def _J(token, delta, reason):
    assert token not in JUSTIFIED, token
    JUSTIFIED[token] = (delta, reason)



# Every entry: the signed change of the token's count from rc6 to rc7, and where it happens:
# "<finding>(<section>) <delta>" per diff hunk of rc7, summed exactly to the change (no
# residue). Finding IDs as in the docstring; ST = status header; CL = working list and
# changelog items 79-96; REANALISE = a value cell or clause re-wrapped, where rc6's
# normalizer had stripped a bare-number table cell as a section cell (SECCELL), so wrapping
# the unchanged value makes it count. Every added number was checked against
# `checks-rc7.json`, the cited artifact or the commit log before writing (APPLY-B-rc7.md).
_J('0', +1, 'C6+FL12(§4.1.1) +1')
_J('0.01', +1, 'FH1(§1) +1')
_J('0.0127', +3, 'FH1+C6+C1(AB) +1; FH1(§1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1')
_J('0.0165', -1, 'C4+C7(AB) -1')
_J('0.025', +1, 'FH1(§1) +1')
_J('0.0320', +1, 'C4(§4.1.1) +1')
_J('0.05', +1, 'FH1(§1) +1')
_J('0.0696', +1, 'REANALISE(§4.1) +1')
_J('0.0721', +1, 'REANALISE(§4.1) +1')
_J('0.0782', +2, 'FH1+C6+C1(AB) +1; C6+FL12(§4.1.1) +1')
_J('0.0855', +1, 'FH1(§1) +1')
_J('0.0896', +1, 'REANALISE(§4.1) +1')
_J('0.09189', +3, 'FL8(§4) +1; FL8(B.1) +1; CL(items 79-96) +1')
_J('0.0994', +1, 'REANALISE(§4.1) +1')
_J('0.1603', +2, 'FH1+C6+C1(AB) +1; FH1(§1) +1')
_J('0.25', +2, 'C6+FL12(§4.1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('0.9325', +2, 'C6+FL12(§4.1.1) +1; CL(items 79-96) +1')
_J('0.9375', +2, 'C6+FL12(§4.1.1) +1; CL(items 79-96) +1')
_J('09-01', +8, 'FL10+C5(§4.0.1b) +1; C6+FL12(§4.1.1) +2; FL10(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +2; CL(items 79-96) +2')
_J('09-02', +4, 'FM5(§3) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(WL 17-19) +1; CL(items 79-96) +1')
_J('09-03', +1, 'C6+FL12(§4.1.1) +1')
_J('09-20', +3, 'C3(§3.0.1) +1; C6+FL12(§4.1.1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1')
_J('1', +4, 'C9(§8.2) +1; CL(items 79-96) +3')
_J('10', +3, 'C4+C7(AB) -1; FH2(§5) +2; CL(items 79-96) +2')
_J('10.3', +3, 'C5(§4.3) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('1056', +2, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('11', +8, 'C5(AB) +1; C4+C7(AB) +1; C5(§4.3) +1; C7(§8.3) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +3')
_J('1159', +3, 'C2(§4) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('1195', +3, 'C2(§4) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('12', +1, 'CL(items 79-96) +1')
_J('13', +2, 'C8+FM3(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('13.86', +1, 'C6+FL12(§4.1.1) +1')
_J('143.92', +2, 'FM6(§1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('15.5', +5, 'C5(AB) +1; C5(§4.0.2) +1; C5(§4.3) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('16:14', +1, 'FM6(§1.1) +1')
_J('16:16:44', +3, 'FM6(§1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('16:20', +2, 'FM6(§1.1) +1; CL(items 79-96) +1')
_J('16:22', +1, 'FM6(§1.1) +1')
_J('16:51:56Z', +3, 'FH1(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('17', +5, 'FM6(§1.1) +1; CL(WL 8) +1; CL(items 79-96) +3')
_J('18', +5, 'CL(WL 8) +1; CL(WL 17-19) +1; CL(items 79-96) +3')
_J('19', +3, 'C1(§4.5) +1; CL(WL 17-19) +1; CL(items 79-96) +1')
_J('19:16:44Z', +1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('2', +7, 'C5(AB) +1; C5(§4.3) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +2; CL(items 79-96) +3')
_J('2.80', +1, 'C4(§4.1.1) +1')
_J('20', +2, 'C4+C7(AB) +1; C7(§8.3) +1')
_J('2000', +2, 'FM6(§1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('2026-08-26', +1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('2026-08-27', +2, 'FH1(§1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1')
_J('2026-08-30', +19, 'FH1+C6+C1(AB) +4; C8+FM3(§1) +2; FH1(§1) +3; C1(§4.5) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +4; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +2; CL(items 79-96) +3')
_J('2026-08-30T21:32:04Z', +1, 'FH1+C6+C1(AB) +1')
_J('2026-09-10', +1, 'FH1+FH2+FM4+FM5+C2+C3(App A) +1')
_J('2026-10-04', +10, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +5; CL(WL 17-19) +2; CL(items 79-96) +3')
_J('2026-10-05', +4, 'ST +1; CL(WL 17-19) +1; CL(items 79-96) +2')
_J('2057', +3, 'FL10(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('2068', +1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('20:51:20Z', +3, 'FH1(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('21:18:35Z', +4, 'C8+FM3(§1) +1; FH1(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('21:32:04Z', +4, 'C8+FM3(§1) +1; FH1(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('22', +2, 'FL10+C5(§4.0.1b) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('22.38', +1, 'C6+FL12(§4.1.1) +1')
_J('24', +2, 'C6+FL12(§4.1.1) +2')
_J('28.0', +1, 'FL10(§4.5) +1')
_J('29', +2, 'C8+FM3(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('3', +3, 'FM6(§1.1) +1; CL(items 79-96) +2')
_J('3.49', +2, 'FL10+C5(§4.0.1b) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('3.92', +1, 'C4(§4.1.1) +1')
_J('31657512', +3, 'C8+FM3(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('31774052', +5, 'FH1+C6+C1(AB) +1; C8+FM3(§1) +1; FH1(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('335', +5, 'C5(AB) +1; FL10+C5(§4.0.1b) +1; C5(§4.3) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('337', +4, 'FL10+C5(§4.0.1b) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +2; CL(items 79-96) +1')
_J('350', +5, 'C5(AB) +1; C5(§4.3) +1; FL10(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('36', +4, 'C2(§4) +1; C2(§6) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('4', +2, 'CL(items 79-96) +2')
_J('4.56', +6, 'C5(AB) +1; FL10+C5(§4.0.1b) +1; C5(§4.0.2) +1; C5(§4.3) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('42', +2, 'FL10+C5(§4.0.1b) +1; FL10(§4.5) +1')
_J('441', +1, 'C6+FL12(§4.1.1) +1')
_J('5', +2, 'CL(items 79-96) +2')
_J('5.3', +2, 'C1(§4.5) +1; CL(items 79-96) +1')
_J('573', +3, 'C1(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('59', +1, 'C4(§4.1.1) +1')
_J('6', +2, 'CL(items 79-96) +2')
_J('611', +3, 'C1(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('630', +3, 'FL10+C5(§4.0.1b) +1; C6+FL12(§4.1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('672', +3, 'FL10+C5(§4.0.1b) +1; C6+FL12(§4.1.1) +2')
_J('7', +6, 'C2(§4) +1; FL10(§4.5) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(items 79-96) +3')
_J('73', +1, 'CL(items 79-96) +1')
_J('7350', +8, 'C5(AB) +1; FL10+C5(§4.0.1b) +1; C5(§4.3) +1; FL10(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +2; CL(items 79-96) +2')
_J('7392', +5, 'FL10+C5(§4.0.1b) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +3; CL(items 79-96) +1')
_J('8', +4, 'FM5(§3) +1; CL(items 79-96) +3')
_J('80', +3, 'C6(AB) +1; C6+FL12(§4.1.1) +1; CL(items 79-96) +1')
_J('84.78', +3, 'C6+FL12(§4.1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('84.8', +2, 'C6+FL12(§4.1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('84.80', +2, 'C6+FL12(§4.1.1) +1; CL(items 79-96) +1')
_J('86', +2, 'C6+FL12(§4.1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('89', +1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('9', +5, 'C4+C7(AB) +1; FM5(§3) +1; C7(§8.3) +1; CL(items 79-96) +2')
_J('91.47', +1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('91.49', +1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1')
_J('93.8', +3, 'C1(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1')
_J('97.0', +1, 'C2(§4) +1')


SECREF_JUSTIFIED = {
    '§1': (+15, 'FH1+C6+C1(AB) +1; FM6+FM3(§1.1) +2; C6+FL12(§4.1.1) +1; FH1(§4.3) +1; FH1(§8.2) +1; FH1(§9) +1; FL9+FH1(§9) +1; FH1+FH2(App A) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(WL 8) +1; CL(items 79-96) +4'),
    '§1.1': (+6, 'FH1(§1) +1; FM6(§7) +1; CL(WL 17-19) +1; CL(items 79-96) +3'),
    '§10.32': (+2, 'FM6(§1.1) +2'),
    '§10.33': (+7, 'FM6(§1.1) +3; FM6(§7) +1; CL(WL 17-19) +1; CL(items 79-96) +2'),
    '§2': (+2, 'FM5(§3) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1'),
    '§3': (+10, 'FH1+C6+C1(AB) +2; FH1(§1) +2; FH1+FH2+FM4+FM5+C2+C3(App A) +3; CL(items 79-96) +3'),
    '§3.0.1': (+2, 'FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(items 79-96) +1'),
    '§4': (+5, 'C2(§6) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +2; CL(items 79-96) +2'),
    '§4.0.1b': (+3, 'C5(§4.0.2) +1; C5(§4.3) +1; CL(items 79-96) +1'),
    '§4.0.2': (+7, 'FH1+C6+C1(AB) +2; FH1(§1) +1; FH1(§1.1) +1; CL(items 79-96) +3'),
    '§4.1.1': (+4, 'CL(items 79-96) +4'),
    '§4.1.2': (+1, 'CL(items 79-96) +1'),
    '§4.2': (-1, 'FH1(§1.1) -1'),
    '§4.3': (+7, 'FH1(§1) +1; FH1(§1) +1; FH1(§1.1) +1; FH1(§9) +1; CL(items 79-96) +3'),
    '§4.4': (+2, 'FH1(§1) +1; FH2(§5) +1'),
    '§4.5': (+5, 'FH1+C6+C1(AB) +1; C1(§1.1) +1; C1(§9) +1; CL(items 79-96) +2'),
    '§4.7': (+1, 'CL(items 79-96) +1'),
    '§5': (+7, 'FH1(§1) +2; FM4(§4) +1; FH1+FH2(App A) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(WL 17-19) +1; CL(items 79-96) +1'),
    '§6': (+3, 'C2(§4) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(items 79-96) +1'),
    '§7': (+2, 'CL(items 79-96) +2'),
    '§8': (+1, 'FH2(§5) +1'),
    '§8.2': (+2, 'CL(items 79-96) +2'),
    '§8.3': (+1, 'CL(items 79-96) +1'),
    '§8.4': (+1, 'CL(items 79-96) +1'),
    '§8.5': (+1, 'CL(items 79-96) +1'),
    '§9': (+5, 'CL(items 79-96) +5'),
}
CODE_JUSTIFIED = {
    '09-01': (+8, 'FL10+C5(§4.0.1b) +1; C6+FL12(§4.1.1) +2; FL10(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +2; CL(items 79-96) +2'),
    '09-02': (+4, 'FM5(§3) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(WL 17-19) +1; CL(items 79-96) +1'),
    '09-03': (+1, 'C6+FL12(§4.1.1) +1'),
    '09-20': (+3, 'C3(§3.0.1) +1; C6+FL12(§4.1.1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1'),
    'ASSIGN-SEED-2026-08-30.md': (+2, 'C8+FM3(§1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'DESIGN-REVISION-2026-08-30.md': (+4, 'FH1+C6+C1(AB) +1; FH1(§1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1; CL(items 79-96) +1'),
    'DESIGNATION-2026-08-26.json': (+1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'ITT-PRELIMINAR.json': (+5, 'FM6(§1.1) +2; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(WL 17-19) +1; CL(items 79-96) +1'),
    'MANIFESTO-LASTRO-P2.json': (+1, 'CL(WL 17-19) +1'),
    'PROSPECTIVE-ESTIMAND-2026-08-30.md': (+5, 'FH1+C6+C1(AB) +1; FH1(§1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +2; CL(items 79-96) +1'),
    'REANALISE': (+6, 'ST +1; CL(WL 17-19) +2; CL(items 79-96) +3'),
    'SHAM-JANELA': (+1, 'CL(items 79-96) +1'),
    '_sprint-2026-10-04/APPLY-B-rc7.md': (+2, 'CL(WL 17-19) +1; CL(items 79-96) +1'),
    '_sprint-2026-10-04/B-rc7/checks-rc7.json': (+7, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +5; CL(WL 17-19) +1; CL(items 79-96) +1'),
    '_sprint-2026-10-04/REVIEW-B-rc6-2026-10-05.md': (+1, 'CL(items 79-96) +1'),
    'carregar_verdicts': (+1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'cobertura_e_m10.py': (+1, 'C1(§4.5) +1'),
    'declaracao': (+1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'deposit/PLAN-v1.13.md': (+2, 'FH1(§1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1'),
    'emissao_de_R': (+1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'mde()': (+1, 'C6+FL12(§4.1.1) +1'),
    'measurement/potencia-h1c.py': (+3, 'C4(§4.1.1) +1; C6+FL12(§4.1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'out/CONCENTRATION-2026-08-30.json': (+2, 'C1(§4.5) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'p = 0.0127': (+3, 'FH1+C6+C1(AB) +1; FH1(§1) +1; FH1+FH2+FM4+FM5+C2+C3(App A) +1'),
    'p = 0.1603': (+2, 'FH1+C6+C1(AB) +1; FH1(§1) +1'),
    'p0': (+1, 'C6+FL12(§4.1.1) +1'),
    'p0 = 0.0782': (+2, 'FH1+C6+C1(AB) +1; C6+FL12(§4.1.1) +1'),
    'p1': (+1, 'C6+FL12(§4.1.1) +1'),
    'p1 = 0.25': (+2, 'C6+FL12(§4.1.1) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'p2-serving.ndjson': (+1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'poder_z': (+1, 'B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1'),
    'unknown': (+4, 'C2(§4) +1; C2(§6) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1'),
    'w = 2': (+4, 'C5(AB) +1; C5(§4.3) +1; B.1 rows(C4,C5,C6,C2,C1,FM6,C8,FL12) +1; CL(items 79-96) +1'),
}
HEADINGS = {
    "### 4.1.1 Our two uncertainty estimates contradict each other":
        ("### 4.1.1 Our two uncertainty statements rest on different constructions", "C4"),
    "### 4.5 Coverage by arm, and the pre-committed explanation it weakens":
        ("### 4.5 Coverage by arm, and a pre-committed explanation it does not test", "C1"),
}
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


# Sections of `DEVIATIONS-FOR-PAPER.md` named in §1.1, §7 and the changelog (FM6); this
# manuscript has no §10, so they cannot resolve to a heading here.
EXTERNAL_REFS = {"10.32", "10.33"}


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
        if ref in EXTERNAL_REFS:
            continue
        out[ref] += 1
    return out


def body_and_refs(text):
    i = text.find("\n## References")
    j = text.find("\n## Appendix A")
    return text[:i] + text[j:], text[i:j]


def sham_spans(text):
    """Return (list of (start, end, content), errors)."""
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
        spans.append((i, k + len(S_CLOSE), text[i + len(S_OPEN):k]))
        pos = k + len(S_CLOSE)
    return spans, errs


def reanalise_blocks(text):
    """Return (blocks [(kind, line, content)], errors)."""
    blocks, errs, stack = [], [], None
    for m in R_ANY.finditer(text):
        tag = m.group(0)
        if tag in (R_VAL, R_REW):
            if stack is not None:
                errs.append(f"reanalise: nested opening at line {text.count(chr(10), 0, m.start()) + 1}")
                return blocks, errs
            stack = (tag, m.end(), text.count("\n", 0, m.start()) + 1)
        else:
            if stack is None:
                errs.append(f"reanalise: closing without opening at line {text.count(chr(10), 0, m.start()) + 1}")
                return blocks, errs
            kind = "value" if stack[0] == R_VAL else "rewrite"
            content = text[stack[1]:m.start()]
            if not content.strip():
                errs.append(f"reanalise: empty block at line {stack[2]}")
            blocks.append((kind, stack[2], content))
            stack = None
    if stack is not None:
        errs.append(f"reanalise: opening at line {stack[2]} never closed")
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
    for h in HEADINGS:
        if h not in h2:
            fails.append(f"heading: rename source {h!r} not in rc6")
    # 3 section refs
    d2, d3 = dangling_refs(old), dangling_refs(new)
    for ref, n in (d3 - d2).items():
        fails.append(f"section ref: new dangling §{ref} (x{n})")
    s2, s3 = collections.Counter(SECALL.findall(old)), collections.Counter(SECALL.findall(new))
    sdiff = {k: s3[k] - s2[k] for k in set(s2) | set(s3) if s3[k] != s2[k]}
    for k, d in sorted(sdiff.items()):
        if k not in SECREF_JUSTIFIED or SECREF_JUSTIFIED[k][0] != d:
            fails.append(f"section ref: '{k}' changes by {d:+d}, not justified as such")
    for k in SECREF_JUSTIFIED:
        if k not in sdiff:
            fails.append(f"section ref: justification for '{k}' is stale")
    # 4 citations and footnotes
    for name, t in (("rc6", old), ("rc7", new)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        if name == "rc7":
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
            fails.append(f"forbidden: pattern {pat!r} occurs {n3} times in rc7 against {n2} in rc6")
    # 6 SHAM-JANELA blocks: same sequence, byte-identical
    so, eo = sham_spans(old)
    sn, en = sham_spans(new)
    fails += eo + en
    if len(sn) != EXPECTED_BLOCKS:
        fails.append(f"sham: {len(sn)} blocks, expected {EXPECTED_BLOCKS}")
    for i, (x, y) in enumerate(zip([c for *_, c in so], [c for *_, c in sn]), 1):
        if x != y:
            fails.append(f"sham: block {i} ({y.strip()[:50]!r}…) is not byte-identical to rc6")
    # 7 REANALISE
    if R_ANY.search(old):
        fails.append("reanalise: rc6 already contains a marker")
    rb, rerr = reanalise_blocks(new)
    fails += rerr
    for st, en_, _ in sn:
        if R_ANY.search(new[st:en_]):
            fails.append("reanalise: marker inside a SHAM-JANELA block")
    nv = sum(1 for k, *_ in rb if k == "value")
    nr = sum(1 for k, *_ in rb if k == "rewrite")
    if (nv, nr) != (EXPECTED_REANALISE, EXPECTED_REWRITE):
        fails.append(f"reanalise: {nv} value + {nr} rewrite blocks, expected "
                     f"{EXPECTED_REANALISE} + {EXPECTED_REWRITE}")
    # a value block must hold a number; a rewrite block must hold a sentence
    for kind, line, c in rb:
        if kind == "value" and not re.search(r"\d", c):
            fails.append(f"reanalise: value block at line {line} holds no number")
        if kind == "rewrite" and len(c.split()) < 5:
            fails.append(f"reanalise: rewrite block at line {line} holds no sentence")
    # 8 identifiers, quotes, DOIs
    c2, c3 = collections.Counter(CODE.findall(old)), collections.Counter(CODE.findall(new))
    cdiff = {k: c3[k] - c2[k] for k in set(c2) | set(c3) if c3[k] != c2[k]}
    for k, d in sorted(cdiff.items()):
        if k not in CODE_JUSTIFIED or CODE_JUSTIFIED[k][0] != d:
            fails.append(f"code span: `{k}` changes by {d:+d}, not justified as such")
    for k, (d, _) in CODE_JUSTIFIED.items():
        if k not in cdiff:
            fails.append(f"code span: justification for `{k}` is stale")
    q2, q3 = collections.Counter(QUOTE.findall(old)), collections.Counter(QUOTE.findall(new))
    if q2 != q3:
        fails.append(f"quote: quoted spans changed: {[x[:60] for x in (q2 - q3)]} -> {[x[:60] for x in (q3 - q2)]}")
    if collections.Counter(DOI.findall(old)) != collections.Counter(DOI.findall(new)):
        fails.append("doi: DOI multiset changed")
    # 9 bold balance per paragraph (fenced code excluded)
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"numeric tokens changed: {len(changed)} (justified entries: {len(JUSTIFIED)})")
        print(f"headings: {len(h3)} in rc7; renamed: {sum(1 for x, y in zip(h2, h3) if x != y)} (allowed {len(HEADINGS)})")
        print(f"dangling internal § refs: rc6 {sum(d2.values())}, rc7 {sum(d3.values())}, new {sum((d3 - d2).values())}")
        print(f"§ refs changed: {len(sdiff)} keys (justified: {len(SECREF_JUSTIFIED)})")
        print(f"SHAM-JANELA blocks: {len(sn)} (expected {EXPECTED_BLOCKS}), byte-identical to rc6: "
              f"{sum(1 for x, y in zip(so, sn) if x[2] == y[2])}")
        print(f"REANALISE blocks: {nv} value + {nr} rewrite (expected {EXPECTED_REANALISE} + {EXPECTED_REWRITE})")
        print(f"code spans changed: {len(cdiff)} (justified: {len(CODE_JUSTIFIED)})")
    return fails


def main():
    old, new = open(OLD, encoding="utf-8").read(), open(NEW, encoding="utf-8").read()
    if "--report" in sys.argv:
        a, b = numbers(old), numbers(new)
        print("APPEARED", sorted((b - a).items()))
        print("DISAPPEARED", sorted((a - b).items()))
        c2, c3 = collections.Counter(CODE.findall(old)), collections.Counter(CODE.findall(new))
        print("CODE+", dict(c3 - c2), "CODE-", dict(c2 - c3))
        s2, s3 = collections.Counter(SECALL.findall(old)), collections.Counter(SECALL.findall(new))
        print("SEC+", dict(s3 - s2), "SEC-", dict(s2 - s3))
        return 0
    if "--list" in sys.argv:
        rb, errs = reanalise_blocks(new)
        for e in errs:
            print("ERR", e)
        for i, (k, line, c) in enumerate(rb, 1):
            print(f"R{i:02d}  l.{line:<5} {k:<7} {' '.join(c.split())[:110]}")
        return 0
    if "--self-test" in sys.argv:
        mutations = [
            ("number changed (99.6% -> 96.6% once)", new.replace("99.6%", "96.6%", 1)),
            ("heading renamed (§4.2)", new.replace("### 4.2 H1a:", "### 4.2 H1a (revised):", 1)),
            ("dangling § ref added", new.replace("80% power (§4.1.1). As pre-committed", "80% power (§4.1.9). As pre-committed", 1)),
            ("word changed inside a SHAM-JANELA block (§4.0.1c)",
             new.replace("**Our error, stated.**", "**Our error.**", 1)),
            ("SHAM-JANELA closing marker dropped", new.replace(S_CLOSE, "", 1)),
            ("REANALISE closing marker dropped", new.replace(R_CLOSE, "", 1)),
            ("REANALISE value unwrapped (p = 0.1603 in the abstract)",
             new.replace(R_VAL + "`p = 0.1603`" + R_CLOSE, "`p = 0.1603`", 1)),
            ("REANALISE nested", new.replace(R_VAL + "22.5" + R_CLOSE, R_VAL + R_VAL + "22.5" + R_CLOSE + R_CLOSE, 1)),
            ("REANALISE marker put inside a SHAM-JANELA block",
             new.replace("**Our error, stated.**", R_VAL + "**Our error, stated.**" + R_CLOSE, 1)),
            ("code identifier renamed outside the blocks",
             new.replace("`estimador_itt.py`, which is", "`estimador_itt2.py`, which is", 1)),
            ("quote reworded", new.replace("it underestimates failures\"*", "it may underestimate failures\"*", 1)),
            ("bold left unbalanced", new.replace("**Washout.**", "**Washout.", 1)),
            ("§ ref removed (§4.5 in §1.1)", new.replace("commitment; §4.5.)*", "commitment.)*", 1)),
            ("claim reverted (Codex 1: 'contradicts' back unstruck)",
             new.replace("~~This contradicts the projection the pre-commitment rests on.~~",
                         "This contradicts the projection the pre-commitment rests on. 93.8", 1)),
        ]
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            f = check(old, mutated, verbose=False)
            print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False)
        print(f"unmutated rc7: {'PASS' if not base else 'FAIL'}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
