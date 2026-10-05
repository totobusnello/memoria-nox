#!/usr/bin/env bash
# Builds spare-capacity-narrow-surface-v1.1.pdf from ../spare-capacity-narrow-surface-v1.1.md (pandoc -> LaTeX -> xelatex x2).
# Gate: 0 "Missing character" in the xelatex log, else exit 1.
set -euo pipefail
cd "$(dirname "$0")"
pandoc ../spare-capacity-narrow-surface-v1.1.md --from=markdown+smart --standalone --to=latex \
  --shift-heading-level-by=-1 \
  -M author="Luiz Antonio Busnello (ORCID 0009-0007-5911-8141)" \
  -M date="Version 1.1, 2026-10-05 · doi:10.5281/zenodo.23163119" \
  -V documentclass=article -V fontsize=10pt -V colorlinks=true \
  --include-in-header=preamble-paperA-v1.1.tex -o spare-capacity-narrow-surface-v1.1.tex
# soul.sty is not in this TeX Live basic install; strikeout via ulem instead.
python3 - <<'PY'
p = "spare-capacity-narrow-surface-v1.1.tex"
t = open(p, encoding="utf-8").read()
assert t.count("\\usepackage{soul}") == 1
t = t.replace("\\usepackage{soul}", "\\usepackage[normalem]{ulem}\\let\\st\\sout")
open(p, "w", encoding="utf-8").write(t)
PY
for i in 1 2; do xelatex -interaction=nonstopmode -halt-on-error spare-capacity-narrow-surface-v1.1.tex > "pass$i.log" 2>&1 || { grep -E '^! ' spare-capacity-narrow-surface-v1.1.log | head; exit 1; }; done
miss=$(grep -c "Missing character" spare-capacity-narrow-surface-v1.1.log || true)
echo "missing glyphs: $miss"
[ "$miss" = "0" ] || { grep "Missing character" spare-capacity-narrow-surface-v1.1.log | sort | uniq -c; exit 1; }
cp spare-capacity-narrow-surface-v1.1.pdf ../spare-capacity-narrow-surface-v1.1.pdf
echo "ok: ../spare-capacity-narrow-surface-v1.1.pdf"
