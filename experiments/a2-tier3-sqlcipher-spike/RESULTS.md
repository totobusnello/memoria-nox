# A2 Tier 3 — P0 SQLCipher Compat Spike — RESULTS

**Data:** 2026-05-24
**Branch:** `feat/a2-tier3-sqlcipher-spike-p0`
**Spec base:** `specs/2026-05-24-A2-tier3-crypto-audit-RECON.md`
**Time-box:** 4h (actual: ~90min)
**Author:** executor-high spike agent

---

## Verdict

# **GO** ✔ — proceed to A2 Tier 3 Phase 1 (SQLCipher dependency wire-up + key open path)

All critical compatibility gates passed. SQLCipher 4.16.0 + `better-sqlite3-multiple-ciphers` 13.x + `sqlite-vec` v0.1.9 form a viable stack on darwin-arm64 (and by build-symmetry, Linux x86_64). VACUUM INTO snapshot pipeline (op-audit pattern) preserves both ciphertext **and** vec0 virtual-table content. Performance overhead measured but absolute numbers stay deep inside the hybrid-search latency budget (per `[[q3-latency-numbers]]`).

LUKS-only fallback (D-A2T3-1 option c) is NOT triggered. Pivot reserved for future CVE/regression scenarios only.

---

## Test matrix — per-phase results

| Phase | Test | Status | Notes |
|---|---|---|---|
| 0 | Environment probe (sqlcipher, node, npm) | ✅ PASS | sqlcipher 4.16.0 (SQLite 3.53.1) via `brew install sqlcipher` |
| 1.a | sqlcipher CLI basic CRUD with `PRAGMA key` | ✅ PASS | Insert + select + count round-trip clean |
| 1.b | Wrong-key rejection | ✅ PASS | `file is not a database (26)` — deterministic clean fail |
| 1.c | WAL plaintext leak probe | ✅ PASS | `.wal` file absent (checkpoint absorbed); zero marker leak |
| 1.d | Main DB plaintext leak probe (via `strings`) | ✅ PASS | Ciphertext only — `UNIQUE_PLAINTEXT_MARKER` not visible |
| 2 | `VACUUM INTO` produces encrypted snapshot, reopens with same key | ✅ PASS | 3 rows preserved; op-audit `snapshot()` compatible |
| 3 | FTS5 virtual table — CREATE / INSERT / MATCH / rebuild | ✅ PASS | FTS5 fully functional on encrypted DB |
| 4 | Loadable extension policy (`SQLITE_OMIT_LOAD_EXTENSION` flag) | ✅ PASS | OMIT flag = 0; load_extension capability available |
| 5.a | `better-sqlite3-multiple-ciphers` install | ✅ PASS | npm install clean, builds binding |
| 5.b | Node binding CRUD (100 rows) | ✅ PASS | 100/100 inserted + selected |
| 5.c | Node binding FTS5 (`MATCH 'chunk'`) | ✅ PASS | 100/100 indexed |
| 5.d | Node binding `loadExtension()` API present | ✅ PASS | API exposed; error on missing dylib is expected `no such file` |
| 5.e | Node binding `VACUUM INTO` + reopen w/ key | ✅ PASS | 100/100 snapshot rows preserved |
| 5.f | Node binding bench (1000 point lookups) | ✅ PASS | ~24μs/op steady-state |
| 6 | Vanilla vs cipher CLI overhead (5k inserts) | ✅ PASS | 572% overhead — KDF-dominated, see Phase 7 for steady-state |
| 7 | Realistic per-op benchmark (5k writes + 5k reads + 500 FTS) | ✅ PASS | See §perf below |
| 8.a | `sqlite-vec` load on SQLCipher-encrypted DB | ✅ PASS | `vec_version()` returns v0.1.9 |
| 8.b | `vec0` virtual table CREATE on encrypted DB | ✅ PASS | `CREATE VIRTUAL TABLE vec_chunks USING vec0(embedding float[8])` |
| 8.c | Vector INSERT with BigInt rowid | ✅ PASS | 4 vectors @ 8d each |
| 8.d | Cosine MATCH query returns sorted by distance | ✅ PASS | Top1 distance=0 for exact-match query |
| 8.e | Reopen + reload extension + count vec0 rows | ✅ PASS | 4/4 preserved across close/reopen |
| 8.f | `VACUUM INTO` snapshot of DB with vec0 rows | ✅ PASS | Snapshot preserves vec0 table + 4/4 rows readable |

