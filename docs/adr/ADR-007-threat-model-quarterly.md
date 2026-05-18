# ADR-007: Threat-model recursive iteration (quarterly security audit cadence)

Date: 2026-05-18

## Status

Accepted

## Context

nox-mem handles sensitive personal and organizational data: agent conversations, financial documents (NUVIVI, PPR, CONTRATOS), personal files, and system credentials referenced in memory chunks. The corpus grew from 20K to 62K+ chunks in a single day (2026-04-27), materially expanding the attack surface without a commensurate security review.

Several critical security findings have emerged from ad-hoc audits:

- **2026-04-21**: Hardcoded API keys in 7 JSON files + ingested chunks + backups; Gemini and Perplexity keys were exposed and revoked. Root cause: no pre-commit secret scanning.
- **2026-04-26 audit**: Snapshot directory 0755 + DB 0644 world-readable (SEC HIGH #1). Only found via `stat` on the live VPS — code review alone missed it.
- **2026-04-26 audit**: UUID 32-bit (brute-forceable), secret leak in `ops_audit` rows, TOCTOU race in `statfsSync`.
- **2026-04-29 audit**: 7 CRITICAL findings including literal API keys in config, `gitleaks` absent, 4 race conditions/memory leaks.
- **2026-05-03 audit**: `execSync` with template strings = command injection even with `escapeRegex` (CWE-78); `Buffer` pool aliasing in typed arrays = silent semantic cache corruption.

Pattern: each audit session finds critical issues missed by prior sessions. The attack surface is not static — new features (A2 export, A3 provider abstraction, P2 hooks) introduce new threat vectors that existing threat models don't cover.

The wave-e threat model (2026-05-18 PR) and wave-f follow-up (threat-model-E1-followup PR) represent the first structured threat modeling exercise rather than incident-driven audits. This ADR formalizes the cadence going forward.

## Decision

**Security audits follow a recursive "threat-model → fix → verify → update model" cycle on a quarterly cadence:**

1. **Quarterly threat model review** (every 3 months): revisit the threat model doc (`docs/THREAT-MODEL.md` or equivalent) against the current feature surface. Every new pillar (Q/A/P item) that touches data ingestion, storage, retrieval, or export gets a threat model section before implementation merges.

2. **Per-feature threat review gate**: before a PR that introduces a new data path (ingestion, export, API endpoint, CLI command with user input) is merged, a threat review checklist must be completed:
   - Input validation (no `execSync` with template strings; use `execFileSync` with array args)
   - Path traversal check (realpath + allowlist validation)
   - Secret exposure check (no API keys in audit tables, logs, or error messages; `scrubSecrets()` applied)
   - Permission check (file/dir ACLs match the 0600/0700 pattern for sensitive data)

3. **Pre-commit secret scanning**: `gitleaks` pre-commit hook is mandatory. Bypassing with `--no-verify` requires explicit justification in the commit message.

4. **Post-incident threat model update**: after any security incident, the threat model is updated within 48h to reflect the new attack vector and mitigations applied. The update is a separate commit from the fix.

5. **Audit findings are tracked, not just fixed**: security findings from each audit session are recorded in `docs/SECURITY-AUDIT-LOG.md` with status (open/fixed/accepted-risk). This provides continuity across sessions and prevents re-discovering the same issues.

## Consequences

- **Positive:** Critical vulnerabilities are caught before production rather than discovered via incident. Historical pattern: each ad-hoc audit found 4–7 CRITICAL issues that prior code review missed.
- **Positive:** Threat model as living document means new contributors can understand the security posture without reconstructing it from incident history.
- **Negative:** Per-feature threat review adds ~30–60 min to PR review time for data-path features. Accepted overhead given the sensitivity of the data handled.
- **Negative:** Quarterly cadence may be insufficient if the feature release rate is high (10+ PRs/week). In that case, cadence should shorten to monthly.
- **Risks:** Quarterly cadence is only effective if someone owns the calendar item. Without a designated owner (currently: primary maintainer), the cadence drifts to incident-driven.

## Alternatives considered

- **Incident-driven audits only** — rejected: prior pattern showed that waiting for an incident means data has already been exposed (keys revoked, users affected). Proactive cadence is strictly better.
- **Continuous automated scanning only (no manual review)** — rejected: automated tools (gitleaks, semgrep) catch well-known patterns but miss logic-level vulnerabilities (Buffer pool aliasing, TOCTOU races, semantic cache corruption). Manual review is irreplaceable for this class of bug.
- **Annual security audit (SOC2-style)** — rejected: release cadence is weekly; annual reviews are too slow to catch issues before they compound. Quarterly is the minimum viable cadence for this rate of change.
- **External security firm** — deferred: appropriate at commercial launch scale; not warranted for current single-VPS personal use. Revisit at NOX-Supermem commercial launch.

## Related

- Supersedes: none
- References:
  - `docs/DECISIONS.md` §4 (incidents table — all security incidents)
  - `docs/DECISIONS.md` §3.Operations & Safety
  - Wave-e PR: `wave-e/2026-05-18/threat-model`
  - Wave-f PR: `wave-f/2026-05-18/threat-model-E1-followup`
  - `feedback_no_secrets_in_git.md`
  - `feedback_execfilesync_over_execsync_for_user_input.md` (CWE-78)
  - `feedback_buffer_pool_aliasing_in_typed_arrays.md`
  - `audits/2026-04-26-7highs-followup-fix.md`
  - `audits/2026-04-29-post-marathon-audit.md`
