#!/usr/bin/env python3
"""Parity check B-v2-rc27.md -> B-v2-rc28.md (Paper B, sprint 2026-10-04; rc28 2026-10-07).

rc28 applies the findings of the two final reads of the package built from rc27 (Grok, receipt
adversary-receipt-grok-2026-10-07T181540-7884.txt; Fable, an agent run), both NO-GO; the Codex read did
not run (exit 1, account out of credits). Every finding was verified before it was applied
(APPLY-B-rc28.md). The text changes in 16 declared hunks, each tied to its finding, plus the rc28
changelog block; no number of the analysis or of the sham results moves.

Checks (exit 1 if any fails):
  A  byte parity: rc28 with each declared hunk reverted (new -> old, each new text exactly once in rc28,
     each old text exactly once in rc27) and its rc28 changelog block removed is rc27 byte for byte
     (pinned sha). So nothing outside the 16 hunks moved.
  N  numbers: every number in rc28 (outside its block) that rc27 does not already carry in any form is
     declared in NEW_NUMBERS, and each declared number is found in the artifact named for it.
  B  carried locks: parity-rc27.py's whole check (pinned sha), run rc24/rc25/rc26 -> rc28, fails with
     EXACTLY the declared set below and nothing else; every declared failure is caused by a hunk or by
     the rc28 block (the header rewrite, the item 8 and item 24 notes, changelog items 211-222).
  C  content locks: the title (line 1) is the author's title; the header lists the three published
     versions exactly as the public API snapshot B-rc28/zenodo-21964093-versions.json has them, says
     rc27 changes only the working list and the changelog, that the rc27 package had two final reads,
     both NO-GO, and "rc3 to rc28"; the abstract carries the horizon sentence and the sham claim with the
     whole-window replay as a forced w = 4 counterfactual; no rc27 wording that put the window on "what
     was served" survives outside the changelog; item 8 is date-neutral; item 24 strikes the planned
     final read, names both receipts (present in receipts/), says Codex did not run and that rc28 itself
     has not been read, and claims no Codex read; the placeholder occurs PLACEHOLDER_COUNT times (build),
     once in the header and once in item 8; the build sources rc28 at its sha.
  E  the deposit description: its <em> title is line 1; no "Versions 1.0 to 1.12", no "every
     deviation"; the twelve of Appendix A and the packaged log; six deviations said to be six; the
     expiry instant; 09-02; assign_arms.py; p = 0.0127; the power caveat; the sham paragraph with the
     counterfactual and 2,016 shared states; OSF yf7d2 not amended; deposit-v2.0.py takes the title from
     line 1 of the manuscript.
  D  changelog: one rc28 block after rc27's, holding items 211..222; items 149..222 in order; the header
     names items 211-222.

Usage:  python3 parity-rc28.py | --report | --self-test     Reads; writes nothing.
"""
import ast
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
RC24F, RC25F, RC26F, OLD, NEW = (SPRINT / f"B-v2-rc{n}.md" for n in (24, 25, 26, 27, 28))
RC27 = SPRINT / "B-rc27" / "parity-rc27.py"
RC27_SHA = "8a58f0511548ab39857b034e66c547ff560b37697126d4476cd7e2c391e9252b"
OLD_SHA = "cb38c5cf0319bbea3ce997a47be6182909145086dbd37f5611a41475d3880b96"
BUILD = P2 / "deposit" / "paperB" / "build-package.py"
DEPOSIT = P2 / "deposit" / "paperB" / "deposit-v2.0.py"
DESC = P2 / "deposit" / "paperB" / "description-v2.0.html"
VERSIONS = HERE / "zenodo-21964093-versions.json"
JANELA = SPRINT / "B-sham-v2" / "JANELA-LANCAMENTO.md"
SPEC = P2 / "SPEC-ANALISE-2026-09-10.md"
RECEIPTS = SPRINT / "receipts"
GROK_RECEIPT = "adversary-receipt-grok-2026-10-07T181540-7884.txt"
CODEX_RECEIPT = "adversary-receipt-codex-2026-10-07T181828-14394.txt"
PLACEHOLDER = "[VERSION-DOI]"
TITLE = ("A registered horizon that outlived the intervention the trial ran: a pre-registered randomized "
         "trial of memory dosing in a production agent fleet")
CL27 = "\n\n**rc27: working list closed for the deposit**"
CL28 = "\n\n**rc28: final reads of the rc27 package applied**"
WL_OPEN = "\n## Working list: struck in the commit that closes it\n"
WL_CLOSE = "\n\n**Caveat.** Items 2 and 3"
H_OPEN, H_CLOSE = "\n\n> **", "\n>\n> **Caveat.**"
ABS_OPEN, ABS_CLOSE = "\n## Abstract\n", "\n## 1. What was registered"
CHANGELOG = "\n## Changelog: v2 (2026-10-04)\n"

assert hashlib.sha256(RC27.read_bytes()).hexdigest() == RC27_SHA, \
    "parity-rc27.py changed: the locks carried from it are no longer the ones rc27 ran"
_spec = importlib.util.spec_from_file_location("parity_rc27", RC27)
R27 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R27)
flat = R27.flat