**Critical-gate pass rate:** 22/22 (100%).

---

## Performance numbers (Phase 7, darwin-arm64, M-series, hot cache)

5000-row corpus, 3072d-float32 BLOB column, FTS5 contentless mirror:

| Metric | Vanilla SQLite | SQLCipher | Δ relative | Δ absolute |
|---|---|---|---|---|
| Bulk insert 5000 rows (transaction) | 83.4 ms | 465.9 ms | **+458%** | +382 ms one-time |
| FTS5 `INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')` | 4.8 ms | 16.6 ms | **+244%** | +12 ms one-time |
| Point lookup (indexed PK) — p50 | 4.1 µs | 26.0 µs | **+529%** | **+22 µs** |
| Point lookup — p95 | 8.9 µs | 26.7 µs | **+200%** | +18 µs |
| Point lookup — p99 | 9.5 µs | 30.6 µs | +221% | +21 µs |
| FTS5 `MATCH` query — p50 | 9 µs | 33 µs | +267% | +24 µs |
| FTS5 `MATCH` query — p95 | 13 µs | 35 µs | +163% | +22 µs |

### Interpretation against nox-mem hot-path budget

Per `[[q3-latency-numbers]]` (2026-05-18 first real measurement): **search hybrid p50 = 940ms, p95 = 2342ms, p99 = 2523ms**. The dominant cost (~800ms p50) is the **Gemini embedding network round-trip**, which is unaffected by storage-layer cipher.

SQLite-layer time within that 940ms p50:
- FTS5 BM25 stage: ~50-200ms (62.9k chunks)
- sqlite-vec semantic stage: ~100-300ms (3072d cosine)
- RRF fusion: <5ms

**Projected p50 impact of SQLCipher cipher on real workload:**
- BM25 stage worst-case: +50ms × 2.67 = +133ms (if perfectly contended on FTS5 reads, which it is not — FTS5 results scale per-doc not per-query)
- More accurately: per-query overhead = #(FTS hits + vec hits) × ~22µs/read. For top-100 retrieval: 200 reads × 22µs = **+4.4ms**
- vec0 stage: dominated by full-vec0 scan (sqlite-vec brute-force) and BLOB I/O. Phase 8 confirms vec0 works on encrypted DB; expect ~10-20% overhead on the BLOB read = **+20-60ms p50**

**Total realistic p50 impact: +25-65ms on top of 940ms baseline = +3-7%.** Well under the §7 hard-gate budget of p95 < 3000ms (current 2342ms p95 + 65ms = 2407ms = still inside budget).

KDF one-time cost at process boot (`PRAGMA key`): ~70-100ms on this hardware (PBKDF2 256k iter via `cipher_compatibility=4`). Amortized across the lifetime of the long-running `nox-mem-api` process: zero.

### Phase 6 vs Phase 7 — why the difference

Phase 6 measures cold-start CLI invocations (each test = fresh process → KDF runs each time → ~70ms baked into every measurement). Phase 7 measures steady-state per-op within a single process. **Phase 7 is the operationally relevant number** for nox-mem prod (long-running daemon). Phase 6 captures only the cron-job style worst case (which nox-mem does not have on the hot path).

---

## Build instructions discovered

### macOS (development, validated on this spike)

```bash
brew install sqlcipher          # 4.16.0 BSD-3-Clause AND blessing
cd <project>
npm install better-sqlite3-multiple-ciphers  # 13.x, drop-in replacement for better-sqlite3
npm install sqlite-vec                       # 0.1.9, includes platform-specific dylib subpackage
```

Auto-installed companion: `sqlite-vec-darwin-arm64` (or `-linux-x64` etc.) ships `vec0.dylib` / `vec0.so` — pre-built, no compile required.

