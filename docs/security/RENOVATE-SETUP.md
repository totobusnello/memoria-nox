# Renovate Setup Guide — memoria-nox

> Config file: `.github/renovate.json`  
> Policy rationale: `docs/security/DEPENDENCY-POLICY.md`  
> Status: Config committed — **app installation pending (user action)**

---

## Overview

Renovate is a dependency update bot that opens PRs automatically when new versions of your dependencies are published. It's similar to Dependabot but more configurable.

For memoria-nox, Renovate handles:
- npm/Node.js packages (`package.json` + `package-lock.json`)
- GitHub Actions versions (`.github/workflows/*.yml`)
- Vulnerability alerts (separate from schedule, highest priority)

The `.github/renovate.json` is already committed and valid. The only remaining step is installing the Renovate GitHub App on the repository.

OpenSSF Scorecard impact: +1 for the `Dependency-Update-Tool` check (activates as soon as the app is installed and detects the config).

---

## Step 1: Install the Renovate App

**This is a user action — cannot be automated.**

1. Go to: https://github.com/apps/renovate
2. Click **Install**
3. Select **Only select repositories**
4. Add `totobusnello/memoria-nox`
5. Click **Install**

The app needs read access to code and write access to pull requests and issues. This is the standard permission set the installer requests.

**Alternative via GitHub Marketplace:**

1. Go to: https://github.com/marketplace/renovate
2. Click **Set up a plan** (free tier is sufficient)
3. Follow the same repository selection flow

After installation, Renovate creates an onboarding PR titled "Configure Renovate" within a few minutes. Because `.github/renovate.json` already exists, Renovate will detect the config and skip the onboarding step — it will go directly to opening the first batch of update PRs.

---

## Step 2: Configure Org/Account Allowlist

If you are installing Renovate on a personal account (not an org), skip this step.

For organization accounts:
1. Go to: `https://github.com/organizations/<org-name>/settings/installations`
2. Find the Renovate app
3. Click **Configure**
4. Ensure `totobusnello/memoria-nox` is in the repository list

---

## Step 3: Verify Config Detection

After installation:

1. Go to the **Issues** tab of the repo
2. Look for an issue titled **"Dependency Dashboard — memoria-nox"** (created by Renovate)
3. The dashboard lists:
   - Pending updates waiting for schedule
   - Open PRs
   - Rate-limited PRs
   - Ignored/snoozed packages

If the dashboard does not appear within 10 minutes:
- Check `https://app.renovatebot.com/dashboard` (sign in with GitHub) — it shows a job queue and logs per repo
- Common causes: repo not in the app's repository list, config JSON syntax error, Renovate app backlog

To manually validate the config JSON locally:

```bash
# Install renovate CLI (one-time)
npm install -g renovate

# Validate config
renovate-config-validator .github/renovate.json
```

Expected output: `Configuration is valid.`

---

## Step 4: Review the First Batch of Update PRs

Renovate will open PRs in batches. The first run typically opens 3–10 PRs depending on how outdated dependencies are.

### Review checklist for each update PR

- [ ] CI passes (lint + typecheck + privacy filter + zero-vendor)
- [ ] For minor/patch updates: check the changelog for breaking changes
- [ ] For `better-sqlite3` updates: run `node -e "require('better-sqlite3')"` in the PR environment to verify the native binding compiles
- [ ] For Gemini/OpenAI/Anthropic SDK updates: verify the API shape hasn't changed (check `src/vectorize.ts` and `src/kg-extract.ts`)

### Auto-merge behavior

Per `.github/renovate.json`:

| Update type | Auto-merge | Notes |
|-------------|------------|-------|
| Security vulnerability | No | Always manual review |
| Patch (stable package) | Yes, if CI passes | Squash merge |
| Minor | No | Review changelog |
| Major | No | Individual PR, manual |
| `typescript` minor/major | No | Breaking types possible |
| `better-sqlite3` any | No | Native binding |
| Gemini/OpenAI/Anthropic SDKs | No | API surface |
| GitHub Actions | No | Review before updating |
| Dev dependency patch | Yes, if CI passes | Low risk |

