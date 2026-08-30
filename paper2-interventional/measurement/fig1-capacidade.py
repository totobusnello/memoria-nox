#!/usr/bin/env python3
"""
fig1-capacidade.py — Figura 1 do manuscrito: tamanho da coleção × exposição.

Emite SVG puro, sem dependência de plotting. A razão não é minimalismo: a figura é
**derivada** do artefato travado (`out/superficie.json`), então ela tem de ser
regenerável por quem tiver o JSON, sem instalar nada, e tem de mudar se o dado mudar.
Figura desenhada à mão é prosa afirmando resultado calculado — cache sem invalidação.

Uso:
  ./fig1-capacidade.py --dados out/superficie.json --out out/fig1-capacidade.svg
"""
import argparse
import json
import math


# limites do vazio no eixo, verbatim de `lacuna-no-eixo-de-tamanho.py`:
# maior tipo pequeno (lesson) e menor tipo grande (graph_node).
VAZIO = (53, 1046)


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy), (mx, my, sxy / sxx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with open(a.dados) as f:
        tipos = json.load(f)["gradiente_de_curadoria"]

    # ⚠️ GUARDA: recusar o artefato FILTRADO. `superficie-de-exposicao.py:124` aplica
    # `HAVING total >= 10`, e os dois tipos que ele remove — `pending` (n=6) e
    # `procedure` (n=3) — estão ambos em 0% de exposição, ou seja, são exatamente os
    # contraexemplos da leitura "os pequenos são muito expostos". Desenhar sobre os 13
    # produz uma figura que AFIRMA VISUALMENTE o que o texto do §4.2 refuta, e o leitor
    # acredita no que vê antes de ler a ressalva. Achado de revisão adversarial, 29/08.
    if len(tipos) < 15:
        raise SystemExit(
            f"⛔ o artefato traz {len(tipos)} tipos; a figura exige os 15 sem filtro. "
            f"Use `out/SIZE-EXPOSURE-15-*.json`, não `out/superficie.json` "
            f"— este último é filtrado por `HAVING total >= 10` e omite justamente os "
            f"dois tipos em 0%."
        )
    zeros = [t["tipo"] for t in tipos if t["pct"] == 0]
    if not zeros:
        raise SystemExit(
            "⛔ nenhum tipo com 0% de exposição no artefato — ou o corpus mudou, ou "
            "o filtro voltou por outro caminho. A figura não pode ser desenhada sem "
            "os contraexemplos."
        )

    xs = [math.log10(t["total"]) for t in tipos]
    ys = [t["pct"] for t in tipos]
    r, (mx, my, b) = pearson(xs, ys)

    # geometria
    W, H = 760, 470
    L, R, T, B = 78, 24, 46, 62
    pw, ph = W - L - R, H - T - B
    x0, x1 = 0.9, math.log10(max(t["total"] for t in tipos)) + 0.25
    y0, y1 = 0, 105

    def px(x): return L + (x - x0) / (x1 - x0) * pw
    def py(y): return T + ph - (y - y0) / (y1 - y0) * ph

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">',
        '<style>'
        ':root{--ink:#1a1a1a;--mut:#6b6b6b;--grid:#e3e3e3;--big:#b4472f;--small:#2f6bb4}'
        '@media (prefers-color-scheme:dark){:root{--ink:#eaeaea;--mut:#9a9a9a;'
        '--grid:#333;--big:#e08a70;--small:#79a9e0}}'
        'text{fill:var(--ink)}.mut{fill:var(--mut)}'
        '</style>',
        f'<rect width="{W}" height="{H}" fill="transparent"/>',
    ]

    # as duas faixas: n<100 e n>=1000. A ausência de sobreposição É o achado, então
    # ela é desenhada, não só afirmada no texto.
    peq = [t for t in tipos if t["total"] < 100]
    gra = [t for t in tipos if t["total"] >= 1000]
    for grupo, cor, rot in ((peq, "var(--small)", "n &lt; 100"), (gra, "var(--big)", "n ≥ 1.000")):
        lo, hi = min(t["pct"] for t in grupo), max(t["pct"] for t in grupo)
        s.append(f'<rect x="{L}" y="{py(hi):.1f}" width="{pw}" '
                 f'height="{py(lo) - py(hi):.1f}" fill="{cor}" opacity="0.10"/>')
        s.append(f'<text x="{W - R - 4:.0f}" y="{(py(hi) + py(lo)) / 2 + 3:.1f}" '
                 f'text-anchor="end" fill="{cor}" font-size="10">'
                 f'{rot}: {lo:.1f}–{hi:.1f}%</text>')

    # grade e eixos
    for y in range(0, 101, 25):
        s.append(f'<line x1="{L}" y1="{py(y):.1f}" x2="{L + pw}" y2="{py(y):.1f}" '
                 f'stroke="var(--grid)" stroke-width="1"/>')
        s.append(f'<text x="{L - 8}" y="{py(y) + 4:.1f}" text-anchor="end" '
                 f'class="mut">{y}%</text>')
    for d in range(1, int(x1) + 1):
        s.append(f'<line x1="{px(d):.1f}" y1="{T}" x2="{px(d):.1f}" y2="{T + ph}" '
                 f'stroke="var(--grid)" stroke-width="1"/>')
        s.append(f'<text x="{px(d):.1f}" y="{T + ph + 16:.0f}" text-anchor="middle" '
                 f'class="mut">10<tspan dy="-4" font-size="8">{d}</tspan></text>')

    # ⚠️ A RETA DE REGRESSÃO FOI RETIRADA em 2026-08-29, e não por estética.
    # O eixo tem um vazio de 1,295 décadas — 32,1% da amplitude, zero tipos entre
    # n=53 e n=1.046 (`lacuna-no-eixo-de-tamanho.py`). Uma reta atravessando esse
    # trecho AFIRMA GRAFICAMENTE a continuidade que o §4.2 retira do texto, e é a
    # forma mais difícil de retratar: o leitor lê a inclinação sem ler a ressalva.
    # No lugar dela, uma faixa que marca explicitamente onde não há observação.
    gx0, gx1 = math.log10(VAZIO[0]), math.log10(VAZIO[1])
    s.append(f'<rect x="{px(gx0):.1f}" y="{T}" width="{px(gx1) - px(gx0):.1f}" '
             f'height="{ph}" fill="var(--mut)" opacity="0.07"/>')
    s.append(f'<text x="{(px(gx0) + px(gx1)) / 2:.1f}" y="{T + 16}" '
             f'text-anchor="middle" class="mut">sem observação</text>')

    # pontos + rótulos
    for t, x, y in zip(tipos, xs, ys):
        cor = "var(--big)" if t["total"] >= 1000 else (
            "var(--small)" if t["total"] < 100 else "var(--mut)")
        s.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="4.5" fill="{cor}"/>')
        # rótulo abaixo quando o ponto está no topo, para não sair do quadro
        dy = 17 if y > 92 else -9
        s.append(f'<text x="{px(x):.1f}" y="{py(y) + dy:.1f}" text-anchor="middle" '
                 f'font-size="10">{t["tipo"]}</text>')

    s += [
        f'<text x="{L}" y="20" font-size="13" font-weight="600">'
        f'Exposição é governada pelo tamanho da coleção, não pela curadoria</text>',
        f'<text x="{L}" y="36" class="mut">Pearson r = {r:.3f} · r² = {r * r:.3f} · '
        f'n = {len(tipos)} tipos · as duas faixas não se sobrepõem</text>',
        f'<text x="{L + pw / 2:.0f}" y="{H - 26}" text-anchor="middle" class="mut">'
        f'chunks no tipo (escala log)</text>',
        f'<text x="16" y="{T + ph / 2:.0f}" class="mut" '
        f'transform="rotate(-90 16 {T + ph / 2:.0f})" text-anchor="middle">'
        f'% exposto em alguma superfície</text>',
        '</svg>',
    ]
    with open(a.out, "w") as f:
        f.write("\n".join(s) + "\n")
    print(f"{a.out}: r={r:.3f} r2={r*r:.3f} n={len(tipos)} "
          f"faixas: n<100 {min(t['pct'] for t in peq):.1f}-{max(t['pct'] for t in peq):.1f}% | "
          f"n>=1000 {min(t['pct'] for t in gra):.1f}-{max(t['pct'] for t in gra):.1f}%")


if __name__ == "__main__":
    main()