# ------------------------------------------------------------------ A: the declared hunks (finding, rc27 text, rc28 text)
HUNKS = [
    ("Grok M4 (title; author's decision)",
     '# A registered horizon that outlived its intervention: a pre-registered randomized trial of memory dosing in a production agent fleet\n',
     '# A registered horizon that outlived the intervention the trial ran: a pre-registered randomized trial of memory dosing in a production agent fleet\n'),
    ('Fable H1 (published versions)',
     '> the DOI of this version is `[VERSION-DOI]`. Versions 1.0 to 1.12 of the record are the\n> registration and its amendments; this version reports the trial. The text was reviewed in\n',
     '> the DOI of this version is `[VERSION-DOI]`. Before this one the record has three published\n> versions: 1.9 (record 21964094, 2026-08-17), the registration; 1.11 (record 21978476,\n> 2026-08-17), a correction of it (1.10 was written and not deposited); and 1.12 (record\n> 22110203, 2026-08-26), an amendment. This version reports the trial. The text was reviewed in\n'),
    ('Fable M2 (rc27 line, final reads)',
     '> the LOW findings of those reads and change wording only; rc26 changes only this header.\n',
     '> the LOW findings of those reads and change wording only; rc26 changes only this header;\n> rc27 changes only the working list and the changelog (items 208–210). The package built\n> from rc27 then had two final reads, Grok and Fable, both NO-GO; rc28 applies their findings\n> (working list 24, changelog items 211–222), and a confirmation read of rc28 is planned\n> before publication.\n'),
    ('Fable M2 (rc3 to rc28)',
     '> validated), are in. The v2 release candidates, rc3 to rc26, are listed in the changelog at\n',
     '> validated), are in. The v2 release candidates, rc3 to rc28, are listed in the changelog at\n'),
    ('Grok M5 (horizon sentence)',
     'same intervention for 214 epochs. The trial retained the registered 234-epoch horizon\nwhile adopting a fixed designation that was eligible for only 20 epochs; the designation\nwas chosen on 2026-08-26, after v1.12 was deposited, and was not deposited itself.\n',
     'same intervention for 214 epochs. The deposited registration was not amended and still\nsaid 234 epochs; the trial adopted a fixed designation, chosen on 2026-08-26 after v1.12\nwas deposited and not deposited itself, that was eligible for 20 epochs, and it closed when\nthat designation expired.\n'),
    ('Grok M3 + M1 (abstract, sham replays)',
     'including two sham replays in which the real designation changed more served briefs than\neach of 20 matched sham designations: on the 2,646 brief states of the `w = 4` epochs (132\nagainst 81–122) and on the 11,812 reconstructible states of the hash-verified trial window\n(790 against 449–583), with `p = 1/21`, the floor for 20 shams, in both. Against these 20\nshams, that is evidence that the dose acted specifically on what was served; the rank is not\na calibrated randomization p-value, the second replay contains the states of the first\n(without `09-01`) rather than replicating it, and it says nothing about outcomes (§4.0.1c). A hypothesis that was demoted from\n',
     'including a sham replay in which, on the 2,646 brief states of the `w = 4` epochs, where\nproduction served that dose and the replay reproduces it, the real designation changed more\nserved briefs than each of 20 matched sham designations would have (132 against 81–122,\n`p = 1/21`, the floor for 20 shams). Against these 20 shams, that is evidence that the dose\nacted specifically on what those epochs served. A second replay forces `w = 4` in all\n11,812 reconstructible states of the hash-verified trial window, control epochs included, so\noutside the `w = 4` epochs it is a counterfactual and not a record of what was served; there\ntoo the real designation exceeds every sham (790 against 449–583, `p = 1/21`). The rank is\nnot a calibrated randomization p-value, the second replay shares 2,016 states with the first\n(the `w = 4` epochs except `09-01`) and is not a replication, and neither says anything about\noutcomes (§4.0.1c). A hypothesis that was demoted from\n'),
    ('Grok LOW (nine epochs as projection)',
     'window closed."* On 2026-09-10 nine of the epochs were still projection. The spec\'s own extremes\n',
     'window closed."* On 2026-09-10 the spec marked nine epochs as projection (`09-11`…`09-19`);\n`09-20`, entered as partial by its clock hours, had not begun either, and `09-10` was still\nopen. The spec\'s own extremes\n'),
    ('Grok M3 (§4.0.1b specificity row)',
     '| **specificity (sham)** | replay 19 non-designated items at the same `w` | ~~running since 2026-09-22 01:40Z~~ ~~**not executed** — the configuration launched was invalid; a valid one is runnable and not yet run (§4.0.1c)~~ **passed, rank 1 of 21**: real designation 132 changed states against 81–122 for 20 shams, `p = 1/21 = 0.0476` (the floor at `K = 20`); restricted to the 2,646 brief states of the `w = 4` epochs and to shams drawn from the 36 boostable items; over the 11,812 reconstructible states of the hash-verified trial window, rank 1 of 21 again, 790 against 449–583 (§4.0.1c) |\n',
     '| **specificity (sham)** | replay 19 non-designated items at the same `w` | ~~running since 2026-09-22 01:40Z~~ ~~**not executed** — the configuration launched was invalid; a valid one is runnable and not yet run (§4.0.1c)~~ **passed, rank 1 of 21**: real designation 132 changed states against 81–122 for 20 shams, `p = 1/21 = 0.0476` (the floor at `K = 20`); restricted to the 2,646 brief states of the `w = 4` epochs and to shams drawn from the 36 boostable items; over the 11,812 reconstructible states of the hash-verified trial window, with `w = 4` forced in every state (a counterfactual outside the `w = 4` epochs), rank 1 of 21 again, 790 against 449–583 (§4.0.1c) |\n'),
    ('Grok M3 (§4.0.1c What it adds)',
     "**What it adds.** The result of the `w = 4` epochs holds over the whole window: the real\ndesignation exceeds every one of the 20 matched shams, by 207 states over the largest (790\nagainst 583), and the shams' 449–583 is the range produced by these 20 matched designations at\n`w = 4` in these states. It lifts the first limit above, the restriction to the `w = 4` epochs,\nas far as the hash-verified window allows: `09-01`, the 53 states and the shadow phase are still\nout. The other three limits are unchanged (shams from the 36 boostable items; a match on\n",
     "**What it adds.** At `w = 4` the real designation exceeds every one of the 20 matched shams\nover the whole window as well, by 207 states over the largest (790 against 583), and the shams'\n449–583 is the range produced by these 20 matched designations at `w = 4` in these states.\nOutside `09-12`, `09-14` and `09-15` production did not serve `w = 4` (control epochs served no\ndose, the others `w = 2` or `w = 7.5`), so there the replay is a counterfactual: it measures\nwhat `w = 4` would have changed in those states, not what was served. It lifts the first limit\nabove, the restriction to the `w = 4` epochs, for that counterfactual question only, and as far\nas the hash-verified window allows: `09-01`, the 53 states and the shadow phase are still\nout. The evidence about what was served remains the 2,646 states of the `w = 4` epochs. The other three limits are unchanged (shams from the 36 boostable items; a match on\n"),
    ('Grok M3 (§4.0.1c What this does, 1)',
     'the same `w`. Neither control bears on whether\n',
     'the same `w`; on the `w = 4` epochs that change is the one production served, and over the rest\nof the window it is the change `w = 4` would have made. Neither control bears on whether\n'),
    ('Grok M3 (§4.0.1c What this does, 2)',
     'a null about a lever that changed 2.83–6.85% of briefs per treatment epoch (§4.0.1b), more\nthrough the designated items than through matched others.\n',
     'a null about a lever that changed 2.83–6.85% of briefs per treatment epoch (§4.0.1b) and that,\nin the `w = 4` epochs, changed more briefs through the designated items than any of 20 matched\nsham designations would have.\n'),
    ('Grok M3 (§7 scope)',
     'designation outranked the 20 tested shams on what was served, in the `w = 4` epochs and over\nthe window; it does not establish specificity against every matched designation, nor an\neffect on outcomes.\n',
     'designation outranked the 20 tested shams on what was served in the `w = 4` epochs, and on\nwhat `w = 4` would have changed over the window, where the second run forces that dose in\nevery state, control epochs included; it does not establish specificity against every\nmatched designation, nor an effect on outcomes.\n'),
    ('Grok M3 (§8.3)',
     'again over the whole hash-verified trial window in a second run, 2026-10-05 to 2026-10-07\n(§4.0.1c). We used no covariate variance reduction [@deng2013cuped] and did\n',
     'again over the whole hash-verified trial window in a second run, 2026-10-05 to 2026-10-07,\nwhich forces `w = 4` in every state (§4.0.1c). We used no covariate variance reduction [@deng2013cuped] and did\n'),
    ('Grok M3 (§8.5)',
     'served over the hash-verified trial window (without epoch `09-01`), not outcomes (§4.0.1c). **What it adds, narrowly:** a live-traffic instance of the positivity failure\n',
     'served in the `w = 4` epochs and, as a counterfactual at `w = 4`, the rest of the\nhash-verified trial window (without epoch `09-01`), not outcomes (§4.0.1c). **What it adds, narrowly:** a live-traffic instance of the positivity failure\n'),
    ('Fable LOW (item 8 date-neutral)',
     '   the deposit itself is not done.)* → **Done, rc27 (2026-10-07)**: deposited as version 2.0\n   of the registration record, version DOI `[VERSION-DOI]`.\n',
     '   the deposit itself is not done.)* → **Done (rc27)**: deposited as version 2.0\n   of the registration record, version DOI `[VERSION-DOI]`. *(rc28: the note no longer dates\n   the deposit; publication is done by hand, after this text is frozen.)*\n'),
    ('Fable M3 (item 24 final reads)',
     '    and the changelog (`B-rc27/parity-rc27.py`). The deposited package gets a final read by\n    Grok, Codex and Fable before publication.\n',
     '    and the changelog (`B-rc27/parity-rc27.py`). ~~The deposited package gets a final read by\n    Grok, Codex and Fable before publication.~~\n    *(rc28, 2026-10-07: what happened instead. The package built from rc27 had two final reads:\n    Grok (`adversary-receipt-grok-2026-10-07T181540-7884.txt`, in `receipts/`), NO-GO with six\n    MEDIUM and five LOW, and Fable (an agent run, no receipt), NO-GO with one HIGH, four MEDIUM\n    and two LOW. Every finding was verified against the text, the artifacts and the public\n    Zenodo API, and applied in rc28 or in the deposit description (`APPLY-B-rc28.md`,\n    `B-rc28/parity-rc28.py`). The Codex\n    read did not run: the call exited 1 after 4 s, the account being out of credits\n    (`adversary-receipt-codex-2026-10-07T181828-14394.txt`, in `receipts/`). rc28 itself has\n    not been read; a confirmation read of it is planned before publication.)*\n'),
]

