# Makefile — nox-mem paper (arXiv-ready)
# Usage:
#   make          — full build → paper.pdf
#   make draft    — single pdflatex pass (no bibliography, fast preview)
#   make clean    — remove auxiliary files
#   make distclean — remove all generated files including paper.pdf

MAIN    = main
OUTPUT  = paper.pdf
LATEX   = pdflatex
BIBTEX  = bibtex
LATEXFLAGS = -interaction=nonstopmode -halt-on-error

.PHONY: all draft clean distclean figures

all: $(OUTPUT)

$(OUTPUT): $(MAIN).tex ../refs.bib figures
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	$(BIBTEX) $(MAIN)
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	mv $(MAIN).pdf $(OUTPUT)

# Single-pass draft — skips bibliography resolution, fast for prose review
draft: $(MAIN).tex
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex

# Check that all four figure PDFs exist before attempting a full build
figures:
	@missing=0; \
	for f in \
	  figures/figure1-system-overview.pdf \
	  figures/figure2-salience-pipeline.pdf \
	  figures/figure3-shadow-state-machine.pdf \
	  figures/figure4-kg-edge-typing.pdf; do \
	  if [ ! -f "$$f" ]; then \
	    echo "MISSING figure: $$f  (see figures/README.md for generation instructions)"; \
	    missing=1; \
	  fi; \
	done; \
	if [ $$missing -eq 1 ]; then \
	  echo ""; \
	  echo "Run 'make figures-stub' to insert placeholder boxes and build anyway."; \
	  exit 1; \
	fi

# Build with placeholder boxes instead of real figures (draft review only)
figures-stub:
	@for f in \
	  figures/figure1-system-overview.pdf \
	  figures/figure2-salience-pipeline.pdf \
	  figures/figure3-shadow-state-machine.pdf \
	  figures/figure4-kg-edge-typing.pdf; do \
	  if [ ! -f "$$f" ]; then \
	    echo "Creating stub for $$f"; \
	    mkdir -p figures; \
	    printf '%s\n' \
	      '\documentclass{standalone}' \
	      '\usepackage{graphicx}' \
	      '\begin{document}' \
	      '\fbox{\parbox{10cm}{\centering\vspace{2cm}[FIGURE PLACEHOLDER]\vspace{2cm}}}' \
	      '\end{document}' > /tmp/stub.tex; \
	    pdflatex -interaction=nonstopmode -output-directory=figures /tmp/stub.tex 2>/dev/null; \
	    mv figures/stub.pdf "$$f" 2>/dev/null || true; \
	  fi; \
	done

stub: figures-stub
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	$(BIBTEX) $(MAIN)
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	$(LATEX) $(LATEXFLAGS) $(MAIN).tex
	mv $(MAIN).pdf $(OUTPUT)

clean:
	rm -f $(MAIN).aux $(MAIN).log $(MAIN).bbl $(MAIN).blg \
	       $(MAIN).out $(MAIN).toc $(MAIN).fls $(MAIN).fdb_latexmk \
	       /tmp/stub.tex /tmp/stub.aux /tmp/stub.log

distclean: clean
	rm -f $(OUTPUT)
