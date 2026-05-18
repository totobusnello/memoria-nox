# Dependency Policy — memoria-nox

> *Explicit rules governing which dependencies may be introduced, how vulnerabilities are handled, and what supply chain controls apply.*

---

## Guiding Principles

1. **Minimal surface.** Every dependency is an attack surface. If a feature can be implemented in 50 lines of TypeScript without pulling in a 5 MB transitive graph, that is the right call.
2. **License certainty.** Contributors and users must be able to ship this software without legal risk. Ambiguous or copyleft licenses that would contaminate MIT are blocked.
3. **Auditable.** Dependency versions are pinned. Changes are reviewed. The SBOM is generated on every push.
4. **Responsive.** Vulnerabilities are not queued behind feature work. The SLA is real.

---

## License Allowlist

The following SPDX license identifiers are **approved** for direct and transitive runtime dependencies:

| License | Notes |
|---------|-------|
| `MIT` | Preferred |
| `Apache-2.0` | Approved; patent grant included |
| `BSD-2-Clause` | Approved |
| `BSD-3-Clause` | Approved |
| `ISC` | Approved (functionally MIT-equivalent) |
| `0BSD` | Approved (zero-clause BSD) |
| `Unlicense` | Approved (public domain dedication) |
| `CC0-1.0` | Approved for non-code assets only |
| `Python-2.0` | Approved (PSF — no runtime use in this project) |

### Denylist (blocked by default)

| License | Reason |
|---------|--------|
| `GPL-2.0` | Copyleft — would require derivative works to be GPL |
| `GPL-3.0` | Same; ASP loophole does not apply to CLI tools |
| `AGPL-3.0` | Network copyleft — incompatible with MIT distribution |
| `LGPL-2.0` / `LGPL-2.1` / `LGPL-3.0` | Static linking ambiguity; avoid unless packaged as isolated optional plugin |
| `EUPL-1.1` / `EUPL-1.2` | Copyleft; EU jurisdiction complications |
| `CDDL-1.0` | Copyleft |
| `MPL-2.0` | File-level copyleft; permitted only if the MPL files are in a self-contained module not mixed with MIT code |
| `BUSL-1.1` | Business Source License — not OSI approved; timed open source with commercial restrictions |
| `Commons-Clause` + any license | Marketing restriction; not open source |
| `SSPL-1.0` | MongoDB license; OSI-rejected; AGPL-equivalent for cloud use |
| `Proprietary` | Obviously blocked |

### Exception process

If a dependency has a blocked license but is critical (no viable alternative), open an issue tagged `license-exception-request` with:
1. The package name and version
2. The license identifier
3. Why no MIT/Apache alternative exists
4. How the dependency will be isolated (dynamic import, optional peer dep, etc.)

Exceptions require explicit maintainer approval and are documented in `docs/DECISIONS.md`.

---

## Vulnerability Response SLA

| Severity | Definition | Target response | Target patch |
|----------|-----------|-----------------|-------------|
| **Critical** (CVSS 9.0–10.0) | RCE, auth bypass, full data exfiltration | 24 hours triage | 7 days |
| **High** (CVSS 7.0–8.9) | Privilege escalation, significant data exposure | 48 hours triage | 30 days |
| **Medium** (CVSS 4.0–6.9) | Limited exposure, requires auth/local access | 1 week triage | 60 days |
| **Low** (CVSS 0.1–3.9) | Theoretical; requires unusual conditions | Batch in next release | 90 days |

**Discovery sources monitored:**
- `npm audit` on every CI run (dependency-review-action blocks PRs with new high/critical)
- GitHub Dependabot alerts (auto-enabled for public repos)
- OSV.dev database (via Renovate security updates)
- Manual review when a CVE is announced in a direct dependency

**Response process:**
1. Security advisory opened privately (GitHub Private Vulnerability Reporting)
2. Fix developed on a private branch
3. Disclosure coordinated with reporter (if externally reported)
4. Patched version tagged and released
5. Security advisory published with CVE reference

---

## Direct vs Transitive Dependencies

### Direct dependencies

Direct dependencies (`dependencies` in `package.json`) are:
- Manually reviewed before addition
- License-checked against the allowlist above
- Added via `npm install <package>` with explicit version pinning (`^` range OK for minor/patch, `~` for patch-only on stability-sensitive packages like `better-sqlite3`)