# ------------------------------------------------------------------ N: numbers rc27 does not carry, and where each is found
NEW_NUMBERS = {
    "21964094": ("versions", "record id of v1.9"),
    "7884": ("receipts", "pid suffix in the Grok receipt's file name"),
    "14394": ("receipts", "pid suffix in the Codex receipt's file name"),
    "1.9": ("versions", "version label"),
    "1.10": ("v111", "v1.11's own description: 1.10 written and never deposited"),
    "211": ("block", "first rc28 changelog item"),
    "222": ("block", "last rc28 changelog item"),
}

# ------------------------------------------------------------------ B: what rc27's check must report, and only this
# Every one of these 82 is caused by a declared hunk or by the rc28 block, and by nothing else (APPLY-B-rc28.md,
# "carried locks"): rc27's own legs A/H/C/D see the header, item 8 and item 24 hunks and items 211-222; the cascade
# through rc26's and rc25's checks sees the same hunks as unlabelled rc24 -> rc25 hunks (title, header, abstract,
# §1.1, §4.0.1b/c, §7, §8.3, §8.5, items 8 and 24), the numbers they bring (1.9, 1.10, 1.11, 21964094, 211, 222;
# 208 and 210 from the header's rc27 line), the rc23-era abstract and §8.3 sentence locks the sham rewrite replaces,
# the qualifier counts it moves ('would have', 'exclude zero', 'deposited reading', 'undeposited'), the title lock
# of 2026-10-05 the author's new title replaces, the receipt count (23 -> 25: the Grok and Codex receipts of 222),
# and, as stale declarations, the rc27-era failures that the rc28 changes now mask. Pinned from --report, then read.
EXPECTED_RC27_FAILS = [
    "A: outside the working list and the rc27 block, rc27 differs from rc26 at char 37: '# A registered horizon that outlived the intervention the trial ran: a pre-re' vs '# A registered horizon that outlived its intervention: a pre-registered rando'",
    "H: an inserted run is not a dated rc27 note: '→ **Done (rc27)**: deposited as version 2.0 of the registration record, version DOI `[VERSION-DOI]`. *(rc28: the note no'",
    "B: rc26's check reports an undeclared failure: A: outside the header and the rc26 block, rc26 differs from rc25 at char 37: '# A registered horizon that outlived the intervention the trial ran: a pre-re' vs '# A registered horizon that outlived its intervention: a pr",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): hedge: hunks [?] move hedge words by [('any', -1), ('could', -1), ('deposited', -3), ('every', -3), ('no', -8), ('not', -14), ('only', 1), ('register",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): hunk rc24 (3, 58) rc25 (3, 17) has no ID: '> **Status: version 2.0 of the pre-registration record.** This text is version 2'",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): numbers: token '09-20' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): numbers: token '1' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): numbers: token '20' removed 2x; JUSTIFIED_REMOVED declares 0x",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): numbers: token '2026-08-17' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): numbers: token '21' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "B: rc26's check reports an undeclared failure: B: a declared rc25-check failure no longer occurs (stale declaration): qualifier: 'not deposited' occurs 16x in rc25 against 17x in rc24, not justified",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: S23/X: SH abstract: expected '(790 against 449–583), with `p = 1/21`, the floor for 20 shams, in both.'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: S24/X5: receipts/ does not hold 23 receipts including the rc23 Codex read",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hedge: hunks [?] move hedge words by [('about', 1), ('all', 1), ('could', -1), ('deposited', -1), ('either', 1), ('every', 1), ('except', 1), ('neither', 1), ('no', -7), ('n",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (1, 1) rc25 (1, 1) has no ID: '# A registered horizon that outlived the intervention the trial ran: a pre-regis'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (1003, 1003) rc25 (975, 975) has no ID: '| **specificity (sham)** | replay 19 non-designated items at the same `w` | ~~ru'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (1279, 1284) rc25 (1251, 1259) has no ID: '**What it adds.** At `w = 4` the real designation exceeds every one of the 20 ma'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (1301, 1301) rc25 (1276, 1277) has no ID: 'the same `w`; on the `w = 4` epochs that change is the one production served, an'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (1303, 1304) rc25 (1279, 1281) has no ID: 'a null about a lever that changed 2.83–6.85% of briefs per treatment epoch (§4.0'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (204, 210) rc25 (170, 180) has no ID: 'including a sham replay in which, on the 2,646 brief states of the `w = 4` epoch'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2150, 2152) rc25 (2127, 2130) has no ID: 'designation outranked the 20 tested shams on what was served in the `w = 4` epoc'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2291, 2292) rc25 (2269, 2270) has no ID: 'again over the whole hash-verified trial window in a second run, 2026-10-05 to 2'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2378, 2378) rc25 (2356, 2357) has no ID: 'served in the `w = 4` epochs and, as a counterfactual at `w = 4`, the rest of th'",
    'B: rc26\'s check reports an undeclared failure: B: rc25\'s check reports an undeclared failure: hunk rc24 (2838, 2837) rc25 (2817, 2818) has no ID: "   *(rc27, 2026-10-07: the caveat is closed by item 11\'s rc8 note; the registere"',
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2843, 2845) rc25 (2824, 2827) has no ID: '   full. *(rc27, 2026-10-07: neither check was done; both concern submission to '",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2853, 2853) rc25 (2835, 2837) has no ID: '   the deposit itself is not done.)* → **Done (rc27)**: deposited as version 2.0'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2878, 2878) rc25 (2862, 2862) has no ID: '11. ~~**Traceability of §4.7 and Figure B1**~~: save the `control` distribution '",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2883, 2883) rc25 (2867, 2870) has no ID: '    §4.7 part stays open.)* → **Closed, rc27 (2026-10-07), as a declared gap**: '",
    'B: rc26\'s check reports an undeclared failure: B: rc25\'s check reports an undeclared failure: hunk rc24 (2888, 2888) rc25 (2875, 2875) has no ID: "13. ~~**Two computations rc2 declares as not done**~~: ~~the H1c MDE at the ITT\'"',
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2892, 2891) rc25 (2879, 2880) has no ID: '    → **Closed, rc27 (2026-10-07), the second not computed**: §4.6 declares the '",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2895, 2894) rc25 (2884, 2884) has no ID: '    *(rc27, 2026-10-07: superseded; rc4, built on rc3, had the regression review'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2909, 2909) rc25 (2899, 2900) has no ID: '    not been reviewed. *(rc27, 2026-10-07: superseded; rc6, built on rc5, had th'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2956, 2955) rc25 (2947, 2947) has no ID: '    *(rc27, 2026-10-07: superseded; rc8, built on rc7, had the two full reads of'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2962, 2962) rc25 (2954, 2954) has no ID: '21. ~~**Review of rc9**~~: the washout switch, the multiplicity under both readi'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2964, 2964) rc25 (2956, 2958) has no ID: '    reviewed by any voice. → **Closed, rc27 (2026-10-07), superseded**: rc9 had '",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (2979, 2979) rc25 (2973, 2973) has no ID: '24. ~~**Review of rc11**~~: the census deviation, the stratum contrasts and the '",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (3, 58) rc25 (3, 23) has no ID: '> **Status: version 2.0 of the pre-registration record.** This text is version 2'",
    'B: rc26\'s check reports an undeclared failure: B: rc25\'s check reports an undeclared failure: hunk rc24 (438, 438) rc25 (408, 410) has no ID: \'window closed."* On 2026-09-10 the spec marked nine epochs as projection (`09-11\'',
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: hunk rc24 (92, 94) rc25 (57, 60) has no ID: 'same intervention for 214 epochs. The deposited registration was not amended and'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: invariant: heading list changed (rc25 changes no heading)",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '1.10' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '1.11' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '1.9' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '20' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '208' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '210' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '211' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '21964094' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: numbers: token '222' added 1x is neither in rc24 nor derived",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: present: M1 Abstract sentence missing: 'The trial retained the registered 234-epoch horizon while adopting a f'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: present: SH abstract caveat sentence missing: 'the second replay contains the states of the first (without `09-01`) r'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: present: X3 sentence missing: 'again over the whole hash-verified trial window in a second run, 2026-'",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: qualifier: 'deposited reading' occurs 27x in rc25 against 26x in rc24, not justified",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: qualifier: 'exclude zero' occurs 9x in rc25 against 8x in rc24, not justified",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: qualifier: 'undeposited' occurs 11x in rc25 against 10x in rc24, not justified",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: qualifier: 'would have' occurs 27x in rc25 against 22x in rc24, not justified",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: tail: rc14-rc25 changelog items are [215, 216, 217, 218, 219, 220, 221, 222]…, expected 149..206",
    "B: rc26's check reports an undeclared failure: B: rc25's check reports an undeclared failure: title: line 1 is not the author's title of 2026-10-05",
    "B: rc26's check reports an undeclared failure: C: header sentence missing: 'The v2 release candidates, rc3 to rc26, are listed in the changelog at the end.'",
    "B: rc26's check reports an undeclared failure: C: header sentence missing: 'Versions 1.0 to 1.12 of the record are the registration and its amendments; this'",
    "B: rc26's check reports an undeclared failure: C: header sentence missing: 'rc24 and rc25 apply the LOW findings of those reads and change wording only; rc2'",
    "B: rc26's check reports an undeclared failure: D: rc14-rc26 changelog items are [217, 218, 219, 220, 221, 222]…, expected 149..207",
    'B: a declared rc26-check failure no longer occurs (stale declaration): A: outside the header and the rc26 block, rc26 differs from rc25 at char 253053: \'th the caption title of §4.2 (item 11).\\n   *(rc27, 2026-10-07: the caveat is clo\' vs "th the caption title of §4.2 (item 11).\\n7. ~~**Rel',
    'B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25\'s check reports an undeclared failure: hunk rc24 (2838, 2837) rc25 (2797, 2798) has no ID: "   *(rc27, 2026-10-07: the caveat is closed by item 11\'s rc8 note; the registere"',
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2843, 2845) rc25 (2804, 2807) has no ID: '   full. *(rc27, 2026-10-07: neither check was done; both concern submission to '",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2853, 2853) rc25 (2815, 2816) has no ID: '   the deposit itself is not done.)* → **Done, rc27 (2026-10-07)**: deposited as'",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2878, 2878) rc25 (2841, 2841) has no ID: '11. ~~**Traceability of §4.7 and Figure B1**~~: save the `control` distribution '",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2883, 2883) rc25 (2846, 2849) has no ID: '    §4.7 part stays open.)* → **Closed, rc27 (2026-10-07), as a declared gap**: '",
    'B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25\'s check reports an undeclared failure: hunk rc24 (2888, 2888) rc25 (2854, 2854) has no ID: "13. ~~**Two computations rc2 declares as not done**~~: ~~the H1c MDE at the ITT\'"',
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2892, 2891) rc25 (2858, 2859) has no ID: '    → **Closed, rc27 (2026-10-07), the second not computed**: §4.6 declares the '",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2895, 2894) rc25 (2863, 2863) has no ID: '    *(rc27, 2026-10-07: superseded; rc4, built on rc3, had the regression review'",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2909, 2909) rc25 (2878, 2879) has no ID: '    not been reviewed. *(rc27, 2026-10-07: superseded; rc6, built on rc5, had th'",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2956, 2955) rc25 (2926, 2926) has no ID: '    *(rc27, 2026-10-07: superseded; rc8, built on rc7, had the two full reads of'",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2962, 2962) rc25 (2933, 2933) has no ID: '21. ~~**Review of rc9**~~: the washout switch, the multiplicity under both readi'",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2964, 2964) rc25 (2935, 2937) has no ID: '    reviewed by any voice. → **Closed, rc27 (2026-10-07), superseded**: rc9 had '",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: hunk rc24 (2979, 2979) rc25 (2952, 2952) has no ID: '24. ~~**Review of rc11**~~: the census deviation, the stratum contrasts and the '",
    "B: a declared rc26-check failure no longer occurs (stale declaration): B: rc25's check reports an undeclared failure: tail: rc14-rc25 changelog items are [203, 204, 205, 206, 207, 208, 209, 210]…, expected 149..206",
    'B: a declared rc26-check failure no longer occurs (stale declaration): D: rc14-rc26 changelog items are [205, 206, 207, 208, 209, 210]…, expected 149..207',
    "C: the rc27 text states the final read as done: 'Fable (an agent run, no receipt), NO-GO'",
    "C: item 24 still reads as open: ['not run']",
    'D: rc14-rc27 changelog items are [217, 218, 219, 220, 221, 222]…, expected 149..210',
    'D: the rc27 block does not hold exactly items 208, 209, 210',
]