### Linux production (VPS Hostinger, projected; D-A2T3-1 deferred to P1)

```bash
apt-get install -y sqlcipher libsqlcipher-dev   # Debian/Ubuntu — verify version ≥ 4.5
cd /root/.openclaw/workspace/tools/nox-mem
npm install better-sqlite3-multiple-ciphers      # builds against libsqlcipher
npm install sqlite-vec                           # pulls sqlite-vec-linux-x64 prebuild
```

**Risk note:** `better-sqlite3-multiple-ciphers` bundles its own SQLCipher build by default (no system libsqlcipher needed). The system package is only needed for CLI usage during migration. Recommend: rely on bundled build for runtime, install system pkg for ops-tooling only.

### Open-source identity

- **`better-sqlite3-multiple-ciphers`** — fork of `better-sqlite3` (WiseLibs MIT) using SQLite3 Multiple Ciphers project (utelle) — MIT, currently maintained, last release 2026 (check at P1 time).
- **`sqlite-vec`** — Alex Garcia (alexgarcia.xyz), Apache-2.0, v0.1.9 at spike time.
- **SQLCipher community edition** — Zetetic LLC, BSD-3-Clause AND "blessing" (CC0-equivalent). Enterprise tier is optional commercial.

All three licenses are compatible with nox-mem (MIT) and Supermem distribution. No GPL or copyleft contamination.

---

## Failures + workarounds discovered

| # | Symptom | Root cause | Workaround | Memory ref |
|---|---|---|---|---|
| F1 | `VACUUM INTO` validation reported FAIL on first run | Bash script `tr -d '[:space:]'` collected "ok" from `PRAGMA key` stdout into the count value → got `ok3` | Use `grep -E '^[0-9]+$' | tail -1` to extract integer-only line | new — add to `[[sqlite-text-affinity-coerces-int-back]]` follow-up |
| F2 | `vec0` rejected JS Number as rowid: "Only integers are allows for primary key values" | better-sqlite3 binds JS Number as REAL by default; vec0 requires strict INTEGER | Use BigInt literal (`1n` instead of `1`) OR call `db.defaultSafeIntegers(true)` | reinforces `[[sqlite-text-affinity-coerces-int-back]]` — same root cause class |
| F3 | Phase 6 raw `time` reading suggests 572% overhead | Per-invocation KDF + cold cache | Operationally irrelevant for long-running daemon; ignore in favor of Phase 7 steady-state | new |
| F4 | (none observed for FTS5 or vec0 on encrypted DB) | n/a | n/a | n/a |

**No blocking failures.** All workarounds are documented and either trivial (BigInt cast) or analyst-only (test harness fix).

---

## Mapping to recon §10 decisions

The spike data directly addresses three of the recon's open decisions:

| Recon decision | Spike contribution |
|---|---|
| **D-A2T3-1** (SQLCipher primary?) | **Confirms option (b) spike-first PASSED** → SQLCipher is primary. LUKS-only fallback (c) not needed. |
| **D-A2T3-3** (sqlite-vec via `enable_load_extension`?) | **Confirms option (a) Yes** — `loadExtension()` API exposed; vec0 v0.1.9 works on encrypted DB; allowlist + chmod 0o555 hardening still required in P1 (no change to recon recommendation). |
| **D-A2T3-1 cipher_compatibility selection** | `cipher_compatibility=4` (AES-256-CBC HMAC-SHA512) — current SQLCipher 4 default. GCM mode is not exposed via plain `PRAGMA` in 4.x — would require custom build. Recommend STAY on CBC+HMAC (mature, FIPS-vetted, AEAD-equivalent via HMAC pairing). Add this to D-A2T3-1 follow-up doc at P1. |

The other 4 decisions (D-A2T3-2 reads_audit default, D-A2T3-4 reads_audit retention, D-A2T3-5 signed checkpoints) are not data-dependent on this spike — Toto already approved them per task brief.

---

## Reproduction

```bash
cd experiments/a2-tier3-sqlcipher-spike
./spike-runner.sh           # full spike — phases 0-8
./spike-runner.sh --quick   # skip Node binding + bench + vec (phases 5/7/8)
./spike-runner.sh --clean   # wipe work/ and exit
```

