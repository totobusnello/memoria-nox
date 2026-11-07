#!/usr/bin/env python3
"""Paper B, step 3 (PREREGISTRATION.md §5, §7.3): the blind human sheet.

  python3 -I b-human.py make   --private <dir> --freeze-ref <c> --judges-ref <c>
  python3 -I b-human.py commit --private <dir> --freeze-ref <c> --judges-ref <c> --sheet-ref <c>

`make` selects the rows §5 lists from the judges' verified labels (1: the two judges disagree;
2: both verify and the chunk the judges saw carries an exception or example marker; 3: 60 drawn
with seed + 1 from the rest), shuffles them with seed + 2 and writes <dir>/human-sheet.csv with
the triple and the same 6,000 characters of chunk the judges saw, and nothing else: no judge, no
quote, no origin. The grader reads <dir>/GRADING.txt (the four principles) and fills the last
column with s or n. It also writes SHEET-COMMITMENT.json (the sheet's sha256 and the counts per
origin); commit and push it before grading.

`commit` recomputes the selection, refuses a sheet whose rows or texts are not what `make` wrote
or that has an ungraded row, and writes HUMAN-COMMITMENT.json (the graded sheet's sha256 and the
counts). Commit and push it before b-read.py.
"""
import argparse
import csv
import importlib.util
import json
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("bcommon", HERE / "b-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
GRADE = "sustenta: s se o trecho sustenta a tripla como escrita / n se não (NAO SEI = n)"
COLS = ["item", "tripla", "trecho", GRADE]
GRADING = """Paper B: como graduar a planilha (PREREGISTRATION.md §4, §5)

Cada linha traz uma TRIPLA (origem --[predicado]--> destino) e o TRECHO registrado como evidência.
Escreva s na última coluna se o trecho sustenta a tripla como ela está escrita, n se não.
Na dúvida, n. As mesmas regras que os juízes receberam:

- Os dois lados têm de aparecer no trecho, ou ser inequívocos a partir dele.
- O predicado tem de ser a relação que o trecho afirma; aparecer na mesma frase não basta.
- P1: tripla que INVERTE a relação (troca quem faz e quem sofre, ou afirma o que o trecho exclui)
  não é sustentada, mesmo com as duas entidades lado a lado.
- P2: predicado mais pobre ou genérico que o trecho, sem contradizê-lo nem invertê-lo, É sustentado.
- P3: nome de exemplo dentro de exemplo ilustrativo (modelo, "Fulano", "X", "<nome>") não é
  entidade: não é sustentada.
- P4: formatação nunca é motivo para rejeitar.

Não abra freeze.json, judges.json nem o cache antes de terminar: a planilha é cega.
"""


def ws(t):
    return re.sub(r"\s+", " ", t or "").strip()


def triple(r):
    return f"({r['source']}) --[{r['predicate']}]--> ({r['target']})"


def select(fz, res, seed, n_random=C.N_RANDOM):
    """[(relation_id, origin)] in sheet order. Origins: 'disagree', 'marker', 'random'."""
    j1, j2 = res["judge1"]["primary"], res["judge2"]["primary"]
    by_id = {r["relation_id"]: r for r in fz["sample"]}
    ids = sorted(by_id)
    origin = {}
    for i in ids:
        v1, v2 = j1[str(i)]["verified"], j2[str(i)]["verified"]
        if v1 != v2:
            origin[i] = "disagree"
        elif v1 and v2 and C.marker(by_id[i]["chunk_text"][:C.CHUNK_CHARS]):
            origin[i] = "marker"
    rest = [i for i in ids if i not in origin]
    for i in random.Random(seed + 1).sample(rest, min(n_random, len(rest))):
        origin[i] = "random"
    pick = sorted(origin)
    random.Random(seed + 2).shuffle(pick)
    return [(i, origin[i]) for i in pick]


def load(a, need_sheet=False):
    P = C.private(a.private)
    refs = [("FREEZE", a.freeze_ref), ("JUDGES", a.judges_ref)]
    if need_sheet:
        refs.append(("SHEET", a.sheet_ref))
    com = C.ordered(C.ROOT, refs)
    C.same_private(com["FREEZE"], "freeze_json_sha256", P / "freeze.json")
    C.same_private(com["JUDGES"], "judges_json_sha256", P / "judges.json")
    fz = json.loads((P / "freeze.json").read_text(encoding="utf-8"))
    res = json.loads((P / "judges.json").read_text(encoding="utf-8"))
    return P, com, fz, res


def write_sheet(path, fz, sel):
    by_id = {r["relation_id"]: r for r in fz["sample"]}
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for k, (i, _) in enumerate(sel, 1):
            r = by_id[i]
            w.writerow([k, triple(r), r["chunk_text"][:C.CHUNK_CHARS], ""])


def read_sheet(path, fz, sel):
    """[(relation_id, origin, grade 0/1)], refusing anything `make` did not write."""
    text = open(path, encoding="utf-8-sig", newline="").read()
    first = text.split("\n", 1)[0]
    delim = ";" if first.count(";") > first.count(",") else ","
    got = list(csv.DictReader(text.splitlines(keepends=True), delimiter=delim))
    if not got or {"item", "tripla", "trecho"} - set(got[0]) or not any(
            c.startswith("sustenta") for c in got[0]):
        raise SystemExit("refusing: the sheet does not have the columns make wrote")
    gcol = next(c for c in got[0] if c.startswith("sustenta"))
    if sorted(int(r["item"]) for r in got) != list(range(1, len(sel) + 1)):
        raise SystemExit("refusing: the sheet's items are not the registered selection")
    by_id = {r["relation_id"]: r for r in fz["sample"]}
    out = []
    for r in got:
        i, origin = sel[int(r["item"]) - 1]
        f = by_id[i]
        if (ws(r["tripla"]), ws(r["trecho"])) != (ws(triple(f)), ws(f["chunk_text"][:C.CHUNK_CHARS])):
            raise SystemExit(f"refusing: item {r['item']}: the texts are not what make wrote")
        v = (r[gcol] or "").strip().lower()
        if v not in ("s", "n"):
            raise SystemExit(f"refusing: item {r['item']} is graded {v!r}, expected s or n")
        out.append((i, origin, int(v == "s")))
    return out


def counts(sel):
    c = {}
    for _, o in sel:
        c[o] = c.get(o, 0) + 1
    return c


def make(a):
    P, com, fz, res = load(a)
    out = P / "human-sheet.csv"
    if out.exists():
        sys.exit(f"refusing: {out} exists; the sheet is made once")
    sel = select(fz, res, fz["seed"])
    write_sheet(out, fz, sel)
    out.chmod(0o600)
    C.write_private(P / "GRADING.txt", GRADING)
    C.write_public(HERE / "SHEET-COMMITMENT.json", {
        "step": "SHEET", "judges_commit": com["JUDGES"]["_commit"], "rows": len(sel),
        "by_origin": counts(sel), "sheet_sha256": C.sha_file(out),
        "selection_sha256": C.sha_json(sel),
        "script_sha256": {p: C.sha_file(HERE / p) for p in ("b-common.py", "b-human.py")}})
    print(f"{len(sel)} rows written to {out} {counts(sel)}; commit SHEET-COMMITMENT.json, "
          f"then grade with {P / 'GRADING.txt'}")


def commit(a):
    P, com, fz, res = load(a, need_sheet=True)
    sel = select(fz, res, fz["seed"])
    if C.sha_json(sel) != com["SHEET"]["selection_sha256"]:
        sys.exit("refusing: the recomputed selection is not the committed one")
    graded = read_sheet(P / "human-sheet.csv", fz, sel)
    C.write_public(HERE / "HUMAN-COMMITMENT.json", {
        "step": "HUMAN", "sheet_commit": com["SHEET"]["_commit"], "rows": len(graded),
        "graded_sheet_sha256": C.sha_file(P / "human-sheet.csv"),
        "grades_sha256": C.sha_json(graded),
        "script_sha256": {p: C.sha_file(HERE / p) for p in ("b-common.py", "b-human.py")}})
    print(f"{len(graded)} grades recorded; commit HUMAN-COMMITMENT.json, then b-read.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("make", "commit"))
    ap.add_argument("--private", required=True)
    ap.add_argument("--freeze-ref", required=True)
    ap.add_argument("--judges-ref", required=True)
    ap.add_argument("--sheet-ref")
    a = ap.parse_args()
    if a.action == "commit" and not a.sheet_ref:
        sys.exit("commit needs --sheet-ref")
    (make if a.action == "make" else commit)(a)


if __name__ == "__main__":
    main()
