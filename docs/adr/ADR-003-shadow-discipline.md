# ADR-003: Shadow discipline for ranking changes

Date: 2026-04-27

## Status

Accepted

## Context

Ranking changes — score multipliers, boost factors, new retrieval tiers, weight adjustments — are high-leverage and high-risk. A change that looks beneficial in unit tests can silently degrade real-world retrieval quality at scale, because:

1. Golden query sets are small (n=5–80); statistical power is low; a single outlier query can shift category metrics by 20–50pp.
2. BM25 + RRF fusion has non-linear interactions: a boost that helps one category can displace gold results in another (observed repeatedly in E05b rounds 1–3, 2026-05-17).
3. Production telemetry (`search_telemetry`) provides a ground truth that unit tests cannot replicate — real query distributions, real chunk competition, real agent usage.

Incident v3.4: multiplicative boost stacking was introduced in a "fix" commit; it compounded with existing boosts and caused a measurable recall regression. The commit message gave no indication this was a scoring change.

The section_boost feature (schema v10) was shipped with `NOX_SECTION_BOOST_MODE=shadow` for 7 days before activation (G02, 2026-05-01). Measured telemetry showed compiled +100.32%, frontmatter +48.94% — both within 1% of design targets. Timeline demotion -17.45% confirmed as intentional. That process was the first clean execution of this discipline.

E05b reason-aware ranking boost was kept in shadow for 14+ days across 3 gate review rounds with n=5, n=65, n=80. All three rounds showed regression. It was eventually CUT (D38) — the shadow period correctly prevented a production regression.

## Decision

**Any change that modifies retrieval ranking or scoring** must ship behind an environment-variable feature flag in `shadow` mode before activation:

- Feature flag convention: `NOX_<FEATURE_NAME>_MODE=shadow` (shadow) / `active` (live) / `off` (disabled).
- **Minimum shadow period: 7 days** wall-clock (not business days). No exceptions for "obvious" improvements.
- **Gate review required**: before flipping to `active`, run gate review using the current golden query set. Pass criteria must be defined in the spec before implementation begins.
- **Baseline first**: the current golden set nDCG@10 must be measured and recorded BEFORE the feature is implemented, so changes have a reference point.
- **Commit prefix enforcement**: ranking/scoring changes must use `tune(search):` or `feat(search):` prefix — never buried in `fix:` commits.

Additive boosts are preferred over multiplicative boosts. Multiplicative stacking creates compounding effects that are difficult to reason about and have caused incidents.

Shadow metrics are exposed via `/api/health` (e.g., `/api/health.salience`, `/api/health.sectionDistribution`) for live inspection without activating the feature.

## Consequences

- **Positive:** Ranking regressions are caught before they affect production. The 14-day shadow period for E05b prevented a confirmed -5pp to -50pp regression across categories.
- **Positive:** Gate reviews generate empirical data that informs design decisions (e.g., E05b CUT was data-driven, not intuitive).
- **Negative:** Minimum 7-day wall-clock delay for every ranking improvement. Features that "feel obviously better" must still wait.
- **Negative:** Maintains two code paths during shadow period (shadow + active), increasing cognitive overhead.
- **Risks:** If shadow metrics are not checked regularly, the 7-day period becomes theater. Canary `*/30min` on `match_type:"semantic"` is the operational safeguard.

## Alternatives considered

- **No shadow mode (ship directly)** — rejected: caused incident v3.4 (multiplicative boost regression). Telemetry confirms production query distributions differ materially from test sets.
- **A/B test with traffic split** — rejected: single-user system; traffic split is not meaningful. Shadow mode with full telemetry is equivalent without the routing overhead.
- **Shorter shadow period (48h)** — rejected: section_boost 7-day period was the calibration reference. E05b confirmed that 7 days is the minimum to see real distribution effects. 48h windows may miss low-frequency query categories entirely.

## Related

- Supersedes: none
- References:
  - `docs/DECISIONS.md` §3.Search & Ranking item 3
  - `docs/DECISIONS.md` D35 (E05b KEEP-SHADOW), D38 (E05b CUT)
  - `docs/DECISIONS.md` §5 (constraint: salience formula multiplicative)
  - `feedback_shadow_mode_for_ranking_changes.md`
  - G02 activation record (2026-05-01): `docs/DECISIONS.md` §2026-05-01
