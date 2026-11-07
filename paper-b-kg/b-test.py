#!/usr/bin/env python3
"""Paper B: offline tests of the registered scripts. No network, no model call, no snapshot.

  python3 -I b-test.py

A synthetic database with the snapshot's schema subset, fake judges and a throwaway git
repository with a bare origin exercise the draw, the freeze, the judges' bookkeeping, the sheet,
the reading and the order of the public commitments. Each check that guards something is also run
against an input built to break it (a mutation), so a check that never fails would be caught.
"""
import csv
import importlib.util
import io
import json
import os
import pathlib
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


C = load("bcommon", "b-common.py")
F = load("bfreeze", "b-freeze.py")
J = load("bjudge", "b-judge.py")
H = load("bhuman", "b-human.py")
R = load("bread", "b-read.py")

FAILS = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


def raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except SystemExit:
        return True
    return False


# ------------------------------------------------------------------ fixture
SOURCES = ["synthetic/doc-a.md", "synthetic/doc-b.md", "synthetic/doc-c.md",
           "synthetic/doc-d.md", "synthetic/doc-e.md"]   # five documents, no real path


def fixture(path, n_rel=900, dead=37):
    con = sqlite3.connect(path)
    con.executescript("""
      CREATE TABLE chunks (id INTEGER PRIMARY KEY, source_file TEXT, chunk_text TEXT);
      CREATE TABLE kg_entities (id INTEGER PRIMARY KEY, name TEXT, entity_type TEXT);
      CREATE TABLE kg_relations (id INTEGER PRIMARY KEY, source_entity_id INTEGER,
        target_entity_id INTEGER, relation_type TEXT, relation_reason TEXT, created_at TEXT,
        evidence_chunk_id INTEGER, extraction_method TEXT, confidence REAL,
        superseded_by_relation_id INTEGER, superseded_at TEXT);""")
    rng = random.Random(7)
    for e in range(1, 201):
        con.execute("INSERT INTO kg_entities VALUES (?,?,?)", (e, f"Entidade {e}", "org"))
    for c in range(1, 301):
        extra = rng.choice(["", " exceto quando houver aditivo.", " Ex: Fulano assina.", ""])
        text = (f"A Entidade {c % 200 + 1} contratou a Entidade {(c * 7) % 200 + 1} em 2026 "
                f"pelo valor de R$ {c * 1000} conforme cláusula {c}.{extra}")
        con.execute("INSERT INTO chunks VALUES (?,?,?)", (c, SOURCES[c % len(SOURCES)], text))
    for r in range(1, n_rel + 1):
        c = rng.randint(1, 300)
        cid = 10_000 + r if r <= dead else c   # the first `dead` cite a gone chunk
        # the entities the chunk names, so a reading judge can find both on its own chunk
        con.execute("INSERT INTO kg_relations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (r * 3, c % 200 + 1, (c * 7) % 200 + 1, "contratou",
                     rng.choice(["role", "ownership", "mention"]), "2026-07-15", cid, None, 0.8,
                     None, None))
    con.commit()
    return con


def fake(judge_bias):
    """A fake caller that reads: it claims support only when both entities of the triple occur in
    the chunk it is shown (and then on a deterministic share), quoting the chunk's first eight
    words. On a mismatched chunk the entities are usually absent, so it rarely claims."""
    def call(judge, prompt):
        text = prompt.split("---\n", 2)[1]
        s, o = re.findall(r"^TRIPLA:  \((.*?)\) --\[.*?\]--> \((.*?)\)$", prompt, re.M)[0]
        has = lambda e: re.search(re.escape(e) + r"(?!\d)", text) is not None
        h = int(C.sha_bytes(prompt.encode())[:6], 16) % 100
        claims = h < judge_bias and has(s) and has(o)
        quote = " ".join(text.split()[:8]) if claims else ""
        return json.dumps({"sustenta": claims, "oito_palavras": quote, "erro": "nenhum",
                           "motivo": "teste"}), 100, 20, judge["model"] + "-served"
    return call


