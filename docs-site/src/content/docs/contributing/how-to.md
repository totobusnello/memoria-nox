---
title: How to Contribute
description: Opening issues, submitting PRs, running tests, and commit conventions.
sidebar:
  order: 1
---

Full source: [`CONTRIBUTING.md`](https://github.com/totobusnello/memoria-nox/blob/main/CONTRIBUTING.md)

## Getting started

```bash
git clone https://github.com/totobusnello/memoria-nox.git
cd memoria-nox
npm install
npm run build
npm test
```

## Branch conventions

| Branch pattern | Purpose |
|---|---|
| `feat/<slug>` | New feature |
| `fix/<slug>` | Bug fix |
| `tune(search):<slug>` | Search tuning (must not mix with fix commits) |
| `docs/<slug>` | Documentation |
| `wave-<n>/YYYY-MM-DD/<slug>` | Overnight / swarm work |

## Commit message format

```
<type>(<scope>): <short description>

<body (optional)>
```

Types: `feat`, `fix`, `docs`, `tune`, `test`, `refactor`, `chore`

**Important:** Never mix ranking/scoring changes into a `fix` commit. Use `tune(search):` or `feat(search):` prefix. This is a hard rule — violations caused incident v3.4.

## Running tests

```bash
npm test                        # all tests
npm test -- --grep "op-audit"   # specific suite
```

The test suite uses Node's built-in `node:test`. No Jest, no Vitest.

:::caution[ESM + env vars]
Static `import`s hoist before the test body. Use dynamic `await import()` inside an async `before()` hook for any env-dependent module setup — otherwise env vars are captured as empty strings in isolation.
:::

## Adding a new doc page

1. Create `docs-site/src/content/docs/<section>/<slug>.md`
2. Add frontmatter:
   ```yaml
   ---
   title: Your Page Title
   description: One-sentence description for search.
   sidebar:
     order: N
   ---
   ```
3. Add to sidebar in `docs-site/astro.config.mjs`
4. Add link to `docs/DOCS.md` under the relevant section

## Security review requirement

Before closing any PR touching `src/lib/`, run both:
- Code reviewer agent
- Security reviewer agent

Audit critical modules in the same session. Smoke tests cover happy-path — adversarial review catches the CRITICAL issues. Investment: 30min. Cost of skipping: weeks. (Lesson from A1 op-audit 2026-04-25.)

## PR checklist

- [ ] Tests pass (`npm test`)
- [ ] Build passes (`npm run build`)
- [ ] No secrets in diff (`git diff | grep -E '(sk-|AIza|key=)'`)
- [ ] DOCS.md updated if new docs added
- [ ] CHANGELOG.md entry added
- [ ] Ranking changes use `tune(search):` prefix, not `fix:`
