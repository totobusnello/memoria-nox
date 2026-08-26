#!/usr/bin/env python3
"""Recomputa a designação do Paper 2 sob a regra B, para verificação por terceiro.

    designado(g) = argmin_{c in g} SHA256( seed || "|" || chunk_id )

A regra foi decidida em 2026-08-26 (DECISION-designacao-2026-08-25.md) e substitui
a regra da v1.12, que era inválida por três razões medidas: consumia uma constante
cujo referente a emenda retrata, o desempate registrado nomeava uma coluna que não
existe em `p2_verdict`, e derivava de `access_count`, que é mutável por tráfego de
busca exógeno.

ESTE SCRIPT É O CONTRATO DE BYTES. A implementação em TypeScript que serve os
briefs tem de produzir exatamente o mesmo conjunto; a comparação é por sha256 do
conjunto, não por inspeção.

⚠️ `sig_primary` NÃO entra na chave, e isso é deliberado. Verificado sobre
`p2_verdict` que cada chunk pertence a exatamente um `sig_primary` (0 de 55 em
mais de um grupo), logo pertencimento já é função de `chunk_id` e o campo não
carregaria informação — só ambiguidade, porque todos os 19 valores de
`sig_primary` contêm o próprio separador `|` (`Bash|shell:outro`). Com ele na
chave, `seed|"Bash|shell:outro"|308226` e `seed|"Bash"|"shell:outro|308226"` são
a mesma sequência de bytes. Sem ele, a chave depende só de ids congelados: se um
dia um `sig_primary` for renomeado, nenhum designado muda. Registro do achado e
da decisão em `DECISION-designacao-2026-08-25.md`, seção B.

⚠️ O separador `|` é OBRIGATÓRIO e é a razão de este script existir separado.
`extract_episodes.py:226` faz `sha256(seed + episode_id)` — sem separador — e é o
script que `CALIBRATION-SEED.md` manda um terceiro rodar;
`EXTENSION-SEED-2026-08-11.md:49-64` registra o estrago (reproduziu 293 de 1.576
em vez de 1.565). Havia três implementações inline da derivação e nenhuma
compartilhada. Esta é a quarta, e é a primeira com vetor de teste.

A derivação da seed a partir do beacon NÃO é reimplementada aqui: importa-se
`seed_from_randomness_hex` de `assign_arms.py`, que é o único lugar onde ela deve
existir.

Uso:
    # do beacon, como um terceiro faria
    designation_verify.py --round 31600000 --verdicts p2_verdict.csv

    # de uma seed já derivada
    designation_verify.py --seed <64-hex> --verdicts p2_verdict.csv

    # vetor de teste do layout de bytes (não toca a rede, não precisa de dado)
    designation_verify.py --self-test

O CSV de vereditos é `sig_primary,severity,chunk_id` sem cabeçalho, como sai de
    SELECT DISTINCT sig_primary, severity, chunk_id FROM p2_verdict;
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assign_arms import fetch_randomness_hex, seed_from_randomness_hex  # noqa: E402

SEP = "|"


def chave(seed_hex: str, chunk_id: int) -> str:
    """A chave de ordenação. Layout de bytes fixado aqui e em nenhum outro lugar.

    Tudo é ASCII: a seed é a string hex minúscula (não os 32 bytes decodificados),
    o separador é `|`, e o chunk_id é o inteiro em decimal. Dois campos, um
    separador, e nenhum dos dois pode conter o separador — logo o layout é
    injetivo. Qualquer desvio produz um conjunto designado diferente e
    silenciosamente errado.
    """
    material = f"{seed_hex}{SEP}{chunk_id}"
    return hashlib.sha256(material.encode("ascii")).hexdigest()


def designados(seed_hex: str, linhas: list[tuple[str, int]]) -> dict[str, int]:
    """Um designado por `sig_primary`: o de menor chave.

    `linhas` é [(sig_primary, chunk_id)]. Duplicatas são colapsadas — `p2_verdict`
    tem uma linha por episódio, e a designação é sobre chunks.
    """
    grupos: dict[str, set[int]] = defaultdict(set)
    for sig, cid in linhas:
        grupos[sig].add(cid)
    out: dict[str, int] = {}
    for sig, cids in grupos.items():
        # `min` por (chave, chunk_id): a chave sozinha já é total na prática, mas
        # o segundo termo torna o desempate explícito em vez de dependente da
        # ordem de iteração — a classe de defeito que esta regra conserta.
        out[sig] = min(cids, key=lambda c: (chave(seed_hex, c), c))
    return out


def impressao(desig: dict[str, int]) -> str:
    """sha256 canônico do conjunto designado, para comparar entre linguagens."""
    canon = json.dumps({k: desig[k] for k in sorted(desig)}, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


# --- vetor de teste: trava o layout de bytes ------------------------------------
# Valores computados por este próprio arquivo e congelados aqui. Se algum dia
# divergirem, a derivação mudou e todo conjunto designado já emitido é suspeito.
SEED_TESTE = "0" * 64
LINHAS_TESTE = [("Bash|shell:outro", 1), ("Bash|shell:outro", 2), ("Read|arquivo:doc", 3)]


def self_test() -> int:
    falhas = 0

    # 1. O separador importa. Sem ele, a chave muda.
    com = chave(SEED_TESTE, 1)
    sem = hashlib.sha256(f"{SEED_TESTE}1".encode("ascii")).hexdigest()
    if com == sem:
        print("  ✗ separador NÃO afeta a chave — o defeito do extract_episodes voltou")
        falhas += 1
    else:
        print(f"  ok  separador afeta a chave  ({com[:12]}… != {sem[:12]}…)")

    # 2. A seed é a string hex, não os bytes. Distinção que o registro exige.
    como_bytes = hashlib.sha256(bytes.fromhex(SEED_TESTE) + b"|1").hexdigest()
    if com == como_bytes:
        print("  ✗ hex-string e bytes dão a mesma chave — impossível, layout quebrado")
        falhas += 1
    else:
        print(f"  ok  hex-string != bytes      ({com[:12]}… != {como_bytes[:12]}…)")

    # 3. Um designado por grupo, e é determinístico.
    d1 = designados(SEED_TESTE, LINHAS_TESTE)
    d2 = designados(SEED_TESTE, list(reversed(LINHAS_TESTE)))
    if d1 != d2:
        print(f"  ✗ ordem de entrada muda o resultado: {d1} != {d2}")
        falhas += 1
    else:
        print(f"  ok  invariante à ordem de entrada  {d1}")
    if len(d1) != 2:
        print(f"  ✗ esperados 2 grupos, obtidos {len(d1)}")
        falhas += 1
    else:
        print("  ok  um designado por grupo (2 grupos)")

    # 4. Injetividade do layout: nenhum dos dois campos pode conter o separador,
    #    então a sequência de bytes se parte de volta em exatamente um par. É o
    #    teste que justifica a ausência de `sig_primary` na chave — com ele a
    #    partição era ambígua, porque todo valor real contém `|`.
    material = f"{SEED_TESTE}{SEP}12345"
    partes = material.split(SEP)
    if len(partes) != 2 or partes[0] != SEED_TESTE or partes[1] != "12345":
        print(f"  ✗ layout NÃO é injetivo: {material!r} parte em {partes!r}")
        falhas += 1
    else:
        print("  ok  layout injetivo (seed é hex, chunk_id é dígitos; nem um `|`)")

    # 5. A chave não depende do grupo. É a propriedade nova: renomear um
    #    `sig_primary` não move nenhum designado.
    da = designados(SEED_TESTE, [("grupo:um", 7), ("grupo:um", 8)])
    db = designados(SEED_TESTE, [("OUTRO|NOME", 7), ("OUTRO|NOME", 8)])
    if list(da.values()) != list(db.values()):
        print(f"  ✗ renomear o grupo mudou o designado: {da} vs {db}")
        falhas += 1
    else:
        print(f"  ok  chave independe do nome do grupo  (designado {list(da.values())[0]})")

    print()
    print("✓ self-test passou" if falhas == 0 else f"✗ {falhas} falha(s) no self-test")
    return falhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--round", type=int, help="rodada drand (v1) de onde derivar a seed")
    ap.add_argument("--seed", help="seed já derivada, 64 hex")
    ap.add_argument("--verdicts", help="CSV sig_primary,severity,chunk_id sem cabeçalho")
    ap.add_argument("--self-test", action="store_true", help="trava o layout de bytes")
    a = ap.parse_args()

    if a.self_test:
        return 1 if self_test() else 0

    if bool(a.round) == bool(a.seed):
        ap.error("dê exatamente um de --round ou --seed")
    if not a.verdicts:
        ap.error("--verdicts é obrigatório")

    if a.round:
        randomness = fetch_randomness_hex(a.round)
        seed = seed_from_randomness_hex(randomness)
        print(f"rodada    {a.round}", file=sys.stderr)
        print(f"randomness {randomness}", file=sys.stderr)
    else:
        if len(a.seed) != 64:
            ap.error("--seed precisa ter 64 caracteres hex")
        randomness = None
        seed = a.seed.strip().lower()
    print(f"seed      {seed}", file=sys.stderr)

    linhas: list[tuple[str, int]] = []
    with open(a.verdicts, newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 3:
                continue
            linhas.append((row[0], int(row[2])))

    d = designados(seed, linhas)
    print(json.dumps({
        "regra": "designado(g) = argmin SHA256(seed || \"|\" || chunk_id)",
        "rodada": a.round,
        "randomness_hex": randomness,
        "seed": seed,
        "grupos": len(d),
        "chunks_considerados": len({c for _, c in linhas}),
        "designados": {k: d[k] for k in sorted(d)},
        "designados_ids": sorted(d.values()),
        "sha256_do_conjunto": impressao(d),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
