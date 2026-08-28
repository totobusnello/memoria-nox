#!/usr/bin/env python3
"""
fig3-dose-resposta.py — Figura 3: dose-resposta e o teto analítico.

Duas séries, dos dois artefatos do replay:

  - **grid grosso** (`dose-350-v3.json`): 9 doses sobre os 350 estados reais;
  - **grid fino** (`limiar-17.json`): 23 doses sobre os 17 estados que se movem em
    alguma dose.

⚠️ **Os dois têm denominadores diferentes e o mesmo numerador**, e é por isso que podem
ir no mesmo eixo: `mexeu` conta estados que se movem, e um estado fora dos 17 não se
move em dose nenhuma (a resposta é monótona em cada estado, §4.4). A conferência não
é retórica — as duas séries compartilham exatamente **uma** dose, `w = 1`, e ali as
duas dão **8**. O script aborta se deixarem de bater, porque duas curvas plotadas
juntas que discordam onde se cruzam são uma figura mentindo em silêncio.

⚠️ **`w = 0` não existe em eixo logarítmico**, e o controle negativo é justamente
`w = 0 ⇒ 0/350`. Ele não é omitido nem espremido no primeiro tick: sai como anotação
explícita fora do eixo. Um controle negativo invisível é um controle negativo não
reportado.

Uso:
  ./fig3-dose-resposta.py --grosso out/dose-350-v3.json --fino out/limiar-17.json \
      --out out/fig3-dose-resposta.svg
"""
import argparse
import json
import math

