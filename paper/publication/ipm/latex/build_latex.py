#!/usr/bin/env python3
"""Convert manuscript.md to the Elsevier CAS single-column template and build the review PDF.

Writes, next to this script:
  manuscript.tex      anonymized article in cas-sc (title, abstract, highlights, keywords, body,
                      declarations, references); no author block
  highlights.txt      the highlights as Elsevier asks for them (separate file, one per line)
  title-page.tex      the title page with the author's identity (separate file, not for reviewers)
and runs xelatex twice on both .tex files.

The CAS class files (cas-sc.cls, cas-common.sty) come from CTAN's els-cas-templates and must sit
in this directory; they are not versioned here (fetch: see README.md).

Gate (--check, also run after every build): every number that tools/provenance.py counts in
manuscript.md appears in the text of manuscript.pdf, and every such number in the PDF text appears
in manuscript.md. The conversion may move a number, never add, drop or change one.
"""
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
IPM = HERE.parent
ROOT = IPM.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from provenance import NUM, numbers  # noqa: E402  (same tokenizer as the CI gate)

MD = (IPM / "manuscript.md").read_text()


def section(md, start, end=None):
    i = md.index(start) + len(start)
    j = md.index(end, i) if end else len(md)
    return md[i:j].strip()


def pandoc(text):
    r = subprocess.run(["pandoc", "-f", "markdown-auto_identifiers+tex_math_dollars", "-t", "latex",
                        "--wrap=preserve"], input=text, capture_output=True, text=True, check=True)
    return r.stdout.replace("\\begin{longtable}[]{", "\\begin{longtable}{")


title = re.match(r"# (.+)\n", MD).group(1)
abstract = section(MD, "## Abstract\n", "## Highlights")
highlights = [l[2:].strip() for l in section(MD, "## Highlights\n", "**Keywords:**").splitlines() if l.startswith("- ")]
keywords = [k.strip() for k in re.search(r"\*\*Keywords:\*\* (.+)", MD).group(1).split(";")]
body = section(MD, "---\n", "## Declaration of generative AI")
back = "## Declaration of generative AI" + section(MD, "## Declaration of generative AI", "## References")
refs = [p.strip() for p in section(MD, "## References\n").split("\n\n") if p.strip()]

# numbered body headings: drop the typed numbers, LaTeX numbers them in the same order
body = re.sub(r"^(#{2,3}) \d+(?:\.\d+)?\.? ", r"\1 ", body, flags=re.M)
body = body.replace("\n## ", "\n# ").replace("\n### ", "\n## ")
if body.startswith("## "):
    body = "# " + body[3:]
# Figure 1: caption paragraph becomes a float
fig = re.search(r"\*\*Figure 1\.\*\* (.+?) \*\(figure file: `(.+?)`\)\*", body)
body = body.replace(fig.group(0), "FIGUREONEPLACEHOLDER")
# back matter: unnumbered, and the separator rules go
back = re.sub(r"^## (.+)$", r"# \1 {-}", back, flags=re.M).replace("\n---\n", "\n")

body_tex = pandoc(body)
figure_tex = ("\\begin{figure}[t]\n\\centering\n\\includegraphics[width=\\textwidth]{../" + fig.group(2) + "}\n"
              "\\caption{" + pandoc(fig.group(1)).strip() + "}\\label{fig1}\n\\end{figure}")
assert body_tex.count("FIGUREONEPLACEHOLDER") == 1
body_tex = body_tex.replace("FIGUREONEPLACEHOLDER", figure_tex)
back_tex = pandoc(back)
refs_tex = "\n".join("\\bibitem{} " + pandoc(r).strip() for r in refs)

PREAMBLE = r"""\PassOptionsToPackage{hyphens}{url}
\documentclass[a4paper,fleqn]{cas-sc}
\usepackage{fontspec}
\usepackage{longtable,booktabs,array,calc,graphicx}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\renewcommand{\printorcid}{}  % anonymized: no author, so no empty "ORCID(s):" line
\newcounter{none}  % pandoc tables set \LTcaptype{none}; this longtable needs the counter
\def\tsc#1{\csdef{#1}{\textsc{\lowercase{#1}}\xspace}}
\begin{document}
\let\WriteBookmarks\relax
\def\floatpagepagefraction{1}
\def\textpagefraction{.001}
"""

tex = PREAMBLE + f"""\\shorttitle{{nox-mem: a pre-specified comparison of agent memory systems}}
\\shortauthors{{Anonymous}}
\\title[mode=title]{{{pandoc(title).strip()}}}
\\begin{{abstract}}
{pandoc(abstract).strip()}
\\end{{abstract}}
\\begin{{highlights}}
{chr(10).join("\\item " + pandoc(h).strip() for h in highlights)}
\\end{{highlights}}
\\begin{{keywords}}
{" \\sep ".join(keywords)}
\\end{{keywords}}
\\maketitle

{body_tex}
{back_tex}
\\section*{{References}}
\\begin{{thebibliography}}{{99}}
\\setlength{{\\itemsep}}{{2pt}}
{refs_tex}
\\end{{thebibliography}}
\\end{{document}}
"""
(HERE / "manuscript.tex").write_text(tex)
(HERE / "highlights.txt").write_text("\n".join(highlights) + "\n")

tp = (IPM / "title-page.md").read_text()
tp_tex = ("\\documentclass[a4paper,11pt]{article}\n\\usepackage{fontspec}\n\\usepackage[margin=25mm]{geometry}\n"
          "\\usepackage[hyphens]{url}\n\\usepackage{hyperref}\n"
          "\\providecommand{\\tightlist}{\\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}\n"
          "\\begin{document}\n" + pandoc(tp) + "\n\\end{document}\n")
(HERE / "title-page.tex").write_text(tp_tex)


def xelatex(name):
    for _ in range(2):
        r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", name], cwd=HERE,
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"xelatex {name} failed:\n" + r.stdout[-3000:])


if "--no-build" not in sys.argv:
    xelatex("manuscript.tex")
    xelatex("title-page.tex")

# gate: the PDF carries exactly the manuscript's numbers
pdf_text = subprocess.run(["pdftotext", "-layout", str(HERE / "manuscript.pdf"), "-"], capture_output=True,
                          text=True, check=True).stdout
pdf_text = pdf_text.replace("\u2212", "-").replace("\ufb01", "fi").replace("\ufb02", "fl")
md_nums = numbers(MD)
pdf_nums = numbers(re.sub(r"-\n\s*", "", pdf_text))
missing = sorted(md_nums - pdf_nums)
# inline code (versions, identifiers) is not counted in the Markdown; the PDF prints it as text
code_nums = {m.group(0).lstrip("−+-") for c in re.findall(r"`([^`]*)`", MD) for m in NUM.finditer(c)}
extra = sorted(pdf_nums - md_nums - code_nums)
print(f"numbers: manuscript.md {len(md_nums)}, manuscript.pdf {len(pdf_nums)}")
if missing:
    print("in manuscript.md but not in the PDF:", missing)
if extra:
    print("in the PDF but not in manuscript.md:", extra)
sys.exit(1 if (missing or extra) else 0)
