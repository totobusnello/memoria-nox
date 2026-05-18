# CodeQL — Static Analysis for memoria-nox

> Workflow: `.github/workflows/codeql.yml`  
> Added: Wave J (2026-05-18)  
> OpenSSF Scorecard impact: +1 (SAST check)

---

## What CodeQL is

CodeQL is GitHub's static analysis engine. It treats code as data — it builds a database of the full program (AST, control flow, data flow, call graph) and then runs queries against that database to find vulnerabilities.

Unlike linters that look at individual lines, CodeQL can trace a value from where it enters the program (a user input, an environment variable, a file read) all the way through every transformation until it reaches a dangerous sink (a SQL query, a shell command, a file path, a network call). This is called **taint analysis**.

For memoria-nox specifically, CodeQL will flag patterns like:
- User-supplied query string reaching a SQLite `prepare()` or `exec()` call without parameterization
- `process.env` value flowing into `execSync()` / `execFileSync()` without validation
- File paths derived from external input reaching `fs.readFile`, `fs.writeFile`, or `fs.unlink` without `path.resolve()` + allowlist check
- Regular expression patterns that could cause catastrophic backtracking (ReDoS)
- Prototype pollution via `Object.assign` or `_.merge` with untrusted input
- XSS patterns in any HTTP API responses (relevant to the `/api/` endpoints on port 18802)

The query suite used is `security-extended,security-and-quality` — this covers ~200+ CWEs including the OWASP Top 10 and the Sans/CWE Top 25.

---

## How the Workflow Runs

The workflow triggers on:
- Every push to `main`
- Every PR targeting `main`
- Weekly schedule (Monday 04:00 UTC) — catches newly-discovered query updates even without code changes

Each run takes 5–15 minutes for a TypeScript project of this size. Results appear in the **Security** tab → **Code scanning alerts**.

### Permissions

The workflow uses minimal permissions:
- `actions: read` — read workflow metadata (needed by CodeQL)
- `contents: read` — checkout the code
- `security-events: write` — upload SARIF results to Security tab

No write permissions to code or PRs.

---

## How to Triage Results

### Finding alerts

1. Go to `https://github.com/totobusnello/memoria-nox/security/code-scanning`
2. Each alert shows:
   - **Rule ID** (e.g., `js/sql-injection`, `js/path-injection`)
   - **Severity** (Critical / High / Medium / Low)
   - **File + line** where the issue was detected
   - **Data flow path** — the full taint trace from source to sink

### Severity triage guide

| Severity | Action | Timeline |
|----------|--------|----------|
| Critical | Fix before merging the PR that introduced it | Immediate |
| High | Fix within 1 sprint | < 1 week |
| Medium | File issue, fix in next planned security sprint | < 1 month |
| Low | Review quarterly; suppress if confirmed false positive | Quarterly |

### Understanding the data flow path

CodeQL shows you exactly how data flows to the sink. Example for SQL injection:

```
[Source] req.query.search (line 42, search-api.ts)
  → passed to buildQuery() as `term` parameter (line 47)
  → concatenated into SQL string at line 89
[Sink] db.prepare(sqlString) (line 89, search-api.ts)
```

If the data flow path goes through a sanitization function you wrote, but CodeQL doesn't recognize it, you may need to either:
1. Add a barrier (suppression comment — see below)
2. Refactor to use a pattern CodeQL does recognize (parameterized query, explicit escape)

### Checking for false positives

Before suppressing, verify:
1. Is the source actually reachable from untrusted input?
2. Does the transformation between source and sink actually sanitize the value?
3. Does the sink actually pose a risk in this context?

For nox-mem specifically:
- The HTTP API on port 18802 is localhost-only — but the Security team recommendation is still to validate inputs, because localhost-only is a deployment assumption, not a code guarantee.
- CLI inputs come from the user running the tool — generally trusted, but injection via shell scripts or cron is a realistic vector.

---

## Suppressing False Positives

When you have confirmed a finding is a false positive, suppress it with a comment directly in the code:

### Single line suppression

```typescript
const result = db.prepare(query).all(); // lgtm[js/sql-injection]
```

### Block suppression (CodeQL v2 format)

```typescript
// codeql[js/sql-injection] - query is built from allowlisted column names only
const result = db.prepare(query).all();
```

### In SARIF (via GitHub UI)

1. Click the alert in the Security tab
2. Click "Dismiss alert"
3. Select "False positive" and add a comment explaining why
4. This creates a dismissal record in the repo — it survives code changes

**Important:** Only suppress if you have verified the finding. If in doubt, fix the code instead. A suppression comment is a permanent claim that this code path is safe — treat it like a security decision that needs justification.

---

## Known Query IDs Relevant to nox-mem

| Query ID | What it catches | Relevant files |
|----------|----------------|----------------|
| `js/sql-injection` | Unsanitized input in SQL | `src/search.ts`, `src/ingest*.ts` |
| `js/path-injection` | User input in file paths | `src/ingest-entity.ts`, `src/lib/op-audit.ts` |
| `js/command-injection` | Shell command injection | Any use of `execSync`/`execFileSync` |
| `js/regexp-injection` | User input in RegExp constructor | `src/search.ts` (query parsing) |
| `js/prototype-pollution` | Prototype pollution | Any `Object.assign` / spread with external data |
| `js/hardcoded-credentials` | Hardcoded API keys, tokens | All source files |
| `js/insecure-randomness` | `Math.random()` for security | Token/ID generation |
| `js/xss` | Cross-site scripting | HTTP API response handlers |
| `js/missing-rate-limiting` | DoS via unbounded requests | HTTP API endpoints |
| `js/redos` | Catastrophic backtracking | Query parser regex |

---

## Alert Lifecycle

```
Open → Dismissed (false positive)
     → Fixed (code change closes the alert automatically)
     → Auto-closed (if branch is deleted without merging)
```

When you fix a finding in code and push to main, the alert closes automatically on the next scan. You do not need to manually close it.

---

## Custom Queries for nox-mem (Future Work)

CodeQL supports custom queries in `.github/codeql/` directory. Planned future additions:

- **nox-mem/chunk-injection**: detect if chunk content from DB reaches shell or file sinks without sanitization (nox-specific taint source)
- **nox-mem/kg-entity-injection**: detect if entity names from kg_entities reach SQL sinks without parameterization
- **nox-mem/api-response-leak**: detect if internal error objects (including stack traces) are included in API responses that reach external callers

These are low priority until the project has external contributors or a public API. File as a tracking issue when ready to implement.

---

## Integration with Branch Protection

Once branch protection is enabled (see `BRANCH-PROTECTION.md`), add `CodeQL Analyze (javascript-typescript)` to the required status checks. This ensures:
- No PR merges with open Critical/High findings introduced by that PR
- The Security tab always reflects the current state of `main`

---

## Relationship to other security tools

| Tool | What it covers | Where configured |
|------|---------------|-----------------|
| CodeQL | Static taint analysis, vulnerability patterns | `.github/workflows/codeql.yml` |
| Dependency Review | Known CVEs in new dependencies | `.github/dependency-review-config.yml` |
| Renovate | Automated dependency updates | `.github/renovate.json` |
| THREAT-MODEL.md | Manual threat assessment | `docs/security/THREAT-MODEL.md` |

These four together form the security automation layer for the Q/A/P pillar (Quality → supply chain integrity).

---

*Maintained by lab@nuvini.com.br. Update when custom queries are added or query suite changes.*
