#!/usr/bin/env bash
# Builds ../DATA-NOTE.pdf from ../DATA-NOTE.md (pandoc -> LaTeX -> xelatex x2), with the
# layout of the deposited papers (Paper A v1.1, Paper B v2.0): same preamble, same title block.
#   - DOI line: DATANOTE_DOI=10.5281/zenodo.NNNN once the record is reserved; without it the
#     date line says "draft".
# Gates: 0 "Missing character" in the xelatex log; Figure 1 included; else exit 1.
set -euo pipefail
cd "$(dirname "$0")"
NAME=DATA-NOTE
VER="Version 1.0"
if [ -n "${DATANOTE_DOI:-}" ]; then DATE="$VER · doi:${DATANOTE_DOI}"; else DATE="$VER · draft rc2, 2026-10-13"; fi
pandoc ../$NAME.md --from=markdown+smart --standalone --to=latex \
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
cp $NAME.pdf ../$NAME.pdf
pdfinfo ../$NAME.pdf | grep -E '^Pages'
echo "ok: ../$NAME.pdf"
