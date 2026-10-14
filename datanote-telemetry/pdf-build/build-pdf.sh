#!/usr/bin/env bash
# Builds ../DATA-NOTE.pdf from ../DATA-NOTE.md (pandoc -> LaTeX -> xelatex x2), with the
# layout of the deposited papers (Paper A v1.1, Paper B v2.0): same preamble, same title block.
#   - DOI line: the DOI reserved for v1.0; DATANOTE_DOI overrides it.
#   - DATANOTE_MD=<path>: build from that file (the deposit copy, ../deposit/deposit.py --build);
#     the PDF then stays in pdf-build/ and ../DATA-NOTE.pdf is not touched.
# Gates: 0 "Missing character" in the xelatex log; Figure 1 included; else exit 1.
set -euo pipefail
cd "$(dirname "$0")"
NAME=DATA-NOTE
VER="Version 1.0"
DOI="${DATANOTE_DOI:-10.5281/zenodo.23354363}"  # reserved for the Zenodo record of v1.0
DATE="$VER · doi:${DOI}"
SRC="${DATANOTE_MD:-../$NAME.md}"
pandoc "$SRC" --from=markdown+smart --standalone --to=latex \
  --resource-path=.. \
  --shift-heading-level-by=-1 \
  -M author="Luiz Antonio Busnello" \
  -M date="$DATE" \
  -V documentclass=article -V fontsize=10pt -V colorlinks=true \
  --include-in-header=preamble-datanote.tex -o $NAME.tex
for i in 1 2; do xelatex -interaction=nonstopmode -halt-on-error $NAME.tex > "pass$i.log" 2>&1 || { grep -E '^! ' $NAME.log | head; exit 1; }; done
miss=$(grep -c "Missing character" $NAME.log || true)
echo "missing glyphs: $miss"
[ "$miss" = "0" ] || { grep "Missing character" $NAME.log | sort | uniq -c; exit 1; }
inc=$(grep -c "figure1\.pdf" $NAME.log || true)
[ "$inc" -ge 1 ] || { echo "Figure 1 not included in the PDF"; exit 1; }
if [ -z "${DATANOTE_MD:-}" ]; then cp $NAME.pdf ../$NAME.pdf; fi
pdfinfo $NAME.pdf | grep -E '^Pages'
echo "ok: $(pwd)/$NAME.pdf"
