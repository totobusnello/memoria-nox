# A2.1 — Passphrase entropy enforcement

> Closes Gap **G1** from `docs/security/THREAT-MODEL.md`: "Passphrase entropy not enforced — `getPassphrase()` accepts 'a'".

## TL;DR

Adds 4 modules + 2 test files to `staged-A2/edits/src/lib/archive/`:

| File | Role |
|---|---|
| `entropy.ts` | Zero-dep zxcvbn-inspired estimator → `estimateEntropyBits()` |
| `strength.ts` | Bits → tier mapping (`weak`/`fair`/`good`/`strong`) + meter |
| `enforce-strength.ts` | `enforcePassphraseStrength()` + `WeakPassphraseError` |
| `common-passwords.ts` | ~400-entry EN+BR dictionary (penalises matches) |

CLI integration (`src/cli/export.ts`):

- New flag `--allow-weak` (explicit opt-out).
- Env override `NOX_A2_ALLOW_WEAK_PASSPHRASE=1` (parity with CLI flag).
- Strength meter rendered to **stderr** (stdout stays machine-parseable).
- Default min tier: **`good`** (≥50 bits) — calibrated against scrypt N=2¹⁷ economics.

## Why zero-dep

- A3 (provider abstraction) ethos is "no vendor lock-in, minimal deps". Adding
  zxcvbn-ts (~700 KB + transitive) for a leaf-policy decision was rejected.
- The lightweight estimator UNDER-estimates when uncertain — safer default.
- Real zxcvbn is a drop-in upgrade if/when a regulator asks for it.

## Test summary

```
$ npm test --prefix staged-A2.1
# entropy.test.ts  → 27 tests
# enforce.test.ts  → 15 tests
# total            → 42 tests
```

## Wire-up from staged-A2

A2.1 ships side-by-side with `staged-A2/`. To enable in the deployed CLI:

1. Copy `staged-A2.1/edits/src/lib/archive/{entropy,strength,enforce-strength,common-passwords}.ts`
   into the live `src/lib/archive/`.
2. Replace `staged-A2/edits/src/cli/export.ts` with
   `staged-A2.1/edits/src/cli/export.ts` (drop-in — same exports).
3. Rebuild + redeploy. No DB migration. No schema change. No restart of long-lived
   services other than the CLI binary.

## Behaviour matrix

| Passphrase | Default | `--allow-weak` | `NOX_A2_ALLOW_WEAK_PASSPHRASE=1` |
|---|---|---|---|
| `""` (empty) | reject (existing) | reject (defensive) | reject |
| `"a"` | reject (weak) | accept + WARN | accept + WARN |
| `"password"` | reject (weak) | accept + WARN | accept + WARN |
| `"hunter2"` | reject (weak) | accept + WARN | accept + WARN |
| `"Tr0ub4dor&3"` | reject (fair) | accept + WARN | accept + WARN |
| `"MxQ7vR!2pK#wL9"` | accept (good) | accept (no warn) | accept (no warn) |
| `"Tr0ub4dor&3-Quantum#X9zP"` | accept (strong) | n/a | n/a |

## Threat-model traceability

- Section: 5.2 T-A2-1 "Passphrase fraca"
- Recommendation R-A2-1 (High, 1d): "Integrar zxcvbn ou min-entropy estimator. Reject `score < 3`."
- Gap row G1 (High, 1d) in Appendix A.

## NÃO faz parte do escopo

- Online checks (HIBP-style breach lookup) — would leak passphrase prefix even via
  k-anonymity API. Maybe A2.2.
- `zxcvbn-ts` integration — see "Why zero-dep" above. Maybe A2.3 when CI lands.
- Passphrase rotation reminders — separate concern (deploy-side, not lib).
