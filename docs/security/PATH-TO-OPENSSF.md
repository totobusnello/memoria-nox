# Path to OpenSSF Badges — memoria-nox

> Practical roadmap from current state to OpenSSF Passing → Silver → Gold + Scorecard badge.  
> Status as of: 2026-05-18  
> Author: Wave I audit + Wave J gap closure

---

## Wave J Gap Closure Status (2026-05-18)

| Action | Status | Notes |
|--------|--------|-------|
| CodeQL workflow added | ✅ Done (this PR) | `.github/workflows/codeql.yml` |
| Renovate config in repo | ✅ Done (this PR) | `.github/renovate.json` |
| CodeQL documentation | ✅ Done (this PR) | `docs/security/CODEQL.md` |
| Renovate setup guide | ✅ Done (this PR) | `docs/security/RENOVATE-SETUP.md` |
| Branch protection guide | ✅ Done (this PR) | `docs/security/BRANCH-PROTECTION.md` |
| CODEOWNERS file | ✅ Done (this PR) | `.github/CODEOWNERS` |
| Renovate app installation | 🟡 Pending Toto action | See `RENOVATE-SETUP.md` Step 1 |
| Branch protection settings | 🟡 Pending Toto action | See `BRANCH-PROTECTION.md` |

**Estimated Scorecard score after Toto completes the two pending actions: ~7–8 / 10**

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

| Fix | Effort | Criterion | Status |
|-----|--------|-----------|--------|
| Add semver git tag convention to CONTRIBUTING.md | 15 min | 1.5, 2.3 | 🟡 Pending |
| Create `v0.1.0-wave-b` or `v1.0.0-beta` git tag | 5 min | 1.5, 2.3 | 🟡 Pending |
| Add "We aim to acknowledge bug reports within 7 days" to CONTRIBUTING.md | 5 min | 3.2 | 🟡 Pending |
| Enable GitHub branch protection on `main` (Settings → Branches) | 15 min | 4.7 | 🟡 Pending — guide in `BRANCH-PROTECTION.md` |
| Merge Wave I PR (SBOM + dependency review + Renovate) | — | 5.5 | 🟡 Pending PR merge |
| Merge Wave J PR (CodeQL + Renovate guide + branch protection docs) | — | Analysis | 🟡 This PR |

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

| Check | Weight | Current status | After Wave J + user actions |
|-------|--------|----------------|---------------------------|
| Code-Review | High | ⚠️ No enforced PR review | ✅ After branch protection |
| Branch-Protection | High | ❌ Not configured | ✅ After branch protection |
| Dangerous-Workflow | Critical | ✅ No `pull_request_target` with write | ✅ Unchanged |
| Dependency-Update-Tool | Medium | ❌ No Renovate/Dependabot | ✅ After Renovate app install |
| Maintained | Medium | ✅ Active commits | ✅ Unchanged |
| Packaging | Medium | ⚠️ No npm publish yet | ⚠️ Unchanged |
| Pinned-Dependencies | High | ⚠️ Actions use `@v4` tags, not SHA | ⚠️ Future work |
| SAST | High | ❌ No CodeQL | ✅ Wave J adds `codeql.yml` |
| Security-Policy | Medium | ✅ SECURITY.md present | ✅ Unchanged |
| Signed-Releases | High | ❌ No signed tags | ❌ Future work |
| Token-Permissions | High | ⚠️ Some workflows use broad permissions | ⚠️ Future work |
| Vulnerabilities | High | ✅ (no known unpatched) | ✅ Unchanged |
| Contributors | Low | ⚠️ Single maintainer | ⚠️ Structural |
| License | Low | ✅ MIT | ✅ Unchanged |

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

*Note: SHA-pinned actions are used here intentionally — the Scorecard workflow itself is a Scorecard check target, so it must lead by example.*

### Scorecard badge URL

```markdown
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/totobusnello/memoria-nox/badge)](https://securityscorecards.dev/viewer/?uri=github.com/totobusnello/memoria-nox)
```

### To improve the Scorecard score from ~4 to ~7+

In priority order:

1. **Enable branch protection** (adds +1 for Branch-Protection, +1 for Code-Review) — 🟡 Pending user action
2. **Install Renovate app** (this PR adds config — +1 for Dependency-Update-Tool) — 🟡 Pending user action
3. **CodeQL added** (this PR — +1 for SAST) — ✅ Done
4. **Pin action SHAs** (+1.5 for Pinned-Dependencies) — Future work
5. **Minimal token permissions** (audit each workflow for `permissions: read-all` default + specific grants) — Future work

Reaching 7/10 is achievable within 1 week of this PR merging + completing the 2 pending user actions.

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
| CodeQL or equivalent SAST | ✅ Wave J adds workflow | — Done |
| Automated test coverage reporting | ⚠️ No c8 | 2h |
| Branch protection enforced | ❌ | 15 min — guide in `BRANCH-PROTECTION.md` |
| Pinned dependency versions (lockfile) | ✅ (lockfile committed) | — |
| Two-factor auth on maintainer account | Unverified | 5 min to verify |
| Documented secure design review | ✅ THREAT-MODEL.md | — |
| Independent security assessment | ❌ Community audit not done | 40h+ (external) |

**Estimated time to Silver: 2–4 weeks** (most of the work is the independent security assessment, which requires finding a willing reviewer from the open source security community).

Practical path to Silver:
1. Merge Wave I PR (SBOM + Renovate + dep-review)
2. Merge Wave J PR (CodeQL + guides — this PR)
3. Install Renovate app + enable branch protection (user actions)
4. Add c8 coverage reporting
5. Enable branch protection + DCO requirement
6. Request a community security audit on forums (OpenSSF Slack, security.txt outreach, etc.)
7. Publish the audit result in `docs/security/`

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

| Milestone | Target | Effort | Status |
|-----------|--------|--------|--------|
| Wave I PR merged (SBOM + Renovate + dep-review) | This sprint | 1 day | 🟡 Pending merge |
| Wave J PR merged (CodeQL + guides) | This sprint | Done | 🟡 This PR |
| Install Renovate app | After PR merge | 5 min | 🟡 Pending user |
| Enable branch protection | After PR merge | 15 min | 🟡 Pending user |
| Self-assessment submitted (Passing tier) | Within 1 week | 3–4 hours | 🟡 Pending |
| Passing badge issued | Within 1 week | Automatic | 🟡 Pending |
| Scorecard workflow added | Within 1 week | 1 hour | 🟡 Pending |
| Scorecard score ≥ 7 | Within 2 weeks | 1 day | 🟡 Pending |
| Silver tier achieved | Within 1 month | 2–4 weeks | 🟡 Pending |
| Gold tier | 6–18 months | External audit | 🟡 Not started |

---

*Maintained by lab@nuvini.com.br. Update this file when badge status changes.*
