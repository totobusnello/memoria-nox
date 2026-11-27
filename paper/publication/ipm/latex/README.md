# CAS LaTeX build of the IP&M manuscript

`build_latex.py` converts `../manuscript.md` to `manuscript.tex` (Elsevier CAS single column,
anonymized, no author block), writes `highlights.txt` and `title-page.tex`, runs `xelatex` twice on
each, and then checks that the PDF prints exactly the manuscript's numbers (same tokenizer as
`tools/provenance.py`; inline code such as version strings is counted on neither side). It exits 1
if a number was added, dropped or changed in the conversion. `--no-build` runs only the check.

The class files are not versioned. Fetch them once into this directory:

```sh
curl -sSLO https://mirrors.ctan.org/macros/latex/contrib/els-cas-templates.zip
unzip -j els-cas-templates.zip 'els-cas-templates/cas-sc.cls' 'els-cas-templates/cas-common.sty'
```

On a BasicTeX install the class also needs, in user mode:
`tlmgr --usermode install charissil footmisc inconsolata makecell moreverb multirow sttools stix wrapfig xstring`.

Files for the submission system: `manuscript.pdf` (anonymized article), `highlights.txt`,
`title-page.pdf` (identity; not for reviewers), `../cover-letter.md`, `../figures/figure1.pdf`, and
`../supplement/S1-S3`.
