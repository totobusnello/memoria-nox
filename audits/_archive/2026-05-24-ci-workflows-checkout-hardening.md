# CI Workflows Checkout Hardening — 2026-05-24

**PR:** fix/ci-workflows-persist-credentials-false  
**Trigger:** 35 transient `401 Bad credentials` email notifications (Sat 2026-05-24) caused by `actions/checkout@v4` persisting GITHUB_TOKEN as a git extraheader on a public repo.  
**Root cause:** `persist-credentials: true` (default) sets `Authorization: basic ***` extraheader via GITHUB_TOKEN. On public repos, anonymous clone works fine. When GitHub's API returns a transient 401, git prompts interactively → CI fail → notification email.

---

## Decision matrix

| Workflow | Checkouts | Action |
|---|---|---|
| `codeql.yml` | 1 (no with:) | Set `persist-credentials: false` |
| `deploy-validator.yml` | 1 (no with:) | Set `persist-credentials: false` |
| `docker-build.yml` | 2 (fetch-depth: 1) | Set `persist-credentials: false` |
| `eval-harnesses.yml` | 3 (fetch-depth: 1) | Set `persist-credentials: false` |
| `eval-smoke.yml` | 1 (no with:) | Set `persist-credentials: false` |
| `lint-and-typecheck.yml` | 1 (fetch-depth: 1) | Set `persist-credentials: false` |
| `lint-docs.yml` | 2 (no with:) | Set `persist-credentials: false` |
| `perf-regression.yml` | 2 (fetch-depth: 1) | Set `persist-credentials: false` |
| `privacy-filter.yml` | 1 (fetch-depth: 1) | Set `persist-credentials: false` |
| `release.yml` | 3 (no with:) | Set `persist-credentials: false` — release creation uses `softprops/action-gh-release` with explicit `GITHUB_TOKEN` env, not checkout credentials |
| `sbom.yml` | 1 (fetch-depth: 1) | Set `persist-credentials: false` — `gh release upload` uses explicit `GH_TOKEN` env |
| `sdk-dotnet.yml` | 1 (no with:) | Set `persist-credentials: false` |
| `sdk-go.yml` | 1 (no with:) | Set `persist-credentials: false` |
| `sdk-java.yml` | 1 (no with:) | Set `persist-credentials: false` |
| `sdk-publish.yml` | 3 (no with:) | Set `persist-credentials: false` — npm publish uses `NODE_AUTH_TOKEN`, PyPI uses `TWINE_PASSWORD`, not checkout credentials |
| `sdk-rust.yml` | 2 (no with:) | Set `persist-credentials: false` — cargo publish uses `CRATES_IO_TOKEN` secret |
| `security.yml` | 3 (1×fetch-depth:0 + 2 bare) | Set `persist-credentials: false` on all 3 |
| `validate-syntax.yml` | 4 (no with:) | Set `persist-credentials: false` |
| `visual-regression.yml` | 1 (fetch-depth: 0) | Set `persist-credentials: false` |
| `zero-vendor.yml` | 1 (fetch-depth: 1) | Set `persist-credentials: false` |

---

## Exception — NOT modified

| Workflow | Reason |
|---|---|
| `perf-nightly.yml` | **KEEP `persist-credentials: true` (implicit default)** — this workflow does `git config user.name`, `git checkout -B benchmark-history`, `git commit`, `git push origin benchmark-history`. It has `permissions: contents: write` and relies on the GITHUB_TOKEN credentials baked in by checkout to authenticate the push. Setting `false` would break the push step. |

---

## Stats

- **Total workflows with `actions/checkout@v4`:** 21
- **Modified:** 20 workflows, 35 checkout occurrences patched
- **Exceptions:** 1 (`perf-nightly.yml` — writes back to repo)
- **YAML lint:** clean (warnings are pre-existing line-length issues, unrelated to this change)

---

## Expected outcome

Transient 401 from GitHub API no longer causes CI failure cascade. Public repo clone proceeds anonymous. Steps that genuinely need auth (release, sbom attach, sdk publish, cargo publish) use explicit `token:` / env secrets — unaffected.
