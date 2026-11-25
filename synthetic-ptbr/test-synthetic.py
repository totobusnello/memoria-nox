#!/usr/bin/env python3
"""Offline tests for the synthetic corpus tooling. No model, no network, no paid call.

  python3 -I synthetic-ptbr/test-synthetic.py

Every gate is shown passing on a valid state AND failing on its synthetic infractor; a gate only
ever seen passing proves nothing (PLANO.md, «Gates»).
  A. planner        deterministic; committed plan matches; invariants refuse a broken plan
  B. check-corpus   passes on a fake corpus built from the plan; fails on each infractor
  C. resolver       the contract of eval/resolve-gold-anchors.py, run for real on a fixture DB
                    through GOLD_DB (the gate «S: resolvedor»)
  D. metrics        hand-computed fixtures pass; a wrong ideal fails them (gate «S: achado 4»)
"""
import copy
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s_common as C  # noqa: E402
import importlib.util  # noqa: E402


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PLAN = load("plan", "plan.py")
CHECK = load("check_corpus", "check-corpus.py")
METRICS = load("metrics", "metrics.py")
RESOLVER = HERE.parent / "eval" / "resolve-gold-anchors.py"

n_ok = n_fail = 0


def ok(cond, msg):
    global n_ok, n_fail
    if cond:
        n_ok += 1
        print(f"  ok   {msg}")
    else:
        n_fail += 1
        print(f"  FAIL {msg}")


FILLER = "Texto de preenchimento sem fatos, escrito só para ocupar espaço."


