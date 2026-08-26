# Serving code — deposited blobs and their provenance

> Added in **v1.12** to close the defect `AMENDMENT-v1.12.md` §7 declares:
> until now the code carrying the mechanism lived only on a private host and
> was unauditable by whoever read the registration. These are the five modules
> the amendment transcribes or cites by line, deposited verbatim.

Keys are flat because the deposit is flat. The original path is authoritative
for reading the amendment's line citations.

| deposited as | original path | commit | committed | bytes | sha256 |
|---|---|---|---|---|---|
| `serving-brief.ts` | `src/api/brief.ts` | `c3c14c19` | 2026-08-22T00:57:18+02:00 | 43457 | `c2da555ca0c193da75d4cdbdc7da83e9…` |
| `serving-brief-diversity.ts` | `src/api/brief-diversity.ts` | `ad2ca37e` | 2026-06-26T15:28:23-03:00 | 8712 | `34c9aee5f80311c8aff5c0ae35f37dd6…` |
| `serving-brief-outcome.ts` | `src/paper2/brief-outcome.ts` | `c3c14c19` | 2026-08-22T00:57:18+02:00 | 11910 | `3786195eba2f7d1bca1696b09b7c0e5b…` |
| `serving-salience.ts` | `src/salience.ts` | `aca868c7` | 2026-08-02T12:37:55-03:00 | 12553 | `083399fc190920ff8f2a590bd74876e2…` |
| `serving-search.ts` | `src/search.ts` | `aee41849` | 2026-06-07T21:42:53-03:00 | 29622 | `d76034e2b7796744ae5836af02c5a115…` |

**Last commit touching `src/`:** `1464db87` (2026-08-22T01:04:13+02:00). No
file in `src/` changed between that commit and the fetch for this deposit
(2026-08-26), verified by `git log --since` on the host.

⚠️ These are the modules, not the whole system. They import from the rest of
the package (`db.js`, the embedding client, the FTS5 layer), which is **not**
deposited, so the blobs are auditable but not executable standalone. That is a
narrower claim than reproducibility and is the honest one.
