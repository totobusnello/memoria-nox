# Suggested README badges (post-CI setup)

After CI lands on main, add the following badges to the README hero section (after the tagline, before the comparison table):

```markdown
![CI](https://github.com/totobusnello/memoria-nox/actions/workflows/validate-syntax.yml/badge.svg)
![Docs](https://github.com/totobusnello/memoria-nox/actions/workflows/lint-docs.yml/badge.svg)
![Security](https://github.com/totobusnello/memoria-nox/actions/workflows/security.yml/badge.svg)
```

## Placement

Insert after the headline block, before `## Why nox-mem?` or the comparison chart.
Keep badges compact — one line, left-aligned, no extra prose.

## Notes

- Badges reflect the last run on `main` only (not PRs).
- `validate-syntax.yml` covers YAML + JSON + Python + Bash — most comprehensive single-status signal.
- `security.yml` badge will be yellow during weekly schedule runs; green once passed.
- `eval-smoke.yml` badge intentionally omitted (only triggers on eval/ path changes — badge would show stale/grey most of the time).
- `release.yml` badge omitted (manual workflow_dispatch only).

## Codespaces badge (post-#253 merge)

After this PR merges, add to README hero:

```markdown
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/totobusnello/memoria-nox)
```
