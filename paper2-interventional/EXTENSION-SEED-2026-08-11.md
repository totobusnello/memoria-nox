# Panel extension — sampling seed declaration (window 2026-07-30 → 08-11)

> **Registered before the round existed.** This file is committed and pushed to
> the public repository on 2026-08-11, **before** the beacon round named below is
> emitted. The repository history is the precedence stamp — the same mechanism as
> `CALIBRATION-SEED.md` and the `SEED_B` of `PILOT-PROJECTION.md` §4.

## Why this extension exists

Completing the moonshot panel (1,050/1,050, 2026-08-11) and reconciling the
five-family panel in `pilot_replay.py` confirmed the same count of analysable
epochs as on 2026-07-29: **12 epochs, 11 usable for the ICC** — below the 30–50
floor that §9 requires. The action corpus (recovered from the hard-coded
`CLAUDE_CONFIG_DIR` bug of 2026-08-10) contains **27 distinct epochs** in total,
of which **8,826 episodes** were never adjudicated.

## Design — locked before the sample

| Field | Value |
|---|---|
| Stratum A (`is_error`, census) | **632** episodes — all of them, no sampling |
| Stratum B (complement, sampled) | **1,576** of 8,194 — target HT weight **5.2×**, the same regime already characterised in piece 3 (introduces no new variance) |
| Panel | **3 families**: `zhipu` (GLM-5.2) · `xai` (Grok-4.5) · `moonshot` (K3) |
| Panel tested and discarded | `zhipu`/`xai`/`deepseek` — measured on 2026-08-11 against the 300-episode calibration set (n=266 complete): **Fleiss' κ = 0.6464** (below the 0.75 floor), Krippendorff's ordinal α = 0.8250 (above). The divergence was not resolved in the trio's favour — we kept the trio already validated on both coefficients (`zhipu`/`xai`/`moonshot`, κ=0.8747 / α=0.8557, measured 2026-07-29) |
| Total episodes | 2,208 |
| Total calls (3 panelists) | 6,624 |

## Seed — locked parameters

| Field | Value |
|---|---|
| Beacon | `drand` / League of Entropy — **quicknet** |
| Chain hash | `52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971` |
| Period | 3 s · genesis `1692803367` |
| `T_declare` | **2026-08-11T21:48:59Z** |
| Rule for `R` | first round with ≥ 5 min of slack over `T_declare`, so that the commit precedes the reveal by a comfortable margin, not merely formally |
| **`R` (pre-computed)** | **31227290** — `ts(R)` = `2026-08-11T21:53:57Z` |
| Endpoint | `https://api.drand.sh/<chain>/public/<R>` — **v1** |
| Derivation | `seed = SHA256( ascii_hex(randomness) )`, lowercase hex, no `0x`, no whitespace — the same encoding rule as `CALIBRATION-SEED.md` (ASCII, not decoded bytes) |

## Third-party verification

```bash
RAND=$(curl -s https://api.drand.sh/52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971/public/31227290 | jq -r .randomness)
SEED=$(printf '%s' "$RAND" | sha256sum | cut -d' ' -f1)
# Stratum B (complement): order by SHA256(seed || "|" || episode_id), take the first 1576
```

> ⚠️ **Correction 2026-08-14 — the `|` separator is mandatory and was missing
> here.** The original version of this section said `SHA256(seed + episode_id)`,
> with no separator. The rule actually used — the one `pilot_replay.py`
> implements (`sha256(seed.encode("ascii") + b"|" + episode_id.encode())`) and
> which `PILOT-PROJECTION.md` §4 already specified — concatenates with `|`.
>
> Verified by reconstruction on 2026-08-14: with the separator, the ordering
> reproduces **1,565 of the 1,576** episodes actually adjudicated (99.3%; the
> remaining 11 are a universe boundary effect — see `SIZING-2026-08-14.md` §1).
> **Without** the separator it reproduces **293**. A third party following the
> published command would wrongly conclude that the sample does not match the
> seed.
>
> The seed, the round and the design **did not change** — only the description of
> the ordering rule, which was incomplete. This is a documentation fix, not a
> method fix.

## Scope — what this seed does NOT govern

- It does not govern arm assignment in the live study (that remains §2).
- It is not a result. It governs only which 1,576 of the complement's 8,194
  episodes go to the panel — the stratum A census needs no seed.
