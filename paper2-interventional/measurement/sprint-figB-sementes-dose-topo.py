#!/usr/bin/env python3
"""
sprint-figB-sementes-dose-topo.py — Paper B, figure for §4.7: how many of the 20 realized
epochs draw the top dose (w = 7.5), over the 2 000 re-drawn designs of the locked artifact.

Plots ONLY what `ITEM7-DOSE-TOPO-2026-09-21.json` holds (the distribution of n over the
seeds, conditioned on the realized dates). Nothing is re-simulated here: the seed recipe of
that run is not recorded in the artifact, so a re-simulation would be a second
measurement, not this one (see `sprint-figB-item7-crosscheck.py` for that, kept separate).

⚠️ GUARDS — abort instead of drawing if any of these fails:
  - the histogram does not sum to `sementes`;
  - `P_n_eq_1`, `P_n_le_1`, `moda`, `media_condicional` do not follow from the histogram
    (to the 4 decimals the artifact keeps). The summary fields and the histogram are two
    copies of one measurement; a figure drawn from one while the text quotes the other
    must not be allowed to diverge silently;
  - `esperado_desenho` ≠ K × (top-dose epochs / all epochs) of the design, where the
    design counts come from `assign_arms.py` itself, not typed here;
  - `deficit_truncamento + deficit_sorteio` ≠ realized − expected;
  - the realized count disagrees with ASSIGNMENT-SERVING.json over the window.

Usage:
  ./sprint-figB-sementes-dose-topo.py \
      --item7 ~/Backups/paper2-ensaio-2026-09-21/ITEM7-DOSE-TOPO-2026-09-21.json \
      --assignment ASSIGNMENT-SERVING.json \
      --out _sprint-2026-10-04/figures/figB2-sementes-dose-topo.svg --png
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from assign_arms import build_epochs, assign  # noqa: E402

JANELA_INI, JANELA_FIM = "2026-09-01", "2026-09-20"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TOPO = 7.5


def render_png(svg: Path, w: int, h: int) -> Path:
    png = svg.with_suffix(".png")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=2", f"--window-size={w},{h}",
         "--default-background-color=ffffffff", f"--screenshot={png}",
         svg.resolve().as_uri()],
        check=True, capture_output=True, timeout=90)
    return png


def m(v: float) -> str:
    """number with a typographic minus"""
    return f"{v}".replace("-", "−")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item7", required=True)
    ap.add_argument("--assignment", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args()

    d = json.load(open(a.item7))
    dist = {int(k): int(v) for k, v in d["distribuicao"].items()}
    S, K = d["sementes"], d["K"]
    ks = sorted(dist)

    # ── guards ──
    falhas = []
    if sum(dist.values()) != S:
        falhas.append(f"histogram sums to {sum(dist.values())}, not {S}")
    if round(dist.get(1, 0) / S, 4) != d["P_n_eq_1"]:
        falhas.append("P_n_eq_1 does not follow from the histogram")
    if round((dist.get(0, 0) + dist.get(1, 0)) / S, 4) != d["P_n_le_1"]:
        falhas.append("P_n_le_1 does not follow from the histogram")
    moda = max(ks, key=lambda k: dist[k])
    if moda != d["moda"]:
        falhas.append(f"mode {moda} ≠ {d['moda']}")
    media = sum(k * c for k, c in dist.items()) / S
    if round(media, 4) != round(d["media_condicional"], 4):
        falhas.append(f"mean {media:.4f} ≠ {d['media_condicional']}")

    plano = build_epochs(JANELA_INI, 234)
    tot = collections.Counter(assign(plano, hashlib.sha256(b"design-counts-only").hexdigest()).values())
    n_ep, n_topo = sum(tot.values()), tot[f"w{TOPO:g}"]
    esperado = K * n_topo / n_ep
    if round(esperado, 4) != d["esperado_desenho"]:
        falhas.append(f"design expectation {esperado:.4f} ≠ {d['esperado_desenho']}")

    real = d["realizado"][f"w{TOPO:g}"]
    serv = [e for e in json.load(open(a.assignment))["epochs"]
            if JANELA_INI <= e["epoch_inicio"] <= JANELA_FIM]
    real_serv = sum(1 for e in serv if float(e["w"]) == TOPO)
    if len(serv) != K or real_serv != real:
        falhas.append(f"ASSIGNMENT-SERVING: {len(serv)} epochs, {real_serv} at w={TOPO:g}; "
                      f"artifact says K={K}, realized {real}")
    if abs((d["deficit_truncamento"] + d["deficit_sorteio"]) - (real - d["esperado_desenho"])) > 1e-3:
        falhas.append("truncation + chance ≠ realized − expected")
    if abs((d["media_condicional"] - d["esperado_desenho"]) - d["deficit_truncamento"]) > 1e-3:
        falhas.append("truncation leg ≠ conditional mean − expected")
    if falhas:
        raise SystemExit("⛔ " + " · ".join(falhas))

    deficit = real - d["esperado_desenho"]
    # Monte-Carlo standard error of the conditional mean, from the histogram itself:
    # the truncation leg is a difference of means estimated on 2 000 seeds, so it is only
    # interpretable against this number.
    var = sum(c * (k - media) ** 2 for k, c in dist.items()) / (S - 1)
    ep_mc = (var / S) ** 0.5
    q_trunc = d["deficit_truncamento"] / deficit
    q_sort = d["deficit_sorteio"] / deficit

    # ── SVG ──
    W, H = 760, 486
    L, R, T, B = 66, 40, 70, 96
    pw, ph = W - L - R, H - T - B
    ymax = 30.0  # percent
    slot = pw / (max(ks) + 1)
    bw = slot - 2
    def px(k): return L + k * slot + 1
    def pxv(v): return L + (v + 0.5) * slot          # continuous value -> x (bar centres at k)
    def py(p): return T + ph - p / ymax * ph

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">',
        '<style>'
        ':root{--ink:#1a1a1a;--mut:#6b6b6b;--grid:#e3e3e3;--bar:#a9a9a6;--hi:#b4472f;--bg:#fcfcfb}'
        '@media (prefers-color-scheme:dark){:root{--ink:#eaeaea;--mut:#9a9a9a;'
        '--grid:#333;--bar:#5c5c5a;--hi:#d47456;--bg:#1a1a19}}'
        'text{fill:var(--ink)}.mut{fill:var(--mut)}'
        '</style>',
        f'<rect width="{W}" height="{H}" fill="var(--bg)"/>',
        f'<text x="{L}" y="22" font-size="13" font-weight="600">One epoch at the top dose is a '
        f'{100*d["P_n_eq_1"]:.2f}% draw, not a truncation effect</text>',
        f'<text x="{L}" y="40" class="mut">epochs at w = {TOPO:g} among the {K} realized, over '
        f'{S:,} re-drawn designs conditioned on the same dates (assign_arms.py)</text>'.replace(f"{S:,}", f"{S:,}".replace(",", chr(0x2009))),
    ]
    for p in range(0, int(ymax) + 1, 10):
        s.append(f'<line x1="{L}" y1="{py(p):.1f}" x2="{L+pw}" y2="{py(p):.1f}" stroke="var(--grid)"/>')
        s.append(f'<text x="{L-8}" y="{py(p)+4:.1f}" text-anchor="end" class="mut">{p}%</text>')
    for k in range(0, max(ks) + 1):
        c = dist.get(k, 0)
        p = 100 * c / S
        x, y = px(k), py(p)
        hh = T + ph - y
        r = min(4, hh / 2)
        cor = "--hi" if k == real else "--bar"
        s.append(f'<path d="M{x:.1f},{T+ph} V{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} '
                 f'H{x+bw-r:.1f} Q{x+bw:.1f},{y:.1f} {x+bw:.1f},{y+r:.1f} V{T+ph} Z" '
                 f'fill="var({cor})"><title>n = {k}: {c} of {S} seeds ({p:.2f}%)</title></path>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{T+ph+16}" text-anchor="middle" class="mut">{k}</text>')
        if k in (moda, real):
            s.append(f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" text-anchor="middle" font-size="10">'
                     f'{p:.1f}%</text>')
    s.append(f'<text x="{L+pw/2:.1f}" y="{T+ph+36}" text-anchor="middle" class="mut">'
             f'n = number of the {K} epochs assigned w = {TOPO:g}</text>')
    s.append(f'<text x="16" y="{T+ph/2:.1f}" class="mut" text-anchor="middle" '
             f'transform="rotate(-90 16 {T+ph/2:.1f})">share of seeds</text>')

    # expected (design) and conditional mean — 0.023 apart: drawn at their true positions
    for v, rot, dy, dash in ((d["esperado_desenho"], "design expectation", 0, "6 4"),
                             (d["media_condicional"], "conditional mean", 14, "2 3")):
        xv = pxv(v)
        s.append(f'<line x1="{xv:.1f}" y1="{T-4}" x2="{xv:.1f}" y2="{T+ph}" stroke="var(--ink)" '
                 f'stroke-width="1.5" stroke-dasharray="{dash}"/>')
    xm = pxv(d["media_condicional"])
    s.append(f'<text x="{xm+8:.1f}" y="{T+6}" font-size="10">design expectation '
             f'{K}×{n_topo}/{n_ep} = {d["esperado_desenho"]:.3f} (dashed)</text>')
    s.append(f'<text x="{xm+8:.1f}" y="{T+20}" font-size="10">conditional mean '
             f'{d["media_condicional"]:.3f} (dotted) — the lines are '
             f'{d["deficit_truncamento"]:.3f} apart</text>')

    # decomposition, as text
    xr = px(real) + bw / 2
    s.append(f'<text x="{xr:.1f}" y="{py(100*dist[real]/S)-22:.1f}" text-anchor="middle" font-size="10" '
             f'font-weight="600" fill="var(--hi)">realized n = {real}</text>'
             .replace('<text', '<text style="fill:var(--hi)"', 1))
    yb = T + ph + 60
    s.append(f'<text x="{L}" y="{yb}" font-size="10.5">deficit {m(round(deficit, 3))} against '
             f'the design = truncation {d["deficit_truncamento"]:+.3f} ({m(round(100*q_trunc, 1))}% of it) + '
             f'chance {m(round(d["deficit_sorteio"], 3))} ({100*q_sort:.1f}% of it)</text>')
    s.append(f'<text x="{L}" y="{yb+16}" class="mut" font-size="10">P(n = 1) = '
             f'{100*d["P_n_eq_1"]:.2f}% · P(n ≤ 1) = {100*d["P_n_le_1"]:.2f}% · mode {moda} '
             f'({100*dist[moda]/S:.1f}%) · with n = {real} there is no dose-response to read '
             f'(spec §7)</text>')
    s.append(f'<text x="{L}" y="{yb+32}" class="mut" font-size="10">Monte-Carlo s.e. of the '
             f'conditional mean ({S} seeds) = {ep_mc:.3f}; the truncation leg '
             f'({d["deficit_truncamento"]:+.3f}) is {abs(d["deficit_truncamento"])/ep_mc:.1f} s.e.: '
             f'its sign is not resolved</text>')
    s.append("</svg>")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(s) + "\n")
    ET.parse(out)
    msg = dict(svg=str(out), sementes=S, K=K, dist=dist, moda=moda, media=round(media, 4),
               esperado=round(esperado, 4), desenho=dict(tot), realizado=real,
               realizado_serving=real_serv, deficit=round(deficit, 4),
               quota_truncamento=round(q_trunc, 4), quota_sorteio=round(q_sort, 4), ep_mc_media=round(ep_mc, 4))
    if a.png:
        msg["png"] = str(render_png(out, W, H))
    print(json.dumps(msg, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
