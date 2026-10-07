#!/usr/bin/env python3
"""
sprint-figB-h1a-inversao-registrado.py — Paper B rc8, Figure B1 under the REGISTERED analysis.

Same pattern as `sprint-figB-h1a-inversao.py` (which is NOT modified and whose outputs
`figB1-h1a-inversao.*` stay as they are): two panels, plain SVG, guards that abort
instead of drawing.

  (a) session-hours per epoch, by designated arm, as the REGISTERED estimator computes
      them: the exposure windows of SPEC §2 (09-01 from the first `active` record, 09-03
      from the first served record, 09-20 until expiry 22:51:23Z) and the 19-epoch set
      (09-02 excluded). Composition, never reimplementation: `carregar_episodios` and
      `span_por_sessao` from `pilot_replay.py`, `janelas_de_exposicao` and
      `predicado_janela` from `estimador_itt_registrado.py`.
  (b) the H1a difference with its 95% interval, per leg: the registered analysis (BCa)
      on the locked leg (`out/ITT-REGISTRADO-2026-10-05.json`, `pernas.registrado`) and
      on the two declared sensitivity legs (`_sprint-2026-10-04/B-rc8/checks-rc8.json`,
      block A), and the analysis of rc7 (percentile, `pernas.atual`) as a sensitivity.

⚠️ GUARDS — the script aborts if:
  - the per-arm sum of panel (a) does not reproduce `horas_sessao` of the registered leg
    (2 decimals, as the artifact keeps), or any epoch differs from checks-rc8.json;
  - checks-rc8.json was produced from a different ITT-REGISTRADO file (sha256), or its
    copy of the registered leg differs from the artifact's;
  - a leg's interval does not contain its own point estimate.

The re-randomization p-value and the Holm adjustment are printed as text, never on the
axis: the test is a different estimand (§4.0.2) and H1a is decided inside the Holm family.

Usage:
  ./sprint-figB-h1a-inversao-registrado.py \
      --itt-registrado out/ITT-REGISTRADO-2026-10-05.json \
      --checks _sprint-2026-10-04/B-rc8/checks-rc8.json \
      --episodes ~/Backups/paper2-ensaio-2026-09-21/episodios-ensaio-20260921.jsonl \
      --serving ~/Backups/paper2-ensaio-2026-09-21/p2-serving.ndjson \
      --assignment ASSIGNMENT-SERVING.json \
      --out _sprint-2026-10-04/figures/figB1-h1a-inversao-registrado.svg --png
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))
from pilot_replay import carregar_episodios, span_por_sessao  # noqa: E402
from estimador_itt_registrado import (  # noqa: E402
    janelas_de_exposicao, predicado_janela, EPOCH_VAZIO, JANELA_INI, JANELA_FIM,
)

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
    ap.add_argument("--itt-registrado", required=True)
    ap.add_argument("--checks", required=True)
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--serving", required=True)
    ap.add_argument("--assignment", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args()

    raw = Path(a.itt_registrado).read_bytes()
    reg = json.loads(raw)
    chk = json.load(open(a.checks))
    if chk["sha256_ITT_REGISTRADO"] != hashlib.sha256(raw).hexdigest():
        raise SystemExit("⛔ checks-rc8.json was produced from a different ITT-REGISTRADO file")
    A = chk["A_pernas_registradas"]
    pr = reg["pernas"]["registrado"]
    for h in ("H1", "H1a", "H1c"):
        if A["registrado"][h]["ponto"] != pr["hipoteses"][h]["dif_pontual"] or \
                A["registrado"][h]["ic95"] != pr["hipoteses"][h]["ic95"]:
            raise SystemExit(f"⛔ checks-rc8.json's registered leg disagrees with the artifact on {h}")
    arm = {e["epoch_inicio"]: (e["arm"], float(e["w"]))
           for e in json.load(open(a.assignment))["epochs"]}

    # ── (a) recomputed denominator under the registered window ──
    ok = predicado_janela("exposicao", janelas_de_exposicao(Path(a.serving)))
    eps = [e for e in carregar_episodios(Path(a.episodes), {}) if ok(e)]
    horas = span_por_sessao(eps)
    h_ep: dict[str, float] = collections.defaultdict(float)
    for (ep, _s), h in horas.items():
        h_ep[ep.strftime("%Y-%m-%d")] += h
    epochs = [k for k in sorted(h_ep) if JANELA_INI <= k <= JANELA_FIM and k != EPOCH_VAZIO]
    if len(epochs) != 19 or any(k not in arm for k in epochs):
        raise SystemExit(f"⛔ registered set has {len(epochs)} epochs with hours, expected 19")
    for k in epochs:
        if round(h_ep[k], 4) != A["horas_por_epoch_registrado"]["por_epoch"][k]:
            raise SystemExit(f"⛔ {k}: {h_ep[k]:.4f} h ≠ checks-rc8.json")
    tot = collections.defaultdict(float)
    for k in epochs:
        tot[arm[k][0]] += h_ep[k]
    for b in ("treatment", "control"):
        if round(tot[b], 2) != pr["por_braco"][b]["horas_sessao"]:
            raise SystemExit(f"⛔ recomputed {b} hours {tot[b]:.4f} ≠ registered {pr['por_braco'][b]['horas_sessao']}")
    pico = max(epochs, key=lambda k: h_ep[k])
    resto = [h_ep[k] for k in epochs if k != pico]
    share = h_ep[pico] / tot[arm[pico][0]]
    sess = collections.defaultdict(list)
    for e in eps:
        if e.epoch.strftime("%Y-%m-%d") == pico:
            sess[e.sessao].append(e.ts)
    spans = {s: ((max(v) - min(v)).total_seconds() / 3600, len(v)) for s, v in sess.items()}
    s_larga = max(spans, key=lambda s: spans[s][0])
    ocupadas = sorted(spans.items(), key=lambda kv: -kv[1][1])[:3]

    # ── (b) legs, from the artifacts only ──
    def leg(d):
        return dict(dif_pontual=d["ponto"], ic95=d["ic95"])
    legs = [
        ("registered · locked", "19 epochs (09-02 excluded), BCa",
         dict(dif_pontual=pr["hipoteses"]["H1a"]["dif_pontual"], ic95=pr["hipoteses"]["H1a"]["ic95"])),
        ("registered · pre-committed sensitivity (spec §9.1)", "partials 09-01, 09-03, 09-20 removed, BCa",
         leg(A["registrado_precomprometida"]["H1a"])),
        ("registered · post-hoc sensitivity", "09-14 removed, chosen after seeing the data, BCa",
         leg(A["registrado_pos_hoc_sem_0914"]["H1a"])),
        ("rc7 analysis (sensitivity) · locked", "20 epochs, percentile, no window cut",
         dict(dif_pontual=reg["pernas"]["atual"]["hipoteses"]["H1a"]["dif_pontual"],
              ic95=reg["pernas"]["atual"]["hipoteses"]["H1a"]["ic95"])),
    ]
    for nome, _, d in legs:
        lo, hi = d["ic95"]
        if not lo <= d["dif_pontual"] <= hi:
            raise SystemExit(f"⛔ leg '{nome}': point outside its own interval")
    p_raw = pr["hipoteses"]["H1a"]["p_rerand"]
    holm = reg["multiplicidade"]["registrado"]["holm_H1a_H1b_H1c_H2x2"]
    pA = holm["A_familia_registada_inavaliaveis_como_p1"]["p_ajustado"]["H1a"]
    pB = holm["B_so_membros_avaliaveis"]["p_ajustado"]["H1a"]
    rejA = holm["A_familia_registada_inavaliaveis_como_p1"]["rejeita"]["H1a"]
    rejB = holm["B_so_membros_avaliaveis"]["rejeita"]["H1a"]
    if rejA or rejB:
        raise SystemExit("⛔ the caption text below assumes Holm does not reject H1a")

    # ── SVG ──
    W, H = 820, 660
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
        f'<text x="{L}" y="22" font-size="13" font-weight="600">H1a: the intervals that exclude zero '
        f'rest on one epoch of idle time, and the registered rule does not reject</text>',
    ]
    T1, ph1 = 70, 210
    ymax = 8.0
    def py1(v): return T1 + ph1 - v / ymax * ph1
    slot = pw / len(epochs)
    bw = slot - 2
    s.append(f'<text x="{L}" y="{T1-22}" font-weight="600">(a) Session-hours per epoch under the '
             f'registered window (span = last − first event of each session, summed)</text>')
    for v in range(0, int(ymax) + 1, 2):
        s.append(f'<line x1="{L}" y1="{py1(v):.1f}" x2="{L+pw}" y2="{py1(v):.1f}" stroke="var(--grid)"/>')
        s.append(f'<text x="{L-8}" y="{py1(v)+4:.1f}" text-anchor="end" class="mut">{v}</text>')
    for i, k in enumerate(epochs):
        b, w = arm[k]
        cor = "--tr" if b == "treatment" else "--ct"
        x = L + i * slot + 1
        y = py1(h_ep[k]); hh = T1 + ph1 - y; r = min(4, hh / 2)
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
        f"other {len(resto)} epochs: {min(resto):.2f}–{max(resto):.2f} h; 09-02 excluded (served no brief)",
    ]
    for j, t in enumerate(linhas):
        s.append(f'<text x="{tx:.1f}" y="{py1(h_ep[pico])+24+13*j:.1f}" text-anchor="end" '
                 f'font-size="10">{t}</text>')
    lx, ly = L + 6, T1 + 4
    for j, (b, cor) in enumerate((("treatment", "--tr"), ("control", "--ct"))):
        s.append(f'<rect x="{lx}" y="{ly+16*j}" width="10" height="10" rx="2" fill="var({cor})"/>')
        s.append(f'<text x="{lx+16}" y="{ly+9+16*j}" font-size="10">{b} · {tot[b]:.2f} h '
                 f'over {sum(1 for k in epochs if arm[k][0]==b)} epochs</text>')

    T2 = T1 + ph1 + 78
    row_h = 52
    ph2 = row_h * len(legs)
    x0, x1 = -300.0, 30.0
    G = 300
    def px(v): return L + G + (v - x0) / (x1 - x0) * (pw - G)
    s.append(f'<text x="{L}" y="{T2-24}" font-weight="600">(b) H1a difference, treatment − '
             f'control (opportunities per session-hour), 95% cluster-bootstrap interval</text>')
    for v in range(-300, 31, 50):
        s.append(f'<line x1="{px(v):.1f}" y1="{T2}" x2="{px(v):.1f}" y2="{T2+ph2}" stroke="var(--grid)"/>')
        s.append(f'<text x="{px(v):.1f}" y="{T2+ph2+16}" text-anchor="middle" class="mut">'
                 f'{("0" if v == 0 else f"{v:+d}".replace("-", chr(0x2212)))}</text>')
    s.append(f'<line x1="{px(0):.1f}" y1="{T2-6}" x2="{px(0):.1f}" y2="{T2+ph2}" '
             f'stroke="var(--ink)" stroke-width="1.5"/>')
    s.append(f'<text x="{px(0)+4:.1f}" y="{T2-8}" font-size="10" class="mut">zero</text>')
    def num(v, sinal=False):
        t = f"{v:+.2f}" if sinal else f"{v:.2f}"
        return t.replace("-", "−")
    for j, (nome, quais, d) in enumerate(legs):
        yc = T2 + row_h * j + row_h / 2
        lo, hi = d["ic95"]
        exclui = hi < 0 or lo > 0
        s.append(f'<text x="{L}" y="{yc-9:.1f}" font-size="10.5">{nome}</text>')
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
             f'interval excludes zero · hollow = contains zero · coverage of these intervals not '
             f'established (§4.1.1, §4.1.2)</text>')
    s.append(f'<text x="{L}" y="{T2+ph2+56}" class="mut" font-size="10">registered re-randomization '
             f'test (different estimand, §4.0.2): unadjusted p = {p_raw:.4f};</text>')
    s.append(f'<text x="{L}" y="{T2+ph2+70}" class="mut" font-size="10">Holm-adjusted '
             f'{pA:.4f} (m = 5) / {pB:.4f} (m = 4): H1a is not rejected under the registered decision rule</text>')
    s.append("</svg>")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(s) + "\n")
    import xml.etree.ElementTree as ET
    ET.parse(out)
    msg = {
        "svg": str(out.name),
        "fonte": {"ITT-REGISTRADO": hashlib.sha256(raw).hexdigest(),
                  "checks-rc8.json": hashlib.sha256(Path(a.checks).read_bytes()).hexdigest()},
        "horas_por_braco": {b: round(v, 4) for b, v in tot.items()},
        "pico": pico, "pico_h": round(h_ep[pico], 4), "pico_share": round(share, 4),
        "outros_n": len(resto), "outros_min_max": [round(min(resto), 4), round(max(resto), 4)],
        "sessao_esparsa": {"id_prefix": s_larga[:8], "episodios": spans[s_larga][1],
                           "span_h": round(spans[s_larga][0], 4)},
        "sessoes_ocupadas": [{"id_prefix": k[:8], "episodios": n, "span_min": round(60 * h, 2)}
                             for k, (h, n) in ocupadas],
        "legs": [{"leg": n, "removidos": q, **d} for n, q, d in legs],
        "H1a_p_bruto": p_raw, "H1a_holm_ajustado": {"m5": pA, "m4": pB},
    }
    if a.png:
        msg["png"] = str(render_png(out, W, H).name)
    out.with_suffix(".run.json").write_text(json.dumps(msg, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(msg, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
