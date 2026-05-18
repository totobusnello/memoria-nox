---
title: Dependency Policy
description: Rules for adding, updating, and auditing dependencies.
sidebar:
  order: 4
---

Full policy: [`docs/security/DEPENDENCY-POLICY.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/security/DEPENDENCY-POLICY.md)

## Adding dependencies

Before adding any new dependency:

1. Check the license — must be compatible with MIT (MIT, Apache 2.0, BSD, ISC are acceptable)
2. Check download count and maintenance status on npmjs.com
3. Check for known CVEs via `npm audit`
4. Pin to a specific version in `package.json`
5. Add to `docs/security/SBOM.md`

## Updating dependencies

- **Patch/minor updates:** Renovate raises PRs automatically. Merge after CI passes.
- **Major updates:** Manual review required. Test against the full eval harness before merging.
- **Security updates:** Priority merge, same-day if CVSS ≥ 7.0.

## Prohibited dependency patterns

- Dependencies with GPL/LGPL/AGPL licenses (incompatible with MIT distribution)
- Dependencies that phone home by default (telemetry must be opt-in)
- Dependencies that require cloud API keys to function (must be optional/swappable)

## Audit commands

```bash
npm audit               # check for known CVEs
npm audit --fix         # auto-fix where safe
npm outdated            # check for stale deps
```

## Renovate configuration

Renovate is configured at `docs/security/RENOVATE-SETUP.md`. It raises PRs for:
- Patch updates: auto-merge if CI passes
- Minor updates: requires one approval
- Major updates: requires manual review + eval harness run
