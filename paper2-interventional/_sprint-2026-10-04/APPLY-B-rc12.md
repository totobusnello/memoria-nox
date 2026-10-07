# APPLY B-rc12: the census restoration attempted after unblinding (2026-10-05)

Manuscript: `B-v2-rc11.md` copied to `B-v2-rc12.md`; only rc12 was edited (rc11 sha256
`951e511a…` unchanged). No git, no Zenodo, no voices, no VPS, no API calls. Not touched:
`B-censo/` (read only), the locked artifacts, every script, every figure, `B-rc11/`.

Sources read: `B-censo/GATES.md`, `B-censo/GATE-RULES-PREDECLARED.md`,
`B-censo/gate2-compare.json`, and the summaries of the raw outputs (`raw/cost-gate1.json`,
`raw/cost-gate2.json`, the `ts`/`served`/`seconds` fields of `raw/gate1-calls.jsonl`, the
counts in `raw/gate2-run.log`). No episode text, panelist reason or credential was read
into the manuscript or this file. `B-censo/SHA256SUMS` verifies (all 21 entries OK).

## What was added, where

| where | what | source |
|---|---|---|
| status header | rc12 line | — |
| §4, Adjudication | one sentence pointing to the attempt | — |
| §4, new paragraph after the tie rule | the attempt after unblinding; rules written before the first call (times); gate 1 passed + alias caveat; gate 2 failed: `xai` 50/50 [0.93; 1.00], `google` 47/50 [0.84; 0.98], `zhipu` 46/50 [0.81; 0.97] against a declared 0.99 (the 99/100 of `STABILITY-TEST.md` §7, another panelist); panel outcome 46/50 [0.81; 0.97], meets its 0.90; two `failure` ↔ `not_failure` flips in opposite directions, two involving `unknown`; census not run, sampled design stays a declared deviation; mixing October and September verdicts would add an instrument change; cost ≈ US$1.18 (154 calls) | `GATES.md`, `gate2-compare.json`, rules file, cost files |
| §7, new paragraph | label-level drift for two of three families bounds how reproducible the adjudication is | `gate2-compare.json` |
| Appendix A, census item | the attempt and its outcome | `GATES.md` |
| Appendix B | one row: `GATES.md`, `GATE-RULES-PREDECLARED.md`, `gate2-ids.txt`, `census-ids.txt`, `run_census.sh`, `SHA256SUMS` (plus a mention of `gate2-compare.json`, `compare_gate2.py`, and of `raw/` kept out of the public repository); **not** in the ballast manifest | — |
| Appendix B caveat | the rc12 files added to the list of artifacts not yet in the manifest | — |
| B.1 | one row for every new number | as above |
| working list | 24 extended (rc12 not reviewed); **25 closed: attempted, gates failed, not run** | — |
| changelog | rc12 section, items 137–140 | — |

## Decisions, with the reason

1. **The credential finding is omitted from the manuscript.** `GATES.md` records that six
   census episodes contain credential-like strings that the extraction redaction missed, and
   that one truncated string was already sent to the panel in September. The manuscript does
   not mention it, not even with the neutral sentence allowed. Reasons: (a) it decided
   nothing. Gate 2 alone stops the census, and the rules that stopped it say nothing about
   secrets. (b) No reported number depends on those episodes being excluded. The six are
   outside the September sample, and the September estimates are unchanged. (c) The
   September transmission of a truncated string is a data-handling matter for the author
   (rotation and redaction), not a threat to validity. (d) A public manuscript that names the
   finding signals that the corpus holds live tokens, and it adds nothing a reader needs in
   order to judge the estimates. If the census is ever run, the six episodes become a
   declared deviation of that run, and the sentence belongs there. `parity-rc12.py` lock 4(h)
   holds this: no credential-like string and none of the words `credential`, `Slack` or
   `unredacted` in rc12.
2. **The time order of the gate rules is stated from file-system metadata, and its weakness
   is stated too.** `GATE-RULES-PREDECLARED.md` has a creation time equal to its
   modification time, **23:13:58Z**. The first call started at **23:14:49Z** (`ts` of
   `raw/gate1-calls.jsonl`, which `gate_harness.py` records before the request). So the
   rules come first, by 51 s. ⚠️ The file's own header says *"Written 2026-10-05T23:15Z"*,
   and `GATES.md` repeats "(23:15Z)". Neither the file-system time nor the call log
   supports that label. It is later than the first call, so read literally it would put the
   rules *after* the calls. The manuscript prints the file-system times and says that the
   header time is not exact and that the file is not versioned. A checkout rewrites the
   file-system time, so `parity-rc12.py` treats a later mismatch as a WARN and this record
   as the source of the literal. `GATES.md` also dates gate 1 from 23:14:52Z (the second
   call). The first call is the zhipu call at 23:14:49Z.
3. **"Gate 1 passed" is reported with the caveat from `GATES.md`.** The ids match, but an id
   is an alias, and September recorded no fingerprint. In this record, gate 2 cannot
   separate a non-deterministic model from a changed one.
