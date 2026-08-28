#!/usr/bin/env python3
"""
sensibilidade-da-designacao.py — o teto de 17/350 depende de QUAIS chunks foram designados?

A regra de designação (opção B, `DECISION-designacao-2026-08-25.md`) escolhe **um chunk
por grupo de assinatura** por `argmin SHA256(seed ‖ "|" ‖ chunk_id)`. A escolha dentro do
grupo é, por construção, **arbitrária** — é sorteio. A pergunta que isso levanta e que o
paper ainda não respondeu:

> o teto de alcançabilidade de 17/350 é propriedade do comparador, ou é acidente de
> **qual** dos chunks de cada grupo o sorteio pegou?

Se o teto balança muito entre seeds, o `4,86%` do §5.7 é um ponto amostral disfarçado de
constante, e o paper tem de reportar a dispersão em vez do ponto. Se não balança, o
número é robusto à arbitrariedade e o §5.7 fica mais forte.

⚠️ **Seeds não podem ser escolhidas à mão.** A `randomness` do beacon original já é
pública, então eu poderia computar offline o resultado de vários rótulos e reportar o que
me favorece — é a mesma pescaria que a rota (a) do plano da designação existia para
impedir. Duas defesas aqui, e as duas importam:

1. a família de seeds é **derivada deterministicamente** de uma frase fixa escrita neste
   arquivo (`FRASE`), então um terceiro regenera exatamente as mesmas;
2. **todas** as seeds da família são reportadas. Nenhuma é descartada. Um resultado
   omitido reintroduz a pescaria por trás da porta.

⚠️ Esta é uma análise de sensibilidade sobre a arbitrariedade **dentro do grupo**. Ela
mantém fixa a população do estudo (os 55 chunks em 19 grupos, definidos pelo painel) e
varia só quem, dentro de cada grupo, recebe o bônus. Ela **não** responde se o teto
depende do painel ter definido essa população — essa é outra pergunta, e exige mexer em
`p2_verdict`, não na seed.

Uso:
  sensibilidade-da-designacao.py --verdicts verdicts.csv --k 8 --saida-dir designacoes/
onde verdicts.csv é `sig_primary,severity,chunk_id` sem cabeçalho, como sai de
  SELECT DISTINCT sig_primary, severity, chunk_id FROM p2_verdict;
"""
import argparse
import csv
import hashlib
import json
import os
import sys

# Frase fixa, escrita antes de qualquer rodada. Trocar isto invalida a análise:
# um terceiro que regenere com outra frase obtém outras seeds e outro resultado.
FRASE = "paper2|sensibilidade-da-designacao|2026-08-28"


def seed_da_familia(i: int) -> str:
    return hashlib.sha256(f"{FRASE}|{i}".encode("ascii")).hexdigest()


def chave(seed_hex: str, chunk_id: int) -> str:
    """Idêntica a `designation_verify.py:chave` — seed em hex ASCII, separador `|`,
    `sig_primary` FORA da chave (ver o cabeçalho daquele arquivo: há assinatura que
    contém o próprio separador, e incluí-la tornaria a chave ambígua)."""
    return hashlib.sha256(f"{seed_hex}|{chunk_id}".encode("ascii")).hexdigest()


def designados(seed_hex: str, linhas):
    por_grupo = {}
    for sig, cid in linhas:
        por_grupo.setdefault(sig, set()).add(cid)
    return {sig: min(cids, key=lambda c: chave(seed_hex, c))
            for sig, cids in sorted(por_grupo.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--saida-dir", required=True)
    ap.add_argument("--referencia", help="DESIGNATION real, para conferir que a "
                                         "derivação local reproduz a publicada")
    a = ap.parse_args()

    linhas = []
    with open(a.verdicts) as f:
        for r in csv.reader(f):
            if len(r) < 3 or not r[2].strip():
                continue
            linhas.append((r[0], int(r[2])))

    grupos = len({s for s, _ in linhas})
    chunks = len({c for _, c in linhas})
    print(f"população: {chunks} chunks em {grupos} grupos")

    # ── âncora: a derivação local tem de reproduzir a designação PUBLICADA ──
    # Sem isto, as designações alternativas poderiam vir de uma regra diferente da que
    # produziu o 17/350, e a comparação seria entre coisas incomparáveis.
    if a.referencia:
        ref = json.load(open(a.referencia))
        meu = designados(ref["seed"], linhas)
        if meu != ref["designados"]:
            dif = {k: (v, ref["designados"].get(k)) for k, v in meu.items()
                   if ref["designados"].get(k) != v}
            print(f"⛔ derivação local NÃO reproduz a publicada em {len(dif)} grupo(s):",
                  file=sys.stderr)
            for k, (x, y) in list(dif.items())[:5]:
                print(f"     {k}: local={x} publicado={y}", file=sys.stderr)
            return 1
        print(f"âncora: derivação local reproduz a designação publicada "
              f"({len(meu)} grupos) ✓")

    os.makedirs(a.saida_dir, exist_ok=True)
    manifesto = {"frase": FRASE, "k": a.k, "grupos": grupos, "chunks": chunks,
                 "designacoes": []}
    for i in range(1, a.k + 1):
        s = seed_da_familia(i)
        d = designados(s, linhas)
        doc = {"seed": s, "designados": d,
               "origem": f"sensibilidade: SHA256({FRASE}|{i})",
               "regra": "argmin SHA256(seed || '|' || chunk_id) por sig_primary"}
        p = os.path.join(a.saida_dir, f"DESIGNATION-sens-{i:02d}.json")
        cru = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True).encode()
        open(p, "wb").write(cru)
        manifesto["designacoes"].append({
            "i": i, "arquivo": os.path.basename(p),
            "sha256": hashlib.sha256(cru).hexdigest(),
            "seed": s, "n_designados": len(set(d.values())),
        })
        print(f"  {i:02d}  {os.path.basename(p)}  sha256={hashlib.sha256(cru).hexdigest()[:12]}…"
              f"  designados={len(set(d.values()))}")

    # nenhuma designação pode ter menos de um por grupo
    ruins = [m for m in manifesto["designacoes"] if m["n_designados"] != grupos]
    if ruins:
        print(f"⛔ {len(ruins)} designação(ões) com contagem != {grupos}", file=sys.stderr)
        return 1

    mp = os.path.join(a.saida_dir, "MANIFESTO.json")
    json.dump(manifesto, open(mp, "w"), indent=2, ensure_ascii=False)
    print(f"→ {mp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
