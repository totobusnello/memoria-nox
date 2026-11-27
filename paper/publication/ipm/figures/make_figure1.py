#!/usr/bin/env python3
"""Draw Figure 1 of the IP&M manuscript (system architecture) as SVG, then PDF and PNG.

Every label states something Section 3 of manuscript.md states; nothing here is a
measurement. No agent names, hosts or counts that identify a deployment.

    python3 -I make_figure1.py          # writes figure1.svg, figure1.pdf, figure1.png
PDF and PNG are printed by headless Chrome (vector PDF); set CHROME to override its path.
"""
import os
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
W, H = 1024, 560
INK, MUTED, LINE, FILL, STORE, ACC = "#1b1f23", "#555b61", "#3a4046", "#f3f4f5", "#e6eef0", "#1f5f66"
FONT = "Helvetica, Arial, sans-serif"

parts = []


def box(x, y, w, h, title, lines=(), fill=FILL, stroke=LINE, dash=False, title_size=13):
    d = ' stroke-dasharray="5 4"' if dash else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.2"{d}/>')
    parts.append(f'<text x="{x + 10}" y="{y + 19}" font-size="{title_size}" font-weight="700" fill="{INK}">{title}</text>')
    for i, ln in enumerate(lines):
        parts.append(f'<text x="{x + 10}" y="{y + 37 + 15 * i}" font-size="11" fill="{MUTED}">{ln}</text>')


def arrow(x1, y1, x2, y2, label=None, lx=None, ly=None, color=LINE, dash=False):
    d = ' stroke-dasharray="5 4"' if dash else ""
    parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.4" marker-end="url(#a)"{d}/>')
    if label:
        parts.append(f'<text x="{lx if lx is not None else (x1 + x2) / 2 + 4}" y="{ly if ly is not None else (y1 + y2) / 2 - 4}" font-size="10.5" fill="{MUTED}" font-style="italic">{label}</text>')


def poly(points, color=LINE, dash=False):
    d = ' stroke-dasharray="5 4"' if dash else ""
    pts = " ".join(f"{x},{y}" for x, y in points)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4" marker-end="url(#a)"{d}/>')


# --- ingestion (left column) ---
box(20, 20, 210, 58, "Markdown and text files", ["notes, decisions, entity files"])
box(20, 112, 210, 74, "Watcher and ingestion", ["re-ingest 2 s after last write", "split by heading; type sets", "retention; entity sections"])
box(20, 222, 210, 58, "Nightly LLM extraction", ["daily notes → topic files"], dash=True)
arrow(125, 78, 125, 110)
poly([(230, 251), (250, 251), (250, 49), (232, 49)], dash=True)

# --- store (centre) ---
box(280, 20, 300, 340, "One SQLite file (WAL mode)", [], fill=STORE, stroke=ACC, title_size=14)
box(295, 50, 270, 76, "Chunks", ["text, source file, type, dates,", "pain, retention window, section,", "importance, access count"], fill="#ffffff")
box(295, 136, 270, 44, "Lexical index (FTS5)", ["BM25; accent folding, no stemming"], fill="#ffffff")
box(295, 190, 270, 44, "Vector index (sqlite-vec)", ["3072-d embeddings; exact search"], fill="#ffffff")
box(295, 244, 270, 60, "Knowledge graph", ["entities, typed relations with", "decaying confidence, evidence chunk"], fill="#ffffff")
box(295, 314, 270, 36, "Audit table + pre-operation snapshot", [], fill="#ffffff", title_size=11.5)
arrow(230, 150, 278, 150)

# --- retrieval (right column) ---
box(640, 20, 340, 40, "Query", [])
box(640, 84, 160, 76, "Lexical layer", ["BM25 over the FTS5 index", "(text, path, type)", "boosts summed (Σδ)"])
box(820, 84, 160, 76, "Dense layer", ["exact L2 search over", "the sqlite-vec index", "boosts summed (Σδ)"])
box(640, 186, 340, 44, "Reciprocal Rank Fusion (k = 60)", ["ranked chunks, each with chunk id and source file"])
box(640, 252, 340, 58, "Salience delta, bounded to [−0.5, +0.5]", ["0.55 importance + 0.15 recency + 0.10 pain + 0.20 access",
                                                               ], fill="#ffffff", stroke=ACC)
parts.append(f'<text x="650" y="302" font-size="10.5" fill="{ACC}">shadow: logged only · active: added to both layers’ boosts</text>')
arrow(720, 60, 720, 82)
arrow(900, 60, 900, 82)
arrow(720, 160, 720, 184)
arrow(900, 160, 900, 184)
poly([(980, 281), (992, 281), (992, 122), (982, 122)], color=ACC, dash=True)
poly([(640, 281), (628, 281), (628, 142), (638, 142)], color=ACC, dash=True)
# store feeds both layers
arrow(580, 104, 638, 104, "reads", 588, 98)

# --- side paths (bottom) ---
box(280, 400, 300, 58, "Knowledge-graph path", ["entity queries: SQL and regular", "expressions over relations; no model call"])
box(640, 400, 340, 58, "Session brief (read-only)", ["top chunks by salience within a scope;", "does not update access counts"])
arrow(430, 360, 430, 398)
poly([(530, 360), (530, 380), (810, 380), (810, 398)])

# --- interfaces ---
box(20, 500, 960, 52, "Interfaces: command line · HTTP API · Model Context Protocol server", [
    "search (hybrid) · answer (8 chunks, inline citations, one retry if a citation falls outside them) · temporal filter (--as-of, --changed-since) as an SQL pre-filter"])
arrow(430, 458, 430, 498)
poly([(980, 208), (1010, 208), (1010, 526), (982, 526)])
parts.append(f'<text x="1004" y="470" font-size="10.5" fill="{MUTED}" font-style="italic" transform="rotate(-90 1004 470)">search results</text>')
arrow(810, 458, 810, 498)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>
<rect width="{W}" height="{H}" fill="#ffffff"/>
{chr(10).join(parts)}
</svg>
'''
(HERE / "figure1.svg").write_text(svg)

chrome = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
with tempfile.TemporaryDirectory() as td:
    page = pathlib.Path(td) / "f.html"
    page.write_text(f'<!doctype html><html><head><style>@page{{size:{W}px {H}px;margin:0}}html,body{{margin:0}}</style></head><body>{svg}</body></html>')
    common = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={td}/p"]
    subprocess.run(common + ["--no-pdf-header-footer", f"--print-to-pdf={HERE / 'figure1.pdf'}", page.as_uri()],
                   check=True, capture_output=True, timeout=120)
    subprocess.run(common + [f"--window-size={W},{H}", "--force-device-scale-factor=2", f"--screenshot={HERE / 'figure1.png'}", page.as_uri()],
                   check=True, capture_output=True, timeout=120)
print("wrote figure1.svg, figure1.pdf, figure1.png")
