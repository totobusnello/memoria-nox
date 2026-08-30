#!/usr/bin/env python3
"""assignment_derive.py — deriva a atribuição de braços da rodada drand declarada.

Implementa exatamente a regra de `ASSIGN-SEED-2026-08-30.md`, e nada além dela:

    seed   = SHA256( ascii_hex(randomness_de_R) )
    key(e) = SHA256( ascii(seed) || "|" || ascii(epoch_index) )

Os 234 epochs são ordenados por `key` crescente; os primeiros 117 recebem controle e os
três blocos de 39 seguintes recebem os braços 1, 2 e 3.

⚠️ O separador `|` é obrigatório. `extract_episodes.py:226` faz `sha256(seed + id)` sem
ele e `EXTENSION-SEED-2026-08-11.md` registra o estrago — 293 episódios reproduzidos em
vez de 1.565. Esta é a quarta implementação da derivação no repositório, e a primeira que
publica vetor de teste junto; `--self-test` falha se o separador for removido.

⚠️ Este script NÃO decide nada. A regra foi travada antes de a rodada existir, e ele
apenas a executa. Se a saída divergir do bloco de verificação por terceiro publicado na
declaração, é a declaração que vale e o estudo não começa.

Uso:
  assignment_derive.py --self-test
  assignment_derive.py --round 31774052 [--out ASSIGNMENT.json]
  assignment_derive.py --seed <hex64>            # para conferência offline
"""
import argparse
import hashlib
import json
import sys
import urllib.request

CHAIN = "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971"
N_EPOCHS = 234
ALOC = (("controle", 117), ("tratamento_1", 39), ("tratamento_2", 39), ("tratamento_3", 39))
SEP = "|"


def chave(seed: str, epoch: int, sep: str = SEP) -> str:
    return hashlib.sha256(f"{seed}{sep}{epoch}".encode("ascii")).hexdigest()


def atribuir(seed: str, sep: str = SEP) -> dict[int, str]:
    ordem = sorted(range(1, N_EPOCHS + 1), key=lambda e: chave(seed, e, sep))
    fora: dict[int, str] = {}
    i = 0
    for nome, quantos in ALOC:
        for e in ordem[i:i + quantos]:
            fora[e] = nome
        i += quantos
    assert i == N_EPOCHS, f"alocação soma {i}, não {N_EPOCHS}"
    return fora


def sha_da_atribuicao(a: dict[int, str]) -> str:
    seq = ",".join(f"{e}:{a[e]}" for e in range(1, N_EPOCHS + 1))
    return hashlib.sha256(seq.encode("ascii")).hexdigest()


def buscar_randomness(rodada: int) -> str:
    url = f"https://api.drand.sh/{CHAIN}/public/{rodada}"
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.load(r)
    if "randomness" not in d:
        raise SystemExit("resposta sem `randomness` — o endpoint v2 não a devolve; use v1")
    if d.get("round") != rodada:
        raise SystemExit(f"o beacon devolveu a rodada {d.get('round')}, não {rodada}")
    return d["randomness"]


def self_test() -> None:
    seed = "00" * 32
    a = atribuir(seed)
    assert len(a) == N_EPOCHS, "nem todo epoch recebeu braço"
    from collections import Counter
    c = Counter(a.values())
    assert c == {n: q for n, q in ALOC}, f"alocação saiu {dict(c)}"
    print("  ok  todos os 234 epochs receberam braço, na alocação 117/39/39/39")

    # o separador importa: sem ele a atribuição MUDA. Se este teste passar com
    # `sep=""`, o layout é ambíguo e o defeito de 2026-08-11 está de volta.
    b = atribuir(seed, sep="")
    assert a != b, "remover o separador não mudou nada — o layout não é injetivo"
    print("  ok  o separador `|` é carregador: removê-lo muda a atribuição")

    # determinismo
    assert sha_da_atribuicao(a) == sha_da_atribuicao(atribuir(seed))
    print(f"  ok  determinístico  (sha {sha_da_atribuicao(a)[:16]}…)")

    # seeds distintas dão atribuições distintas
    assert sha_da_atribuicao(a) != sha_da_atribuicao(atribuir("11" * 32))
    print("  ok  seeds distintas dão atribuições distintas")
    print("\n✓ self-test passou")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int)
    ap.add_argument("--seed")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if bool(a.round) == bool(a.seed):
        ap.error("dê exatamente um de --round ou --seed")

    rand = None
    if a.round:
        rand = buscar_randomness(a.round)
        seed = hashlib.sha256(rand.encode("ascii")).hexdigest()
    else:
        seed = a.seed.strip().lower()
        if len(seed) != 64 or not all(c in "0123456789abcdef" for c in seed):
            ap.error("--seed deve ser 64 hex minúsculos")

    atrib = atribuir(seed)
    saida = {
        "gerado_por": "assignment_derive.py",
        "declaracao": "ASSIGN-SEED-2026-08-30.md, commit 57980ed pushado 2026-08-30T21:18:35Z",
        "beacon": {"chain": CHAIN, "rodada": a.round, "randomness_hex": rand},
        "seed": seed,
        "regra": 'braço(e) por ordem crescente de SHA256(seed || "|" || epoch), 117/39/39/39',
        "n_epochs": N_EPOCHS,
        "alocacao": {n: q for n, q in ALOC},
        "atribuicao": {str(e): atrib[e] for e in range(1, N_EPOCHS + 1)},
        "sha256_da_atribuicao": sha_da_atribuicao(atrib),
    }
    txt = json.dumps(saida, ensure_ascii=False, indent=2)
    if a.out:
        import pathlib
        p = pathlib.Path(a.out)
        if p.exists():
            raise SystemExit(f"{p} já existe — o T_seed_assign não se sobrescreve")
        p.write_text(txt + "\n", encoding="utf-8")
        print(f"gravado: {p}")
        print(f"sha256_da_atribuicao: {saida['sha256_da_atribuicao']}")
    else:
        print(txt)


if __name__ == "__main__":
    sys.exit(main())
