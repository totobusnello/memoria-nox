# Branch Protection — memoria-nox

> Applies to: `main` branch  
> Configured via: GitHub Settings → Branches → Branch protection rules  
> Status: **Not yet configured — pending user action**  
> OpenSSF Scorecard impact: +1 (Branch-Protection) + +1 (Code-Review)

---

## Why Branch Protection Matters

Without branch protection:
- Anyone with write access can push directly to `main`, bypassing CI
- Force pushes can rewrite history and destroy evidence
- PRs can be merged without passing tests or security scans
- The OpenSSF Scorecard `Branch-Protection` check gives 0 points

With branch protection on `main`, the OpenSSF Scorecard estimates a jump of **+2 points** (Branch-Protection + Code-Review checks together). Combined with CodeQL (+1) and Renovate (+1), this takes the estimated score from ~4–5 to **~7–8 / 10**.

---

## How to Configure (User Action Required)

1. Go to: `https://github.com/totobusnello/memoria-nox/settings/branches`
2. Under **Branch protection rules**, click **Add rule**
3. In **Branch name pattern**, type: `main`
4. Apply the settings below
5. Click **Create** (or **Save changes** if editing an existing rule)

---

## Recommended Settings

### Pull Request Requirements

**✅ Require a pull request before merging**

This is the most important setting. It prevents direct pushes to `main` and requires all changes to go through a PR where CI can run.

> Sub-settings:

**✅ Require approvals — set to: 1**

Minimum 1 approval before merging. For a single-maintainer project, this means self-approval is not possible — you need at least one review. This adds friction intentionally: it forces a second look before merging.

*For a solo project, this can be set to 0 if the friction is too high. However, OpenSSF Code-Review check requires at least 1 approval to give full credit. Recommended: start at 1.*

**✅ Dismiss stale pull request approvals when new commits are pushed**

When you push a new commit to an already-approved PR, the approval is dismissed and a new review is required. This prevents the pattern of approving a safe version and then pushing a malicious/broken commit.

**✅ Require review from Code Owners**

Since `.github/CODEOWNERS` is committed, GitHub will automatically request a review from `@totobusnello` for every PR. This ensures the owner always sees and approves every change. Effective as long as you are the Code Owner.

---

### Status Check Requirements

**✅ Require status checks to pass before merging**

No PR can merge unless all required CI checks pass.

**✅ Require branches to be up to date before merging**

The PR branch must be up to date with `main` before merging. This prevents the "merging stale" pattern where a PR passes CI against an old version of main but would fail against the current version.

#### Required status check names

These must match the job names **exactly** as they appear in GitHub Actions:

| Status check name | Workflow file | What it validates |
|-------------------|--------------|-------------------|
| `Lint + Typecheck` | `lint-and-typecheck.yml` | TypeScript compilation + ESLint |
| `A1 Privacy Filter Tests` | `privacy-filter.yml` | PII detection regression suite |
| `A4 Zero-Vendor — all 8 checks` | `zero-vendor.yml` | Zero-vendor-lock invariants |
| `CodeQL Analyze (javascript-typescript)` | `codeql.yml` | Static security analysis |
| `Eval Harnesses (Dry-Run)` | `eval-harnesses.yml` | Retrieval quality regression |

**How to add these checks:**

1. In the branch protection rule, under "Status checks that are required", click the search box
2. Type each check name from the table above
3. GitHub will show the check once it has run at least once — if a check hasn't run yet, type the full name manually
4. Click "Add" for each

**Note:** `CodeQL Analyze (javascript-typescript)` will not appear in the search until the first CodeQL run completes. After the `codeql.yml` workflow runs for the first time on `main`, it will be available.

---

### Conversation and History

**✅ Require conversation resolution before merging**

All review comments and inline comments must be resolved before the PR can be merged. This prevents "resolve all" spam — reviewers must actually address each comment.

---

### Commit Integrity

**✅ Require signed commits** *(Recommended for OpenSSF Silver)*

All commits to `main` must be GPG-signed or signed via GitHub's commit signing. This provides cryptographic proof that commits came from the claimed author.

Setup guide for GPG signing:
```bash
# Generate a key (if you don't have one)
gpg --gen-key

# Get the key ID
gpg --list-secret-keys --keyid-format=long

# Configure git to use it
git config --global user.signingkey <KEY-ID>
git config --global commit.gpgsign true

# Add the public key to GitHub
# Settings → SSH and GPG keys → New GPG key
gpg --armor --export <KEY-ID>
```

*Note: Signed commits is a Silver tier requirement, not Passing. You can defer this until pursuing Silver badge.*

**✅ Require linear history** *(no merge commits)*

Only squash merges and rebase merges are allowed. No merge commits. This keeps the `main` history clean and readable:

- Every commit on `main` represents a single logical change
- `git log --oneline` shows a clear story of what changed and why
- Bisection (`git bisect`) works cleanly