# ------------------------------------------------------------------ C: content locks
HEADER_MUST = [
    "Before this one the record has three published versions: 1.9 (record 21964094, 2026-08-17), the "
    "registration; 1.11 (record 21978476, 2026-08-17), a correction of it (1.10 was written and not deposited); "
    "and 1.12 (record 22110203, 2026-08-26), an amendment. This version reports the trial.",
    "rc27 changes only the working list and the changelog (items 208–210).",
    "The package built from rc27 then had two final reads, Grok and Fable, both NO-GO;",
    "(working list 24, changelog items 211–222), and a confirmation read of rc28 is planned before publication.",
    "The v2 release candidates, rc3 to rc28, are listed in the changelog",
]
ABSTRACT_MUST = [
    "The deposited registration was not amended and still said 234 epochs; the trial adopted a fixed "
    "designation, chosen on 2026-08-26 after v1.12 was deposited and not deposited itself, that was eligible "
    "for 20 epochs, and it closed when that designation expired.",
    "on the 2,646 brief states of the `w = 4` epochs, where production served that dose and the replay "
    "reproduces it,",
    "A second replay forces `w = 4` in all 11,812 reconstructible states of the hash-verified trial window, "
    "control epochs included, so outside the `w = 4` epochs it is a counterfactual and not a record of what "
    "was served;",
    "the second replay shares 2,016 states with the first (the `w = 4` epochs except `09-01`) and is not a "
    "replication",
]
# rc27 wording that put the whole-window replay (or the horizon) on what was served; must not survive outside
# the changelog
GONE = [
    "Versions 1.0 to 1.12 of the record",
    "The trial retained the registered 234-epoch horizon",
    "evidence that the dose acted specifically on what was served; the rank",
    "the second replay contains the states of the first",
    "The result of the `w = 4` epochs holds over the whole window",
    "more through the designated items than through matched others",
    "outranked the 20 tested shams on what was served, in the `w = 4` epochs and over the window",
    "its specificity control covers what was served over the hash-verified trial window",
    "On 2026-09-10 nine of the epochs were still projection",
    "→ **Done, rc27 (2026-10-07)**",
    "outlived its intervention: a pre-registered",
]
ITEM24_MUST = [
    "~~The deposited package gets a final read by Grok, Codex and Fable before publication.~~",
    f"Grok (`{GROK_RECEIPT}`, in `receipts/`), NO-GO",
    "Fable (an agent run, no receipt), NO-GO",
    "The Codex read did not run: the call exited 1 after 4 s",
    f"(`{CODEX_RECEIPT}`, in `receipts/`)",
    "rc28 itself has not been read; a confirmation read of it is planned before publication.",
]
CODEX_CLAIM = [r"\bCodex\b[^.;]*\b(read|reviewed|found|returned|gave)\b(?![^.;]*\bdid not\b)",
               r"\bCodex\b[^.;]*\bGO\b"]
