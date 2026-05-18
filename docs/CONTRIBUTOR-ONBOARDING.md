# Contributor Onboarding — memoria-nox

> **Audience:** first-time contributors to the nox-mem OSS repo
> **Time investment:** Day 0 (~1h setup) → Day 1-3 (first contribution) → Week 1 (deep-dive) → Month 1 (specialization)
> **Prerequisite:** Node.js 18+, git, a Gemini API key (free tier is enough for local testing)

---

## Day 0 — Setup (~1 hour)

### 1. Clone and verify the build

```bash
git clone https://github.com/totobusnello/memoria-nox.git
cd memoria-nox
npm install
npm test
```

Expect: tests pass (or known failures listed in `docs/HANDOFF.md` — check there first before filing a bug). The test suite runs without any API key for the static/unit layer. Integration tests require `GEMINI_API_KEY`.

### 2. Set your API key

```bash
export GEMINI_API_KEY=your_key_here
```

For persistent local dev, add to your shell profile. The system defaults to `gemini-2.5-flash-lite` for embeddings and KG extraction — free tier quota is sufficient for local development volumes.

**Do not hardcode the API key.** Do not commit it. See `SECURITY.md` for the full rule. Violation history: one literal key caused Gemini revocation in 2026-04 and broke production for 12 hours.

### 3. Run a smoke test against sample data

```bash
nox-mem ingest ./benchmark/fixtures/        # ingest bundled sample fixtures
nox-mem search "test query" 5               # should return results
```

If ingest runs but `nox-mem vectorize` says "Done: 0 embedded, N errors" — you forgot `GEMINI_API_KEY`. The error is silent by design (quota protection), not a bug.

### 4. Read the two canonical docs (~30 min)

Read these in order. Everything else references them.

1. **`docs/VISION.md`** — the mission, the three pillars (Q/A/P), what we will never do, 18-month horizon. This is the north star. If a PR conflicts with VISION, it will not merge regardless of technical quality.

2. **`docs/ROADMAP.md`** — current sprint work by pillar, capacity allocation (60% product / 40% Lab), gate criteria for each item. This tells you what is actively being worked and what is deferred.

### 5. Read the three most recent architectural decisions (~15 min)

- **D40** — Q/A/P pivot (2026-05-17): why we reorganized from research-heavy to product-first. Sets the frame for all current work.
- **D41** — five polish decisions from 2026-05-18: visual assets, GTM asset bundle, blog timing, benchmark publishing discipline, contributor onboarding. Context for the sprint you are entering.
- **D42** (if present) — most recent decision. Always read the latest two before touching any ranked feature.

