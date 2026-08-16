# Calibration set — sampling seed declaration

> **Registered before the seed existed.** This file was committed and pushed to
> the public repository on 2026-07-28, **before** the instant `T_calib` defined
> below. The beacon round named here did not exist at commit time, and the
> repository history is the precedence stamp.

---

## Why there is a seed separate from §2's

§2 of the pre-registration derives the **arm-assignment** seed from a `drand`
round whose `T_seed` is, by construction, **strictly later than OSF
registration**. The numeric severity cut that calibration produces is a
`[TO LOCK]` item — it must be filled in **at** registration.

So calibration precedes registration, and registration precedes `T_seed`. **The
calibration cannot use §2's seed: the ordering makes that impossible.**

§4.1 says *"The production seed will be derived from the beacon (§2), not
chosen."* The operative part is **"derived from the beacon, not chosen"** — the
property required is the absence of author discretion, not the identity of the
round. This declaration satisfies that requirement with its own round, prior to
registration and equally outside the author's control.

**Pending correction in §4.1:** the sentence must distinguish `T_seed_calib`
(here) from `T_seed_assign` (§2). Without it, a reader takes line 148 as a broken
promise.

## Parameters — locked

| Field | Value |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| Chain hash | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| Period | 3 s · genesis `1692803367` |
| `T_calib` | **2026-07-29T01:20:00Z** (22:20 BRT on 2026-07-28) |
| Rule for `R` | first round with `timestamp ≥ T_calib`, i.e. `R = floor((T_calib − genesis)/3) + 1` |
| **`R` (pre-computed)** | **30828212** — `ts(R)` = `2026-07-29T01:20:00Z` exactly |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** |
| Derivation | `seed = SHA256( ascii_hex(randomness) )`, lowercase hex, no `0x`, no whitespace |

### Two points of precision — verified, not assumed

1. **The encoding is ASCII, not bytes.** For round 30800000, `SHA256` over the
   hex string gives `1ae88fbf27fe83bc…`; over the decoded bytes it gives
   `0e6824e682b9d776…`. These are different seeds. Locked: **the hex string**.
2. **API v2 does not return `randomness`** — only `round` and `signature`. The
   `randomness` field exists solely on the v1 endpoint. A rule that does not pin
   the endpoint is not reproducible. **Both points apply to §2 as well**, which
   currently writes `SHA256(randomness_hex(R))` without pinning either.

**Fallback** (beacon unreachable at `T_calib`): `seed = SHA256(block_hash(H))`,
`H` = first Bitcoin block mined at or after `T_calib`. Use of the fallback is
recorded in the deviations changelog.

## Third-party verification

```bash
RAND=$(curl -s https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971/public/30828212 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)
python extract_episodes.py --sample 300 --seed "$SEED"
```

The resulting sample is byte-deterministic: `extract_episodes.py` orders by
`SHA256(seed + episode_id)`, with no unseeded `random` and no execution
timestamp.

## Scope — what this seed does NOT govern

- It does **not** govern arm assignment (that is §2, a distinct round, later than registration).
- It is **not** a result. It governs only *which* 300 episodes out of 4,560 go to the panel.
- Stratification by primary signature is independent of the seed and already verified:
  a draw of 300 covers all **72** primary signatures.

## Filled in after `T_calib` — 2026-07-29T01:20:00Z

| Field | Value |
|---|---|
| `randomness(R)` | `da5c9bde5b640648a70466bb98a106613afcee13a2bee3c22130d97f89900421` |
| **derived `seed`** | **`f61f4c463dc86251e0f6620c37c5cece202b36b3c183e13f0ec5e98f488f4319`** |
| SHA-256 of the 300-episode sample | `8e95d70ee20533eab4129641fe968dd9afb86c3bc8672571e9f712fd44df2eff` |
| SHA-256 of the **full corpus** at sampling time | `34dc3fd13e8e8c73774578457a70f7eab32f091ebdb4b0fd937fb63432ef3d76` |

⚠️ The sample hash is computed over the body **without** the trailing newline;
`shasum` of the on-disk file gives `b0862afc…` and the difference is exactly that
byte. This is not corruption — but anyone verifying needs to know which of the
two they are reproducing.

### Corpus state at sampling — and why this has to be frozen

| | pre-registration (2026-07-26) | sampling (2026-07-29) |
|---|---|---|
| episodes | 4,560 | **5,547** |
| `is_error` | 434 (9.5%) | **514 (9.3%)** |
| coarse / primary / fine | 14 / 72 / 162 | 14 / **74** / **168** |

The 300-episode sample covers **74 of 74** primary signatures — the *property*
asserted in §4.1 (full coverage) held; the *number* changed. Distribution: 20.0%
`is_error` in the sample against 9.3% in the corpus, the expected effect of
stratification, which over-samples rare signatures.

**What this exposes:** the `sig()` taxonomy is derived from the data, and the
corpus grows by ~330 episodes/day. Without freezing, any published number goes
stale between writing and submission — which is what happened to "72" in three
days. Declaring the seed is **not enough** for reproducibility: a seed orders a
set, and the set moves. The corpus hash above freezes the set for this sampling,
but actually reproducing it requires a snapshot of the `action-archive` at that
date, not just the hash. **Open item, not resolved here.**