DESC_MUST = [
    "Before this version the record has three published versions: 1.9 (2026-08-17)",
    "1.11 (2026-08-17), a correction of it (1.10 was written and not deposited); and 1.12 (2026-08-26), an amendment.",
    "Appendix A of the manuscript lists the twelve deviations a reader cannot reconstruct from the estimates; "
    "the append-only log <code>DEVIATIONS-FOR-PAPER.md</code>, in the package, holds the others.",
    "The OSF registration <code>yf7d2</code> (2026-08-18) is not amended",
    "<strong>Six of the deviations reported in the manuscript (§1, Appendix A; the full list is there):</strong>",
    "at 2026-09-20 22:51:23Z, during the 20th epoch",
    "one (2026-09-02, lost to an outage) served no brief, and the other 19 form the analysis set.",
    "The arms served came from <code>assign_arms.py</code>",
    "H1 rejects under the deposited reading (<code>p = 0.0127</code>)",
    "under the BCa construction only: the percentile intervals contain zero, and on time the raw difference "
    "has the opposite sign (−1.18 s).",
    "uses an intra-cluster correlation estimated for a different quantity and is not a calibrated measure",
    "so outside the <code>w = 4</code> epochs it is a counterfactual, not a record of what was served;",
    "The two replays share 2,016 states (the <code>w = 4</code> epochs except 2026-09-01)",
]
DESC_GONE = ["Versions 1.0 to 1.12", "every deviation", "This shows that the dose acted on what was served",
             "contains the states of the first", "after 20 epochs", "20 epochs ran"]