All decisions are in `docs/DECISIONS.md`. The "NÃO FAZEMOS" section (#1–28+) is equally important — it documents paths we explored and rejected, with reasons. Read it before proposing a feature; there is a good chance it was already evaluated.

---

## Day 1-3 — First contribution

### Finding your first issue

Look for the `good-first-issue` label on GitHub. Good candidates:
- Documentation improvements (no shadow-mode required)
- Test additions for existing functionality
- Fixing a specific bug listed in `docs/HANDOFF.md` under "known issues"
- CLI UX improvements (cosmetic output, help text)

**Avoid as a first PR:** any change that touches `src/search.ts`, `src/rrf.ts`, `src/salience.ts`, `src/kg-*.ts`, or any file with "ranking" in the name. These require shadow discipline (see below) and are not appropriate entry points.

### Branch naming

```
feature/<short-description>     # new capability
fix/<short-description>         # bug fix
docs/<short-description>        # documentation only
test/<short-description>        # tests only
lab/<experiment-name>           # Lab-gated experiment (see Lab section)
```

Examples:
- `fix/reflect-cache-unicode-boundary`
- `docs/quickstart-windows-path`
- `feature/cli-stats-csv-export`
- `lab/l2-conflict-detection-schema`

### Test-first: write the failing test first

Before writing implementation code, write a test that fails for the right reason. This is not optional — it is how we know the fix actually fixes the thing it claims to fix.

```bash
npm test -- --filter "your test name"   # run a specific test
```

The test suite uses Node's built-in `node:test`. No Jest, no Mocha. See `src/__tests__/` for examples.

**Special rule for ESM:** the codebase is `type: module`. No `require()`. All imports must be top-level `import` statements. If you add `require(...)` anywhere in `src/**/*.ts`, the TypeScript compiler will not catch it in all cases — grep for it before submitting:

```bash
grep -r "require(" src/ --include="*.ts"
```

### Cross-link related ADRs in your PR

When your PR touches a design decision, link to the relevant decision in `docs/DECISIONS.md`. Format:

```
Related: docs/DECISIONS.md#D39 (FTS5 AND-strict design)
```

This creates a navigation trail that future contributors (and future you) can follow.

### Mandatory closure steps for every PR

These steps are not optional. A PR without them will be returned.

1. **Write the code** with a failing test first
2. **Run tests:** `npm test` — all existing tests must pass
3. **Run build:** `npm run build` — `dist/` must compile clean
4. **Commit:**
   ```bash
   git add <specific files>    # never git add -A or git add . without reviewing
   git commit -m "fix(scope): description"
   ```
5. **Push:**
   ```bash
   git push -u origin fix/your-branch-name
   ```
6. **Open PR** with:
   - Title following conventional commits: `fix(scope):`, `feat(scope):`, `docs(scope):`, etc.
   - Body with: what changed, why, how tested, related ADR links
7. **Verify PR URL** loads and CI passes before marking ready for review

**Commit message conventions:**
- `fix(search):` — bug fix in retrieval pipeline
- `feat(cli):` — new CLI command or option
- `docs(contributing):` — documentation change
- `tune(search):` — ranking/scoring change (triggers shadow discipline requirement)
- `test(eval):` — test additions
- `chore(deps):` — dependency updates

**Never use `fix(search):` for a ranking/scoring change.** Scoring is feature work, tagged `tune(search):` or `feat(search):`. This rule exists because a mistagged commit caused incident v3.4 — a ranking change was buried in a "fix" commit and bypassed shadow-mode review.

---

## Week 1 — Onboarding deep-dive

### Read all key ADRs (~45 min)

`docs/DECISIONS.md` is the canonical record of architectural choices. Work through:

1. **Section 1: NÃO FAZEMOS** — 28+ items with rationale. This is the most important read.
2. **Section 2: Q5 cross-encoder reranker** — example of a properly deferred decision with explicit trigger criteria.
3. **Section 3: Decisões arquiteturais válidas** — why the system is structured as it is (hybrid search, salience multiplicative, shadow-mode, chunks canonical, schema additive, workspace memory format).

### Walk through one pillar end-to-end

Pick one pillar and read its spec + implementation:

**P1 (answer primitive) is the best starter.** It is the `nox-mem answer` command — answer a question before searching. Spec: check `specs/` for P1 spec. Implementation: `src/commands/reflect.ts` (closest existing analog). Test: `src/__tests__/reflect.test.ts`.

This pillar touches search, the semantic cache, citation formatting, and CLI output — a complete cross-section of the codebase without touching the ranking core.

### Run cross-pillar integration tests

```bash
npm test -- --reporter=spec
```

Look for tests marked `[integration]` — these require `GEMINI_API_KEY` and a local DB. Run them at least once to understand what the full round-trip looks like.

### Read THREAT-MODEL.md (~1h)

`docs/THREAT-MODEL.md` (or `SECURITY.md` if not yet split) covers:
- Why `execFileSync(cmd, [args])` is mandatory for any user input (not `execSync` with template strings — command injection risk)
- Why `Buffer.from()` with a typed array needs an explicit copy (pool aliasing corrupts semantic cache — lesson from 2026-05-03)
- Why snapshot atomicity matters (`withOpAudit()` before any destructive op)
- Why world-readable file permissions on `nox-mem.db` are a security finding (ACL 0600 mandatory)

These are not theoretical. Every item in the threat model has a production incident that caused it.

---

## Month 1 — Specialization

### Pick a pillar

| Pillar | Good for | Entry point |
|---|---|---|
| **Quality (Q)** | Data scientists, ML engineers, eval methodology | `eval/` harness, `docs/DECISIONS.md` Q-section, `paper/` |
| **Autonomy (A)** | Systems engineers, crypto, P2P protocols | `src/lib/provider-abstraction.ts` (A3), zero-vendor CI invariant |
| **Product (P)** | Full-stack devs, CLI/UX, IDE integration | `src/commands/`, MCP server, P1-P5 specs |
| **Lab** | Researchers, NLP/IR specialists | `specs/` experiment specs, shadow-mode infra |

### Review 5 recent merged PRs in your pillar

```bash
git log --oneline --all | grep -i "your-pillar-keyword" | head -20
```

Read the PR descriptions, the linked ADRs, and the test additions. Pay attention to what triggered shadow-mode review and what did not.

### Reach out

If you are interested in owners-level access to a specific pillar — co-maintaining a module, having merge rights on non-ranking PRs — open an issue titled "Maintainer interest: [pillar name]" and describe what you want to work on. Toto will respond within a week.

---

## Common mistakes to avoid

### 1. "tu/te/ti/teu/tua" in PT-BR documentation

This repo has PT-BR documentation. The hard rule: **always "você + third person."** Never "tu dizes/podes/queres" — always "você diz/pode/quer." São Paulo register, not European Portuguese or southern Brazilian. Pre-send mental grep before committing any PT-BR text.

This rule is enforced at review. PRs with "tu" forms will be returned for correction.

### 2. Skipping shadow discipline on ranking changes

Any change that modifies how results are ordered — salience weights, section boost multipliers, RRF parameters, FTS anchor behavior, KG edge type weights — **must** go through shadow mode.

The process:
1. Implement the change behind a `NOX_<FEATURE>_MODE=shadow` flag
2. Run in shadow mode for ≥7 days in production (or provide compelling baseline data from eval harness showing the change strictly improves nDCG with no category regressions)
3. Analyze `/api/health` telemetry
4. Open a PR tagged `tune(search):` with the baseline comparison

**"It's a small fix" is not an exception.** The salience formula incident and the section_boost incident both started as "small fixes." Shadow discipline exists precisely because small ranking changes have non-local effects.

### 3. Not testing crypto with round-trip integration tests

If your PR touches encryption (AES-256-GCM export, scrypt KDF, any `crypto` usage) — write a round-trip test that encrypts AND decrypts AND verifies the plaintext matches. A test that only checks "encrypt doesn't throw" misses AAD (Additional Authenticated Data) bugs where decryption silently returns wrong data. Lesson from the AAD incident 2026-04.

### 4. Committing in the worktree branch instead of a proper branch

If you are working in a git worktree (e.g., `wave-*/...`), do not commit directly to the worktree branch and push. Create a proper feature branch off main, do your work there, and PR from that branch. Worktree branches are used by the agent coordination system and are managed separately.

```bash
# wrong:
git checkout wave-j/2026-05-18/some-worktree
# do work
git commit ...

# right:
git checkout main
git checkout -b feature/my-contribution
# do work
git commit ...
git push -u origin feature/my-contribution
```

### 5. Using `execSync` with template strings for user input

```typescript
// WRONG — command injection risk:
execSync(`grep -r "${userInput}" ./src`);

// RIGHT — array form bypasses shell:
execFileSync('grep', ['-r', userInput, './src']);
```

Any PR that passes user-controlled input to `execSync` via template string will be flagged as CRITICAL security and will not merge. Use `execFileSync(cmd, [args])` form always.

---

## FAQs

**Do I need to know SQLite deeply?**

Basics yes, advanced no. You need to understand `SELECT`, `JOIN`, `CREATE TABLE`, and `ALTER TABLE ADD COLUMN`. You do not need to understand WAL checkpointing, page boundaries, or sqlite-vec internals to contribute to most pillars. The Q pillar (eval harness) and A pillar (schema migrations) benefit from deeper SQLite knowledge.

**Is this for AI agents or for humans?**

Both — but agents are the primary consumer. The system is designed so that 6 agents can query the same corpus without coordination overhead. Human developers also query it via CLI and HTTP API. The UX (P pillar) is specifically about making the human-facing CLI and IDE integration feel natural, not just functional.

**Why not just use LangChain memory?**

LangChain BufferMemory is a session-scoped key-value store. It works for single-agent, single-session use. It does not address: multi-agent shared knowledge, long-term memory across sessions, knowledge graph derivation, retrieval quality measurement, or data portability. See the comparison table in `README.md` for the full breakdown.

**When will it support X IDE / X embedding provider / X database?**

Check `docs/ROADMAP.md` first. If X is not listed:
1. Open an issue with the use case
2. If it fits the Q/A/P framework, it will get triaged
3. If it requires compromising data autonomy (e.g., cloud-only database with no local option), it will not be built

**Why Gemini 3072d embeddings instead of OpenAI?**

Quality numbers on the production corpus: Gemini hybrid gets nDCG@10 = 0.5831 vs multilingual-e5-base = 0.3070 (1.9× better) on the same 60-query eval. Cost at <$11/month total OPEX including KG extraction makes it defensible. Provider abstraction (A3) will allow OpenAI/Voyage/local once scaffolded — contributions welcome.

**Why not publish the benchmark until you win it?**

The honest answer is in `docs/VISION.md`: "Benchmark based on massaged metrics destroys technical credibility, and technical credibility is this project's asset." If the LoCoMo or LongMemEval numbers are not leading or tied at top when we run them, `COMPARISON.md` does not publish. We publish the harness and methodology so others can verify — but the marketing claim waits for the number. This is unusual. We think it is correct.

**Can I contribute to the Lab experiments (L2, L3)?**

Yes, but with higher bar. Lab experiments require:
1. Explicit hypothesis with expected baseline delta
2. Shadow-mode implementation (no direct activation)
3. Gate metric defined before starting (e.g., "L3 confidence field requires ≥1.0 pp absolute lift in eval to integrate to ranking — below that, schema stays isolated")
4. Cut criteria explicit — when does the experiment die if the gate is not met?

Open a `lab/<experiment>` branch, write the spec first (see existing specs in `specs/` for format), and open a draft PR linking the spec before writing code.

---

*Last updated: 2026-05-18. For state of active work: `docs/HANDOFF.md`. For decisions: `docs/DECISIONS.md`. For what is coming: `docs/ROADMAP.md`.*
