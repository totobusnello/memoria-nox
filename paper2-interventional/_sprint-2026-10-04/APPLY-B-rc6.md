# APPLY — `B-v2-rc5.md` → `B-v2-rc6.md` (Paper B, 2026-10-05)

Three things, and nothing else: (1) the ballast text of `LASTRO-B-item10.md` §4–§5, applied as
prescribed; (2) `<!-- SHAM-JANELA -->` markers around every passage that depends on the
whole-window sham, wording unchanged; (3) an `avoid-ai-writing` pass (edit mode, technical
voice) over the rest. No git command, no Zenodo, no adversarial voice, no VPS. The manifest
was read only.

| | rc5 | rc6 |
|---|---:|---:|
| sha256 | `efc04188d3f71d76…` (unchanged) | `5cc3af919ccd4bc2…` |
| lines / bytes / words | 2,039 / 156,347 / 23,429 | 2,068 / 157,944 / 23,696 |
| em dashes, all | 37 | 29 |
| em dashes in running prose | 7 (all §6 list separators; the other 6 outside tables are struck, quoted or history) | **0**; the 29 left are 23 in tables and the same 6 in struck text, quotes or history entries |
| bold spans | 448 | 294 |
| headings | 40 | 40, identical |

The whole edit is reproducible from the scratchpad scripts (`apply.py` = markers, prose
edits, LASTRO edits, then the bold pass `unbold.py`), each replacement asserted to match
exactly once in rc5.

## 1. Ballast (working list 10), verified before writing

Every count was recomputed from `~/Backups/paper2-ensaio-2026-09-21/MANIFESTO-LASTRO-P2.json`
(read-only) and the receipts beside it:

| claim in the text | manifest | ✓ |
|---|---|---|
| manifest sha256 `172c5382…` | `shasum -a 256` = `172c5382bcc79d23…` | ✓ |
| 50 artifacts | `n_artefatos` 50, `len(artefatos)` 50, `ausentes` 0 | ✓ |
| 165 473 805 bytes = 158 MiB | `bytes_totais` 165 473 805 = sum of entries = 157.8 MiB | ✓ |
| first 20 = 154 MiB, hashed 2026-09-21 | sum of entries 1–20 = 154.1 MiB; `gerado_em` 2026-09-21T20:43Z | ✓ |
| +30 = 24 (`item10`) + 6 (`item10-b`) | `extensoes[0].adicionados` 24, `extensoes[1].adicionados` 6 | ✓ |
| 16 copied outside the repo = 12 + 4 | 12 of the first 20 are outside the repo; 4 of the 30 have no `git_commit` (`ITT-SENSIB…`, the 3 C12 files) | ✓ |
| 34 versioned = 8 + 26 | 8 of the first 20 inside the repo (tracked); 26 of the 30 carry `versionado`/`git_commit` | ✓ |
| 16/16 at the destination, both legs; 26/26 against `origin/main`; pre-check with nothing copied | `RECIBO-ITEM10B-20261005T130316Z.txt` (local 16/16, off-machine 16/16 examined = local, git 6/6 + 20/20) | ✓ |
| "again 2026-10-05 13:03Z" | post-check receipt `recibos/backup-20261005T130316Z.txt` | ✓ |
| "every artifact in this table" | scripted: every path in the Appendix B table except the manifest row resolves to a manifest entry | ✓ |