ITEMS = list(range(149, 223))


def _norm(msg):
    def sub(m):
        try:
            d = ast.literal_eval(m.group(0))
        except Exception:
            return m.group(0)
        return repr(sorted(d.items())) if isinstance(d, dict) else m.group(0)
    return re.sub(r"\{[^{}]*\}", sub, msg)


def nums(s):
    """Numbers as a reader sees them (not inside an identifier such as v1.12 or zenodo.22110203)."""
    return set(re.findall(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?(?!\d)", s))



def items(t):
    i, j = t.find(WL_OPEN), t.find(WL_CLOSE)
    out = {}
    for it in re.split(r"\n(?=\d+\. )", t[i:j])[1:]:
        out[int(it.split(".", 1)[0])] = it
    return out


def build_consts():
    b = BUILD.read_text(encoding="utf-8")
    g = lambda r: (re.search(r, b, re.M) or [None, None])[1]  # noqa: E731
    return {"VERSION": g(r'^VERSION = "([^"]+)"'), "COUNT": g(r"^PLACEHOLDER_COUNT = (\d+)"),
            "FONTE": g(r'^FONTE = f"\{SPRINT\}/([^"]+)"'), "FONTE_SHA": g(r'^FONTE_SHA = "([0-9a-f]+)"')}


def check(rc24, rc25, rc26, old, new, desc, verbose=True, report=False, consts=None):
    fails = []
    bc = consts or build_consts()
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("A: rc27 is not the cb38c5cf… bytes the deposit draft was first filled from")
    # A
    k = new.find(CL28)
    if k < 0:
        fails.append("D: the rc28 changelog block is missing")
        k = len(new)
    body = new[:k] + ("\n" if k < len(new) else "")
    rev = body
    for fid, o, n in HUNKS:
        if rev.count(n) != 1:
            fails.append(f"A: hunk [{fid}] occurs {rev.count(n)}x in rc28 (exactly 1 required)")
            continue
        if old.count(o) != 1:
            fails.append(f"A: hunk [{fid}]'s rc27 text occurs {old.count(o)}x in rc27")
        rev = rev.replace(n, o, 1)
    if rev != old:
        n = next((x for x in range(min(len(rev), len(old))) if rev[x] != old[x]), min(len(rev), len(old)))
        fails.append(f"A: outside the declared hunks and the rc28 block, rc28 differs from rc27 at char {n}: "
                     f"{rev[max(0, n - 40):n + 40]!r} vs {old[max(0, n - 40):n + 40]!r}")
    # N
    vj = json.loads(VERSIONS.read_text(encoding="utf-8"))
    src = {"versions": json.dumps(vj), "block": new[k:], "label": "rc28",
           "v111": "1.10 was written and never deposited",
           "receipts": " ".join(p.name for p in RECEIPTS.iterdir())}   # quoted from record 21978476, fetched 2026-10-07
    carried = lambda x: re.search(r"(?<!\d)" + re.escape(x) + r"(?![\d])", old)  # noqa: E731
    for x in sorted(y for y in nums(body) if not carried(y)):   # whole rc28 text outside its block
        if x not in NEW_NUMBERS:
            fails.append(f"N: rc28 carries a number rc27 does not carry and that is not declared: {x}")
    for x, (where, why) in NEW_NUMBERS.items():
        if x not in src[where]:
            fails.append(f"N: declared number {x} ({why}) not found in its source {where}")
    # B
    got = R27.check(rc24, rc25, rc26, new, verbose=False)
    gn, en = {_norm(x) for x in got}, {_norm(x) for x in EXPECTED_RC27_FAILS}
    for x in sorted(gn - en):
        fails.append(f"B: rc27's check reports an undeclared failure: {x[:220]}")
    for x in sorted(en - gn):
        fails.append(f"B: a declared rc27-check failure no longer occurs (stale declaration): {x[:220]}")
    # C
    if new.split("\n", 1)[0] != "# " + TITLE:
        fails.append("C: line 1 is not the author's title")
    hi, hj = new.find(H_OPEN), new.find(H_CLOSE)
    hdr, cl = flat(re.sub(r"\n> ?", "\n", new[hi:hj])), new.find(CHANGELOG)
    for s in HEADER_MUST:
        if flat(s) not in hdr:
            fails.append(f"C: header statement missing: {s[:90]!r}")
    vs = {v["version"]: v for v in vj["versions"]}
    if vj["hits_total"] != 3 or set(vs) != {"1.9", "1.11", "1.12"}:
        fails.append(f"C: the API snapshot lists {sorted(vs)} ({vj['hits_total']}), not the three the header names")
    for ver, rid in (("1.9", 21964094), ("1.11", 21978476), ("1.12", 22110203)):
        v = vs.get(ver, {})
        if v.get("id") != rid or flat(f"{ver} (record {rid}, {v.get('publication_date')})") not in hdr:
            fails.append(f"C: header version {ver} does not match the API snapshot ({v.get('id')}, "
                         f"{v.get('publication_date')})")
    ai, aj = new.find(ABS_OPEN), new.find(ABS_CLOSE)
    ab = flat(new[ai:aj])
    for s in ABSTRACT_MUST:
        if flat(s) not in ab:
            fails.append(f"C: abstract statement missing: {s[:90]!r}")
    if "shares 2,016 of job-v2b's 2,646 states" not in flat(JANELA.read_text(encoding="utf-8")):
        fails.append("C: JANELA-LANCAMENTO.md no longer says the window run shares 2,016 of 2,646 states")
    if "as 9 de `09-11`…`09-19` são projeção" not in SPEC.read_text(encoding="utf-8"):
        fails.append("C: the spec no longer marks the nine epochs 09-11…09-19 as projection")
    pre = flat(new[:cl])
    for s in GONE:
        if flat(s) in pre:
            fails.append(f"C: rc27 wording survives outside the changelog: {s[:90]!r}")
    its = items(new)
    i8, i24 = its.get(8, ""), its.get(24, "")
    if "→ **Done (rc27)**: deposited as version" not in flat(i8):
        fails.append("C: item 8 does not close date-neutral")
    for s in ITEM24_MUST:
        if flat(s) not in flat(i24):
            fails.append(f"C: item 24 statement missing: {s[:90]!r}")
    note = flat(i24[i24.find("*(rc28, 2026-10-07"):])
    for pat in CODEX_CLAIM:
        m = re.search(pat, note)
        if m:
            fails.append(f"C: item 24 claims a Codex read: {m.group(0)[:100]!r}")
    for r in (GROK_RECEIPT, CODEX_RECEIPT):
        p = RECEIPTS / r
        if not p.exists():
            fails.append(f"C: receipts/{r} does not exist")
        else:
            t = p.read_text(encoding="utf-8")
            want = "exit: 0" if "grok" in r else "exit: 1"
            if want not in t or "/" "Users/" in t or not re.search(r"^host: \(redacted\)$", t, re.M):
                fails.append(f"C: receipts/{r} is not the scrubbed receipt with {want}")
    cnt = int(bc["COUNT"]) if bc["COUNT"] else None
    if (new.count(PLACEHOLDER), new[hi:hj].count(PLACEHOLDER), i8.count(PLACEHOLDER)) != (cnt, 1, 1):
        fails.append(f"C: placeholder {new.count(PLACEHOLDER)}x (build {cnt}), "
                     f"{new[hi:hj].count(PLACEHOLDER)}x header, {i8.count(PLACEHOLDER)}x item 8")
    if bc["FONTE"] != "B-v2-rc28.md" or bc["FONTE_SHA"] != hashlib.sha256(new.encode()).hexdigest():
        fails.append(f"C: build-package.py sources {bc['FONTE']} at {str(bc['FONTE_SHA'])[:12]}…, not rc28 at its sha")
    # E
    m = re.search(r"<em>([^<]+)</em>", desc)
    if not m or m.group(1) != TITLE:
        fails.append("E: the description's <em> title is not line 1")
    for s in DESC_MUST:
        if s not in desc:
            fails.append(f"E: description statement missing: {s[:90]!r}")
    for s in DESC_GONE:
        if s in desc:
            fails.append(f"E: description still says {s!r}")
    if 'split("\\n", 1)[0].lstrip("# ")' not in DEPOSIT.read_text(encoding="utf-8"):
        fails.append("E: deposit-v2.0.py no longer takes the title from line 1 of the manuscript")
    # D
    blk = new[k:]
    tn = new[cl:] if cl >= 0 else ""
    i14 = tn.find("\n**rc14: writing pass**")
    got_items = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i14:] if i14 >= 0 else "", re.M)]
    if got_items != ITEMS:
        fails.append(f"D: rc14-rc28 changelog items are {got_items[-6:]}…, expected 149..222")
    if [int(x) for x in re.findall(r"^(\d+)\. ", blk, re.M)] != list(range(211, 223)):
        fails.append("D: the rc28 block does not hold exactly items 211..222")
    if new.find(CL27) < 0 or new.find(CL27) > k:
        fails.append("D: the rc28 block is not after the rc27 block")
    if "No number of the analysis or of the sham results moves" not in flat(blk):
        fails.append("D: the rc28 block does not say that no number moves")
    if verbose:
        print(f"A: rc28 minus 16 declared hunks and the rc28 block == rc27: {rev == old}")
        print(f"B: rc27's check on rc24/rc25/rc26 -> rc28: {len(got)} failures, declared {len(EXPECTED_RC27_FAILS)}, "
              f"undeclared {len(gn - en)}, stale {len(en - gn)}")
        print(f"C: title ok {new.split(chr(10), 1)[0] == '# ' + TITLE}; versions {sorted(vs)}; "
              f"placeholder {new.count(PLACEHOLDER)}x (build {cnt}); build source {bc['FONTE']}")
        print(f"words: rc27 {len(old.split())}, rc28 {len(new.split())}")
    if report:
        print("\nrc27's check on rc24/rc25/rc26 -> rc28:")
        for x in got:
            print(repr(x))
    return fails


