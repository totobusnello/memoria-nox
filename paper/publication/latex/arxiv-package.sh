#!/usr/bin/env bash
# arxiv-package.sh — package the nox-mem paper for arXiv submission
#
# Usage:
#   ./arxiv-package.sh [output-name.tar.gz]
#
# Output: <output-name.tar.gz> in the latex/ directory, ready to upload at
#         https://arxiv.org/submit
#
# Layout packed:
#   arxiv-pkg/
#     main.tex
#     sec_abstract.tex   (\input from main.tex)
#     sec_1_3.tex        (\input from main.tex)
#     sec_4_7.tex        (\input from main.tex)
#     neurips_2024.sty
#     refs.bib
#     figures/
#       figure1.pdf  (figure1-system-overview.pdf alias)
#       figure2.pdf  (figure2-salience-pipeline.pdf alias)
#       figure3.pdf  (figure3-shadow-state-machine.pdf alias)
#       figure4.pdf  (figure4-kg-edge-typing.pdf alias)
#
# Excluded: .aux .log .out .toc .bbl .blg .DS_Store .git symlinks README.md
# arXiv limit: 50 MB hard; typical output here is ~400 KB.

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="${1:-arxiv-submission.tar.gz}"

# Absolute output path — always land in latex/ regardless of cwd
OUTPUT_PATH="$SCRIPT_DIR/$OUTPUT"

# Staging dir in a temp parent so trap cleanup is a simple rm -rf of one dir
TMPPARENT="$(mktemp -d)"
STAGING="$TMPPARENT/arxiv-pkg"

trap 'rm -rf "$TMPPARENT"' EXIT

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
echo "=== Pre-flight checks ==="

PREFLIGHT_FAIL=0

check_file() {
    local label="$1" path="$2"
    if [ -f "$path" ]; then
        printf "  [OK]  %s\n" "$label"
    else
        printf "  [MISSING] %s — expected at %s\n" "$label" "$path"
        PREFLIGHT_FAIL=1
    fi
}

check_file "main.tex"           "$SCRIPT_DIR/main.tex"
check_file "sec_abstract.tex"   "$SCRIPT_DIR/sec_abstract.tex"
check_file "sec_1_3.tex"        "$SCRIPT_DIR/sec_1_3.tex"
check_file "sec_4_7.tex"        "$SCRIPT_DIR/sec_4_7.tex"
check_file "neurips_2024.sty"   "$SCRIPT_DIR/neurips_2024.sty"
check_file "refs.bib"           "$SCRIPT_DIR/../refs.bib"
check_file "figures/figure1.pdf" "$SCRIPT_DIR/figures/figure1.pdf"
check_file "figures/figure2.pdf" "$SCRIPT_DIR/figures/figure2.pdf"
check_file "figures/figure3.pdf" "$SCRIPT_DIR/figures/figure3.pdf"
check_file "figures/figure4.pdf" "$SCRIPT_DIR/figures/figure4.pdf"

# Detect figure size anomalies (< 5 KB usually means a stub or corrupt file)
for i in 1 2 3 4; do
    fig="$SCRIPT_DIR/figures/figure$i.pdf"
    if [ -f "$fig" ]; then
        size=$(wc -c < "$fig")
        if [ "$size" -lt 5120 ]; then
            printf "  [WARN] figures/figure%d.pdf is only %d bytes — may be a stub\n" "$i" "$size"
        fi
    fi
done

if [ "$PREFLIGHT_FAIL" -eq 1 ]; then
    echo ""
    echo "ERROR: Required files are missing. Aborting."
    echo "       Run 'make' in $SCRIPT_DIR to build first, or check figures/README.md."
    exit 1
fi
echo ""

# ---------------------------------------------------------------------------
# Assemble staging directory
# ---------------------------------------------------------------------------
echo "=== Assembling package ==="

mkdir -p "$STAGING/figures"

# Core source files
cp "$SCRIPT_DIR/main.tex"                    "$STAGING/main.tex"
cp "$SCRIPT_DIR/sec_abstract.tex"            "$STAGING/sec_abstract.tex"
cp "$SCRIPT_DIR/sec_1_3.tex"                 "$STAGING/sec_1_3.tex"
cp "$SCRIPT_DIR/sec_4_7.tex"                 "$STAGING/sec_4_7.tex"
cp "$SCRIPT_DIR/neurips_2024.sty"            "$STAGING/neurips_2024.sty"
cp "$SCRIPT_DIR/../refs.bib"                 "$STAGING/refs.bib"

