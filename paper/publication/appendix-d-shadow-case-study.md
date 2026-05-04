# Appendix D: Shadow Discipline in Practice — The Salience Activation Case Study

## D.1 Background

Ranking changes in retrieval systems carry an asymmetric risk: they affect every query, yet their impact is nearly invisible post-hoc unless a precise baseline was captured before deployment. This observation is not new in information retrieval \cite{sanderson2010test}, but its application to personal operational memory systems has not been systematically addressed.

Prior agent memory systems—including MemGPT \cite{packer2023memgpt}, Mem0 \cite{chhikara2025mem0}, and A-MEM \cite{xu2025amem}—ship retrieval changes without shadow gates. Absence of shadow validation does not reflect negligence; these systems target benchmark-driven evaluation over production environments where corpora are stable and curated. In an operational corpus that changes daily, the risk profile differs materially: a ranking regression that reduces relevant chunk recall for one agent may propagate silently across all six agents sharing the same canonical store.

NOX-Supermem codifies a rule that elevates this concern to an architectural constraint: **every ranking-affecting change must operate in shadow mode for a minimum of seven days before activation**. Shadow mode computes the new scoring formula and logs its effects to `search_telemetry`, but does not apply the boost to the live ranking order. This appendix documents the first rigorous application of this rule, Salience Activation Phase 1.7b-b, as a replicable methodology contribution.

## D.2 Methodology

**Shadow deployment.** The salience formula `salience(chunk) = recency × pain × importance` (§3.2) was implemented in full but gated behind the environment variable `NOX_SALIENCE_MODE=shadow`. When shadow mode is active, the system computes a per-chunk salience score on every search invocation and writes the score to `search_telemetry`, alongside `query_text`, `top_chunk_ids`, and `top_scores` (the A0 telemetry extension). The live `rrfScore` returned to callers is not modified.

**Data collected.** Over seven wall-clock days (2026-04-23 to 2026-04-30), the system accumulated per-chunk salience scores across all organic search traffic from six agents. No synthetic workload was injected. Scores were bucketed into three categories using distribution percentile thresholds computed nightly:

- **Promote**: salience > P95. These chunks would gain a ranking boost upon activation; they are concentrated in high-pain, high-importance, recently-accessed entries.
- **Review**: P50 < salience ≤ P95. Neutral zone; the formula would not materially reorder these chunks relative to the existing RRF baseline.
- **Archive**: salience ≤ P50. These chunks would lose ranking position; they are typically legacy entries with low pain annotation and low recent access.

**Health endpoint.** Distribution statistics were exposed continuously at `/api/health.salience.distribution`, allowing real-time inspection without requiring a database query. The endpoint reports bucket counts, mean, and median salience across the active corpus.

**Activation gate.** Activation was not automated. A human reviewer (the author) inspected the distribution after seven days and evaluated two criteria: (1) absence of degenerate clustering—specifically, that the promote bucket did not capture a degenerate share of the corpus; and (2) alignment with expected content types—specifically, that promote candidates were concentrated in incident documentation, decisions, and recent commits rather than uniformly distributed or concentrated in low-signal content. No nDCG@10 simulation was run against the live corpus prior to activation, which represents a limitation discussed in D.5.

**Seven-day window rationale.** The choice of seven days is an operational tradeoff rather than a statistically derived threshold. A 14-day or 30-day window would provide a more representative sample across weekly work patterns, but extends the delay for legitimate improvements. A 48-hour window has been observed to miss low-frequency query patterns in this corpus. Seven days was chosen as the minimum that captures at least one full weekly cycle of agent interactions. This is an acknowledged limitation: future work should empirically validate the minimum shadow window for corpora of varying size and access frequency.

## D.3 Results

After seven days of shadow telemetry over 62,542 scored chunks, the distribution was:

| Bucket | Count | Share |
|---|---|---|
| **Promote** (salience > P95) | 191 | 0.31% |
| **Review** (P50 < salience ≤ P95) | 16,608 | 26.5% |
| **Archive** (salience ≤ P50) | 45,743 | 73.2% |

Mean salience across the corpus: 0.1106. Median: 0.078.

The promote bucket (191 chunks, 0.31%) exhibited the expected content profile: incident documentation (lessons/feedback files), architectural decisions with high pain annotations, and entity files for the core agents and projects. This concentration is consistent with the intended behavior of the pain dimension—high-pain, frequently-accessed, recent entries should surface preferentially.