def main():
    rc24, rc25, rc26, old, new = (p.read_text(encoding="utf-8") for p in (RC24F, RC25F, RC26F, OLD, NEW))
    desc = DESC.read_text(encoding="utf-8")
    if "--self-test" in sys.argv:
        return self_test(rc24, rc25, rc26, old, new, desc)
    f = check(rc24, rc25, rc26, old, new, desc, verbose=True, report="--report" in sys.argv)
    for x in f:
        print("FAIL", x)
    print("PARITY: PASS" if not f else f"PARITY: FAIL ({len(f)})")
    return 0 if not f else 1


def self_test(rc24, rc25, rc26, old, new, desc):
    consts = build_consts()
    rep = lambda s, a, b: (s.replace(a, b, 1), a in s)  # noqa: E731
    T = [  # (name, leg, text mutation or None, description mutation or None)
        ("A: a body number moved (H1c p)", "A", rep(new, "`p = 0.4006`", "`p = 0.4106`"), None),
        ("A: an undeclared word outside the hunks", "A", rep(new, "This is Paper B of the split", "This is Paper B of a split"), None),
        ("A: a declared hunk edited", "A", rep(new, "1.11 (record 21978476,", "1.11 (record 21978477,"), None),
        ("N: an undeclared new number in a hunk", "N", rep(new, "was eligible for 20 epochs, and it closed",
                                                          "was eligible for 20 epochs (8.6%), and it closed"), None),
        ("C: title reverted", "C", rep(new, "# " + TITLE, "# A registered horizon that outlived its intervention: a "
                                       "pre-registered randomized trial of memory dosing in a production agent fleet"), None),
        ("C: header back to 1.0 to 1.12", "C", rep(new, "Before this one the record has three published\n> versions:",
                                                  "Versions 1.0 to 1.12 of the record are the\n> registration and its amendments. Before this one the record has three published\n> versions:"), None),
        ("C: header version date wrong", "C", rep(new, "1.12 (record\n> 22110203, 2026-08-26)", "1.12 (record\n> 22110203, 2026-08-27)"), None),
        ("C: header drops rc3 to rc28", "C", rep(new, "rc3 to rc28", "rc3 to rc27"), None),
        ("C: abstract window back on what was served", "C", rep(new, "so\noutside the `w = 4` epochs it is a counterfactual and not a record of what was served;",
                                                             "so\nit is evidence about what was served;"), None),
        ("C: old 'more through the designated items' restored", "C",
         rep(new, "changed more briefs through the designated items than any of 20 matched\nsham designations would have.",
             "more\nthrough the designated items than through matched others."), None),
        ("C: item 8 dated again", "C", rep(new, "→ **Done (rc27)**", "→ **Done, rc27 (2026-10-07)**"), None),
        ("C: item 24 claims a Codex read", "C", rep(new, "rc28 itself has\n    not been read;", "Codex read rc28 and gave GO;\n    rc28 itself has\n    not been read;"), None),
        ("C: item 24 planned read unstruck", "C", rep(new, "~~The deposited package gets a final read by\n    Grok, Codex and Fable before publication.~~",
                                                       "The deposited package gets a final read by\n    Grok, Codex and Fable before publication."), None),
        ("E: description says every deviation", "E", None, rep(desc, "it declares the deviations", "it declares every deviation")),
        ("E: description title stale", "E", None, rep(desc, "<em>" + TITLE, "<em>A registered horizon that outlived its intervention: a pre-registered randomized trial of memory dosing in a production agent fleet")),
        ("E: description sham back to 'what was served'", "E", None,
         rep(desc, "so outside the <code>w = 4</code> epochs it is a counterfactual, not a record of what was served;", "so it shows what was served;")),
        ("E: description loses the power caveat", "E", None,
         rep(desc, "uses an intra-cluster correlation estimated for a different quantity and is not a calibrated measure", "is approximate")),
        ("D: changelog item 222 dropped", "D", (new[:new.find("\n222. ")] + "\n", True), None),
        ("D: rc28 block removed", "D", (new[:new.find(CL28)] + "\n", True), None),
    ]
    ok = True
    for name, leg, tm, dm in T:
        mt, ad = (tm if tm else (new, True))
        md, bd = (dm if dm else (desc, True))
        assert ad and bd and (mt != new or md != desc), f"mutation did not apply: {name}"
        f = [x for x in check(rc24, rc25, rc26, old, mt, md, verbose=False, consts=consts) if x.startswith(leg + ":")]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    for name, c in (("C: build sources rc27", dict(consts, FONTE="B-v2-rc27.md")),
                    ("C: build PLACEHOLDER_COUNT 1", dict(consts, COUNT="1"))):
        f = [x for x in check(rc24, rc25, rc26, old, new, desc, verbose=False, consts=c) if x.startswith("C:")]
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(rc24, rc25, rc26, old, new, desc, verbose=False, consts=consts)
    print(f"unmutated rc28: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(T) + 2}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
