#!/usr/bin/env python3
"""
sprint-figB-h1a-inversao.py — Paper B, figure for §4.2: the H1a single-epoch inversion.

Two panels, one story:

  (a) session-hours per epoch, by DESIGNATED arm — the H1a denominator. Computed by
      COMPOSITION, never reimplementation: `carregar_episodios` + `span_por_sessao`
      are imported from `pilot_replay.py`, exactly as `estimador_itt.py` does. The span
      depends only on (ts, session), so the verdicts are not needed and an empty
      verdict map is passed (read `span_por_sessao`: it never touches `estado`).
  (b) the H1a difference (treatment − control, opportunities per session-hour) with its
      95% cluster-bootstrap interval, per leg, straight from the locked JSONs.

⚠️ GUARDS — the script aborts instead of drawing if:
  - the per-arm sum of panel (a) does not reproduce `horas_sessao` of the locked
    `ITT-2026-09-21.json` (to the 2 decimals the artifact keeps). Panel (a) is a
    recomputation; panel (b) is the artifact. If they disagree, the figure would show
    a mechanism that does not produce the number beside it;
  - the window does not hold exactly the 20 designated epochs of ASSIGNMENT-SERVING;
  - a leg's interval does not contain its own point estimate.

The pre-committed sensitivity (§9.1 of the analysis spec — all partials removed) lives
in `ITT-SENSIB-PRECOMPROMETIDA.json`. It is drawn by default because the manuscript's
own rule (§4.1) is "the registered sensitivity first"; `--sem-precomprometida` drops it.
⚠️ §4.2 of MANUSCRIPT-B.md does NOT report this leg for H1a today — see the sprint
report: that is a finding about the text, not a plotting choice.

The re-randomization p-value is printed as text, never on the axis: it tests a different
estimand (difference of arm means of trend-residualized per-epoch outcomes, §4.0.2).

Output: SVG (light/dark via CSS custom properties, same convention as fig1–fig3) and,
with --png, a PNG rendered by headless Chrome from that same SVG (light mode).

Usage:
  ./sprint-figB-h1a-inversao.py \
      --itt ~/Backups/paper2-ensaio-2026-09-21/ITT-2026-09-21.json \
      --itt-precomp ~/Backups/paper2-ensaio-2026-09-21/ITT-SENSIB-PRECOMPROMETIDA.json \
      --rerand ~/Backups/paper2-ensaio-2026-09-21/RERANDOMIZACAO-2026-09-21.json \
      --episodes ~/Backups/paper2-ensaio-2026-09-21/episodios-ensaio-20260921.jsonl \
      --assignment ASSIGNMENT-SERVING.json \
      --out _sprint-2026-10-04/figures/figB1-h1a-inversao.svg --png
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
from pilot_replay import carregar_episodios, span_por_sessao  # noqa: E402

JANELA_INI, JANELA_FIM = "2026-09-01", "2026-09-20"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render_png(svg: Path, w: int, h: int) -> Path:
    png = svg.with_suffix(".png")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=2", f"--window-size={w},{h}",
         "--default-background-color=ffffffff", f"--screenshot={png}",
         svg.resolve().as_uri()],
        check=True, capture_output=True, timeout=90)
    return png


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--itt", required=True)
    ap.add_argument("--itt-precomp")
    ap.add_argument("--rerand")
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--assignment", required=True)
    ap.add_argument("--sem-precomprometida", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args()

    itt = json.load(open(a.itt))
    arm = {e["epoch_inicio"]: (e["arm"], float(e["w"]))
           for e in json.load(open(a.assignment))["epochs"]}

    # ── (a) recomputed denominator, composed from pilot_replay ──
    eps = carregar_episodios(Path(a.episodes), {})
    horas = span_por_sessao(eps)
    h_ep: dict[str, float] = collections.defaultdict(float)
    for (ep, _s), h in horas.items():
        h_ep[ep.strftime("%Y-%m-%d")] += h
    epochs = [k for k in sorted(h_ep) if JANELA_INI <= k <= JANELA_FIM]
    if len(epochs) != 20 or any(k not in arm for k in epochs):
        raise SystemExit(f"⛔ window has {len(epochs)} epochs with hours; "
                         f"not in ASSIGNMENT: {[k for k in epochs if k not in arm]}")

    tot = collections.defaultdict(float)
    for k in epochs:
        tot[arm[k][0]] += h_ep[k]
    for b in ("treatment", "control"):
        want = itt["primario"]["por_braco"][b]["horas_sessao"]
        if round(tot[b], 2) != want:
            raise SystemExit(f"⛔ recomputed {b} hours {tot[b]:.4f} ≠ locked {want}")

    pico = max(epochs, key=lambda k: h_ep[k])
    resto = [h_ep[k] for k in epochs if k != pico]
    share = h_ep[pico] / tot[arm[pico][0]]

    # the sparse session inside the peak epoch, and the busiest sessions there
    sess = collections.defaultdict(list)
    for e in eps:
        if e.epoch.strftime("%Y-%m-%d") == pico:
            sess[e.sessao].append(e.ts)
    spans = {s: ((max(v) - min(v)).total_seconds() / 3600, len(v)) for s, v in sess.items()}
    s_larga = max(spans, key=lambda s: spans[s][0])
    ocupadas = sorted(spans.items(), key=lambda kv: -kv[1][1])[:3]

    # ── (b) legs, from the locked artifacts only ──
    legs = [("locked", "all 20 epochs", itt["primario"]["H1a_diferenca"], "registered")]
    if a.itt_precomp and not a.sem_precomprometida:
        pc = json.load(open(a.itt_precomp))
        rem = ", ".join(d[5:] for d in pc["sensibilidade"]["epochs_removidos"])
        legs.append(("pre-committed sensitivity (spec §9.1)", f"partials {rem} removed",
                     pc["sensibilidade"]["H1a_diferenca"], "registered"))
        if pc["primario"]["H1a_diferenca"] != itt["primario"]["H1a_diferenca"]:
            raise SystemExit("⛔ the two ITT JSONs disagree on the LOCKED leg — not the same run")
    rem = ", ".join(d[5:] for d in itt["sensibilidade"]["epochs_removidos"])
    legs.append(("sensitivity", f"{rem} removed",
                 itt["sensibilidade"]["H1a_diferenca"], "chosen after seeing the data"))
    for nome, _, d, _ in legs:
        lo, hi = d["ic95"]
        if not lo <= d["dif_pontual"] <= hi:
            raise SystemExit(f"⛔ leg '{nome}': point outside its own interval")
    rr = None
    if a.rerand:
        rr = json.load(open(a.rerand))["resultados"]["H1a_taxa"]

    # ── SVG ──
    W, H = 820, 600
    L, R = 78, 40
    pw = W - L - R
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">',
        '<style>'
        ':root{--ink:#1a1a1a;--mut:#6b6b6b;--grid:#e3e3e3;--tr:#b4472f;--ct:#2f6bb4;--bg:#fcfcfb}'
        '@media (prefers-color-scheme:dark){:root{--ink:#eaeaea;--mut:#9a9a9a;'
        '--grid:#333;--tr:#d47456;--ct:#4f8ee0;--bg:#1a1a19}}'
        'text{fill:var(--ink)}.mut{fill:var(--mut)}'
        '</style>',
        f'<rect width="{W}" height="{H}" fill="var(--bg)"/>',
        f'<text x="{L}" y="22" font-size="13" font-weight="600">H1a turns on one epoch: '
        f'the exposure denominator counts idle time</text>',
    ]

    # panel (a)
    T1, ph1 = 70, 210
    ymax = 8.0
    def py1(v): return T1 + ph1 - v / ymax * ph1
    slot = pw / len(epochs)
    bw = slot - 2   # 2 px surface gap between adjacent bars
    s.append(f'<text x="{L}" y="{T1-22}" font-weight="600">(a) Session-hours per epoch '
             f'(span = last − first event of each session, summed)</text>')
    for v in range(0, int(ymax) + 1, 2):
        s.append(f'<line x1="{L}" y1="{py1(v):.1f}" x2="{L+pw}" y2="{py1(v):.1f}" '
                 f'stroke="var(--grid)"/>')
        s.append(f'<text x="{L-8}" y="{py1(v)+4:.1f}" text-anchor="end" class="mut">{v}</text>')
    for i, k in enumerate(epochs):
        b, w = arm[k]
        cor = "--tr" if b == "treatment" else "--ct"
        x = L + i * slot + 1
        y = py1(h_ep[k])
        hh = T1 + ph1 - y
        r = min(4, hh / 2)
        # rounded data-end at the top, square at the baseline
        s.append(f'<path d="M{x:.1f},{T1+ph1} V{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} '
                 f'H{x+bw-r:.1f} Q{x+bw:.1f},{y:.1f} {x+bw:.1f},{y+r:.1f} V{T1+ph1} Z" '
                 f'fill="var({cor})"><title>{k} · {b} (w={w:g}) · {h_ep[k]:.2f} h</title></path>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{T1+ph1+14}" text-anchor="middle" class="mut" '
                 f'font-size="9">{k[8:]}</text>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{T1+ph1+26}" text-anchor="middle" class="mut" '
                 f'font-size="8">{"ctl" if b == "control" else f"w{w:g}"}</text>')
    s.append(f'<text x="{L-46}" y="{T1+ph1+14}" class="mut" font-size="9">Sep</text>')
    s.append(f'<text x="{L-46}" y="{T1+ph1+26}" class="mut" font-size="8">arm</text>')
    s.append(f'<text x="18" y="{T1+ph1/2:.1f}" class="mut" text-anchor="middle" '
             f'transform="rotate(-90 18 {T1+ph1/2:.1f})">hours</text>')
    ip = epochs.index(pico)
    xp = L + ip * slot + 1 + bw / 2
    s.append(f'<line x1="{xp-14:.1f}" y1="{py1(h_ep[pico])+6:.1f}" x2="{xp-60:.1f}" '
             f'y2="{py1(h_ep[pico])+20:.1f}" stroke="var(--mut)"/>')
    tx = xp - 64
    linhas = [
        f"{pico}: {h_ep[pico]:.2f} h = {100*share:.0f}% of all {arm[pico][0]} exposure",
        f"one session with {spans[s_larga][1]} episodes spans {spans[s_larga][0]:.2f} h;",
        "the busiest sessions there: " + " / ".join(str(n) for _, (_, n) in ocupadas)
        + " episodes, each within "
        + f"{60*min(h for _, (h, _) in ocupadas):.1f}–{60*max(h for _, (h, _) in ocupadas):.1f} min",
        f"other 19 epochs: {min(resto):.2f}–{max(resto):.2f} h",
    ]
    for j, t in enumerate(linhas):
        s.append(f'<text x="{tx:.1f}" y="{py1(h_ep[pico])+24+13*j:.1f}" text-anchor="end" '
                 f'font-size="10">{t}</text>')
    # legend
    lx, ly = L + 6, T1 + 4
    for j, (b, cor) in enumerate((("treatment", "--tr"), ("control", "--ct"))):
        s.append(f'<rect x="{lx}" y="{ly+16*j}" width="10" height="10" rx="2" fill="var({cor})"/>')
        s.append(f'<text x="{lx+16}" y="{ly+9+16*j}" font-size="10">{b} · {tot[b]:.2f} h '
                 f'over {sum(1 for k in epochs if arm[k][0]==b)} epochs</text>')

    # panel (b)
    T2 = T1 + ph1 + 78
    row_h = 52
    ph2 = row_h * len(legs)
    x0, x1 = -230.0, 30.0
    G = 290   # text gutter of panel (b)
    def px(v): return L + G + (v - x0) / (x1 - x0) * (pw - G)
    s.append(f'<text x="{L}" y="{T2-24}" font-weight="600">(b) H1a difference, treatment − '
             f'control (opportunities per session-hour), 95% cluster-bootstrap interval</text>')
    for v in range(-200, 31, 50):
        s.append(f'<line x1="{px(v):.1f}" y1="{T2}" x2="{px(v):.1f}" y2="{T2+ph2}" '
                 f'stroke="var(--grid)"/>')
        s.append(f'<text x="{px(v):.1f}" y="{T2+ph2+16}" text-anchor="middle" class="mut">'
                 f'{("0" if v == 0 else f"{v:+d}".replace("-", chr(0x2212)))}</text>')
    s.append(f'<line x1="{px(0):.1f}" y1="{T2-6}" x2="{px(0):.1f}" y2="{T2+ph2}" '
             f'stroke="var(--ink)" stroke-width="1.5"/>')
    s.append(f'<text x="{px(0)+4:.1f}" y="{T2-8}" font-size="10" class="mut">zero</text>')
    def num(v, sinal=False):
        t = f"{v:+.2f}" if sinal else f"{v:.2f}"
        return t.replace("-", "\u2212")
    for j, (nome, quais, d, tipo) in enumerate(legs):
        yc = T2 + row_h * j + row_h / 2
        lo, hi = d["ic95"]
        exclui = hi < 0 or lo > 0
        s.append(f'<text x="{L}" y="{yc-9:.1f}" font-size="10.5">{nome} · {tipo}</text>')
        s.append(f'<text x="{L}" y="{yc+4:.1f}" font-size="10" class="mut">{quais}</text>')
        s.append(f'<text x="{L}" y="{yc+17:.1f}" font-size="10" class="mut">'
                 f'{num(d["dif_pontual"])} [{num(lo)}; {num(hi, True)}] · '
                 f'{"excludes" if exclui else "contains"} zero</text>')
        s.append(f'<line x1="{px(lo):.1f}" y1="{yc:.1f}" x2="{px(hi):.1f}" y2="{yc:.1f}" '
                 f'stroke="var(--ink)" stroke-width="2"/>')
        for xe in (lo, hi):
            s.append(f'<line x1="{px(xe):.1f}" y1="{yc-5:.1f}" x2="{px(xe):.1f}" y2="{yc+5:.1f}" '
                     f'stroke="var(--ink)" stroke-width="2"/>')
        fill = "var(--ink)" if exclui else "var(--bg)"
        s.append(f'<circle cx="{px(d["dif_pontual"]):.1f}" cy="{yc:.1f}" r="5" fill="{fill}" '
                 f'stroke="var(--ink)" stroke-width="2"/>')
    s.append(f'<text x="{L}" y="{T2+ph2+40}" class="mut" font-size="10">filled marker = '
             f'interval excludes zero · hollow = contains zero · intervals under-cover (§4.1.1, §4.4.1)</text>')
    if rr:
        s.append(f'<text x="{L}" y="{T2+ph2+56}" class="mut" font-size="10">registered '
                 f're-randomization test (different estimand, §4.0.2): p = {rr["p_bilateral"]:.4f}, '
                 f'{"rejects" if rr["rejeita_nulo_agudo_a_5pct"] else "does not reject"} at 5%</text>')
    s.append("</svg>")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(s) + "\n")
    import xml.etree.ElementTree as ET
    ET.parse(out)   # ⛔ a malformed SVG renders as a browser error page — fail here instead
    msg = {
        "svg": str(out),
        "horas_por_braco": {b: round(v, 4) for b, v in tot.items()},
        "pico": pico, "pico_h": round(h_ep[pico], 4), "pico_share": round(share, 4),
        "outros_min_max": [round(min(resto), 4), round(max(resto), 4)],
        "sessao_esparsa": {"id_prefix": s_larga[:8], "episodios": spans[s_larga][1],
                           "span_h": round(spans[s_larga][0], 4),
                           "ts": [t.isoformat() for t in sorted(sess[s_larga])]},
        "sessoes_ocupadas": [{"id_prefix": k[:8], "episodios": n, "span_min": round(60 * h, 2)}
                             for k, (h, n) in ocupadas],
        "legs": [{"leg": n, "removidos": q, **d} for n, q, d, _ in legs],
        "rerand_H1a": rr,
    }
    if a.png:
        msg["png"] = str(render_png(out, W, H))
    print(json.dumps(msg, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
