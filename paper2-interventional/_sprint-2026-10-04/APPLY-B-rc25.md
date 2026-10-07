# APPLY B-rc25: the three LOW of Fable's diff check of rc24 (2026-10-07)

`B-v2-rc24.md` (`f66bf8c6…`) was copied to `B-v2-rc25.md` (`fba9fdda…`), and only rc25 was
edited. No git write, no Zenodo write, no voices, no VPS, no LLM API call; the ballast (manifest
and both copies) was read, not changed. Parity: `B-rc25/parity-rc25.py` (`9564a6cb…`) passes;
`--self-test` caught 20 of 20 mutations (each S25 mutation by its own S25 leg) and the unmutated
file passes. `parity-rc24.py` still passes on rc23 → rc24.

## Source

Fable's diff check of rc23 → rc24 (critic agent run; no file left): **GO**, three LOW, all in
Appendix B / B.1. rc25 changes wording only; no number of the analysis or of the sham results
moves (parity: no numeric token removed; the one token added, `12:31Z`, is derived and checked).

## Findings, verified, applied

| # | where | verification | applied |
|---|---|---|---|
| L1 | Appendix B, row of the rc23 Codex read (rc24 l.2691) | `~/Claude/scripts/adversary-run.sh` l.490: `STAMP="$(date +%Y-%m-%dT%H%M%S)"` (also l.253, l.571), no `-u` anywhere ⇒ local time; this machine `date +%z` = `-0300` (America/Sao_Paulo, no DST in 2026); receipt `timestamp: 2026-10-07T093115` ⇒ 12:31:15Z (finished 093513 ⇒ 12:35:13Z); manifest `extensoes[-1]` = `item15-janela2`, `em 2026-10-07T12:02:12Z` | after "written after the rc23 ballast manifest": "(the receipt's stamp is local time, UTC−3: 12:31Z, after the 12:02Z extension)" |
| L2 | B.1 ballast paragraph (rc24 l.2782) | same finding as rc24/X5: neither record is in the manifest (S24/M) | "…is not in the manifest, nor are the two records of the final Codex read of rc23 (Appendix B)." |
| L3 | Appendix B, manifest row (rc24 l.2682) | wording: "`B-censo/raw/`, see its row, and …" read as four items | "the manifest itself, `B-censo/raw/` (see its row), and …" |

## Text changes (rc24 → rc25)

| where | change |
|---|---|
| status header | "rc24 has not been reviewed" → rc24's diff check recorded; rc25 entry |
| Appendix B | L1 (Codex-read row), L3 (manifest row) |
| B.1 | L2 |
| working list 24 | rc25 note |
| changelog | block rc25, items 204–206 |

Not changed: any number of the analysis or of the sham results, any heading, any earlier
changelog line, any struck span, the H1 family.

## Parity (`B-rc25/parity-rc25.py`)

- Pins `parity-rc24.py` at `5340173f…` and rc24 at `f66bf8c6…`; carries every earlier lock and
  integrity block (S…S24).
- Replaced, not dropped: the status mark "rc24 has not been reviewed" (now forbidden in the
  header), the rc24 present-locks of the manifest row (L3) and of the Codex-read row (L1), and
  the rc23 present-lock "AB raw excluded" (L2: the sentence now continues).
- New sweep locks forbid each old wording; new present-locks pin each new one.
- S25 checks the facts L1 rests on: `adversary-run.sh` stamps without `-u`; `093115` at UTC−3 is
  12:31Z (zoneinfo); the manifest's last extension is `item15-janela2` at 12:02Z.
- Declared hedge deltas: ST `only` +1 ("rc25 changes wording only"); L2 `nor` +1.
- **Caveat:** S24/M and S25/M read `~/Backups/paper2-ensaio-2026-09-21`, and S25/R1 reads
  `~/Claude/scripts/adversary-run.sh` (both outside the repository); without them, NOT VERIFIED
  warnings, never a pass.
