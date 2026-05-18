# DEPENDENCIES.md — Aggregated Dependency Manifest

> **Status:** Generated 2026-05-18. Single source of truth for direct dependencies across all sub-packages.
> Auto-update: run `find . -name "package.json" -not -path "*/node_modules/*" -not -path "*/.claude/*"` and cross-check with this file after any `npm install`.
>
> For the full supply-chain policy, vulnerability SLA, and license allowlist, see [`docs/security/DEPENDENCY-POLICY.md`](docs/security/DEPENDENCY-POLICY.md).
> For SBOM artifacts, see the `sbom/` directory (generated on each CI push via `@cyclonedx/cyclonedx-npm`).

---

## 1. Root Package

There is **no root-level `package.json`** in this repository. The codebase is organized as a collection of isolated sub-packages — each staged-* directory, sdk/, tests/, and eval/ subdirectory contains its own package.json. There is intentionally no shared root lockfile.

**Implication:** `npm audit` and Renovate run independently per sub-package. The dependency-review-action in CI diffs each sub-package's lockfile on every PR.

---

## 2. Per-Package Dependency Tables

### 2.1 staged-A1.1 — `nox-mem-privacy-br`

Brazilian PII pattern library (CPF/CNPJ/PIX/CEP/RG) for the privacy filter.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0 (zero-dependency module — by design)
**Risk:** None. Pure TypeScript type definitions only.

---

### 2.2 staged-A2 — `nox-mem-archive`

Export/Import archive primitives (T1-T9): TAR.gz format, AES-256-GCM encryption, schema migration.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `tar-stream` | `^3.1.7` | MIT | dep | Streaming TAR builder/parser — only runtime dep |
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |
| `@types/tar-stream` | `^3.1.3` | MIT | devDep | Types for tar-stream |

**Direct dep count:** 1 runtime, 3 dev
**Transitive runtime deps:** ~4 (`tar-stream` pulls `b4a`, `fast-fifo`, `streamx`, `readable-stream` — all MIT)
**Risk:** Low. `tar-stream` is actively maintained (JoeKarlsson, npm: 5M+ weekly downloads). Last major release 2023. No known CVEs.

---

### 2.3 staged-A2.1 — `nox-mem-archive-strength`

Passphrase entropy enforcement (Gap G1 from THREAT-MODEL). Zero external runtime dependencies.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0
**Risk:** None.

---

### 2.4 staged-A3 — `nox-mem-providers`

Provider abstraction (T9-T16): fallback chain, cost cap, telemetry, multi-provider factory.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0
**Note:** Providers are instantiated at runtime by the host package (which imports the Gemini SDK, OpenAI SDK, etc.). staged-A3 itself only ships types and the factory interface.

---

### 2.5 staged-G5 — `nox-mem-error-sanitizer`

Central error sanitizer middleware (Gap G5 from THREAT-MODEL). Strips stack traces from API responses.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0

---

### 2.6 staged-L2 — `nox-mem-conflict-detection`

