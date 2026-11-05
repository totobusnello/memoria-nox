#!/usr/bin/env bash
# Builds the Paper A manuscript PDF from ../MANUSCRIPT.md with the preamble, table-width pass and
# layout check of Paper 3 (paper3-construction/pdf-build), read from there so the two papers
# typeset the same way. It builds from a COPY: table-widths.py --apply rewrites the table
# separator rows, and the source markdown stays as written.
#
#   MANUSCRIPT_MD=<path>     build from that file (a deposit copy).
#   MANUSCRIPT_LINE="<text>"  date line under the title (default: working draft, not deposited).
#
# Gates, in order: the provenance gate and the table-parity gate on the source (a PDF is never
# built from a text whose numbers fail); 0 "Missing character" in the xelatex log; no heading
# stranded at a page foot (check-layout.py, exit 1).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(git rev-parse --show-toplevel)"
P3="$ROOT/paper3-construction/pdf-build"
NAME=MANUSCRIPT
LINE="${MANUSCRIPT_LINE:-Working draft, not deposited, not peer reviewed}"
(cd "$ROOT" && python3 -I tools/provenance.py --check paper-a-eval-ptbr \
   && python3 -I paper-a-eval-ptbr/manuscript-tables.py --check)
cp "${MANUSCRIPT_MD:-../MANUSCRIPT.md}" manuscript-build.md
python3 -I "$P3/table-widths.py" manuscript-build.md --apply
pandoc manuscript-build.md --from=markdown+smart --standalone --to=latex \
  --resource-path=.. \
  --shift-heading-level-by=-1 \
  -M date="$LINE" \
  -V documentclass=article -V fontsize=10pt -V colorlinks=true \
  --include-in-header="$P3/preamble-prereg.tex" -o $NAME.tex
# same longtable fix as Paper 3: ask for the space BEFORE the environment, so a page break does
# not land inside it after the head is set
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
python3 -I "$P3/check-layout.py" $NAME.pdf manuscript-build.md
pdfinfo $NAME.pdf | grep -E '^Pages'
echo "ok: $(pwd)/$NAME.pdf"