`JANELA-LANCAMENTO.md` is **not** in the manifest and the text says so (item 10: "not yet in
it; they enter together when the job completes"), by the decision of `LASTRO-B-item10.md` §6.

Applied, verbatim from `LASTRO-B-item10.md`:

- §4: working list 10 replaced by the struck item and its "Done, 2026-10-05" text; item 8
  `Blocked by ~~9 (valid sham) and 10 (ballast gap) and~~ 15`; item 1 `Open as item 10; closed 2026-10-05.`
- §5.1: manifest row → `sha256 of every artifact in this table, for loss detection` (the "caveat: except the rows marked †" and "(2026-10-04)" are gone).
- §5.2–5.3: the leading `† ` dropped from all nine rows (`ITT-SENSIB…` plus eight); `Not in the manifest, and not listed here before v2` → `Not listed here before v2`.
- §5.4: the B caveat's first two sentences replaced (20 → 50, 154 → 158 MiB, 12 → 16 copied, 8 → 34 versioned); the "Done" sentence gains `and again 2026-10-05 13:03Z after item 10` and `then 16/16` on both legs.
- §5.5: changelog item 75 with the prescribed line; items 76–78 record the rest of rc6. STATUS header: rc6.

## 2. SHAM-JANELA blocks (10)

`<!-- SHAM-JANELA: pending -->` … `<!-- /SHAM-JANELA -->`. Inside each, the text is byte-identical
to rc5 (parity check 6). No marker opens a line except the two around §4.0.1c, which stand
alone (a comment that starts a line would swallow that line into a raw HTML block).

| # | rc6 lines | passage |
|---|---|---|
| 1 | 10–13 | STATUS: "A second sham replay, over the whole trial window … is running, and its result will be added before deposit (§4.0.1c)." |
| 2 | 87–92 | Abstract: "including a sham replay … says nothing about outcomes (§4.0.1c)." |
| 3 | 523–709 | **all of §4.0.1c**, heading to artifact list (includes the first declared limit, "is now running (`job-janela2` …)") |
| 4 | 1244–1252 | §7 "Scope of the specificity control" (the whole paragraph) |
| 5 | 1364–1368 | §8.3: "The sham replay, the placebo-like specificity control, … on the `w = 4` epochs (§4.0.1c)." |
| 6 | 1442–1443 | §8.5: "its specificity control covers what was served on the `w = 4` epochs only, not outcomes (§4.0.1c)." |
| 7 | 1648 | B.1 row "whole-window sham, running: …" (markers inside the first and last cells) |
| 8 | 1720–1721 | working list 8: "15 (whole-window sham)." |
| 9 | 1729–1731 | working list 9: "The larger set (… 11,812 reconstructible states …) … is running as item 15." |
| 10 | 1756–1761 | working list 15, the whole item |

**§9 has no sentence about the sham**, so nothing there is marked.

Not marked, and likely touched by the integration anyway:

- working list 10, last sentence ("The whole-window sham (item 15) and `JANELA-LANCAMENTO.md` are not yet in it …"): new in rc6, so it cannot be byte-identical to rc5;
- §4.0.1b table, specificity row (the `w = 4` result; it does not mention the larger set);
- B.1 row "sham: 132 / 146 …" (the `w = 4` numbers);
- Appendix B: a new row for the `job-janela2` artifacts and `JANELA-LANCAMENTO.md`;
- the changelog: a new block, not an edit of old items.

## 3. Writing pass (`avoid-ai-writing`, edit mode, technical voice)

Scope: the whole manuscript except SHAM-JANELA blocks, quoted material (`*"…"*`, the
blockquote in §4.1.1), tables, code, struck text, References, working list and changelog
(history entries keep their form), and the LASTRO-prescribed caveat paragraph of B.1.

Done:

- **Em dashes:** the seven §6 list separators became colons; running prose now has none.
- **Bold:** 147 spans unbolded by rule (`unbold.py`), plus the manual edits. Kept: run-in
  labels (`**Caveat.**`, `**Correction (…).**`, `**Estimator.**` …: paragraph-initial ≤ 6
  words, or ending in `:`, or starting "Correction"/"Caveat"), four longer noun-phrase labels
  (§4.0.2 ×2, §4.1, §4.3), list-item lead terms, figure caption titles, the STATUS line and
  the three §9 lead sentences.
- **Labels and stacked bold:** the four `**Critical.**` labels in the abstract and §1.1 and
  `**Key point.**` (§3.0.1) removed; "Two different adversarial reviews, and the distinction
  matters" → "There were two different adversarial reviews"; "What is lost, stated plainly" → "What is lost".
- **Pivots:** "the intervention is not weak: it does not exist" → "the intervention does not
  exist"; "`H1` is not an independent hypothesis. It is the product …" → "`H1` is the product
  of the other two, so it is not an independent hypothesis"; "the residual gap is not the sparse
  session. It is volume" → "the sparse session does not explain the residual gap; volume does";
  "That is not a coincidence we are asserting away; it is visible …" → "This follows from the
  arithmetic above, not from a coincidence we assert away"; "the parts that do carry
  information are not the effect estimate" → "lie outside the effect estimate"; §9 "not a
  missing lock but two locks …" → "two locks …"; "What remains is not an effect estimate but"
  → "What remains, in place of an effect estimate, is".
- **Moral adjectives / intensifiers:** "the honest category", "The honest reading", "The
  honest statement", "faithfully", "perfectly evaluable", "the asymmetry is real", three
  "precisely", and "the measurement is unambiguous" removed or replaced.
- **Tier 1:** "the nesting the pre-registration calls load-bearing" → "the nesting that, per
  the pre-registration, makes the joint reporting work" (the phrase §1 quotes).
- **Aphoristic closers rewritten as statements:** §1.1 (post-hoc account; "keeps the rest of
  the paper"), §3.0, §3.0.1 ×3, §3.1 ×2, §4 estimator, §4.0.1b ×2, §4.1, §4.2, §4.3, §5,
  Appendix A.

Unchanged by design (checked by parity, not by eye): every number, unit, § / table / figure
reference, code span, path, DOI, citation key and quoted span. The scope qualifiers stand as
written: `p = 1/21` a rank against these 20 shams and not a calibrated randomization p-value
(abstract, §4.0.1b; §4.0.1c and §7 are inside blocks); H1 ratios "a proportional-dilution
calculation, not a causal bound" (abstract, §4.0.2, §4.3); fractional counting primary,
whole-epoch a sensitivity (abstract, §1.1, §4.1.1, §9); condition (i) "the implemented proxy"
(§4); C12 tie counts and both −0.026566 / −0.026571 (§4, §7, B.1).

Left deliberately:

- "Absence of significance is not evidence of absence of effect" (a standard maxim; only its
  tail was tightened, "evidence of nothing either way").
- §9's last two sentences ("the only circumstance in which a pre-commitment demonstrably did
  its job"; "worth less than nothing"): each carries a claim, and rewording them risks changing it.
- "X, not Y" scope qualifiers throughout (e.g. "a property of the registration, not of the
  realized window"): they are the scope statements the task says not to weaken.
- Tables, struck text, history entries and the SHAM-JANELA blocks keep their em dashes and
  bold; §4.0.1c in particular still has its own bold leads (e.g. "Our error, stated.").

## 4. Parity

`B-rc6/parity-rc6.py` (rc5 → rc6; adapted from `B-rc5/parity-rc5.py`, plus three checks):
**PARITY: PASS**.

- numbers: 19 tokens change, 19 justified, all `LASTRO-10` (WL10, WL1, manifest row, caveat,
  status, changelog), none unlisted or stale; the prose pass moves no number;
- headings 40, identical; dangling § refs 13 → 13, 0 new; § ref multiset unchanged;
  citation keys unchanged; no host, IP or personal path added;
- SHAM-JANELA: 10 blocks, balanced, not nested, each byte-identical to exactly one span of rc5;
- code spans: 16 added, all justified `LASTRO-10` (item 10 and changelog), none removed;
  quoted spans and DOIs unchanged;
- bold balanced in every paragraph.

`--self-test`: 8 mutations, **8 caught** (number, heading, dangling ref, a word inside §4.0.1c,
a dropped closing marker, a renamed identifier, a reworded quote, an unbalanced `**`);
unmutated rc6 passes. `B-rc5/parity-rc5.py` still passes on rc4 → rc5.

## 5. Open for the author

1. Deposit is now blocked by 15 alone (`job-janela2`, ETA 2026-10-07T03:00Z). On
   completion: `LASTRO-B-item10.md` §7 (extend the manifest with label `item15-janela2`, then
   verify), then edit only the ten blocks above plus the "not marked" list, and remove the markers.
2. rc6 has not been reviewed adversarially. The prose pass is checked mechanically for
   numbers, identifiers, refs and quotes; that a reworded sentence keeps its claim was
   checked by reading only.