The large archive bucket (73.2%) reflects the corpus composition: the bulk of the 62K+ chunks derive from converted PDF and office documents that carry default pain scores (`pain = 0.2`) and low recent access. These chunks are not irrelevant—they are available to retrieval when queries demand them—but they do not warrant persistent ranking prominence.

The distribution showed no degenerate clustering: the promote bucket did not approach 10% of the corpus, which would have suggested the P95 threshold was miscalibrated. Based on this inspection, the decision to activate was made on 2026-04-30 at 13:11 BRT via the script `activate-salience.sh --apply`, setting `NOX_SALIENCE_MODE=active` in the production environment. A pre-activation atomic snapshot was saved to `/var/backups/nox-mem/pre-op/` per the `withOpAudit` protocol (§3.8, \cite{noxmem2026opaudit}).

Post-activation monitoring over 30+ subsequent days showed no retrieval regressions as measured by eval harness runs (§4.1). The system remained in GREEN state throughout.

## D.4 Counterfactual: The April 25 Incident

On 2026-04-25 at 22:03 BRT, a cron job executed `nox-mem reindex` without the `--dry-run` flag. The reindex operation traversed all 183 entity files but routed them through the generic `ingestFile()` function rather than the entity-aware `ingestEntityFile()`, which preserves `section`, `retention_days`, and `section_boost` annotations. The result: 183 entities lost all structural annotations, collapsing to generic chunks. No error was logged. No alert fired. The database simply obeyed the instruction.

This incident motivated two architectural responses: the `withOpAudit` pre-operation snapshot system (F02, shipped 2026-04-26) and the `--dry-run` mode for all destructive operations (A5, shipped 2026-04-27). It also, in retrospect, provided the clearest validation argument for shadow discipline.

Had the April 25 incident occurred after salience activation but before the seven-day shadow window, the ranking effects would have been silent and ambiguous. The section_boost values for 183 entity files would have dropped to zero overnight; salience scores for those chunks would shift, but without a telemetry baseline, distinguishing formula-driven change from corpus corruption would require manual inspection of individual chunk metadata.

Shadow telemetry makes this class of regression detectable: a corpus-level event that zeroes out section_boost for a significant chunk fraction would shift the nightly distribution calculation, because importance (derived in part from entity_type prior and mention_count) would diverge from the previous night's snapshot. A practitioner monitoring `/api/health.salience.distribution` would observe an anomalous shift in the promote/review boundary within hours.

This is the core claim of shadow discipline as an architectural principle: it converts silent regression risk into a visible signal, contingent only on the practitioner monitoring the distribution endpoint.

## D.5 Generalization and Limitations

Shadow discipline as described here is not specific to the salience formula. The same methodology—env-var gating, telemetry collection, distribution inspection, human activation gate—has been applied to section_boost activation (G02, activated 2026-05-01), SPO vault-facts injection (E03b, shadow 2026-05-02), and session focus boost (E04b, shadow 2026-05-02). The pattern is:

1. Implement behind `NOX_*_MODE=shadow`
2. Log effects to `search_telemetry` for ≥7 days
3. Expose distribution at `/api/health.<feature>`
4. Human reviews distribution; activates if distribution matches expected semantics
5. Rollback available via `withOpAudit` pre-op snapshot

The cost of this discipline is approximately seven days of wall-clock delay per ranking change, with minimal engineering overhead: one env-var branch, one telemetry write per search invocation, and one health endpoint field. The anti-pattern—deploying directly with `NOX_*_MODE=active`—is enforced against by the deploy script, which checks for shadow gate completeness before allowing activation.

**Limitations.** This case study represents a single activation event (n=1) on a single operational corpus. Generalization claims require additional replications across corpora with different size, access frequency, and pain distribution characteristics. The seven-day shadow window is not empirically validated as a minimum; it is a practitioner heuristic. The activation decision is human-gated, which introduces subjectivity and does not scale to automated pipelines. The absence of a pre-activation nDCG@10 simulation against held-out queries means the quantified retrieval benefit of salience activation (versus no salience) is estimated post-hoc from ablation studies (§5.5) rather than measured at the activation boundary. Future work should address these gaps, particularly by running simulated nDCG@10 over held-out queries during the shadow period as an objective activation criterion, reducing reliance on subjective distribution inspection.
