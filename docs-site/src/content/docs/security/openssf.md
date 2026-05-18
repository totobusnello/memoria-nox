---
title: OpenSSF Path
description: Progress toward OpenSSF Best Practices badge and supply chain security.
sidebar:
  order: 2
---

Full source: [`docs/security/PATH-TO-OPENSSF.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/security/PATH-TO-OPENSSF.md)

## OpenSSF Best Practices Badge

Target: **Passing** badge before GTM Phase 2 activation.

### Completed controls

| Control | Evidence |
|---|---|
| HTTPS for all external calls | All Gemini/OpenAI calls use TLS |
| No hardcoded credentials | `execFileSync` + env var injection |
| Dependency pinning | `package-lock.json` committed |
| Signed commits encouraged | Repository policy |
| Vulnerability reporting policy | `SECURITY.md` |
| Code of conduct | `CODE_OF_CONDUCT.md` |
| SBOM | `docs/security/SBOM.md` |

### In progress

| Control | Status |
|---|---|
| Automated dependency updates | Renovate config (`docs/security/RENOVATE-SETUP.md`) |
| CodeQL static analysis | Config at `docs/security/CODEQL.md` |
| Branch protection rules | `docs/security/BRANCH-PROTECTION.md` |
| Signed releases | Planned pre-v1.0 |

## SBOM

Software Bill of Materials at [`docs/security/SBOM.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/security/SBOM.md).

Key runtime dependencies:
- `better-sqlite3` — SQLite bindings (MIT)
- `sqlite-vec` — vector extension (Apache 2.0)
- `@google/generative-ai` — Gemini SDK (Apache 2.0)
- `fastify` — HTTP server (MIT)

## Dependency policy

Full policy: [`docs/security/DEPENDENCY-POLICY.md`](https://github.com/totobusnello/memoria-nox/blob/main/docs/security/DEPENDENCY-POLICY.md)

- Dependencies are reviewed before addition
- Major version updates gated by CI passing
- Renovate raises PRs automatically for patch/minor updates
- No dependencies with licenses incompatible with MIT