**Rule:** every new direct dependency requires a corresponding comment in the PR body explaining why no existing dep covers the use case.

### Transitive dependencies

Transitive dependencies (installed by direct deps) are:
- Automatically inventoried in the SBOM
- Scanned by `npm audit` in CI
- Covered by the license deny check in dependency-review-action

Transitive dependency licenses that fall in the denylist **block the PR** even if the direct dep is approved. The PR author must resolve by finding an alternative direct dep or requesting a formal exception.

### Dev dependencies

Development-only dependencies (`devDependencies`) are not shipped in the production binary. They:
- Follow the same license allowlist (to avoid copyleft toolchain contamination)
- Are not included in the SBOM (build tool deps are excluded via `--production` flag in SBOM generation)
- Are still scanned for known vulnerabilities (`npm audit` checks all deps by default)

---

## Pinned Versions Policy

### npm packages

The project uses semver range pins (`^` for most, `~` for native modules). Renovate is configured to:
- Auto-merge patch updates for approved packages
- Open PRs for minor updates (maintainer reviews)
- Open PRs for major updates (maintainer reviews + PR must pass full CI)

Lockfiles (`package-lock.json`) are committed and updated by Renovate PRs. The lockfile is the canonical pin — the `package.json` range is the floor.

### GitHub Actions

All `uses:` references in `.github/workflows/` should be pinned to a commit SHA rather than a mutable tag (e.g., `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` instead of `actions/checkout@v4`).

**Current status:** workflows use `@v4` tags. This is a known gap flagged in the OpenSSF Scorecard (Pinned-Dependencies check). The migration to SHA pins is tracked as a P2 action.

**Tooling to automate:** `pinact` (GitHub) or `step-security/harden-runner` can pin all action versions in bulk.

### Docker base images (future)

If memoria-nox ships a Dockerfile, base images must be pinned by digest:

```dockerfile
# Do not use:
FROM node:22-alpine

# Use instead:
FROM node:22-alpine@sha256:<digest>
```

The SBOM generator will be extended to cover container images when applicable.

---

## Dependency Review CI Gate

All PRs are checked by `.github/dependency-review-config.yml` via `actions/dependency-review-action`. The check:

1. Diffs new dependencies introduced in the PR against the base branch
2. Fails the PR if any new dependency has a vulnerability with severity ≥ `high`
3. Fails the PR if any new dependency has a license on the deny list
4. Posts a summary comment to the PR with the dependency diff

To override a false positive (e.g., a CVE that does not apply to this use of the library):
1. Open an issue documenting why the CVE does not apply
2. Add the package to the `allow-licenses` override in the config with a comment referencing the issue

---

## Automated Updates (Renovate)

Renovate is configured via `.github/renovate.json`. It:
- Runs weekly on a Monday UTC schedule
- Proposes PRs for out-of-date deps
- Groups security updates into a single high-priority PR (`Security Updates` label)
- Does not auto-merge major bumps
- Respects the branch protection rules (CI must pass before merge)

Renovate PRs are reviewed like any other PR. The reviewer verifies:
1. CHANGELOG for the updated package (look for breaking changes)
2. CI passes
3. No new transitive deps introduced with blocked licenses

---

## Dependency Inventory

Key direct dependencies by sub-package:

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| `better-sqlite3` | ^9.x | MIT | SQLite binding |
| `typescript` | ^5.4 | Apache-2.0 | Compiler (devDep) |
| `@google/generative-ai` | ^0.x | Apache-2.0 | Gemini embeddings |
| `openai` | ^4.x | Apache-2.0 | OpenAI provider stub |
| `@anthropic-ai/sdk` | ^0.x | MIT | Anthropic provider stub |
| `@cyclonedx/cyclonedx-npm` | ^1.x | Apache-2.0 | SBOM generation (devDep) |

*Full inventory is in the SBOM files at `sbom/*.cdx.json`.*

---

## Questions and Exceptions

Open a GitHub Issue tagged `dependency-policy` for any questions about this policy. For license exceptions, use `license-exception-request`. For vulnerability disclosures, follow the process in [`SECURITY.md`](../../SECURITY.md).

---

*Policy version: 1.0.0 — effective 2026-05-18. Maintainer: lab@nuvini.com.br.*