4. **The panel outcome is reported as meeting its criterion.** It does (0.92 ≥ 0.90). The
   overall FAIL comes from the per-provider criterion. The text says both, so the reader
   can see that the failure is in the labels and not in the consolidated outcome.
5. **The projected census cost (~US$110, ~45% over the authorized ~US$75) is not in the
   manuscript.** The census was not run, and the projection is not a property of the
   reported analysis. It stays in `GATES.md`.
6. **§7 says "bounds how reproducible"** and makes no claim that the September labels are
   wrong. It adds that the reported estimates are those of the September run.

## Parity

`python3 B-rc12/parity-rc12.py` gives **PASS**. 12 hunks, all with an ID (ST, CENSUS,
DRIFT, APPB, B1, CL). 78 numeric tokens were added. Hunks that carry census content (CENSUS,
DRIFT, B1) must justify their numbers from the census record only: 25 derived at run time
(cost total and call count from the `usage` files, the first call's start, the header time
and both criteria from the rules file, 99/100, 4 756 = 5 556 − 800 = lines of
`census-ids.txt`, 50 = lines of `gate2-ids.txt`, the date in the `GATES.md` title), 23 from
`gate2-compare.json`, 1 literal per hunk (23:13:58Z, the file-system time), and 9 declared
context numbers (5 556, 800, 1 195, the 95 of Wilson 95%, gate and section numbers, the
sprint path). The other 19 come from rc11. No heading was added or renamed. The 10
SHAM-JANELA blocks are byte-identical to rc11, which an independent regex extraction
confirms. No quote was added. All 46 added code spans resolve.

Carried, imported from `B-rc11/parity-rc11.py` (pinned by sha256 `c4daf8e4…`, abort if it
changed): rc11's 24 headline strings, its claim locks (a)–(f), its census-deviation check in §4
and Appendix A, and its script-integrity check 13. `B-rc11/parity-rc11.py` still passes
against rc11.

New locks: **4(g)**, no sentence says the census was run or restored (negations allowed);
**4(h)**, the credential lock above. The census attempt must appear in §4, §7 and Appendix A.
**14**, census record: `SHA256SUMS` verifies every file it lists, including the six
registered files and the raw sources of the numbers. `GATES.md` says FAIL. 50 distinct
gate-2 ids. The census ids are 4 756, distinct, and disjoint from the gate-2 ids. The rules
file time precedes the first call. `~/.paper2-verdicts/censo-B-20261005/` holds only its 48
input batches (`calls/` and `retry-in/` are empty, and no census output exists).

`--self-test`: **32 mutations, all caught.** 27 are mutations of the manuscript. Seven of
those are lock mutations, and each must be caught by the claim locks alone, not by a
headline or a number. The other 5 are census-record mutations: GATES says PASS, a
registered file altered, a census output present, rules after the first call, census ids
overlapping the sample. A catch by "hunk has no ID" alone does not count. The unmutated
rc12 passes.

## Credential scan of `B-censo/` outside `raw/` (no value printed)

Patterns: Slack `xox?-`, `sk-`, AWS `AKIA`, GitHub `gh?_`, Google `AIza`, `xai-`, Bearer,
JWT, PEM private key, `*_KEY/SECRET/TOKEN/PASSWORD = …`, and any 40+ character
`[A-Za-z0-9+/_-]` run that is not a sha256 hex.

- **No full-length credential** in the 12 files.
- `GATES.md`: two occurrences of the type marker `xoxp-` followed by `…`, with no characters
  of a value. **One occurrence of `sk-` followed by 2 characters of the real key** and then
  `…` (the 35-character key in two census episodes). That is a value fragment, too short to
  use, but it is a fragment. Before `B-censo/` is committed to the public repo, it should
  read `sk-…`. Not changed here, because only rc12 was to be edited.
- `run_census.sh`, `census_tools.py`: the markers as patterns of the secret scan (`xoxp-`,
  `sk-` with 0 value characters).
- Every 40+ character run is a file path: `GATE-RULES-PREDECLARED.md` (4), `GATES.md` (1),
  `census_tools.py` (1), `compare_gate2.py` (2), `gate_harness.py` (1), `run_census.sh` (2).
  Of these, `GATES.md`, `census_tools.py`, `compare_gate2.py`, `gate_harness.py` and
  `run_census.sh` contain the personal home path (`/Users/…`). That is not a credential, but
  the manuscript's parity forbids it, and the repository is public.
- `census-ids.txt`, `gate2-ids.txt`, `census-lotes.sha256`, `census-pins.sha256`,
  `SHA256SUMS`, `gate2-compare.json`: ids and hashes only.

## Not done (declared)

- Ballast: the `B-censo/` files are not in `MANIFESTO-LASTRO-P2.json` (working list 17).
- Review of rc11 and rc12 (working list 24).
- The `sk-` fragment and the personal paths in `B-censo/` (above) are for the author or the
  next step that commits `B-censo/`.
