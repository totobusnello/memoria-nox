#!/usr/bin/env bash
# Builds the pre-registration PDF from ../PREREGISTRATION-DRAFT.md
# (pandoc -> LaTeX -> xelatex x2), with the layout of the deposited papers
# (Paper A v1.1, Paper B v2.0, the data note v1.0): same preamble, same title block.
#
#   - DOI line: PREREG_DOI must be set — unlike the data note's script there is no
#     default, because a pre-registration with the wrong DOI in its own PDF is worse
#     than one that fails to build.
#   - PREREG_MD=<path>: build from that file (the deposit copy, written by
#     deposit/deposit.py --build); the PDF then stays in pdf-build/.
#
# Gates: 0 "Missing character" in the xelatex log, and the DOI present in the
# extracted text. No figure gate — this document has no figures.
set -euo pipefail
cd "$(dirname "$0")"
NAME=PREREGISTRATION
VER="${PREREG_VER:-Version 1.0}"
: "${PREREG_DOI:?set PREREG_DOI (the reserved DOI); this script has no default on purpose}"
DATE="$VER · doi:${PREREG_DOI}"
SRC="${PREREG_MD:-../PREREGISTRATION-DRAFT.md}"
pandoc "$SRC" --from=markdown+smart --standalone --to=latex \
  --resource-path=.. \
  --shift-heading-level-by=-1 \
  -M author="Luiz Antonio Busnello" \
  -M date="$DATE" \
  -V documentclass=article -V fontsize=10pt -V colorlinks=true \
  --include-in-header=preamble-prereg.tex -o $NAME.tex
for i in 1 2; do
  xelatex -interaction=nonstopmode -halt-on-error $NAME.tex > "pass$i.log" 2>&1 \
    || { grep -E '^! ' $NAME.log | head; exit 1; }
done
miss=$(grep -c "Missing character" $NAME.log || true)
echo "missing glyphs: $miss"
[ "$miss" = "0" ] || { grep "Missing character" $NAME.log | sort | uniq -c; exit 1; }
# NOT a pipe into `grep -q`: under `set -o pipefail`, grep -q exits as soon as it
# matches, pdftotext takes SIGPIPE, and the pipeline then FAILS precisely when the
# grep succeeded. Capture first, test second. (Third time this class bit today,
# after `node --test | grep` and `python | tail`.)
PDFTXT="$(pdftotext -enc UTF-8 $NAME.pdf -)"
case "$PDFTXT" in
  *"$PREREG_DOI"*) : ;;
  *) echo "the DOI is not in the extracted text"; exit 1 ;;
esac
pdfinfo $NAME.pdf | grep -E '^Pages'
echo "ok: $(pwd)/$NAME.pdf"
