# Paper 1 → Information Processing & Management: submission plan

Status: plan, 2026-11-26. Decided by the project owner on 2026-11-26: a peer-reviewed Elsevier
venue for Paper 1 (*nox-mem: Pain-Weighted Hybrid Memory for LLM Agents*, Zenodo
doi:10.5281/zenodo.22649268, v1.0.6). Primary venue: Information Processing & Management (IP&M),
subscription route (no APC). Fallbacks: Journal of Systems and Software (subscription), then
SoftwareX (open access only, a software paper). alphaXiv not now: the Zenodo record is already the
public preprint.

## What the venue requires (read on the IP&M Guide for Authors, 2026-11-26)

| item | requirement | Paper 1 today |
|---|---|---|
| article type | research, methods, review or **critical application** ("system design research") | fits critical application |
| review | **double anonymized** | author name, ORCID, GitHub owner and Zenodo DOIs throughout |
| abstract | at most 250 words | 505 |
| length | no limit stated | 28,256 words in the Markdown source; a journal article is usually 8,000–12,000 |
| preprint | "Sharing preprints, such as on a preprint server, will not count as prior publication" | Zenodo v1.0.6, CC BY 4.0: allowed |
| generative AI | declared at submission; Elsevier's statement goes at the end, above the references | a disclosure section exists (192 words) |
| data | deposit and link, or a statement of why not | code MIT on GitHub, evaluation outputs partly outside git (CLAUDE.md rule 13) |
| template | Elsevier CAS LaTeX (`els-cas-templates`) | Pandoc to LaTeX with our preamble |

Not stated on the guide page: highlights and graphical abstract (Elsevier journals usually ask for
3–5 highlights); the open-access price (only needed if we choose OA).

## Words by section today

| section | words |
|---|---|
| Abstract | 505 |
| 1 Introduction (incl. related work) | 2,624 |
| 2 Architecture | 1,197 |
| 3 Memory pipeline | 1,449 |
| 4 Hybrid search | 584 |
| 5 Empirical evaluation | 9,209 |
| 6 Cross-system comparison (pre-specified) | 7,168 |
| 7 Limitations and future work | 1,967 |
| 8 Conclusion | 552 |
| references and footnotes | 2,651 |

## Proposed article (≈ 11,000 words before references)

1. **Title without "Pain-Weighted".** The pain dimension's isolated effect is +0.0065 [−0.0143,
   +0.0338], n = 31 (§7.1); the roadmap took it out of the product slogan on 2026-11-08. A reviewer
   will read the title as the claim. Candidate: *nox-mem: a single-file hybrid memory for LLM
   agents, and a pre-specified comparison against five memory systems*. Owner's call.
2. **Centre on the pre-specified comparison (§6)**, cut to ≈ 4,000 words: methodology, the
   per-dataset table, the per-category table, the fair-comparison and anti-cherry-pick statements,
   the findings that cut against the headline.
3. **System (§2–4) in ≈ 2,000 words**, one figure.
4. **Evaluation (§5) in ≈ 2,500 words**: keep the ablation trajectory summary (5.1), LongMemEval (5.6)
   and the operational profile (5.7); move LoCoMo cross-bench, the F_MH paradox, the orchestration
   series (5.5) and the 5-batch protocol detail to supplementary material.
5. **Related work** rebuilt against 2025–2026 memory papers (the scan of 2026-11-26 for the
   construction study found seven controlled studies where raw history matches or beats
   extraction; a reviewer will expect them).
6. Abstract ≤ 250 words; 3–5 highlights; Elsevier generative-AI statement; data availability
   statement pointing to the Zenodo record and the repository.
7. **Anonymized version** for review: no name, no ORCID, repository through an anonymizing mirror,
   Zenodo DOIs cited as "anonymized for review"; a title page with the identities goes separately.

## Order of work

1. Owner decides the title and the cut above (this file).
2. Cut and rewrite in a branch, in English, with the provenance gate on every number kept.
3. avoid-ai-writing pass; voices only if the owner asks.
4. Convert to the CAS template; build the anonymized PDF and the title page.
5. Owner reviews and submits through Elsevier's system (submission is the owner's, as with Zenodo).

Risks: a single independent author can be desk-rejected regardless of content; the comparison is
from June 2026 and the systems compared have released new versions since, which a reviewer may ask
to re-run.
