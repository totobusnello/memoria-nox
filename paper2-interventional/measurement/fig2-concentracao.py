#!/usr/bin/env python3
"""
fig2-concentracao.py — Figura 2 do manuscrito: concentração da superfície do brief.

Curva de Lorenz do carrossel: rank do chunk (por slots recebidos) × share cumulativo
dos slots. Marca os 3 chunks presentes em 100% dos briefs e o corte do top-10, porque
são os dois números que o §4.3 cita — a figura tem de mostrar a mesma coisa que o texto
afirma, derivada do mesmo artefato.

Mesma disciplina da Figura 1: SVG puro, sem dependência de plotting, derivado de
`out/superficie.json`. Figura desenhada à mão é prosa afirmando resultado calculado.

⚠️ A diagonal de igualdade NÃO é hipótese nula plausível aqui, e o rótulo diz isso: um
brief de 10 slots servido 4.632 vezes não poderia distribuir 46.295 slots igualmente
entre 67.187 chunks nem em princípio — só cabem 201. A diagonal é referência de
LEITURA da curva, não linha de comparação.

Uso:
  ./fig2-concentracao.py --dados out/superficie.json --out out/fig2-concentracao.svg
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with open(a.dados) as f:
        c = json.load(f)["concentracao_do_brief"]

    curva = c["curva_slots_por_rank"]
    if not curva:
        raise SystemExit("artefato sem `curva_slots_por_rank` — regere o superficie.json")
    tot = sum(curva)
    if tot != c["slots_7d"]:
        raise SystemExit(f"curva soma {tot} mas slots_7d é {c['slots_7d']}: artefato inconsistente")

    n = len(curva)
    cum, s_ = [], 0
    for v in curva:
        s_ += v
        cum.append(100 * s_ / tot)

    const = c["chunks_em_100pct_dos_briefs_7d"]
    top10 = c["pct_top10"]

    W, H = 760, 440
    L, R, T, B = 62, 24, 46, 58
    pw, ph = W - L - R, H - T - B

    def px(i): return L + (i / n) * pw          # i = rank 0-based, contínuo
    def py(y): return T + ph - (y / 100) * ph

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">',
        '<style>'
        ':root{--ink:#1a1a1a;--mut:#6b6b6b;--grid:#e3e3e3;--cur:#b4472f;--mark:#2f6bb4}'
        '@media (prefers-color-scheme:dark){:root{--ink:#eaeaea;--mut:#9a9a9a;'
        '--grid:#333;--cur:#e08a70;--mark:#79a9e0}}'
        'text{fill:var(--ink)}.mut{fill:var(--mut)}'
        '</style>',
        f'<rect width="{W}" height="{H}" fill="transparent"/>',
    ]

    for y in (0, 25, 50, 75, 100):
        s.append(f'<line x1="{L}" y1="{py(y):.1f}" x2="{L+pw}" y2="{py(y):.1f}" '
                 f'stroke="var(--grid)" stroke-width="1"/>')
        s.append(f'<text x="{L-8}" y="{py(y)+4:.1f}" text-anchor="end" class="mut">{y}%</text>')
    for i in range(0, n + 1, 50):
        s.append(f'<line x1="{px(i):.1f}" y1="{T}" x2="{px(i):.1f}" y2="{T+ph}" '
                 f'stroke="var(--grid)" stroke-width="1"/>')
        s.append(f'<text x="{px(i):.1f}" y="{T+ph+18}" text-anchor="middle" class="mut">{i}</text>')

    # diagonal de igualdade — referência de leitura, ver o aviso no cabeçalho
    s.append(f'<line x1="{L}" y1="{py(0):.1f}" x2="{L+pw}" y2="{py(100):.1f}" '
             f'stroke="var(--mut)" stroke-width="1" stroke-dasharray="3 4" opacity="0.6"/>')
    s.append(f'<text x="{L+pw*0.62:.1f}" y="{py(58):.1f}" class="mut" font-size="10" '
             f'transform="rotate(-19 {L+pw*0.62:.1f} {py(58):.1f})">'
             f'distribuição igual entre os 201 servidos</text>')

    pts = " ".join(f"{px(i+1):.1f},{py(v):.1f}" for i, v in enumerate(cum))
    s.append(f'<polyline points="{px(0):.1f},{py(0):.1f} {pts}" fill="none" '
             f'stroke="var(--cur)" stroke-width="2"/>')

    # os 3 constantes
    s.append(f'<line x1="{px(const):.1f}" y1="{T}" x2="{px(const):.1f}" y2="{T+ph}" '
             f'stroke="var(--mark)" stroke-width="1.2" stroke-dasharray="4 3"/>')
    s.append(f'<circle cx="{px(const):.1f}" cy="{py(cum[const-1]):.1f}" r="4" fill="var(--mark)"/>')
    s.append(f'<text x="{px(const)+8:.1f}" y="{py(cum[const-1])-6:.1f}" fill="var(--mark)" '
             f'font-size="10">{const} chunks em 100% dos briefs = {cum[const-1]:.1f}% dos slots</text>')

    # top-10
    s.append(f'<line x1="{px(10):.1f}" y1="{T}" x2="{px(10):.1f}" y2="{T+ph}" '
             f'stroke="var(--mark)" stroke-width="1.2" stroke-dasharray="4 3"/>')
    s.append(f'<circle cx="{px(10):.1f}" cy="{py(top10):.1f}" r="4" fill="var(--mark)"/>')
    s.append(f'<text x="{px(10)+8:.1f}" y="{py(top10)+16:.1f}" fill="var(--mark)" '
             f'font-size="10">top-10 = {top10:.2f}% dos slots</text>')

    # Separador de milhar pt-BR aplicado NO NÚMERO, não na string montada: um
    # `.replace(",", ".")` sobre a linha inteira também trocava a vírgula entre as duas
    # datas da janela, e imprimiu `[2026-08-20. 2026-08-27)`.
    def mil(x): return f"{x:,}".replace(",", ".")

    s.append(f'<text x="{L}" y="20" font-size="13" font-weight="600">'
             f'A superfície do brief é um carrossel: {n} chunks distintos em '
             f'{mil(c["slots_7d"])} slots</text>')
    s.append(f'<text x="{L}" y="36" class="mut">janela fechada '
             f'[{c["janela_7d"][0]}, {c["janela_7d"][1]}) · {mil(c["briefs_7d"])} briefs · '
             f'top-20 = {c["pct_top20"]:.2f}%</text>')
    s.append(f'<text x="{L+pw/2:.1f}" y="{H-16}" text-anchor="middle" class="mut">'
             f'chunks servidos, ordenados por slots recebidos</text>')
    s.append(f'<text x="14" y="{T+ph/2:.1f}" class="mut" text-anchor="middle" '
             f'transform="rotate(-90 14 {T+ph/2:.1f})">share cumulativo dos slots</text>')
    s.append("</svg>")

    with open(a.out, "w") as f:
        f.write("\n".join(s) + "\n")
    print(f"{a.out}: n={n} slots={tot} top10={top10}% top20={c['pct_top20']}% "
          f"{const} constantes={cum[const-1]:.1f}%")


if __name__ == "__main__":
    main()
