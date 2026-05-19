# Security policy

> Pain-weighted hybrid memory with shadow discipline — yours by design.
> Security is a first-class concern. See also: `docs/security/THREAT-MODEL.md`.

## Supported versions

| Version | Supported |
|---------|-----------|
| main | ✅ active development |
| Wave E / D / C / B | ✅ shipped |
| Pre-Wave B | ❌ unsupported |

## Reporting a vulnerability

**DO NOT open public issues for security vulnerabilities.**

Instead:

1. **Email:** `lab@nuvini.com.br` — subject line `[SECURITY] memoria-nox — <brief description>`
2. **Preferred:** [GitHub Private vulnerability reporting](https://github.com/totobusnello/memoria-nox/security/advisories) — opens a confidential advisory draft visible only to maintainer
3. **PGP:** `<to be filled by maintainer — public key link>`

We aim to:
- Acknowledge receipt within **48 hours**
- Triage and assign severity within **1 week**
- Patch high-severity (Critical / High) within **30 days**
- Coordinate public disclosure with the reporter

## Vulnerability scope

### In scope

- Code in `main` and merged PRs
- Authentication / authorization bypass
- Data exfiltration paths (memory store, export archives, SSE stream)
- Cryptographic weaknesses (AES-256-GCM at rest, scrypt key derivation, AAD verification)
- Injection: SQL injection, command injection (`execSync` patterns), prompt injection (when privacy-relevant)
- Information disclosure: stack traces in HTTP responses, env vars / API keys in logs, PII escaping redaction
- Privacy bypass: PII filter (A1) circumvention, viewer opt-in controls (`NOX_VIEWER_SHOW_QUERY`)
- Append-only audit log bypass (ops_audit, conflict_audit)
- Path traversal in export/import archive unpacking (A2)

### Out of scope

- Vulnerabilities in dependencies — report to the upstream project
- Theoretical issues without a working proof-of-concept
- Issues requiring physical access to the machine
- Social engineering attacks
- Denial-of-service requiring authenticated / privileged access
- Issues in third-party embedding providers (Gemini, OpenAI) — report to them directly

## Known threats and controls

Full STRIDE analysis is in [`docs/security/THREAT-MODEL.md`](docs/security/THREAT-MODEL.md).

Summary of controls shipped:

| Area | Control | Source |
|------|---------|--------|
| Data at rest | AES-256-GCM encryption on export archives | A2 |
| PII redaction | 13 regex patterns at write time (CPF, CNPJ, credit cards, phones, emails, …) | A1 / A1.1 |
| Audit integrity | Append-only `ops_audit` — DELETE + UPDATE on terminal rows blocked via DB triggers | W2-1 |
| Provider lock-in | Provider abstraction layer — no vendor hard-coding | A3 |
| Secret handling | API keys only in `.env` (0600) — gitleaks pre-commit enforced | CLAUDE.md |
| Viewer privacy | SSE query text opt-in (`NOX_VIEWER_SHOW_QUERY=1` required) | P5 |
| Export path safety | `realpathSync` allowlist + symlink-aware validation | A2 |
| CLI injection | `execFileSync(cmd, [args])` array form — no shell interpolation | A5 |

## Hall of fame

Researchers who responsibly disclosed vulnerabilities to this project:

- *(none yet — be the first!)*

## Coordinated disclosure policy

Default: **90-day coordinated disclosure.** The reporter may publish their findings after the fix is shipped or after 90 days have elapsed from initial report, whichever comes first. Extensions granted on request for complex issues.

We credit reporters in release notes and this section unless they prefer anonymity.
