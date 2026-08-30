#!/usr/bin/env python3
"""
base-rate-h1c.py — congela `p0` e as oportunidades/dia numa JANELA FECHADA.

O dimensionamento de H1c (opção C da revisão de 2026-08-30) apoia-se em duas
quantidades medidas no archive vivo: a taxa base `p0` e as oportunidades por dia. Ambas
**crescem com o archive**, e citá-las como instante é a classe de defeito que já custou
caro neste projeto — o `583.973` era uma série viva citada sem o instante, e envelheceu
para falso enquanto ninguém olhava.

Este script fecha a janela e grava o artefato com os limites explícitos.

⚠️ **Os dias de borda são excluídos por serem PARCIAIS**, não por conveniência. O
primeiro dia do archive começa quando a retenção o alcançou, e o último é o dia
corrente, ainda em curso. Incluí-los mistura dias completos com frações e move a média
por um artefato de janela, não por mudança de comportamento.

⚠️ **`is_error` é proxy do veredito do painel.** O painel adjudica a τ=S1 e nem toda
ação com erro é falha adjudicada; `p0` aqui é, portanto, um teto da taxa real. Declarado
e não corrigido, porque corrigir exigiria o painel — que julgou um corpus que não existe
mais.

Uso:
  base-rate-h1c.py --episodios eps.jsonl [--out ...]
"""
import argparse, collections, json, statistics, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodios", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    eps = [json.loads(l) for l in open(a.episodios) if l.strip()]
    if not eps:
        print("⛔ corpus vazio", file=sys.stderr); return 1
    eps.sort(key=lambda e: e.get("ts", ""))
    dias = sorted({e["ts"][:10] for e in eps})
    if len(dias) < 3:
        print(f"⛔ só {len(dias)} dia(s) — excluir as duas bordas parciais deixaria "
              f"janela vazia ou de um dia, e uma média de um dia não é uma taxa base.",
              file=sys.stderr)
        return 1
    fechados = dias[1:-1]          # exclui borda inicial e o dia corrente
    jan = set(fechados)

    ja, op, rep, por_dia = set(), 0, 0, collections.Counter()
    for e in eps:                                   # o estado "já falhou" acumula desde
        s = e.get("sig_primary")                    # o começo do archive: uma oportunidade
        d = e["ts"][:10]                            # do dia N depende de falhas anteriores,
        if s in ja and d in jan:                    # inclusive fora da janela fechada.
            op += 1; por_dia[d] += 1
            if e.get("is_error"): rep += 1
        if e.get("is_error"): ja.add(s)

    if op == 0:
        print("⛔ zero oportunidades na janela fechada", file=sys.stderr); return 1
    vals = [por_dia.get(d, 0) for d in fechados]
    saida = {
        "gerado_por": "measurement/base-rate-h1c.py",
        "JANELA_FECHADA": {"de": fechados[0], "ate": fechados[-1], "dias": len(fechados)},
        "bordas_excluidas_por_serem_parciais": [dias[0], dias[-1]],
        "oportunidades": op,
        "falhas_repetidas_proxy_is_error": rep,
        "p0": round(rep / op, 4),
        "oportunidades_por_dia": {
            "mediana": statistics.median(vals),
            "media": round(op / len(fechados), 1),
            "min": min(vals), "max": max(vals),
        },
        "p0_e_um_TETO_porque": "is_error é proxy do veredito do painel a τ=S1",
        "corpus": "archive VIVO — o congelado do CORPUS-FREEZE.md não existe mais",
    }
    # ⚠️ Guarda: uma janela fechada cuja variação diária é enorme não sustenta uma
    # média como parâmetro de dimensionamento. Reportar sem isso seria dar ao número
    # uma estabilidade que ele não tem.
    if vals and min(vals) * 4 < max(vals):
        saida["ATENCAO_VARIACAO"] = (
            f"oportunidades/dia variam {min(vals)}–{max(vals)} na janela fechada "
            f"({max(vals)/max(1,min(vals)):.1f}×). A média é frágil como parâmetro de "
            f"dimensionamento e o cálculo de potência deve ser lido como ordem de "
            f"grandeza.")
    print(json.dumps(saida, indent=2, ensure_ascii=False))
    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
    return 0

if __name__ == "__main__":
    sys.exit(main())
