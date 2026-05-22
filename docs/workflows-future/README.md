# Future workflows (not yet active)

Templates that get moved to `.github/workflows/` when needed.

## `perf-baseline-refresh.yml.template`

Manual-only baseline refresh workflow. Currently parked here because GitHub Actions
creates phantom "No jobs were run" notifications on every push when this is in
`.github/workflows/` (even with `workflow_dispatch:` only trigger).

### Activate when
- Tagging `v1.0.0-rc1` (refresh baseline after G10d + temporal spike stable)
- Tagging `v1.1.0` (after A2 encrypted backup + A3 provider overhead ship)
- Any intentional architecture change setting a new performance baseline

### Activation steps
```bash
git mv docs/workflows-future/perf-baseline-refresh.yml.template .github/workflows/perf-baseline-refresh.yml
git commit -m "ci: activate perf-baseline-refresh for v<version>"
git push
gh workflow run perf-baseline-refresh.yml -f version=v1.0.0-rc1 -f note="..."
```

After successful baseline refresh + commit, move template back:
```bash
git mv .github/workflows/perf-baseline-refresh.yml docs/workflows-future/perf-baseline-refresh.yml.template
git commit -m "ci: park perf-baseline-refresh (notification quirk)"
```

This dance kills the phantom-run notification spam while keeping the workflow
reachable for tag-time invocation.
