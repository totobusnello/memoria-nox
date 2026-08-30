#!/usr/bin/env python3
"""assignment_to_serving.py — translate the canonical assignment into the shape the
serving code actually reads.

Two shapes exist for the same fact, and nothing in the repository connected them:

    canonical (assign_arms.py, deposited in v1.12)
        {"atribuicao": {"2026-09-01": "w4", "2026-09-02": "control", ...}}

    consumed (src/paper2/brief-outcome.ts :: resolverBraco)
        {"epochs": [{"epoch_inicio": "2026-09-01", "arm": "treatment", "w": 4.0}, ...]}

`resolverBraco` does `parsed.epochs ?? []` and then `find(l => l.epoch_inicio === ...)`.
Handed the canonical file it finds an empty list, fails every lookup, and returns
CONTROL with a reason string — silently, for every brief. That is not a hypothetical:
it happened in production on 2026-08-30, and the log showed `servido: control` in 7 of
7 decisions while the process environment said `NOX_P2_OUTCOME=active`.

⚠️ This script MUST NOT decide anything. The assignment was fixed by
`assign_arms.py assign --round 31774052 --start 2026-09-01 --epochs 234`, under the
stratified rule registered in the pre-registration and deposited in v1.12 — two weeks
before the drand round was drawn. This is a pure relabelling:

    control -> {"arm": "control",   "w": 0}
    w2      -> {"arm": "treatment", "w": 2.0}
    w4      -> {"arm": "treatment", "w": 4.0}
    w7.5    -> {"arm": "treatment", "w": 7.5}

The dose band `w ∈ {2.0, 4.0, 7.5}` is the one locked on 2026-08-16. The superseded
band it replaced is deliberately not written here as a set: `claims_check.py` sweeps for
it, and a quotation is indistinguishable from a live claim to a regex. It was replaced
after the two lower arms were measured to reach exactly zero.

`--check` re-derives the mapping in the opposite direction and fails if any epoch does
not round-trip, so a typo in the table above cannot survive.

Usage:
  assignment_to_serving.py --in ASSIGNMENT.json --out ASSIGNMENT-SERVING.json
  assignment_to_serving.py --in ASSIGNMENT.json --check ASSIGNMENT-SERVING.json
"""
import argparse
import hashlib
import json
import pathlib
import sys

# group -> (arm, w). The only judgement in this file, and it is a relabelling.
TABELA = {
    "control": ("control", 0),
    "w2": ("treatment", 2.0),
    "w4": ("treatment", 4.0),
    "w7.5": ("treatment", 7.5),
}
INVERSA = {("control", 0): "control", ("treatment", 2.0): "w2",
           ("treatment", 4.0): "w4", ("treatment", 7.5): "w7.5"}


def traduzir(canon: dict) -> dict:
    at = canon["atribuicao"]
    desconhecidos = sorted(set(at.values()) - set(TABELA))
    if desconhecidos:
        raise SystemExit(f"grupo(s) sem tradução: {desconhecidos} — a banda mudou?")
    epochs = []
    for data in sorted(at):
        arm, w = TABELA[at[data]]
        epochs.append({"epoch_inicio": data, "arm": arm, "w": w})
    return {
        "_nota": ("forma consumida por src/paper2/brief-outcome.ts::resolverBraco. "
                  "A FONTE é ASSIGNMENT.json (assign_arms.py); este arquivo é uma "
                  "tradução mecânica, verificável por assignment_to_serving.py --check."),
        "fonte": {
            "arquivo": "ASSIGNMENT.json",
            "round": canon.get("round"),
            "seed": canon.get("seed"),
            "esquema": canon.get("esquema"),
            "script_sha256": canon.get("script_sha256"),
        },
        "epochs": epochs,
    }


def conferir(canon: dict, servido: dict) -> list[str]:
    """Round-trip: a forma consumida tem de reconstruir a canônica, epoch a epoch."""
    fails = []
    at = canon["atribuicao"]
    eps = {e["epoch_inicio"]: e for e in servido.get("epochs", [])}
    if set(eps) != set(at):
        so_canon, so_serv = sorted(set(at) - set(eps)), sorted(set(eps) - set(at))
        if so_canon: fails.append(f"epochs só na canônica: {len(so_canon)} (ex.: {so_canon[:2]})")
        if so_serv: fails.append(f"epochs só na servida: {len(so_serv)} (ex.: {so_serv[:2]})")
    for data in sorted(set(at) & set(eps)):
        e = eps[data]
        volta = INVERSA.get((e["arm"], e["w"]))
        if volta != at[data]:
            fails.append(f"{data}: servida diz {e['arm']}/w={e['w']} -> {volta}, "
                         f"canônica diz {at[data]}")
    n_trat = sum(1 for e in eps.values() if e["arm"] == "treatment")
    n_ctrl = sum(1 for e in eps.values() if e["arm"] == "control")
    if (n_ctrl, n_trat) != (117, 117):
        fails.append(f"alocação saiu {n_ctrl} controle / {n_trat} tratamento, "
                     f"esperado 117/117 (117 + 39·3)")
    for e in eps.values():
        if e["arm"] == "treatment" and e["w"] not in (2.0, 4.0, 7.5):
            fails.append(f"{e['epoch_inicio']}: w={e['w']} fora da banda travada")
        if e["arm"] == "control" and e["w"] != 0:
            fails.append(f"{e['epoch_inicio']}: controle com w={e['w']}, esperado 0")
    return fails


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="entrada", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check")
    a = ap.parse_args()
    canon = json.loads(pathlib.Path(a.entrada).read_text(encoding="utf-8"))

    if a.check:
        servido = json.loads(pathlib.Path(a.check).read_text(encoding="utf-8"))
        fails = conferir(canon, servido)
        if fails:
            print("\n".join("  🔴 " + f for f in fails))
            raise SystemExit(f"\n{len(fails)} divergência(s)")
        print(f"  ok  {len(servido['epochs'])} epochs voltam à canônica, um a um")
        print("  ok  117 controle / 117 tratamento, banda {2.0, 4.0, 7.5}")
        return

    if not a.out:
        ap.error("dê --out ou --check")
    saida = traduzir(canon)
    fails = conferir(canon, saida)
    if fails:
        print("\n".join("  🔴 " + f for f in fails))
        raise SystemExit("a tradução não faz round-trip — nada gravado")
    txt = json.dumps(saida, ensure_ascii=False, indent=2) + "\n"
    pathlib.Path(a.out).write_text(txt, encoding="utf-8")
    print(f"gravado: {a.out}")
    print(f"  epochs: {len(saida['epochs'])}  ·  "
          f"{saida['epochs'][0]['epoch_inicio']} → {saida['epochs'][-1]['epoch_inicio']}")
    print(f"  sha256: {hashlib.sha256(txt.encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    sys.exit(main())
