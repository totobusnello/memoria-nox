#!/usr/bin/env python3
"""
fig0-arquitetura.py — figura do §2: as duas superfícies e os 10 slots.

⚠️ **Esta é a única figura do paper que NÃO deriva de dado — ela descreve estrutura.**
A geometria é escrita à mão porque um diagrama de arquitetura é uma afirmação sobre o
código, não sobre uma medição. Mas **todo número rotulado nela vem do artefato**
(`out/superficie.json`), pelo mesmo motivo de sempre: rótulo digitado envelhece para
falso em silêncio, e já envelheceu uma vez neste projeto (o `w_min` fixado em 7,5).

Se o artefato disser outra coisa, a figura muda. Se a estrutura do código mudar, a
figura **não** muda sozinha — e isso é um limite declarado, não um descuido: nenhum
artefato deste repo descreve topologia.

Uso:
  ./fig0-arquitetura.py --dados out/superficie.json --out out/fig0-arquitetura.svg
"""
import argparse
import json

FRESH = 2   # freshSlots em produção. Ver §2 e §5.3: é default sem override, e é TETO.
N_SLOTS = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    d = json.load(open(a.dados))
    corpus = d["corpus"]
    cum = d["cumulativo_exato"]
    conc = d["concentracao_do_brief"]

    def mil(x): return f"{x:,}".replace(",", ".")

    W, H = 780, 430
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">',
        '<style>'
        ':root{--ink:#1a1a1a;--mut:#6b6b6b;--box:#c9c9c9;--brief:#b4472f;'
        '--busca:#2f6bb4;--cob:#7a9a4a;--fundo:#00000008}'
        '@media (prefers-color-scheme:dark){:root{--ink:#eaeaea;--mut:#9a9a9a;'
        '--box:#555;--brief:#e08a70;--busca:#79a9e0;--cob:#a8c47a;--fundo:#ffffff10}}'
        'text{fill:var(--ink)}.mut{fill:var(--mut)}'
        '.cx{fill:var(--fundo);stroke:var(--box);stroke-width:1.2;rx:6}'
        '</style>',
        f'<rect width="{W}" height="{H}" fill="transparent"/>',
        f'<text x="24" y="22" font-size="13" font-weight="600">'
        f'Duas superfícies, dez slots: por onde um chunk pode chegar a um agente</text>',
    ]

    # corpus
    s += [f'<rect class="cx" x="24" y="46" width="150" height="120"/>',
          f'<text x="99" y="72" text-anchor="middle" font-weight="600">corpus</text>',
          f'<text x="99" y="92" text-anchor="middle">{mil(corpus)} chunks</text>',
          f'<text x="99" y="112" text-anchor="middle" class="mut" font-size="10">SQLite · FTS5</text>',
          f'<text x="99" y="127" text-anchor="middle" class="mut" font-size="10">vetores · grafo</text>',
          f'<text x="99" y="150" text-anchor="middle" class="mut" font-size="10">'
          f'{mil(cum["nenhuma_superficie"])} nunca expostos</text>']

    # canal principal
    s += [f'<rect class="cx" x="250" y="40" width="196" height="62"/>',
          f'<text x="348" y="60" text-anchor="middle" font-weight="600">pool principal</text>',
          f'<text x="348" y="78" text-anchor="middle" class="mut" font-size="10">'
          f'ordenado por salience (soma aditiva)</text>',
          f'<text x="348" y="93" text-anchor="middle" font-size="10">'
          f'→ {N_SLOTS - FRESH} slots</text>']

    # canal de cobertura — o que carrega o mecanismo
    s += [f'<rect class="cx" x="250" y="118" width="196" height="86" '
          f'stroke="var(--cob)" stroke-width="2"/>',
          f'<text x="348" y="138" text-anchor="middle" font-weight="600" fill="var(--cob)">'
          f'pool de cobertura</text>',
          f'<text x="348" y="157" text-anchor="middle" font-size="10">'
          f'comparador LEXICOGRÁFICO</text>',
          f'<text x="348" y="172" text-anchor="middle" font-size="10">'
          f'(last_served ASC, salience DESC)</text>',
          f'<text x="348" y="192" text-anchor="middle" font-size="10">'
          f'→ até freshSlots = {FRESH} slots</text>']

    for y0, y1 in ((106, 71), (106, 160)):
        s.append(f'<line x1="174" y1="{y0}" x2="250" y2="{y1}" stroke="var(--box)" '
                 f'stroke-width="1.2"/>')

    # brief
    s += [f'<rect class="cx" x="522" y="40" width="234" height="164" '
          f'stroke="var(--brief)" stroke-width="2"/>',
          f'<text x="639" y="60" text-anchor="middle" font-weight="600" fill="var(--brief)">'
          f'superfície 1 — brief proativo</text>',
          f'<text x="639" y="78" text-anchor="middle" class="mut" font-size="10">'
          f'/api/brief · {N_SLOTS} itens, sempre · o agente não pede</text>']
    for i in range(N_SLOTS):
        x = 542 + i * 21
        cor = "var(--cob)" if i >= N_SLOTS - FRESH else "var(--box)"
        preenche = "var(--cob)" if i >= N_SLOTS - FRESH else "none"
        s.append(f'<rect x="{x}" y="90" width="16" height="22" rx="2" stroke="{cor}" '
                 f'fill="{preenche}" fill-opacity="0.25" stroke-width="1.4"/>')
    s += [f'<text x="639" y="130" text-anchor="middle" class="mut" font-size="10">'
          f'os {FRESH} verdes são o canal de cobertura</text>',
          f'<text x="639" y="152" text-anchor="middle" font-size="10">'
          f'{mil(cum["brief"])} chunks já expostos aqui</text>',
          f'<text x="639" y="170" text-anchor="middle" class="mut" font-size="10">'
          f'em 7 dias: {conc["distintos_7d"]} distintos em '
          f'{mil(conc["slots_7d"])} slots</text>',
          f'<text x="639" y="188" text-anchor="middle" class="mut" font-size="10">'
          f'top-10 = {conc["pct_top10"]:.1f}% dos slots</text>']
    s.append('<line x1="446" y1="122" x2="522" y2="122" stroke="var(--brief)" stroke-width="1.6"/>')

    # busca
    s += [f'<rect class="cx" x="522" y="226" width="234" height="86" '
          f'stroke="var(--busca)" stroke-width="2"/>',
          f'<text x="639" y="246" text-anchor="middle" font-weight="600" fill="var(--busca)">'
          f'superfície 2 — busca</text>',
          f'<text x="639" y="264" text-anchor="middle" class="mut" font-size="10">'
          f'sob demanda · o agente decide procurar</text>',
          f'<text x="639" y="286" text-anchor="middle" font-size="10">'
          f'{mil(cum["busca"])} chunks já expostos aqui</text>',
          f'<text x="639" y="304" text-anchor="middle" class="mut" font-size="10">'
          f'híbrido: BM25 + semântico + RRF</text>',
          f'<line x1="174" y1="140" x2="380" y2="269" stroke="var(--busca)" '
          f'stroke-width="1.2" stroke-dasharray="4 3"/>',
          f'<line x1="380" y1="269" x2="522" y2="269" stroke="var(--busca)" stroke-width="1.6"/>']

    # ─── a conta, e ela NÃO fecha ingenuamente ───────────────────────────────
    # 11.051 + 56.288 = 67.339, que excede o corpus em exatamente 152 — o número de
    # chunks servidos no brief e APAGADOS depois. A união conta o que já foi exposto
    # alguma vez (inclusive o que não existe mais); o complemento conta o que existe
    # hoje e nunca foi. São populações diferentes, e imprimir "união + nunca = corpus"
    # seria afirmar uma identidade falsa com ar de verificação.
    apagados = cum["servidos_no_brief_e_depois_apagados"]
    vivos_expostos = cum["uniao"] - apagados
    resid = vivos_expostos + cum["nenhuma_superficie"] - corpus
    if resid != 0:
        raise SystemExit(
            f"identidade não fecha nem descontando os apagados: "
            f"{vivos_expostos} + {cum['nenhuma_superficie']} − {corpus} = {resid}. "
            f"O artefato mudou de forma que esta figura não sabe descrever.")

    s += [f'<rect class="cx" x="24" y="332" width="732" height="80"/>',
          f'<text x="40" y="354" font-weight="600">'
          f'{cum["pct_nenhuma"]}% do corpus vivo nunca foi exposto: '
          f'{mil(cum["nenhuma_superficie"])} de {mil(corpus)}</text>',
          f'<text x="40" y="373" class="mut" font-size="10">'
          f'{mil(cum["brief"])} (brief) + {mil(cum["busca"])} (busca) '
          f'− {mil(cum["brief"] + cum["busca"] - cum["uniao"])} (interseção) '
          f'= {mil(cum["uniao"])} já expostos alguma vez. Não há terceira superfície: '
          f'"nunca exposto" é ausência de registro nas duas, não inferência.</text>',
          f'<text x="40" y="389" class="mut" font-size="10">'
          f'⚠️ {mil(cum["uniao"])} + {mil(cum["nenhuma_superficie"])} excede o corpus '
          f'em {apagados}: são chunks servidos e APAGADOS depois. Descontando-os, '
          f'{mil(vivos_expostos)} + {mil(cum["nenhuma_superficie"])} = {mil(corpus)}.</text>',
          f'<text x="40" y="405" class="mut" font-size="10">'
          f'⚠️ Dos nunca expostos, {mil(cum["invisiveis_que_passam_o_piso"])} passam o '
          f'piso de importância — elegíveis, e mesmo assim nunca chegaram.</text>']

    s.append("</svg>")
    open(a.out, "w").write("\n".join(s) + "\n")
    print(f"{a.out}: corpus={mil(corpus)} · união={mil(cum['uniao'])} "
          f"· nunca={cum['pct_nenhuma']}% · elegíveis invisíveis="
          f"{mil(cum['invisiveis_que_passam_o_piso'])}")


if __name__ == "__main__":
    main()
