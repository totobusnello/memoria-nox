#!/usr/bin/env python3
"""Sensibilidade ao washout — quanto tempo de borda de epoch é preciso descartar?

⚠️ ANALISE EXPLORATORIA, NAO PRE-ESPECIFICADA. Ela não entra no desfecho do
estudo e não altera nenhum número do `pilot_replay`. Existe para responder uma
pergunta que bloqueia uma decisão de desenho: **o washout de 2h basta?**

POR QUE A PERGUNTA IMPORTA AGORA
`SIZING-2026-08-14-v2.md` §4 mostra que encurtar o epoch é a única alavanca que
compra calendário sem vender MDE (24h→242 d, 8h→113 d). Mas o washout é FIXO em
2h: ele custa 8% de um epoch de 24h e 25% de um de 8h. Pior, a premissa de que
2h bastam para lavar o efeito do braço anterior foi calibrada para epochs de
24h e nunca foi verificada. Encurtar o epoch aproxima as trocas de braço, e uma
premissa não verificada fica mais exigida, não menos.

O QUE ESTE SCRIPT MEDE, E O QUE ELE NAO PODE MEDIR
Ele mede o perfil de `p0` (repeats/oportunidades) e da densidade de
oportunidades ao longo das horas desde a fronteira do epoch, no corpus do
replay. Se houver efeito de borda residual além de 2h, ele aparece como
gradiente nas primeiras horas pós-washout.

⚠️ LIMITE FUNDAMENTAL: no corpus do replay **todo epoch é controle** — nunca
houve troca de braço. Portanto isto NAO mede carry-over de tratamento. Mede o
que existe de estrutura temporal intra-epoch na ausência de intervenção: ritmo
de trabalho, sessões que atravessam a fronteira, efeitos de fuso. Um gradiente
aqui é evidência de que a fronteira do epoch não é um ponto neutro — o que é
condição NECESSARIA para o washout ser suficiente, não suficiente para
afirmá-lo. Ausência de gradiente não prova que 2h bastam sob tratamento;
presença de gradiente prova que 2h não bastam nem sem ele.

    python3 washout_sensitivity.py --episodes ... --verdicts ... --estrato-b-ids ...
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_replay as pr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--replicas", nargs="*", default=[])
    ap.add_argument("--bin-h", type=float, default=2.0, help="largura do bin, horas")
    a = ap.parse_args()

    instaveis = frozenset(pr.episodios_instaveis(a.replicas)) if a.replicas else frozenset()
    verdicts = pr.carregar_verdicts(Path(a.verdicts), instaveis)
    eps = pr.carregar_episodios(Path(a.episodes), verdicts)

    primeiro_failure: dict[str, object] = {}
    for e in sorted(eps, key=lambda x: x.ts):
        if e.estado == "failure" and (e.sig not in primeiro_failure
                                      or e.ts < primeiro_failure[e.sig]):
            primeiro_failure[e.sig] = e.ts
    from datetime import timedelta
    limiar = timedelta(hours=pr.EPOCH_H)

    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    # Sem filtro de washout: o ponto do exercicio e OLHAR a zona descartada.
    estrato_a = [e for e in eps if e.err]
    resto = [e for e in eps if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})

    oport: dict[int, float] = collections.defaultdict(float)
    repeat: dict[int, float] = collections.defaultdict(float)
    desconhecido: dict[int, int] = collections.defaultdict(int)
    # Contagens BRUTAS em paralelo. O peso HT amplifica o estrato B por ~5,2x,
    # o que infla qualquer n usado num teste de proporcao e produz significancia
    # onde nao ha. Todo teste abaixo roda no bruto; os pesos ficam para a
    # estimativa pontual, que e o que eles existem para corrigir.
    oport_n: dict[int, int] = collections.defaultdict(int)
    repeat_n: dict[int, int] = collections.defaultdict(int)
    for e in estrato_a + estrato_b:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar:
            continue
        b = int(e.offset_h // a.bin_h)
        if e.estado == "unknown":
            desconhecido[b] += 1
            continue
        oport[b] += peso[e.id]
        oport_n[b] += 1
        if e.estado == "failure":
            repeat[b] += peso[e.id]
            repeat_n[b] += 1

    def agreg(ls):
        o = sum(l["oportunidades"] for l in ls)
        r = sum(l["repeats"] for l in ls)
        n = sum(l["n_bruto"] for l in ls)
        rn = sum(l["repeats_bruto"] for l in ls)
        return {"oportunidades": round(o, 1), "repeats": round(r, 1),
                "p0": round(r / o, 4) if o else None,
                "n_bruto": n, "repeats_bruto": rn,
                "p0_bruto": round(rn / n, 4) if n else None}

    def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
        """IC de Wilson — não degenera com k=0 nem com n pequeno, ao contrário
        do intervalo normal, que devolve [0,0] e finge certeza."""
        if n == 0:
            return None
        p = k / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
        return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))

    def compara(nome: str, a_ls, b_ls) -> dict:
        """Diferença de proporções entre dois conjuntos de bins, no BRUTO."""
        ka, na = sum(l["repeats_bruto"] for l in a_ls), sum(l["n_bruto"] for l in a_ls)
        kb, nb = sum(l["repeats_bruto"] for l in b_ls), sum(l["n_bruto"] for l in b_ls)
        if not (na and nb):
            return {"comparacao": nome, "conclusivo": False}
        pa, pb = ka / na, kb / nb
        # Erro-padrão da diferença sob a hipótese de proporções independentes.
        se = (pa * (1 - pa) / na + pb * (1 - pb) / nb) ** 0.5
        dif = pa - pb
        return {
            "comparacao": nome,
            "p0_A": round(pa, 4), "n_A": na, "ic_A": wilson(ka, na),
            "p0_B": round(pb, 4), "n_B": nb, "ic_B": wilson(kb, nb),
            "diferenca": round(dif, 4),
            "ic_diferenca": [round(dif - 1.96 * se, 4), round(dif + 1.96 * se, 4)],
            "cruza_zero": bool(dif - 1.96 * se <= 0 <= dif + 1.96 * se),
        }

    bins = sorted(set(oport) | set(desconhecido))
    linhas = []
    for b in bins:
        o, r = oport[b], repeat[b]
        linhas.append({
            "bin": f"{b*a.bin_h:.0f}-{(b+1)*a.bin_h:.0f}h",
            "inicio_h": b * a.bin_h,
            "oportunidades": round(o, 1),
            "repeats": round(r, 1),
            "p0": round(r / o, 4) if o else None,
            "n_bruto": oport_n[b],
            "repeats_bruto": repeat_n[b],
            "p0_bruto": round(repeat_n[b] / oport_n[b], 4) if oport_n[b] else None,
            "unknown": desconhecido[b],
        })

    # ── p0 POR ESTRATO — a comparacao agregada e confundida ─────────────────
    # Primeira leitura desta analise concluiu "ha efeito de borda": p0 bruto de
    # 0,397 em 0-2h contra 0,316 em 2h+, IC da diferenca sem cruzar zero. Estava
    # ERRADO. A proporcao de estrato A varia por zona (37,5% em 0-2h contra
    # ~30% depois) e p0_A ~ 0,96 contra p0_B ~ 0,05 — logo a diferenca agregada
    # mede COMPOSICAO, nao borda. Aplicando a composicao de 2h+ a zona 0-2h:
    # 0,30*0,967 + 0,70*0,056 = 0,329, contra os 0,316 observados. O "efeito"
    # some.
    #
    # Dentro de cada estrato nao ha gradiente algum. Por isso o agregado fica
    # marcado como NAO USAR na saida, em vez de removido: quem reproduzir a
    # analise precisa ver a armadilha, nao um resultado limpo que esconde que
    # ela existe.
    zonas: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"A": 0, "B": 0, "repA": 0, "repB": 0})
    for e in estrato_a + estrato_b:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar or e.estado == "unknown":
            continue
        z = "0-2h" if e.offset_h < 2 else ("2-6h" if e.offset_h < 6 else "6h+")
        k = "A" if e.err else "B"
        zonas[z][k] += 1
        if e.estado == "failure":
            zonas[z]["rep" + k] += 1
    por_estrato = []
    for z in ("0-2h", "2-6h", "6h+"):
        d = zonas[z]
        n = d["A"] + d["B"]
        por_estrato.append({
            "zona": z, "pct_estrato_A": round(d["A"] / n, 4) if n else None,
            "n_A": d["A"], "p0_A": round(d["repA"] / d["A"], 4) if d["A"] else None,
            "n_B": d["B"], "p0_B": round(d["repB"] / d["B"], 4) if d["B"] else None,
        })

    # ── Incidencia de erro no UNIVERSO — o teste que de fato responde ───────
    # `is_error` e censo: nao ha amostragem, nao ha peso, nao ha composicao a
    # confundir. Se a fronteira do epoch tem efeito, ele aparece aqui limpo.
    inc_bins = [(0, 2), (2, 4), (4, 6), (6, 12), (12, 24)]
    incidencia = []
    for lo, hi in inc_bins:
        sub = [e for e in eps if lo <= e.offset_h < hi]
        k = sum(1 for e in sub if e.err)
        incidencia.append({"zona": f"{lo}-{hi}h", "n": len(sub), "erros": k,
                           "taxa": round(k / len(sub), 4) if sub else None,
                           "ic": wilson(k, len(sub))})

    dentro = [l for l in linhas if l["inicio_h"] < pr.WASHOUT_H]
    fora = [l for l in linhas if l["inicio_h"] >= pr.WASHOUT_H]

    # Primeiras 2h APOS o washout vs o resto do epoch — o teste que interessa:
    # se o washout de 2h fosse curto demais, a zona logo apos ele ainda
    # carregaria o efeito de borda.
    logo_apos = [l for l in linhas if pr.WASHOUT_H <= l["inicio_h"] < pr.WASHOUT_H + 4]
    restante = [l for l in linhas if l["inicio_h"] >= pr.WASHOUT_H + 4]

    print(json.dumps({
        "bin_h": a.bin_h,
        "washout_h": pr.WASHOUT_H,
        "perfil": linhas,
        "zona_descartada_0_2h": agreg(dentro),
        "zona_analisada_2h_em_diante": agreg(fora),
        "logo_apos_washout_2_6h": agreg(logo_apos),
        "restante_6h_em_diante": agreg(restante),
        "testes_confundidos_NAO_USAR": [
            compara("zona descartada (0-2h) vs analisada (2h+)", dentro, fora),
            compara("logo apos washout (2-6h) vs restante (6h+)", logo_apos, restante),
        ],
        "por_estrato": por_estrato,
        "incidencia_de_erro_no_universo": incidencia,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