KG conflict detection (memanto Gap #5 differentiator). Type 1 direct contradictions, shadow-first.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `better-sqlite3` | `^11.0.0` | MIT | devDep | SQLite binding (test corpus) |
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |
| `@types/better-sqlite3` | `^7.6.0` | MIT | devDep | Types for better-sqlite3 |

**Direct dep count:** 0 runtime, 4 dev
**Transitive runtime deps:** 0
**Note:** `better-sqlite3` here is a devDep (test-only). The runtime SQLite instance comes from the host `nox-mem` package.
**Version note:** Uses `^11.0.0` while staged-P1 uses `^12.10.0` — minor drift, both MIT. Should be aligned to `^12.x` when merged.

---

### 2.7 staged-L3 — `nox-mem-confidence-field`

Confidence + provenance field staged patch (T1-T13).

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0

---

### 2.8 staged-L4 — `nox-mem-regex-extract`

Regex-first typed-link extraction with Gemini fallback (T1-T6).

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0

---

### 2.9 staged-P1 — `nox-mem-answer-primitive`

Answer primitive staged patch (T1-T14): retrieval, prompt, provider, telemetry, CLI, HTTP, MCP, integration tests.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `better-sqlite3` | `^12.10.0` | MIT | devDep | SQLite binding (test corpus) |
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |
| `@types/better-sqlite3` | `^7.6.13` | MIT | devDep | Types for better-sqlite3 |

**Direct dep count:** 0 runtime, 4 dev
**Transitive runtime deps:** 0

---

### 2.10 staged-P2 — `nox-mem-hooks-autocapture`

Hooks auto-capture (T1-T15): 5 privacy layers, source allowlist, session tracking.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0

---

### 2.11 staged-P5 — `nox-mem-viewer-realtime`

Viewer real-time SSE staged patch (T1-T15): event taxonomy, instrumentation.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0

---

### 2.12 staged-privacy — `nox-mem-privacy-filter`

Privacy filter staged patch — pre-storage redaction for nox-mem.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0

---

### 2.13 sdk/typescript — `@nox-mem/client`

Type-safe TypeScript client for the memoria-nox HTTP API.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.5.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^22.0.0` | MIT | devDep | Node.js type definitions (22.x — higher than staged-* which use 20.x) |
| `jest` | `^29.0.0` | MIT | devDep | Test runner |
| `ts-jest` | `^29.0.0` | MIT | devDep | Jest TypeScript transformer |
| `openapi-typescript` | `^7.0.0` | MIT | devDep | OpenAPI → TypeScript types generator |

**Direct dep count:** 0 runtime, 5 dev
**Transitive dev deps:** ~50 (jest ecosystem — babel-jest, jest-circus, etc. — all MIT or BSD)
**Note:** No runtime deps. The client is zero-dependency at runtime (pure fetch + generated types). This is intentional per D41 autonomy pillar.
**Node version drift:** Uses `@types/node@^22` while most staged-* use `@20` — SDK supports Node 22 explicitly. Not a conflict but worth aligning over time.

---

### 2.14 scripts/deploy-validator — `deploy-validator`

Local dry-run validator for DEPLOY-WAVE-B.md commands.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.5` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |
| `ts-node` | `^10.9.2` | MIT | devDep | TypeScript executor (no separate build step) |

**Direct dep count:** 0 runtime, 3 dev
**Transitive dev deps:** ~15 (`ts-node` pulls `@cspotcode/source-map-support`, `@tsconfig/node*`, `acorn`, `acorn-walk`, `arg`, `create-require` — all MIT)
**Note:** Dev tool only. Not shipped to production. `ts-node@10.x` is compatible with `typescript@5.4.x` but `ts-node` has not released a v11 — the underlying `ts-node@10` + `tsc@5.x` combo works but is worth monitoring as TypeScript 6.x approaches.

---

### 2.15 tests/cross-pillar — `nox-mem-cross-pillar-tests`

Cross-pillar integration tests (Wave G). 12 scenarios exercising staged module combinations.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |
| `better-sqlite3` | `^12.10.0` | MIT | devDep | In-memory SQLite for test corpus |
| `@types/better-sqlite3` | `^7.6.13` | MIT | devDep | Types for better-sqlite3 |

**Direct dep count:** 0 runtime, 4 dev
**Transitive runtime deps:** 0

---

### 2.16 tests/visual-regression — `nox-mem-visual-regression`

Playwright visual regression tests for P5 viewer frontend.

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `@playwright/test` | `^1.44.0` | Apache-2.0 | devDep | Browser automation + test runner |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |

**Direct dep count:** 0 runtime, 3 dev
**Transitive dev deps:** ~200 (Playwright bundles its own browser binaries + CDP bindings — all Apache-2.0 or MIT)
**Note:** Playwright is by far the heaviest dev dependency in the repo. Its browser binaries are not counted in the dep graph but consume ~600 MB on disk. This is acceptable for a visual regression suite.

---

### 2.17 eval/latency — `nox-mem-latency-bench`

Latency benchmark harness (p50/p95/p99 for hybrid search + ingest).

| Package | Version Range | License | Type | Purpose |
|---------|--------------|---------|------|---------|
| `typescript` | `^5.4.0` | Apache-2.0 | devDep | TypeScript compiler |
| `@types/node` | `^20.0.0` | MIT | devDep | Node.js type definitions |

**Direct dep count:** 0 runtime, 2 dev
**Transitive runtime deps:** 0

---

## 3. License Summary

All direct dependencies use licenses from the [approved allowlist](docs/security/DEPENDENCY-POLICY.md#license-allowlist). No blocked licenses detected.

| License | Packages | Count |
|---------|----------|-------|
| **MIT** | `better-sqlite3`, `@types/better-sqlite3`, `@types/node`, `jest`, `ts-jest`, `ts-node`, `tar-stream`, `openapi-typescript` | 8 unique packages |
| **Apache-2.0** | `typescript`, `@playwright/test` | 2 unique packages |
| **MIT (transitive, tar-stream)** | `b4a`, `fast-fifo`, `streamx`, `readable-stream` | 4 transitive |
| **MIT (transitive, jest)** | jest ecosystem (~50 packages) | ~50 transitive |
| **Apache-2.0 (transitive, Playwright)** | Playwright internals + browser bindings | ~200 transitive |

**No GPL, LGPL, AGPL, MPL, BUSL, or proprietary licenses detected in any direct or known transitive dependency.**

**Copyleft exposure: NONE.** Every runtime dependency is MIT or Apache-2.0.

---

## 4. High-Risk Dependency Assessment

A dep is flagged as high-risk if any of:
- Last release > 2 years ago with open security issues
- Known CVE unpatched
- Maintenance status "deprecated" or "unmaintained"
- Used only in one sub-package while better alternatives exist

| Package | Version | Flag | Notes |
|---------|---------|------|-------|
| `tar-stream` | `^3.1.7` | LOW | Actively maintained. No known CVEs. Transitive deps are all stable. |
| `ts-node` | `^10.9.2` | WATCH | No v11 released. `ts-node@10` + `typescript@5.4.x` works but is an informal compatibility path. The `tsx` ecosystem is emerging as an alternative. Not urgent — deploy-validator is a local tool only. |
| `better-sqlite3` | `^11.0.0` (L2) vs `^12.10.0` (P1, cross-pillar) | LOW | Version drift across sub-packages. Both are MIT. Recommend aligning to `^12.10.0` when staged modules graduate. |
| `jest` | `^29.0.0` | WATCH | Jest 30 is in development. Migrate when jest-ts ecosystem catches up (ts-jest@30 needed first). |
| `@playwright/test` | `^1.44.0` | LOW | Released 2024. Actively maintained by Microsoft. Check for `^1.45+` for any relevant fixes. |
| `openapi-typescript` | `^7.0.0` | LOW | Recent release. Active maintenance. No known issues. |

**Overall: no CRITICAL or HIGH-risk dependencies.** The two WATCH items are versioning / ecosystem gaps, not vulnerabilities.

---

## 5. Cross-Package Version Consistency

### `typescript`

| Sub-package | Range | Effective |
|-------------|-------|-----------|
| Most staged-* | `^5.4.0` | 5.4.x |
| sdk/typescript | `^5.5.0` | 5.5.x |
| scripts/deploy-validator | `^5.4.5` | 5.4.x |

All within TypeScript 5.x. No breaking changes between minor versions. Recommendation: align to `^5.5.0` uniformly when staged modules graduate.

### `@types/node`

| Sub-package | Range |
|-------------|-------|
| Most staged-* | `^20.0.0` |
| sdk/typescript | `^22.0.0` |

The SDK targets Node 22 explicitly (LTS as of 2025). Staged modules use `^20` for broader compatibility. This is an intentional split, not a problem. When staged modules graduate, update to `^22`.

### `better-sqlite3`

| Sub-package | Range |
|-------------|-------|
| staged-L2 | `^11.0.0` |
| staged-P1 | `^12.10.0` |
| tests/cross-pillar | `^12.10.0` |

Align staged-L2 to `^12.10.0` before graduation. The API is backward-compatible.

---

## 6. Update Strategy

### Automated updates (Renovate)

Renovate is configured via [`.github/renovate.json`](.github/renovate.json) and runs weekly on Mondays UTC. It:
- Auto-merges **patch** updates for packages with no breaking history
- Opens PRs for **minor** updates (maintainer review required)
- Opens PRs for **major** updates (full CI + changelog review required)
- Groups all security updates into a single high-priority PR

See [`docs/security/DEPENDENCY-POLICY.md#automated-updates-renovate`](docs/security/DEPENDENCY-POLICY.md#automated-updates-renovate) for full configuration details.

### Manual review triggers

Review all dependencies manually when:
1. A CVE is announced against any direct dependency (check via `npm audit` in the relevant sub-package)
2. A direct dependency releases a major version
3. A sub-package graduates from `staged-*` to main — run `npm audit --audit-level=high` in the staged dir before merging

### Adding a new dependency

Per [`docs/security/DEPENDENCY-POLICY.md#direct-vs-transitive-dependencies`](docs/security/DEPENDENCY-POLICY.md#direct-vs-transitive-dependencies):

1. Verify the license is on the allowlist
2. Check for known CVEs: `npm info <package> | grep -i cve`
3. Check maintenance status: last publish date, open issues, download trends
4. Add a comment in the PR body: "Why no existing dep covers this?"
5. Update this file under the relevant sub-package section

---

## 7. SBOM Cross-Reference

SBOM artifacts (CycloneDX JSON format) are generated on every CI push via `@cyclonedx/cyclonedx-npm`. They are stored in the `sbom/` directory (not yet present — target: Wave C completion).

When `sbom/` is populated, each artifact follows the naming convention:

```
sbom/<sub-package>.cdx.json
```

Example:
```
sbom/staged-A2.cdx.json
sbom/sdk-typescript.cdx.json
```

Until SBOM artifacts are present, treat this file as the canonical dependency inventory.

For supply-chain audit procedures, see [`docs/security/OPENSSF-AUDIT.md`](docs/security/OPENSSF-AUDIT.md).

---

## 8. Known Gaps and TODOs

| ID | Gap | Priority |
|----|-----|----------|
| DEP-1 | `sbom/` directory not yet populated — SBOM generation is scoped to Wave C | Medium |
| DEP-2 | `better-sqlite3` version drift (^11 vs ^12) across staged-L2 vs staged-P1 | Low — fix at graduation time |
| DEP-3 | `ts-node` in deploy-validator has no clear successor plan — monitor `tsx` adoption | Low |
| DEP-4 | GitHub Actions SHA pinning not yet applied (using `@v4` tags) — flagged in OpenSSF Scorecard | Medium — tracked as P2 action in DEPENDENCY-POLICY |
| DEP-5 | `@types/node@^20` vs `@types/node@^22` drift — align when staged modules graduate | Low |

---

*Document version: 1.0.0 — 2026-05-18. Update this file whenever a sub-package's `package.json` changes. Cross-check with `docs/security/DEPENDENCY-POLICY.md` for policy questions.*