BANDA = [2.0, 4.0, 7.5]      # doses registradas, §2 do pré-registro
SAT = (4.0, 4.4)             # região de saturação medida no grid fino


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grosso", required=True)
    ap.add_argument("--fino", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    g = json.load(open(a.grosso))["dose"]["tabela"]
    f_ = json.load(open(a.fino))["dose"]["tabela"]

    G = {float(r["w"]): r for r in g}
    F = {float(r["w"]): r for r in f_}

    comuns = sorted(set(G) & set(F) - {0.0})
    if not comuns:
        raise SystemExit("os dois grids não compartilham dose alguma: nada garante que "
                         "sejam comparáveis, e plotá-los juntos seria invenção")
    div = [w for w in comuns if G[w]["mexeu"] != F[w]["mexeu"]]
    if div:
        raise SystemExit("grids DIVERGEM em " + ", ".join(
            f"w={w}: {G[w]['mexeu']} vs {F[w]['mexeu']}" for w in div))

    n_estados = G[0.0]["estados"] if 0.0 in G else max(r["estados"] for r in g)
    ctrl = G.get(0.0)
    teto = max(max(r["mexeu"] for r in g), max(r["mexeu"] for r in f_))

    pts_g = sorted((w, G[w]["mexeu"]) for w in G if w > 0)
    pts_f = sorted((w, F[w]["mexeu"]) for w in F if w > 0)

    W, H = 760, 440
    L, R, T, B = 66, 52, 50, 62
    pw, ph = W - L - R, H - T - B
    x0, x1 = math.log10(0.015), math.log10(2e5)
    y0, y1 = 0, teto + 3

    def px(w): return L + (math.log10(w) - x0) / (x1 - x0) * pw
    def py(v): return T + ph - (v - y0) / (y1 - y0) * ph

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">',
        '<style>'
        ':root{--ink:#1a1a1a;--mut:#6b6b6b;--grid:#e3e3e3;--gro:#b4472f;--fin:#2f6bb4;'
        '--sat:#7a9a4a}'
        '@media (prefers-color-scheme:dark){:root{--ink:#eaeaea;--mut:#9a9a9a;'
        '--grid:#333;--gro:#e08a70;--fin:#79a9e0;--sat:#a8c47a}}'
        'text{fill:var(--ink)}.mut{fill:var(--mut)}'
        '</style>',
        f'<rect width="{W}" height="{H}" fill="transparent"/>',
    ]

    # Região de saturação, ANTES das curvas para não cobri-las.
    # ⚠️ Em 7 décadas de eixo log, (4,0 ; 4,4] mede ~4 px. NÃO alargo: a faixa é
    # estreita porque a saturação está estreitamente localizada, e engordá-la para
    # "ficar visível" seria desenhar uma incerteza que a medição não tem. O que a torna
    # legível são as duas linhas de fronteira e a chamada, não uma largura inventada.
    xa, xb = px(SAT[0]), px(SAT[1])
    s.append(f'<rect x="{xa:.1f}" y="{T}" width="{max(xb-xa, 1.0):.1f}" '
             f'height="{ph}" fill="var(--sat)" opacity="0.35"/>')
    for x_ in (xa, xb):
        s.append(f'<line x1="{x_:.1f}" y1="{T}" x2="{x_:.1f}" y2="{T+ph}" '
                 f'stroke="var(--sat)" stroke-width="1"/>')
    s.append(f'<line x1="{xb:.1f}" y1="{T+18}" x2="{xb+22:.1f}" y2="{T+10}" '
             f'stroke="var(--sat)" stroke-width="1"/>')
    s.append(f'<text x="{xb+26:.1f}" y="{T+13}" fill="var(--sat)" font-size="10">'
             f'saturação em w ∈ ({SAT[0]:g} ; {SAT[1]:g}] — largura real, ~4 px em 7 décadas</text>')

    for v in range(0, int(y1) + 1, 5):
        s.append(f'<line x1="{L}" y1="{py(v):.1f}" x2="{L+pw}" y2="{py(v):.1f}" '
                 f'stroke="var(--grid)" stroke-width="1"/>')
        s.append(f'<text x="{L-8}" y="{py(v)+4:.1f}" text-anchor="end" class="mut">{v}</text>')
        s.append(f'<text x="{L+pw+8}" y="{py(v)+4:.1f}" class="mut" font-size="10">'
                 f'{100*v/n_estados:.2f}%</text>')

    for e in range(-2, 6):
        w = 10.0 ** e
        s.append(f'<line x1="{px(w):.1f}" y1="{T}" x2="{px(w):.1f}" y2="{T+ph}" '
                 f'stroke="var(--grid)" stroke-width="1"/>')
        s.append(f'<text x="{px(w):.1f}" y="{T+ph+18}" text-anchor="middle" class="mut">'
                 f'10<tspan dy="-4" font-size="8">{e}</tspan></text>')

    # teto
    s.append(f'<line x1="{L}" y1="{py(teto):.1f}" x2="{L+pw}" y2="{py(teto):.1f}" '
             f'stroke="var(--ink)" stroke-width="1" stroke-dasharray="6 4" opacity="0.55"/>')
    s.append(f'<text x="{L+6}" y="{py(teto)-6:.1f}" font-size="10">'
             f'teto {teto}/{n_estados} = {100*teto/n_estados:.2f}% dos briefs</text>')

    # banda registrada
    for w in BANDA:
        s.append(f'<line x1="{px(w):.1f}" y1="{T+ph}" x2="{px(w):.1f}" y2="{T+ph+7}" '
                 f'stroke="var(--ink)" stroke-width="2"/>')
    s.append(f'<text x="{px(BANDA[1]):.1f}" y="{T+ph+34}" text-anchor="middle" font-size="10">'
             f'banda registrada {{{" · ".join(f"{w:g}" for w in BANDA)}}}</text>')

    def curva(pts, cor, largura):
        d = " ".join(f"{px(w):.1f},{py(v):.1f}" for w, v in pts)
        s.append(f'<polyline points="{d}" fill="none" stroke="var({cor})" '
                 f'stroke-width="{largura}"/>')
        for w, v in pts:
            s.append(f'<circle cx="{px(w):.1f}" cy="{py(v):.1f}" r="2.6" fill="var({cor})"/>')

    curva(pts_f, "--fin", 1.6)
    curva(pts_g, "--gro", 2.2)

    # controle negativo — fora do eixo log, e dito por extenso. Vai na legenda e não
    # sob o eixo: ali ele colidia com o rótulo do eixo x, e anotação que se sobrepõe a
    # outra é anotação que ninguém lê.
    s.append(f'<circle cx="{L+pw-170}" cy="{T+8}" r="3.5" fill="var(--gro)"/>')
    s.append(f'<text x="{L+pw-162}" y="{T+12}" font-size="10">grid grosso · {n_estados} estados</text>')
    s.append(f'<circle cx="{L+pw-170}" cy="{T+24}" r="3.5" fill="var(--fin)"/>')
    s.append(f'<text x="{L+pw-162}" y="{T+28}" font-size="10">grid fino · 23 doses</text>')
    if ctrl is not None:
        s.append(f'<text x="{L+pw-170}" y="{T+44}" font-size="10" class="mut">'
                 f'controle negativo w = 0 ⇒ {ctrl["mexeu"]}/{ctrl["estados"]}</text>')
        s.append(f'<text x="{L+pw-170}" y="{T+57}" font-size="10" class="mut">'
                 f'(fora do eixo log)</text>')

    s.append(f'<text x="{L}" y="20" font-size="13" font-weight="600">'
             f'A resposta é monótona e satura: o bônus tem teto analítico</text>')
    s.append(f'<text x="{L}" y="36" class="mut">as duas séries concordam em w = '
             f'{comuns[0]:g} ({G[comuns[0]]["mexeu"]} estados), única dose que compartilham</text>')
    s.append(f'<text x="{L+pw/2:.1f}" y="{H-8}" text-anchor="middle" class="mut">'
             f'dose w (múltiplos de Δ_cut, escala log)</text>')
    s.append(f'<text x="14" y="{T+ph/2:.1f}" class="mut" text-anchor="middle" '
             f'transform="rotate(-90 14 {T+ph/2:.1f})">estados que se movem</text>')
    s.append("</svg>")

    open(a.out, "w").write("\n".join(s) + "\n")
    print(f"{a.out}: teto={teto}/{n_estados} ({100*teto/n_estados:.2f}%) · "
          f"grids batem em w={comuns} · controle negativo={ctrl['mexeu'] if ctrl else '?'}")


if __name__ == "__main__":
    main()
