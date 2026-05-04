# refs-audit-report.md
# Citation Audit — memoria-nox paper
# Generated: 2026-05-03

## Scope

Three paper files audited:
- `paper-draft-sec1-3.md` (§1–§3)
- `paper-draft-sec4-7.md` (§4–§7 + Appendices A–D inline)
- `appendix-d-shadow-case-study.md` (Appendix D standalone)

Reference database: `refs.bib`

---

## All \cite{} keys found — match status

### paper-draft-sec1-3.md (9 unique keys)

| Key | refs.bib entry | Status |
|---|---|---|
| `lewis2020rag` | `@inproceedings{lewis2020rag}` | OK |
| `packer2023memgpt` | `@misc{packer2023memgpt}` | OK |
| `chhikara2025mem0` | `@misc{chhikara2025mem0}` | OK |
| `xu2025amem` | `@inproceedings{xu2025amem}` | OK |
| `edge2024graphrag` | `@misc{edge2024graphrag}` | OK |
| `huang2025hirag` | `@inproceedings{huang2025hirag}` | OK |
| `guo2024hipporag` | `@misc{guo2024hipporag}` | OK |
| `cormack2009rrf` | `@inproceedings{cormack2009rrf}` | OK |
| `topoteretes2024cognee` | `@misc{topoteretes2024cognee}` | OK |

### paper-draft-sec4-7.md (14 unique keys)

| Key | refs.bib entry | Status |
|---|---|---|
| `rogers2021just` | `@inproceedings{rogers2021just}` | OK |
| `manning2008introduction` | `@book{manning2008introduction}` | OK |
| `thakur2021beir` | `@inproceedings{thakur2021beir}` | **FIXED** (was missing — added 2026-05-03) |
| `muennighoff2022mteb` | `@inproceedings{muennighoff2022mteb}` | OK |
| `yang2018anserini` | `@article{yang2018anserini}` | OK |
| `chen2024bge` | `@inproceedings{chen2024bge}` | OK |
| `wang2023improving` | `@misc{wang2023improving}` | OK |
| `fuhr2018some` | `@article{fuhr2018some}` | OK |
| `packer2023memgpt` | `@misc{packer2023memgpt}` | OK |
| `edge2024graphrag` | `@misc{edge2024graphrag}` | OK |
| `chhikara2025mem0` | `@misc{chhikara2025mem0}` | OK |
| `xu2025amem` | `@inproceedings{xu2025amem}` | OK |
| `huang2025hirag` | `@inproceedings{huang2025hirag}` | OK |
| `topoteretes2024cognee` | `@misc{topoteretes2024cognee}` | OK |

### appendix-d-shadow-case-study.md (5 keys — all wrong before fix)

| Original key (wrong) | Corrected key | refs.bib entry | Status |
|---|---|---|---|
| `\cite{Sanderson2010}` | `\cite{sanderson2010test}` | `@article{sanderson2010test}` | **FIXED** (key renamed + entry added) |
| `\cite{Packer2023}` | `\cite{packer2023memgpt}` | `@misc{packer2023memgpt}` | **FIXED** (key renamed) |
| `\cite{Chhikara2025}` | `\cite{chhikara2025mem0}` | `@misc{chhikara2025mem0}` | **FIXED** (key renamed) |
| `\cite{AMEM2024}` | `\cite{xu2025amem}` | `@inproceedings{xu2025amem}` | **FIXED** (key renamed) |
| `\cite{OpAudit2026}` | `\cite{noxmem2026opaudit}` | `@misc{noxmem2026opaudit}` | **FIXED** (key renamed + entry added) |

---

## refs.bib entries added (2026-05-03)

| Key | Type | Citation |
|---|---|---|
| `thakur2021beir` | `@inproceedings` | Thakur et al., BEIR, NeurIPS D&B 2021, arXiv:2104.08663 |
| `sanderson2010test` | `@article` | Sanderson, Foundations & Trends IR 4(4), 2010, DOI:10.1561/1500000009 |
| `noxmem2026opaudit` | `@misc` | Busnello, nox-mem op-audit, GitHub commit 8c3f3d2 |

---

## refs.bib entries defined but not cited in any audited file

| Key | Note |
|---|---|
| `sarthi2024raptor` | Secondary reference; cited in HiRAG comparison context — may be used in final camera-ready |

---

## Total citation count

| File | \cite{} occurrences | Unique keys | Orphan keys after fix |
|---|---|---|---|
| paper-draft-sec1-3.md | 16 | 9 | 0 |
| paper-draft-sec4-7.md | 25 | 14 | 0 |
| appendix-d-shadow-case-study.md | 5 | 5 | 0 |
| **Total** | **46** | **22 unique** | **0** |

---

## LaTeX compile recommendation

Run the following sequence from the directory containing `refs.bib`:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Or with BibLaTeX/biber:

```bash
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

After the first `bibtex`/`biber` pass, check `.blg` for any "I didn't find a database entry for" warnings — all 22 unique keys audited above should resolve cleanly. The one previously undefined key (`thakur2021beir`) and the five mismatched Appendix D keys are now resolved.
