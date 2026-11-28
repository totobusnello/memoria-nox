# Cover letter (to the editor; not sent to reviewers)

Dear Editor,

Please consider the enclosed manuscript, "nox-mem: a single-file hybrid memory for LLM agents, and a
pre-specified comparison against five memory systems", for publication in *Information Processing &
Management* as a research article.

Memory systems for LLM agents are compared today mostly through numbers their vendors publish, on
different benchmarks, metrics and backbones. The article reports a comparison designed to avoid that:
the execution plan, with an anti-cherry-pick statement, was committed to a public repository before the
first run, and five systems (Mem0, Zep, Letta, agentmemory and EverOS) were set up against ours on one
corpus and one query set of 2,482 questions. Those that ran were scored with the same retrieval metric;
those that could not were reported with the reason. The results do not favour our system throughout.
The ordering between it and Mem0 depends on the embedder, EverOS leads on the full set, and our own
ablations find no measurable effect of the severity signal the
system was first built around. We report these results as measured, with the confounds of each run
declared. We think the comparison, and the way it was planned and reported, fit the journal's interest
in the evaluation of information retrieval systems.

Three points the editor should know before review:

1. **Preprint.** The article condenses a technical report deposited on Zenodo under CC BY 4.0
   (doi:10.5281/zenodo.22649268). The journal's policy does not count a preprint as prior publication.
   The report and this manuscript share an author and the system's name, so a reviewer who searches for
   the name can find the report.
2. **No new measurement.** Every decimal number and percentage in the manuscript occurs verbatim in
   version 1.0.6 of the report; a script in the public repository checks this on every change.
3. **Generative AI.** Its use in preparing the manuscript is declared in the manuscript, in the form the
   journal asks for.

The manuscript has not been submitted elsewhere and is not under consideration by another journal. The
author has no competing financial interest with the developers of the compared systems. Code, the
per-query outputs and the verifier of the comparison are publicly available, as stated in the data
availability section; the anonymized supplementary files S1 to S4 accompany the submission (S4 holds the code, the two evaluation harnesses and the evidence with its verifier).

Sincerely,

Luiz Antonio Busnello
Independent Researcher
ORCID 0009-0007-5911-8141
