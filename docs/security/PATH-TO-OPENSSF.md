# Path to OpenSSF Badges — memoria-nox

> Practical roadmap from current state to OpenSSF Passing → Silver → Gold + Scorecard badge.  
> Status as of: 2026-05-18  
> Author: Wave I audit

---

## Overview

OpenSSF (Open Source Security Foundation) provides two complementary signals for open source projects:

| Signal | What it measures | How earned |
|--------|-----------------|------------|
| **Best Practices Badge** | Process maturity (docs, tests, vuln response, security design) | Self-assessment at bestpractices.dev |
| **Scorecard** | Supply chain security (CI hygiene, dep pinning, code review, etc.) | Automated GitHub analysis |

Both are free for public repos. Both appear as README badges and signal to potential users and contributors that the project takes security seriously.

---

## Step 1: Self-Assessment (Passing Tier)

**Target: OpenSSF Best Practices Passing badge**

**Estimated time to complete: 2–3 hours (assessment) + ~1 day (gap fixes)**

### What to do

1. Go to https://www.bestpractices.dev/projects/new
2. Sign in with GitHub
3. Enter the repo URL: `https://github.com/totobusnello/memoria-nox`
4. Work through the 66 criteria using `docs/security/OPENSSF-AUDIT.md` as a guide
5. For each "Met" criterion, paste the evidence URL (file + line)
6. Save progress — the form is persistent

### Current assessment from audit (2026-05-18)

| Category | Met | Partial | Not Met | N/A |
|----------|-----|---------|---------|-----|
| Basics | 5 | 1 | 0 | 0 |
| Change Control | 2 | 2 | 0 | 0 |
| Reporting | 4 | 1 | 0 | 0 |
| Quality | 8 | 4 | 0 | 1 |
| Security | 9 | 4 | 1 | 3 |
| Analysis | 0 | 3 | 1 | 0 |

The 2 criteria marked "Not Met" are labeled SUGGESTED in the OpenSSF criteria — they do not block Passing tier. All MUST criteria are met or partially met with clear fixes.

### Fixes needed before self-assessment (estimated ~1 day)

| Fix | Effort | Criterion |
|-----|--------|-----------|
| Add semver git tag convention to CONTRIBUTING.md | 15 min | 1.5, 2.3 |
| Create `v0.1.0-wave-b` or `v1.0.0-beta` git tag | 5 min | 1.5, 2.3 |
| Add "We aim to acknowledge bug reports within 7 days" to CONTRIBUTING.md | 5 min | 3.2 |
| Enable GitHub branch protection on `main` (Settings → Branches) | 15 min | 4.7 |
| Merge this PR (SBOM + dependency review + Renovate) | — | 5.5 |

After those fixes: submit self-assessment. Badge appears automatically when criteria score meets the passing threshold.

### Badge URL (add to README after badge is issued)

```markdown
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/<ID>/badge)](https://www.bestpractices.dev/projects/<ID>)
```

Replace `<ID>` with the project ID assigned after submission.

---

## Step 2: Scorecard Badge (Automated)

**Target: OpenSSF Scorecard badge (auto-computed on every push)**

**Estimated time: 2–4 hours**

Scorecard analyzes the repo automatically via a GitHub Actions workflow and produces a score (0–10). Current estimated score without any Scorecard-specific fixes: **~4–5 / 10** (based on audit findings).

### What Scorecard checks (and current status)

| Check | Weight | Current status |
|-------|--------|---------------|
| Code-Review | High | ⚠️ No enforced PR review |
| Branch-Protection | High | ❌ Not configured |
| Dangerous-Workflow | Critical | ✅ No `pull_request_target` with write |
| Dependency-Update-Tool | Medium | ❌ No Renovate/Dependabot yet (this PR adds it) |
| Maintained | Medium | ✅ Active commits |
| Packaging | Medium | ⚠️ No npm publish yet |
| Pinned-Dependencies | High | ⚠️ Actions use `@v4` tags, not SHA |
| SAST | High | ❌ No CodeQL |
| Security-Policy | Medium | ✅ SECURITY.md present |
| Signed-Releases | High | ❌ No signed tags |
| Token-Permissions | High | ⚠️ Some workflows use broad permissions |
| Vulnerabilities | High | ✅ (no known unpatched) |
| Contributors | Low | ⚠️ Single maintainer |
| License | Low | ✅ MIT |

### How to add the Scorecard workflow

Create `.github/workflows/scorecard.yml`:

```yaml
name: OpenSSF Scorecard

on:
  branch_protection_rule: {}
  schedule:
    - cron: '30 1 * * 6'  # Weekly — Saturday 01:30 UTC
  push:
    branches: [main]

permissions: read-all

jobs:
  analysis:
    name: Scorecard analysis
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      id-token: write
      contents: read
      actions: read

    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
        with:
          persist-credentials: false

      - uses: ossf/scorecard-action@62b2cac7ed8198b15735ed49ab1e5cf35480ba46  # v2.4.0
        with:
          results_file: results.sarif
          results_format: sarif
          publish_results: true

      - uses: actions/upload-artifact@65462800fd760344b1a7b4382951275a0abb4808  # v4.3.3
        with:
          name: SARIF file
          path: results.sarif
          retention-days: 5

      - uses: github/codeql-action/upload-sarif@1b549b9259bda1cb5ddde3b41741a82a2d15a841  # v3.24.5
        with:
          sarif_file: results.sarif
```

