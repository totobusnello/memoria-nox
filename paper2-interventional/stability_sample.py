#!/usr/bin/env python3
"""Sorteia a amostra do teste de estabilidade intra-painelista (STABILITY-TEST.md).

A seed vem do beacon drand no round DECLARADO EM 2026-08-13T13:47Z, antes de o
round existir. Rodar este script depois nao muda nada: o sorteio e deterministico
dado o round, e qualquer terceiro reproduz baixando o mesmo round.

Uso:
    python3 stability_sample.py            # sorteia e grava o jsonl de entrada
    python3 stability_sample.py --check    # so verifica se o round ja saiu

Depois:
    python3 run_panel.py --episodes <saida> --only moonshot --workers 2 \
        --out ~/.paper2-verdicts/extensao-moonshot-stability-6373493.jsonl
    python3 stability_sample.py --score    # compara com os vereditos originais
"""
import argparse
import glob
import json
import pathlib
import random
import sys
import urllib.request

ROUND = 6373493  # DECLARADO 2026-08-13T13:47Z, quando o latest era 6373253
CHAIN_PREFIX = "8990e7a9aaed2ffe"  # drand mainnet, periodo 30s
N = 100
V = pathlib.Path.home() / ".paper2-verdicts"
BACKLOG_GLOB = str(V / "extensao-moonshot-cycle-*.jsonl")
OUT_SAMPLE = V / f"stability-sample-{ROUND}.jsonl"
OUT_VERDICTS = V / f"extensao-moonshot-stability-{ROUND}.jsonl"
PANELIST = "moonshot"


def fetch_round(rnd):
    url = f"https://api.drand.sh/public/{rnd}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def load_originals():
    """episode_id -> (verdict, arquivo, ordem). Detecta duplicatas da colisao."""
    seen = {}
    dups = set()
    for f in sorted(glob.glob(BACKLOG_GLOB)):
        mtime = pathlib.Path(f).stat().st_mtime
        for line in open(f):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") != "ok" or r.get("panelist") != PANELIST:
                continue
            eid = r["episode_id"]
            if eid in seen:
                dups.add(eid)
                # mantem o cronologicamente anterior (regra do STABILITY-TEST.md §6)
                if mtime < seen[eid][2]:
                    seen[eid] = (r.get("verdict"), f, mtime)
            else:
                seen[eid] = (r.get("verdict"), f, mtime)
    return seen, dups


def episodes_by_id():
    src = V / "extensao-moonshot-restante.jsonl"
    return {json.loads(l)["episode_id"]: json.loads(l) for l in open(src) if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()

    originals, dups = load_originals()

    if a.score:
        if not OUT_VERDICTS.exists():
            sys.exit(f"ainda nao existe: {OUT_VERDICTS}")
        agree = disagree = 0
        transitions = {}
        for line in open(OUT_VERDICTS):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") != "ok":
                continue
            eid = r["episode_id"]
            if eid not in originals:
                continue
            before, after = originals[eid][0], r.get("verdict")
            if before == after:
                agree += 1
            else:
                disagree += 1
            transitions[(before, after)] = transitions.get((before, after), 0) + 1
        n = agree + disagree
        if n == 0:
            sys.exit("nenhum par comparavel")
        p = agree / n
        # IC de Wilson 95%
        z = 1.959963985
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
        print(f"pares comparados: {n}")
        print(f"concordam: {agree}  divergem: {disagree}")
        print(f"estabilidade: {p:.4f}  IC95 Wilson: [{c - h:.4f} ; {c + h:.4f}]")
        print("transicoes (antes -> depois):")
        for (b, af), k in sorted(transitions.items(), key=lambda x: -x[1]):
            flag = "" if b == af else "   <-- divergencia"
            print(f"  {b} -> {af}: {k}{flag}")
        return

    try:
        beacon = fetch_round(ROUND)
    except Exception as e:
        sys.exit(f"round {ROUND} indisponivel ({e}) — ainda nao saiu? Espere e repita.")
    rnd_hex = beacon["randomness"]
    print(f"round {ROUND} OK, randomness = {rnd_hex[:24]}...")
    if a.check:
        return

    # populacao: adjudicados ok pelo moonshot, EXCLUINDO os 40 da colisao (§3)
    pool = sorted(eid for eid in originals if eid not in dups)
    print(f"populacao: {len(pool)} (excluidos {len(dups)} da colisao)")
    if len(pool) < N:
        sys.exit(f"populacao menor que N={N}")

    rng = random.Random(int(rnd_hex, 16))
    picked = rng.sample(pool, N)

    eps = episodes_by_id()
    missing = [e for e in picked if e not in eps]
    if missing:
        sys.exit(f"{len(missing)} sorteados sem episodio de origem — abortar, corpus inconsistente")

    OUT_SAMPLE.write_text(
        "\n".join(json.dumps(eps[e], ensure_ascii=False, sort_keys=True) for e in picked) + "\n"
    )
    print(f"gravado: {OUT_SAMPLE}  ({N} episodios)")
    print("\nproximo passo:")
    print(f"  python3 run_panel.py --episodes {OUT_SAMPLE} --only {PANELIST} \\")
    print(f"      --workers 2 --out {OUT_VERDICTS}")
    print("  python3 stability_sample.py --score")


if __name__ == "__main__":
    main()