To enforce this on GitHub, also go to:
- Settings → General → Pull Requests
- Uncheck "Allow merge commits"
- Keep "Allow squash merging" checked
- Keep "Allow rebase merging" checked (optional — squash-only is cleaner)

---

### Push Controls

**❌ Disable force pushes**

Force pushes to `main` are disabled by default when branch protection is enabled. Keep this as-is. Force pushing to `main` can destroy history and invalidate signed commits.

*Exception: if you ever need to remove a secret accidentally committed, use `git filter-repo` + force push. In that case, temporarily disable branch protection, do the surgery, re-enable. Document the incident in `docs/INCIDENTS.md`.*

**❌ Disable deletions**

`main` cannot be deleted. Keep this as-is.

---

### Restriction on Who Can Push

**✅ Restrict who can push to matching branches**

Set this to: **only admins and repository administrators**.

This ensures that even collaborators with write access cannot bypass the PR requirement by pushing directly. Only the repository owner can push directly (useful for emergency hotfixes).

*For a solo project with no collaborators, this setting has no practical effect today but is good hygiene for when contributors are added.*

---

## Settings Summary Table

| Setting | Value | Reason |
|---------|-------|--------|
| Require PR before merging | ✅ Enabled | Core protection |
| Required approvals | 1 | OpenSSF Code-Review credit |
| Dismiss stale approvals | ✅ Enabled | Prevent post-approval commits |
| Require Code Owner review | ✅ Enabled | CODEOWNERS file present |
| Require status checks | ✅ Enabled | CI must pass |
| Required checks | See table above | 5 workflows |
| Require branch up-to-date | ✅ Enabled | No stale merges |
| Require conversation resolution | ✅ Enabled | Review hygiene |
| Require signed commits | ✅ Recommended | OpenSSF Silver requirement |
| Require linear history | ✅ Enabled | Clean history |
| Allow force pushes | ❌ Disabled | Immutable history |
| Allow deletions | ❌ Disabled | Branch permanence |
| Restrict push access | ✅ Admins only | Defense in depth |

---

## Impact on Workflow

After enabling branch protection, the day-to-day workflow changes as follows:

### Before (no protection)
```
git push origin main   ← always allowed, bypasses CI
```

### After (with protection)
```
git checkout -b my-feature
# make changes
git push origin my-feature
# open PR on GitHub
# wait for CI (5–15 min)
# get approval (self-review if solo)
# merge via GitHub UI
```

### For emergency hotfixes

If you need to push directly to fix a production incident:
1. Go to Settings → Branches → Edit the rule
2. Check "Allow specified actors to bypass required pull requests" → add yourself
3. Make the fix
4. Re-disable the bypass immediately after
5. Document in `docs/INCIDENTS.md`

Alternatively: make the fix in a branch, open a PR, approve it yourself, merge. For true emergencies this is fast enough.

---

## Renovate + Branch Protection

Renovate PRs need to pass CI to auto-merge. With branch protection enabled:

1. Renovate opens a PR
2. CI runs automatically
3. If all required checks pass AND auto-merge is enabled for that package type, GitHub merges it automatically
4. If auto-merge is not enabled (or the package is in the manual-review list), the PR waits for a human review

For auto-merge to work with branch protection, you may need to:
- Enable "Allow auto-merge" in Settings → General → Pull Requests
- Add a bypass rule for the Renovate app account OR reduce required approvals to 0 for automated PRs

Simpler approach: keep required approvals at 1, review Renovate's weekly digest PR manually (takes 2–3 minutes), approve, and let it merge.

---

## CODEOWNERS Integration

The `.github/CODEOWNERS` file already committed (this PR) will be active once branch protection is enabled with "Require review from Code Owners" turned on.

Current CODEOWNERS rules:
- `*` → `@totobusnello` (every file)
- `/docs/security/` → `@totobusnello` (explicit for security-sensitive docs)
- `/staged-A1.1/`, `/staged-A2/`, `/staged-A3/` → `@totobusnello` (privacy + encryption + providers)

When additional contributors are added in the future, CODEOWNERS can be updated to route specific directories to the relevant people.

---

## OpenSSF Score Impact

After enabling branch protection with these settings:

| OpenSSF Scorecard check | Before | After |
|------------------------|--------|-------|
| Branch-Protection | ❌ 0 | ✅ +1 |
| Code-Review | ❌ 0 | ✅ +1 |
| SAST (CodeQL) | ❌ 0 | ✅ +1 (from codeql.yml) |
| Dependency-Update-Tool | ❌ 0 | ✅ +1 (after Renovate app install) |
| **Estimated total** | **~4–5** | **~7–8 / 10** |

The remaining gap to 10/10 requires:
- Pinned action SHAs (replace `@v4` with full commit SHA)
- Signed releases
- Multiple contributors (structural limitation for single-maintainer projects)

---

*Maintained by lab@nuvini.com.br. Update when branch protection settings change or new required checks are added.*