### Scorecard badge URL

```markdown
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/totobusnello/memoria-nox/badge)](https://securityscorecards.dev/viewer/?uri=github.com/totobusnello/memoria-nox)
```

### To improve the Scorecard score from ~4 to ~7+

In priority order:

1. **Enable branch protection** (adds +1 for Branch-Protection, +1 for Code-Review)
2. **Add Renovate** (this PR — +1 for Dependency-Update-Tool)
3. **Pin action SHAs** (+1.5 for Pinned-Dependencies)
4. **Add CodeQL** (+1 for SAST)
5. **Minimal token permissions** (audit each workflow for `permissions: read-all` default + specific grants)

Reaching 7/10 is achievable within 1 week of this PR merging.

---

## Step 3: Passing Tier — Active Badge

After self-assessment submission and all MUST criteria are confirmed:

1. Badge status transitions from "submitted" to "passing"
2. Add badge to `README.md` top badge row (do not add until the badge is actually issued)
3. Reference the badge in `SECURITY.md`

Estimated time from self-assessment submission to badge issuance: **same day** for passing tier (automated scoring).

---

## Step 4: Silver Tier

Silver tier requires passing all of the following additional criteria (above Passing):

| Silver requirement | Current status | Estimated effort |
|-------------------|---------------|------------------|
| Signed commits (DCO or GPG) | ❌ Not enforced | 2h — add DCO action or GPG key docs |
| CodeQL or equivalent SAST | ❌ Missing | 1h — add workflow |
| Automated test coverage reporting | ⚠️ No c8 | 2h |
| Branch protection enforced | ❌ | 15 min |
| Pinned dependency versions (lockfile) | ✅ (lockfile committed) | — |
| Two-factor auth on maintainer account | Unverified | 5 min to verify |
| Documented secure design review | ✅ THREAT-MODEL.md | — |
| Independent security assessment | ❌ Community audit not done | 40h+ (external) |

**Estimated time to Silver: 2–4 weeks** (most of the work is the independent security assessment, which requires finding a willing reviewer from the open source security community).

Practical path to Silver:
1. Merge this PR (SBOM + Renovate + dep-review)
2. Add CodeQL workflow
3. Add c8 coverage reporting
4. Enable branch protection + DCO requirement
5. Request a community security audit on forums (OpenSSF Slack, security.txt outreach, etc.)
6. Publish the audit result in `docs/security/`

---

## Step 5: Gold Tier

Gold requires everything in Silver plus:

- **Independent security review** by a third party (not a community volunteer — an organization or security researcher with a track record)
- The review must be public and linked from the Best Practices badge page
- Re-review required if substantial changes are made

**Estimated time to Gold: 6–18 months** — depends on finding a suitable reviewer and the scope of the review. Not a near-term goal.

---

## Badge Placement (README.md)

When badges are earned, add them to the top badge row in `README.md`, between the current CI badge and the paper badge:

```markdown
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/<ID>/badge)](https://www.bestpractices.dev/projects/<ID>)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/totobusnello/memoria-nox/badge)](https://securityscorecards.dev/viewer/?uri=github.com/totobusnello/memoria-nox)
```

**Important:** Do not add badges speculatively. Add only after the badge is confirmed issued by the respective system. The OpenSSF Passing badge page and the Scorecard API both verify project status in real time.

---

## Other Relevant Badges (available today)

These do not require any action — they can be added to README now:

```markdown
[![License: MIT](https://img.shields.io/github/license/totobusnello/memoria-nox?style=for-the-badge&color=00C896)](LICENSE)
```
*Already present in README.*

```markdown
[![CI](https://img.shields.io/github/actions/workflow/status/totobusnello/memoria-nox/lint-and-typecheck.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/totobusnello/memoria-nox/actions/workflows/lint-and-typecheck.yml)
```
*Already present (generic CI badge). Consider pointing to a specific workflow.*

---

## Summary Timeline

| Milestone | Target | Effort |
|-----------|--------|--------|
| Wave I PR merged (SBOM + Renovate + dep-review) | This sprint | 1 day |
| Self-assessment submitted (Passing tier) | Within 1 week | 3–4 hours |
| Passing badge issued | Within 1 week | Automatic |
| Scorecard workflow added | Within 1 week | 1 hour |
| Scorecard score ≥ 7 | Within 2 weeks | 1 day |
| Silver tier achieved | Within 1 month | 2–4 weeks |
| Gold tier | 6–18 months | External audit |

---

*Maintained by lab@nuvini.com.br. Update this file when badge status changes.*