def build_fake_corpus(plan, root):
    """What PR (2)'s assembler will produce, with filler instead of model text."""
    root = pathlib.Path(root)
    for f in plan["files"]:
        paras = []
        for it in f["items"]:
            if f["kind"] == "entity":
                continue
            paras += [it["text"]] * it["count"]
        if f["kind"] == "entity":
            compiled = [it["text"] for it in f["items"] if it["section"] == "compiled"]
            body = (f"---\nname: {f['entity']}\ndescription: ficha de {f['entity']}\n"
                    f"type: reference\n---\n\n{FILLER}\n\n" + "\n\n".join(compiled + [FILLER]) +
                    f"\n\n## Timeline\n\n- **2027-02-01** — [nota] {FILLER}\n")
        else:
            title = f"# {f['date']}" if f["kind"] == "daily" else f"# {f['kind']} de {f['date']}"
            body = title + "\n\n" + "\n\n".join([FILLER] + paras + [FILLER]) + "\n"
        p = root / f["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


def corpus_fails(plan, root):
    return CHECK.check(plan, root)


def part_a():
    print("A. planner")
    p1, p2 = PLAN.build(), PLAN.build()
    ok(C.dump_json(p1) == C.dump_json(p2), "same seed, same plan (byte for byte)")
    ok(C.PLAN_FILE.read_text(encoding="utf-8") == C.dump_json(p1), "committed plan.json is the plan")
    ok(C.dump_json(PLAN.build(seed=1)) != C.dump_json(p1), "another seed gives another plan")
    bad = copy.deepcopy(p1)
    op = next(f for f in bad["facts"] if f["operation"])
    tgt = next(f for f in bad["files"] if f["path"] == op["primary"]["path"])
    tgt["items"].append({"id": "X", "role": "paraphrase", "value": "F99", "section": None,
                         "text": "intruso", "count": 1})
    try:
        PLAN.verify(bad)
        ok(False, "verify refuses an operation file shared with another item")
    except PLAN.PlanError:
        ok(True, "verify refuses an operation file shared with another item")
    bad = copy.deepcopy(p1)
    qp = next(q for q in bad["queries"] if q["kind"] == "false_premise")
    f0 = bad["facts"][0]
    qp["attribute"], qp["entity"] = f0["attribute"], f0["entity"]
    try:
        PLAN.verify(bad)
        ok(False, "verify refuses a false premise that is planted")
    except PLAN.PlanError:
        ok(True, "verify refuses a false premise that is planted")
    return p1


def mutate(plan, base, fn):
    with tempfile.TemporaryDirectory() as d:
        shutil.copytree(base, d, dirs_exist_ok=True)
        fn(pathlib.Path(d))
        return corpus_fails(plan, d)


def part_b(plan):
    print("B. check-corpus")
    tmp = tempfile.mkdtemp()
    try:
        build_fake_corpus(plan, tmp)
        base_fails = corpus_fails(plan, tmp)
        ok(base_fails == [], f"fake corpus built from the plan passes ({len(base_fails)} problems)")
        for x in base_fails[:5]:
            print(f"       {x}")
        root = pathlib.Path(tmp)
        F = {f["id"]: f for f in plan["facts"]}
        plain = next(f for f in plan["facts"] if not f["duplicate"] and f["primary"]["section"] is None)
        dup = next(f for f in plan["facts"] if f["duplicate"])
        ent = next(f for f in plan["facts"] if f["primary"]["section"] == "compiled")
        numeric = next(f for f in plan["facts"] if f["attribute"] == "tiragem")
        spelled = next(f for f in plan["facts"] if f["attribute"] == "prazo")
        neg = next(n for f in plan["facts"] for n in f["negatives"])
        empty = next(f["path"] for f in plan["files"] if not f["items"] and f["kind"] == "daily")

        def edit(path, fn):
            def go(r):
                p = r / path
                p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")
            return go

        cases = [
            ("a primary sentence removed",
             edit(plain["primary"]["path"], lambda t: t.replace(plain["primary"]["text"], FILLER)),
             "found 0x"),
            ("a value literal copied into an unlabelled file",
             edit(empty, lambda t: t + f"\nAlguém anotou {numeric['literal']} sem contexto.\n"),
             "outside its items"),
            ("a spelled-out variant written outside T (no digit involved)",
             edit(empty, lambda t: t + f"\nFalaram em {spelled['forms'][1]} na conversa.\n"),
             "outside its items"),
            ("a negative's value written in another file",
             edit(empty, lambda t: t + f"\nVoltaram a citar {neg['forms'][-1]} por engano.\n"),
             "outside its items"),
            ("a duplicate undone",
             edit(dup["primary"]["path"], lambda t: t.replace(dup["primary"]["text"], FILLER, 1)),
             "found 1x, want 2x"),
            ("a stray digit in free text",
             edit(empty, lambda t: t + "\nA reunião começou às 15h.\n"),
             "digit in free text"),
            ("an entity item moved from compiled to timeline",
             edit(ent["primary"]["path"], lambda t: t.replace(ent["primary"]["text"] + "\n\n", "")
                  .rstrip("\n") + f"\n- **2027-02-02** — [nota] {ent['primary']['text']}\n"),
             "not in section compiled"),
            ("an extra file",
             lambda r: (r / "memory" / "intruso.md").write_text("# intruso\n", encoding="utf-8"),
             "file not in plan"),
            ("a missing file",
             lambda r: (r / empty).unlink(),
             "missing file"),
        ]
        for name, fn, expect in cases:
            fails = mutate(plan, tmp, fn)
            ok(any(expect in x for x in fails), f"infractor «{name}» fails with «{expect}»")
        del F
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def part_c():
    print("C. resolver contract (eval/resolve-gold-anchors.py via GOLD_DB)")
    d = pathlib.Path(tempfile.mkdtemp())
    try:
        db = d / "fixture.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, source_file TEXT, section TEXT, "
                    "chunk_text TEXT)")
        head = "Parágrafo longo de abertura que repete as mesmas palavras " * 4   # > 160 chars
        rows = [
            (1, "memory/a.md", None, "O pedido de impressão recebeu o número PED-00001."),
            (2, "memory/a.md", None, "O pedido de impressão recebeu o número PED-00001."),
            (3, "memory/entities/livros/x.md", "frontmatter", "name: X. O contrato tem o código AUT-AAAA."),
            (4, "memory/entities/livros/x.md", "compiled", "O contrato tem o código AUT-AAAA e outras notas."),
            (5, "memory/b.md", None, "Prazo combinado: tudo pronto antes da feira, disse a editora."),
            (6, "memory/b.md", None, "Na outra reunião, prazo combinado: tudo pronto antes da feira de novo."),
            (7, "memory/c.md", None, head + " e no fim o valor era 111."),
            (8, "memory/d.md", None, "Uma frase que só existe uma vez neste arquivo."),
            (9, "memory/e.md", None, "Primeiro texto qualquer do arquivo e."),
            (10, "memory/e.md", None, "Segundo texto qualquer do arquivo e."),
            (11, "memory/e.md", None, "Terceiro texto qualquer do arquivo e."),
        ]
        con.executemany("INSERT INTO chunks VALUES (?,?,?,?)", rows)
        con.commit()
        con.close()

        def resolve(anchor, sf, recorded=0, prefix=None):
            gold = d / "gold.jsonl"
            gold.write_text(json.dumps({"query_id": 1, "gold": [
                {"source_file": sf, "anchor": anchor, "chunk_id": recorded}]}) + "\n", encoding="utf-8")
            out = d / "out.json"
            env = {**os.environ, "GOLD_DB": str(db)}
            if prefix:
                env["ANCHOR_PREFIX"] = str(prefix)
            r = subprocess.run([sys.executable, "-I", str(RESOLVER), str(gold), str(out)],
                               env=env, capture_output=True, text=True)
            e = json.loads(out.read_text())["entries"][0]
            return r.returncode, e["state"], sorted(e["resolved_ids"])

        rc, st, ids = resolve("O pedido de impressão recebeu o número PED-00001.", "memory/a.md")
        ok((rc, st, ids) == (0, "ambiguous_duplicate", [1, 2]),
           f"exact duplicate: accepted with both ids, rc 0 (got rc={rc} {st} {ids})")
        rc, st, ids = resolve("O contrato tem o código AUT-AAAA", "memory/entities/livros/x.md")
        ok((rc, st, ids) == (0, "ambiguous_structural", [3, 4]),
           f"entity frontmatter+compiled pair: accepted, rc 0 (got rc={rc} {st} {ids})")
        rc, st, ids = resolve("prazo combinado: tudo pronto antes da feira", "memory/b.md")
        ok(rc != 0 and st == "ambiguous",
           f"two distinct texts sharing the span: refused, rc != 0 (got rc={rc} {st})")
        rc, st, _ = resolve("Uma frase que só existe uma vez neste arquivo.", "memory/d.md", recorded=8)
        ok((rc, st) == (0, "resolved"), f"unique anchor on its recorded id: resolved (got {rc} {st})")
        rc, st, _ = resolve("Uma frase que só existe uma vez neste arquivo.", "memory/d.md", recorded=99)
        ok((rc, st) == (0, "moved"), f"unique anchor, id changed: moved, rc 0 (got {rc} {st})")
        rc, st, _ = resolve("Esta frase não existe em lugar nenhum.", "memory/d.md")
        ok(rc != 0 and st == "unresolved", f"dead anchor: unresolved, rc != 0 (got {rc} {st})")
        rc, st, _ = resolve("Uma frase que só existe uma vez neste arquivo.", "memory/renomeado.md")
        ok(rc != 0 and st == "unresolved",
           f"file renamed without re-ingest: the anchor looks up the recorded path and fails (got {rc} {st})")
        changed = head + " e no fim o valor era 222."
        rc, st, _ = resolve(changed, "memory/c.md")
        ok(st == "resolved" or st == "moved",
           f"DEFAULT prefix of 160: an anchor whose conclusion changed still resolves (documented risk; got {st})")
        rc, st, _ = resolve(changed, "memory/c.md", prefix=100000)
        ok(rc != 0 and st == "unresolved",
           f"full-anchor mode (ANCHOR_PREFIX=100000): the changed conclusion is refused (got {rc} {st})")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def part_d():
    print("D. metrics")
    ok(METRICS.run_fixtures() == [], "hand-computed fixtures pass")
    wrong = METRICS.run_fixtures(gold=METRICS.ndcg_ranking_ideal)
    ok(wrong != [], f"scorer with the ranking ideal in place of the gold ideal fails ({len(wrong)} cases)")
    zero_as_one = METRICS.run_fixtures(rank=lambda r, rel: METRICS.ndcg_ranking_ideal(r, rel) or 1.0)
    ok(zero_as_one != [], "an ideal-zero case scored as 1 instead of undefined fails")


def main():
    plan = part_a()
    part_b(plan)
    part_c()
    part_d()
    print(f"\n{n_ok} ok, {n_fail} failed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