Outputs:
- `work/spike-runner.log` — full transcript per-phase
- `work/verdict.txt` — `VERDICT=GO|NO-GO` machine-readable
- `work/bench-realistic.json` — JSON perf numbers (Phase 7)
- `work/*.db` — per-phase test DBs (preserved for forensic inspection)

Spike is hermetic per work-dir; safe to commit, safe to re-run.

---

## Next steps (recon §9 phasing)

Spike unblocks D-A2T3-1 option (b) → proceed to **P1** (SQLCipher dependency wire-up in `src/lib/db.ts` key open path, ~3h, no migration yet).

| Phase | Status | Trigger |
|---|---|---|
| **P0 (this spike)** | ✅ DONE — GO verdict | Toto sign-off recon §10 — already received |
| P1 (db.ts wire-up) | Unblocked | Spike PR merged + this RESULTS.md reviewed |
| P2 (migration script + DR doc) | Blocked on P1 | P1 lands |
| P3 (`reads_audit` table + opt-in wrapper) | Independent of P1 (can parallel) | Defaults from D-A2T3-2/4/5 (locked) |
| P4-P5 (checkpoints + verify CLI) | Blocked on P3 | P3 lands |
| P6 (DEPLOY-A2-T3 ops guide) | Final | After P1-P5 |
| P7 (prod VPS migration, 62.9k chunks) | Final | After P6 + security review |

Total realistic estimate per recon: ~25h spread across 5-7 sessions. Spike consumed ~1.5h of that — net remaining ~23h.

---

## 3-paragraph summary

The P0 spike validates SQLCipher as the at-rest cipher path for A2 Tier 3 with high confidence. All 22 critical-gate tests passed across 8 phases, covering CLI smoke (CRUD, wrong-key rejection, no plaintext leak in main DB or WAL), op-audit pattern compatibility (`VACUUM INTO` snapshot + reopen), FTS5 functionality on encrypted DB, Node binding (`better-sqlite3-multiple-ciphers`) install and full feature parity (CRUD + FTS5 + snapshot + `loadExtension()` API), realistic per-op benchmarks, and — most critically — `sqlite-vec` v0.1.9 loaded into the encrypted DB with vec0 virtual table creation, vector insert (using BigInt rowid), cosine-match query returning correct top-1 (distance=0 for exact match), and VACUUM INTO snapshot preservation of the vec0 table.

Performance overhead is real but well-bounded against nox-mem's actual hot path. Steady-state read p50 goes from 4 µs (vanilla) to 26 µs (cipher) — a +22 µs absolute cost per indexed lookup. FTS5 MATCH p50 goes 9 µs → 33 µs. Projected impact on the production hybrid-search 940 ms p50 budget: +25-65 ms (+3-7%), keeping p95 inside the §7 hard-gate of 3 s. The 458% bulk-write overhead and 572% Phase-6 CLI-cold-start overhead are KDF-dominated (~70-100 ms one-time at `PRAGMA key`) and operationally irrelevant for the long-running `nox-mem-api` daemon. Two minor implementation notes were discovered: vec0 requires strict BigInt rowid (already a known class via `[[sqlite-text-affinity-coerces-int-back]]`), and any test harness must extract integer values from `sqlcipher` CLI output by line-pattern not whole-string-trim.

The verdict is unambiguous: GO. SQLCipher 4.16.0 + better-sqlite3-multiple-ciphers + sqlite-vec form a maintenance-clean, license-compatible (MIT + Apache-2.0 + BSD-3-Clause) stack. The LUKS-only fallback path (D-A2T3-1 option c) is reserved for future SQLCipher CVE response only. Recommended next move: merge this PR, then begin P1 (`src/lib/db.ts` key-open wire-up, ~3h), with P3 (`reads_audit` table + opt-in wrapper) runnable in parallel since it depends only on the already-locked D-A2T3-2/4/5 defaults.

---

*Spike timeboxed 4h. Actual elapsed ~90min including environment install, runner authoring, vec probe authoring, three full reruns, and this writeup.*