---

## Configuration Reference

The full config is in `.github/renovate.json`. Key decisions explained:

### Schedule

```json
"schedule": ["before 6am on Monday"]
```

Updates are batched to Monday mornings (Sao Paulo time). This avoids update churn during the workweek and keeps the PR queue predictable. Security vulnerabilities bypass this schedule and open immediately (`"schedule": ["at any time"]`).

### Grouping

```json
"extends": ["group:allNonMajor"]
```

All non-major updates are grouped into a single PR per week. This reduces noise — instead of 20 individual patch PRs, you get one "Non-major updates" PR with all patches. Major updates always get individual PRs.

### Rate limiting

```json
"prConcurrentLimit": 5,
"prHourlyLimit": 2
```

At most 5 open Renovate PRs at any time and 2 new PRs per hour. This prevents Renovate from flooding the PR queue.

### Lock file maintenance

```json
"lockFileMaintenance": {
  "enabled": true,
  "schedule": ["before 6am on the first day of the month"]
}
```

On the first Monday of each month, Renovate opens a PR that refreshes `package-lock.json` to the latest resolutions within semver constraints. This catches transitive dependency security fixes that don't bump the direct dependency version.

### License policy

```json
"matchLicenses": ["GPL-2.0", "GPL-3.0", "AGPL-3.0", ...]
"enabled": false
```

Packages with copyleft licenses are blocked. This is kept in sync with `.github/dependency-review-config.yml`. If you want to add a GPL package, you must explicitly override this rule for that package.

---

## Configuration Tuning

### Snoozing noisy packages

If a package produces false-positive security alerts or updates too frequently, add a `packageRule`:

```json
{
  "description": "Snooze noisy-package until v2 is stable",
  "matchPackageNames": ["noisy-package"],
  "enabled": false
}
```

Add with a comment and a target date for re-evaluation.

### Adding a new package to the never-auto-merge list

For any new package that:
- Has native bindings (compiled)
- Is a provider SDK (external API)
- Has historically shipped breaking changes in minor versions

Add an explicit rule:

```json
{
  "description": "new-package — reason for manual review",
  "matchPackageNames": ["new-package"],
  "automerge": false,
  "labels": ["dependencies", "manual-review"]
}
```

### Increasing the batch size

If you want to process updates faster, increase `prConcurrentLimit` temporarily:

```json
"prConcurrentLimit": 10,
"prHourlyLimit": 5
```

Reset after the catch-up sprint.

---

## Maintenance Schedule

| Cadence | Task |
|---------|------|
| Weekly | Review and merge the Monday update PR if CI passes |
| Monthly | Review the lock file maintenance PR |
| Quarterly | Audit `renovate.json` — remove snoozed packages, review major-update PRs, check for new Renovate features |
| On demand | Security vulnerability PRs — review and merge ASAP |

---

## Troubleshooting

### Renovate dashboard doesn't appear

- Verify the app is installed on the repo: `https://github.com/settings/installations`
- Check the Renovate dashboard: `https://app.renovatebot.com/dashboard`
- Look at Renovate job logs for errors

### PR opened but CI fails

1. Check if the failure is in the test suite or a compilation error
2. For native modules (`better-sqlite3`): the new version may require a rebuild — check if there's a post-install script that ran correctly
3. For TypeScript updates: run `npx tsc --noEmit` locally with the new version to identify type errors

### Renovate opened too many PRs

Set `prConcurrentLimit` to a lower value (e.g., 3) and merge or close the excess PRs manually. The limit is enforced going forward.

### Auto-merge not working

Auto-merge requires:
1. The PR's CI checks to pass
2. `platformAutomerge: true` — GitHub's auto-merge feature must be enabled on the repo (Settings → General → Allow auto-merge)
3. Branch protection allowing auto-merge from bot accounts

If branch protection requires a human reviewer, auto-merge will not work for Renovate PRs unless you add a bypass for the Renovate app account.

---

*Maintained by lab@nuvini.com.br. Update this file when renovate.json changes significantly or app setup process changes.*