# ------------------------------------------------------------------ tests
def t_pure():
    check("seed is the first 8 hex digits", C.seed_of("a" * 8 + "0" * 32) == 0xaaaaaaaa)
    check("seed refuses a non-sha", raises(C.seed_of, "paper-b-prereg-v1.0"))
    t = "**Cláusula 3** — A *Granix* contrata a Treviso, no valor de R$ 50.000,00."
    check("P4 check accepts markup and accents",
          C.quote_ok("Clausula 3 A Granix contrata a Treviso no valor", t))
    check("P4 check rejects a changed digit", not C.quote_ok("valor de R$ 60.000,00", t))
    check("P4 check rejects a short quote", not C.quote_ok("A Granix", t))
    rng = random.Random(1)
    q = "A Granix contrata a Treviso no valor de"
    sw = C.swap_two(q, rng)
    check("swap_two changes the quote and the check rejects it",
          sw is not None and sw != q and not C.quote_ok(sw, t))
    check("swap_two gives None when no two words differ", C.swap_two("a a a", rng) is None)
    check("marker finds exception", C.marker("vale tudo, exceto aditivos") == "exception")
    check("marker finds example", C.marker("Ex: Fulano de Tal") == "example")
    check("marker ignores 'excetuando'-like words", C.marker("excetuando nada") is None)
    check("wilson 135/150 matches October [0.842, 0.938]", all(abs(x - y) < 6e-4 for x, y in zip(C.wilson(135, 150), [0.842, 0.938])))
    check("kappa perfect = 1", C.kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0)
    check("kappa undefined on constant labels", C.kappa([1, 1], [1, 1]) is None)
    check("judge 2 refuses to run unnamed", raises(C.ready, C.JUDGE2))
    check("judge 1 is ready", not raises(C.ready, C.JUDGE1))
    check("public writer refuses chunk text", raises(
        C.write_public, os.devnull, {"x": "A Entidade 1 contratou a Entidade 7 em 2026 " * 4}))


