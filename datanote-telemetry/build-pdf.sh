#!/bin/sh
# Build DATA-NOTE.pdf from DATA-NOTE.md (pandoc + xelatex). Run from this folder.
set -e
pandoc DATA-NOTE.md -o DATA-NOTE.pdf \
  --pdf-engine=xelatex --shift-heading-level-by=-1 \
  -V geometry:margin=2.4cm -V fontsize=11pt \
  -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  -V header-includes='\usepackage{float}\floatplacement{figure}{H}\usepackage{needspace}\usepackage{etoolbox}\AtBeginEnvironment{longtable}{\needspace{12\baselineskip}}' -V geometry:top=2.2cm,bottom=2.4cm