# Fix bibliography path: in the source tree, refs.bib lives at paper/publication/refs.bib
# while .tex files are at paper/publication/latex/, so main.tex uses \bibliography{../refs}.
# In the arXiv tarball everything is at the root of arxiv-pkg/, so the path must become
# \bibliography{refs}. Patch on-the-fly without touching the source file.
sed -i.bak 's|\\bibliography{\.\./refs}|\\bibliography{refs}|g' "$STAGING/main.tex"
rm -f "$STAGING/main.tex.bak"

# Figures — copy real files (resolve symlinks with cp -L so tar gets actual data)
for i in 1 2 3 4; do
    cp -L "$SCRIPT_DIR/figures/figure$i.pdf" "$STAGING/figures/figure$i.pdf"
done

# Also copy the long-name symlink targets as real files, because main.tex
# references them by the descriptive names (figure1-system-overview.pdf etc.)
# bash 3.2 (macOS default) lacks declare -A, so use a function instead.
_figname() {
    case "$1" in
        1) printf '%s' "figure1-system-overview.pdf" ;;
        2) printf '%s' "figure2-salience-pipeline.pdf" ;;
        3) printf '%s' "figure3-shadow-state-machine.pdf" ;;
        4) printf '%s' "figure4-kg-edge-typing.pdf" ;;
    esac
}
for i in 1 2 3 4; do
    cp "$STAGING/figures/figure$i.pdf" "$STAGING/figures/$(_figname "$i")"
done

echo "  Copied: main.tex, sec_abstract.tex, sec_1_3.tex, sec_4_7.tex, neurips_2024.sty, refs.bib"
echo "  Copied: figures/figure{1-4}.pdf + descriptive-name copies"
echo ""

# ---------------------------------------------------------------------------
# Validation — nothing forbidden should be present
# ---------------------------------------------------------------------------
echo "=== Package contents ==="
ls -lh "$STAGING/"
echo ""
ls -lh "$STAGING/figures/"
echo ""

# Sanity: no build artifacts crept in
FORBIDDEN=$(find "$STAGING" -name "*.aux" -o -name "*.log" -o -name "*.bbl" \
                             -o -name "*.blg" -o -name "*.out" -o -name "*.toc" \
                             -o -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
if [ "$FORBIDDEN" -gt 0 ]; then
    echo "ERROR: Forbidden build artifacts found in staging. This is a script bug."
    find "$STAGING" -name "*.aux" -o -name "*.log" -o -name "*.bbl" \
                    -o -name "*.blg" -o -name "*.out" -o -name "*.toc" \
                    -o -name ".DS_Store" 2>/dev/null
    exit 1
fi

TOTAL_UNCOMPRESSED="$(du -sh "$STAGING" | cut -f1)"
echo "Total uncompressed size : $TOTAL_UNCOMPRESSED"

FILE_COUNT="$(find "$STAGING" -type f | wc -l | tr -d ' ')"
echo "Total files             : $FILE_COUNT"
echo ""

# ---------------------------------------------------------------------------
# Create archive
# ---------------------------------------------------------------------------
echo "=== Creating archive ==="

# cd to temp parent so tar root is "arxiv-pkg/" — arXiv expects a single
# top-level directory inside the tarball, not loose files at root.
cd "$TMPPARENT"
tar -czf "$OUTPUT_PATH" "arxiv-pkg/"

ARCHIVE_SIZE="$(ls -lh "$OUTPUT_PATH" | awk '{print $5}')"
echo "Archive : $OUTPUT_PATH"
echo "Size    : $ARCHIVE_SIZE"
echo ""

# Sanity check against arXiv 50 MB hard limit
ARCHIVE_BYTES="$(wc -c < "$OUTPUT_PATH")"
LIMIT_BYTES=$((50 * 1024 * 1024))
if [ "$ARCHIVE_BYTES" -gt "$LIMIT_BYTES" ]; then
    echo "ERROR: Archive exceeds arXiv 50 MB hard limit. Remove large files and retry."
    exit 1
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo "Package ready. Next steps:"
echo "  1. Verify: tar -tzf '$OUTPUT_PATH'"
echo "  2. Upload: https://arxiv.org/submit"
echo "  3. See: $(dirname "$OUTPUT_PATH")/arxiv-submit-runbook.md"
