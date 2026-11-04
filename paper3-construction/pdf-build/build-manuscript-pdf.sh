#!/usr/bin/env bash
# Builds the manuscript PDF from ../MANUSCRIPT.md with the preamble and title block of the
# pre-registration PDF (build-pdf.sh). It builds from a COPY: table-widths.py --apply rewrites
# the table separator rows, and the source markdown stays as written.
#
#   MANUSCRIPT_MD=<path>     build from that file (the deposit copy, written by
#                             deposit/deposit-manuscript.py --build).
#   MANUSCRIPT_LINE="<text>"  date line under the title (default: working draft, not deposited).
#                             When a DOI is reserved, put it here; there is no DOI gate yet,
#                             because the manuscript has none.
#
# Gates: 0 "Missing character" in the xelatex log; no heading stranded at a page foot
# (check-layout.py, exit 1).
set -euo pipefail
cd "$(dirname "$0")"
NAME=MANUSCRIPT
LINE="${MANUSCRIPT_LINE:-Working draft, not deposited, not peer reviewed}"
cp "${MANUSCRIPT_MD:-../MANUSCRIPT.md}" manuscript-build.md
python3 -I table-widths.py manuscript-build.md --apply
pandoc manuscript-build.md --from=markdown+smart --standalone --to=latex \
  --resource-path=.. \
  --shift-heading-level-by=-1 \
  -M date="$LINE" \
  -V documentclass=article -V fontsize=10pt -V colorlinks=true \
  --include-in-header=preamble-prereg.tex -o $NAME.tex
# The preamble's \needspace runs INSIDE longtable (AtBeginEnvironment). When it breaks the page
# there, longtable has already set its head, and the table opens the next page with the head
# twice (seen on the §5 table). Asking for the same space just BEFORE the environment moves the
# break outside it, and the inner \needspace then finds the room and does nothing.
python3 -I - "$NAME.tex" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
n = t.count("\\begin{longtable}")
p.write_text(t.replace("\\begin{longtable}", "\\needspace{10\\baselineskip}\\begin{longtable}"), encoding="utf-8")
print(f"needspace before {n} longtables")
PY
for i in 1 2; do
  xelatex -interaction=nonstopmode -halt-on-error $NAME.tex > "pass$i.log" 2>&1 \
    || { grep -E '^! ' $NAME.log | head; exit 1; }
done
miss=$(grep -c "Missing character" $NAME.log || true)
echo "missing glyphs: $miss"
[ "$miss" = "0" ] || { grep "Missing character" $NAME.log | sort | uniq -c; exit 1; }
python3 -I check-layout.py $NAME.pdf manuscript-build.md
pdfinfo $NAME.pdf | grep -E '^Pages'
echo "ok: $(pwd)/$NAME.pdf"
