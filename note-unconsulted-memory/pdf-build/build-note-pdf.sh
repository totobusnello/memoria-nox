#!/usr/bin/env bash
# Builds the data note PDF (the memory the agent does not consult) from ../NOTE.md with the preamble, table-width pass and
# layout check of Paper 3 (paper3-construction/pdf-build), read from there so the two papers
# typeset the same way. It builds from a COPY: table-widths.py --apply rewrites the table
# separator rows, and the source markdown stays as written.
#
#   NOTE_MD=<path>     build from that file (a deposit copy).
#   NOTE_LINE="<text>"  date line under the title (default: working draft, not deposited).
#
# Gates, in order: the provenance gate on the source (a PDF is never
# built from a text whose numbers fail); 0 "Missing character" in the xelatex log; no heading
# stranded at a page foot (check-layout.py, exit 1).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(git rev-parse --show-toplevel)"
P3="$ROOT/paper3-construction/pdf-build"
NAME=NOTE
LINE="${NOTE_LINE:-Working draft, not deposited, not peer reviewed}"
(cd "$ROOT" && python3 -I tools/provenance.py --check note-unconsulted-memory)
cp "${NOTE_MD:-../NOTE.md}" manuscript-build.md
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
t = t.replace("\\begin{longtable}", "\\needspace{10\\baselineskip}\\begin{longtable}")
# a heading set right before a table must travel with it: when only blank lines and pandoc's
# caption group sit between them, ask for the space before the HEADING, or the table moves to the
# next page and leaves the heading at the foot of this one (seen 2026-11-20 on "What ran, in order")
import re
t, m = re.subn(r"(\\(?:sub)*section\{[^\n]*\}\\label\{[^}]*\}\n\n\{\\def\\LTcaptype\{none\} % do not increment counter\n)\\needspace\{10\\baselineskip\}",
               lambda x: "\\needspace{14\\baselineskip}" + x.group(1), t)
p.write_text(t, encoding="utf-8")
print(f"needspace before {n} longtables, {m} moved before their heading")
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
