#!/bin/bash
# Compile cycle for nox-mem paper
set -e
export PATH=$PATH:/Users/lab/Library/TinyTeX/bin/universal-darwin
cd /Users/lab/Claude/Projetos/memoria-nox/paper/publication/latex

echo "=== Pass 1: pdflatex ==="
pdflatex -interaction=nonstopmode main.tex 2>&1 | tail -20

echo "=== bibtex ==="
bibtex main 2>&1 | tail -10

echo "=== Pass 2: pdflatex ==="
pdflatex -interaction=nonstopmode main.tex 2>&1 | tail -5

echo "=== Pass 3: pdflatex (final) ==="
pdflatex -interaction=nonstopmode main.tex 2>&1 | tail -10

echo "=== Summary ==="
grep -E "^(Output written|! |Error|Warning|Overfull)" main.log | head -30

echo "=== Overfull hbox count ==="
grep -c "Overfull" main.log || echo "0 overfull"

echo "=== Pages and size ==="
pdfinfo main.pdf 2>/dev/null | grep -E "Pages:|File size:" || ls -lh main.pdf