def t_pipeline(tmp):
    db = tmp / "snap.db"
    con = fixture(db)
    con.close()
    con = C.ro(db)
    pop = C.population(con)
    check("population excludes dead evidence", len(pop) == 900 - 37)
    old = F.C.POPULATION          # each script loads its own copy of b-common.py
    F.C.POPULATION = len(pop)
    try:
        fz = F.freeze(con, 12345)
        fz2 = F.freeze(con, 12345)
        fz3 = F.freeze(con, 54321)
    finally:
        F.C.POPULATION = old
    check("freeze refuses a population that is not the census's", raises(F.freeze, con, 1))
    ids = [r["relation_id"] for r in fz["sample"]]
    check("draw is n=300, unique, inside the population",
          len(ids) == 300 == len(set(ids)) and set(ids) <= set(pop))
    check("draw is reproducible for a seed", ids == [r["relation_id"] for r in fz2["sample"]])
    check("draw changes with the seed", ids != [r["relation_id"] for r in fz3["sample"]])
    check("mismatch is 30 of the sample", len(fz["mismatch"]) == 30
          and {m["relation_id"] for m in fz["mismatch"]} <= set(ids))
    own = {r["relation_id"]: r["source_file"] for r in fz["sample"]}
    check("mismatched chunk is from a different document",
          all(m["source_file"] != own[m["relation_id"]] for m in fz["mismatch"]))
    body = json.dumps(fz, ensure_ascii=False)
    com = F.commitment(fz, C.TAG, "f" * 40, body)
    pub = json.dumps(com, ensure_ascii=False)
    check("freeze commitment carries no chunk text or entity name",
          "contratou" not in pub and "Entidade" not in pub)
    check("freeze commitment hashes the private file", com["freeze_json_sha256"] == C.sha_bytes(body.encode()))

    cache, led = C.Cache(tmp / "cache.sqlite"), C.Ledger()
    j1 = dict(C.JUDGE1)
    j2 = dict(C.JUDGE2, model="fake-2", usd_in=1e-6, usd_out=1e-6)
    res, errors = J.run(fz, (j1, j2), cache, led, {"judge1": fake(80), "judge2": fake(70)})
    check("every call returned", not errors and all(
        len(res[n]["primary"]) == 300 and len(res[n]["mismatch"]) == 30 for n in res))
    calls = led.calls
    J.run(fz, (j1, j2), cache, led, {"judge1": fake(80), "judge2": fake(70)})
    check("a rerun is served from the cache, not paid", led.calls == calls and led.cached >= 660)
    check("a verdict is verified only when its quote checks out", all(
        v["verified"] == (v["claims"] and v["quote_ok"])
        for n in res for k in res[n].values() for v in k.values()))
    check("cap aborts", raises(C.Ledger(cap=0.0).add, 0.01))

    sel = H.select(fz, res, fz["seed"])
    origins = dict(sel)
    dis = [i for i in ids if res["judge1"]["primary"][str(i)]["verified"]
           != res["judge2"]["primary"][str(i)]["verified"]]
    check("every disagreement is on the sheet", all(origins.get(i) == "disagree" for i in dis))
    check("60 random rows", sum(o == "random" for o in origins.values()) == 60)
    check("marker rows are both-verified with a marker", all(
        res["judge1"]["primary"][str(i)]["verified"] and C.marker(
            next(r for r in fz["sample"] if r["relation_id"] == i)["chunk_text"])
        for i, o in sel if o == "marker"))
    check("selection is reproducible", sel == H.select(fz, res, fz["seed"]))

    sheet = tmp / "human-sheet.csv"
    H.write_sheet(sheet, fz, sel)
    raw = sheet.read_text(encoding="utf-8")
    check("sheet carries no judge output", "teste" not in raw and "served" not in raw)
    rows = list(csv.reader(io.StringIO(raw)))
    rows_graded = [rows[0]] + [r[:-1] + ["s" if k % 3 else "n"] for k, r in enumerate(rows[1:])]
    with open(sheet, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, delimiter=";").writerows(rows_graded)
    graded = H.read_sheet(sheet, fz, sel)
    check("a graded sheet with ';' (Numbers export) reads back", len(graded) == len(sel))
    bad = [r[:] for r in rows_graded]
    bad[1][2] = bad[1][2] + " editado"
    with open(tmp / "bad.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(bad)
    check("an edited chunk is refused", raises(H.read_sheet, tmp / "bad.csv", fz, sel))
    bad = [r[:] for r in rows_graded]
    bad[2][-1] = "talvez"
    with open(tmp / "bad2.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(bad)
    check("an ungraded row is refused", raises(H.read_sheet, tmp / "bad2.csv", fz, sel))

    out = R.reading(fz, res, graded)
    check("B-F covers the 300 rows", out["B_F"]["n"] == 300)
    check("final label is human on every sheet row",
          out["final_label_source"].get("human") == len(sel))
    check("controls ran for both judges", set(out["controls"]) == {"judge1", "judge2"})
    neg = out["controls"]["judge1"]["negative_citation"]
    check("negative citation control rejects swapped quotes", neg["tested"] > 0 and neg["passes"])
    check("mismatch control passes for a judge whose quotes fail elsewhere",
          out["controls"]["judge1"]["mismatched_evidence"]["passes"])
    # mutation: a judge whose 'verified' ignores the check fails the mismatch control
    res_m = json.loads(json.dumps(res))
    for v in res_m["judge2"]["mismatch"].values():
        v["verified"] = True
    ctl = R.controls(fz, res_m, {i: (o, g) for i, o, g in graded}, fz["seed"])
    check("mutation: a judge accepting mismatched evidence fails", not ctl["judge2"]["passes"])
    fin = R.final_labels(fz, res_m, {i: (o, g) for i, o, g in graded}, ctl)
    check("a failed judge's labels do not count off the sheet",
          all(s in ("human", "judge1") for _, s in fin.values()))
    for v in res_m["judge1"]["mismatch"].values():
        v["verified"] = True
    out_m = R.reading(fz, res_m, graded)
    check("both judges failing falls back to the human random rows",
          out_m["B_F"]["n"] == 60 and "random" in out_m["B_F"]["basis"])
    pub = json.dumps(out, ensure_ascii=False)
    check("reading carries no chunk text or entity name", "contratou" not in pub and "Entidade" not in pub)


def git(cwd, *a):
    r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(cwd), *a],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


def t_order(tmp):
    origin, work = tmp / "origin.git", tmp / "work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    git(work, "config", "user.email", "t@t")
    git(work, "config", "user.name", "t")
    d = work / C.D
    d.mkdir()

    def commit(name=None, msg="x"):
        if name:
            (d / f"{name}-COMMITMENT.json").write_text(json.dumps({"step": name}))
        else:
            (d / "README.md").write_text(msg)
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", msg)
        git(work, "push", "-q", "origin", "main")
        return git(work, "rev-parse", "HEAD")

    base = commit(msg="base")
    git(work, "tag", C.TAG)
    git(work, "push", "-q", "origin", C.TAG)
    check("tag found and clean", C.tag_commit(work) == base)
    fr = commit("FREEZE", "freeze")
    jr = commit("JUDGES", "judges")
    com = C.ordered(work, [("FREEZE", fr), ("JUDGES", jr)])
    check("commitments in order are accepted", com["FREEZE"]["_commit"] == fr and com["_tag"] == base)
    check("out-of-order names are refused", raises(C.ordered, work, [("JUDGES", jr)]))
    check("a commitment that is the tag's own commit is refused",
          raises(C.ordered, work, [("FREEZE", base)]))
    (d / "FREEZE-COMMITMENT.json").write_text(json.dumps({"step": "FREEZE", "v": 2}))
    git(work, "commit", "-qam", "rewrite")
    git(work, "push", "-q", "origin", "main")
    check("a commitment rewritten later is refused", raises(C.ordered, work, [("FREEZE", fr)]))
    git(work, "checkout", "-q", "-b", "side", base)
    (d / "x").write_text("x")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "side")
    side = git(work, "rev-parse", "HEAD")
    check("a commit not on origin/main is refused", raises(C.ordered, work, [("FREEZE", side)]))


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="paper-b-test-"))
    try:
        t_pure()
        t_pipeline(tmp)
        t_order(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(FAILS)} failures" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
