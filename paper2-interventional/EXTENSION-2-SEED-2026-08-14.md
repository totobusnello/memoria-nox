# Panel extension 2 — sampling seed declaration (epochs 2026-08-12 → 08-14)

> **Registered before the round existed.** This file is committed and pushed to
> the public repository at **2026-08-14T18:10Z**, **before** the beacon round
> named below is emitted (it is issued at 18:20:27Z). The repository history is
> the precedence stamp — the same mechanism as `CALIBRATION-SEED.md`,
> `EXTENSION-SEED-2026-08-11.md` and the `SEED_B` of `PILOT-PROJECTION.md` §4.

## Why this extension exists

`SIZING-2026-08-14.md` closed the extension-1 corpus and produced **27 analysable
epochs (24 usable for the ICC)** — still below the **30–50** floor that §9
requires to estimate an ICC reliably. The width of the resulting CI
([0.0554 ; 0.1786]) alone moves the study from 172 to 456 days, which blocks any
informed decision on MDE or duration.

Corpus diagnosis: it contains **30 epochs**, of which **25** have at least one
adjudicated episode. The five without adjudication are 07-16 and 07-17 (2 and 1
episodes — they yield no usable sessions) and **08-12, 08-13 and 08-14** (233,
223 and 244 episodes). Adjudicating these three takes us from 27 to **30
epochs**.

**30 is the ceiling of the current corpus, and it is exactly §9's floor.** There
is no slack: if any of the three yields no analysable sessions, we fall short
again.

## Design — locked before the sample

| Field | Value |
|---|---|
| Universe (epochs 08-12 → 08-14, boundary 09:00 UTC) | **700** episodes |
| Stratum A (`is_error`, census) | **65** — all of them, no sampling |
| Stratum B (complement, sampled) | **122** of 635 |
| Stratum B rate | **19.235%** — identical to extension 1's (1,576/8,194) |
| Panel | **3 families**: `zhipu` (GLM-5.2) · `xai` (Grok-4.5) · `moonshot` (K3) |
| Total to adjudicate | 187 episodes · **561 calls** |
| Distinct sessions across the 3 epochs | 47 |

**Why the same rate, and not a census.** `pilot_replay.py` applies a single
Horvitz–Thompson weight, `len(resto)/len(estrato_b)`, to the whole of stratum B.
Censusing the new epochs would give them weight 1.0 against the older ones' 5.2,
mixed in the same estimator — the code does not support per-epoch weights, and
changing it **after seeing the sizing results** would mean touching the estimator
with the data in view. An identical rate keeps the estimator valid without
altering a line of it.

## Seed — locked parameters

| Field | Value |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| Chain hash | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| Period | 3 s · genesis `1692803367` |
| `T_declare` | **2026-08-14T18:10:27Z** |
| Rule for `R` | first round with ≥ 5 min of slack over `T_declare` |
| **`R` (pre-computed)** | **31309420** — `ts(R)` = **2026-08-14T18:20:27Z** (10 min slack) |
| Round observed at declaration time | 31309220 |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** |
| Derivation | `seed = SHA256( ascii_hex(randomness) )`, lowercase hex, no `0x`, no whitespace |
| **Ordering** | `key(e) = SHA256( ascii(seed) \|\| "\|" \|\| e.episode_id )` — **the `\|` separator is mandatory** |

## Third-party verification

```bash
CHAIN=52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971
RAND=$(curl -s https://api.drand.sh/$CHAIN/public/31309420 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)
# Stratum B: order by SHA256(SEED || "|" || episode_id), take the first 122
```

> The `|` separator is explicit here **because its absence in
> `EXTENSION-SEED-2026-08-11.md` was a reproducibility defect**: anyone following
> that command reproduced 293 of the 1,576 instead of 1,565. Corrected in that
> file on 2026-08-14.

## Scope — what this seed does NOT govern

- It does not govern arm assignment in the live study (that remains §2 of the pre-registration).
- It is not a result. It governs only which **122 of the complement's 635**
  episodes go to the panel; the stratum A census needs no seed.
- It does not alter τ, the panel, the outcome rule, or the instability rule
  (`STABILITY-TEST.md` §9.2).

## Extraction check (2026-08-14, post-declaration)

The universe was regenerated from the VPS `action-archive` and **matches the
design declared above exactly**: 700 episodes, 65 in stratum A, 47 distinct
sessions. Drawing the 122 with round 31309420 (`randomness` `6a9b71b4…f0b57`,
`seed = SHA256(randomness)` = `fd9b4027…aa85`) lands at **19.213%** — the
declared 19.235% is the exact fraction `1,576/8,194`; 122 is its rounding to an
integer.

### ⚠️ Right-censoring in the last epoch of every extraction

The same extraction showed epoch **08-11 with 316 episodes**, against the **264**
frozen in extension 1's `universo-extensao.jsonl` — because that extraction ran
*during* 08-11 and captured 83.5% of the epoch. **Every last epoch of an
extraction is partial**, and this had not been recorded anywhere.

Consequences, in this order:

1. **Extension 1's 08-11 epoch stays as it is.** Completing it now would mean
   touching the corpus after seeing the sizing result — exactly what the design
   forbids. It enters as a smaller cluster, which the ICC accommodates.
2. **This extension's 08-14 epoch is also partial** (244 episodes, extracted at
   ~23:00 UTC from an epoch that only closes at 09:00 UTC on 08-15). It enters
   partial, and this is declared *before* adjudication, not after.
3. For future extractions: **discard the current epoch** or wait for its
   boundary. A truncated cluster does not bias the ICC by itself, but it reduces
   m̄ non-randomly — and m̄ is the term that dominates the design effect.

## What this extension does not solve

Even on complete success we reach **30 epochs — the floor, not slack**. The ICC
interval will remain wide; 30 clusters narrow it, they do not close it. And the
corpus has no more epochs to offer: any gain beyond this requires **waiting for
more days of traffic**, not more adjudication.
