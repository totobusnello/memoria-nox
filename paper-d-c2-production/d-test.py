#!/usr/bin/env python3
"""Paper D: offline test of the registered pipeline. No network, no key, no real session.

  python3 -I d-test.py            (from anywhere; needs git, and the branch committed for test 2)

Builds a synthetic archive, transcript sessions, a gzipped snapshot with session_distill_log and
production units, and a deployed session-distill.ts, in a temporary directory outside any
repository. Every model call is replaced by a deterministic stub (the distiller copies sentences,
the reader looks the parameter up, the judges check the reference string), so what is tested is
the plumbing: frame, draw, copy, manifests, windows, validation, extension, arms, cut,
counterfactual, visible prefix, serving, the human sheet, the order checks and the reading.

  1. freeze `host` + `commit` on the synthetic archive: frame counts, MAX of processed_at,
     exclusions, manifest; a tampered file is refused
  2. freeze `run` with ssh and scp shimmed to local commands (smoke, HEAD archive)
  3. generate (smoke): validation drops by reason; the extension rule with patched sizes
  4. run (smoke): estimate without --yes; every arm and the counterfactual; C2-cut loses the fact
  5. human make / commit (smoke, n 20); a changed answer in the sheet is refused
  6. read (smoke): controls, hypotheses, descriptives
  7. the order of the public history, in a scratch repository with a local origin: the good
     order passes; a commitment written twice, one out of order, and one at the tag are refused
"""
import contextlib
import csv
import gzip
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
os.environ.setdefault("GEMINI_API_KEY", "test-not-a-key")
os.environ.setdefault("OPENAI_API_KEY", "test-not-a-key")
FAILS = []


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def refuses(fn, needle):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn()
    except SystemExit as e:
        return needle in str(e.code)
    return False


def call(mod, *argv):
    old = sys.argv
    sys.argv = ["x", *argv]
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = mod.main()
        return r, buf.getvalue()
    finally:
        sys.argv = old


# ------------------------------------------------------------------ synthetic world
def uuid(i):
    return f"{i:08x}-0000-4000-8000-{i:012x}"


def sentence(i, k):
    return f"Na sessao {i} decidimos que o parametro p{i}x{k} fica em {100 + 7 * k + i} unidades."


def make_world(T):
    arc, rnd = T / "archive", random.Random(5)
    (arc / "agent-a").mkdir(parents=True)
    (arc / "agent-b").mkdir()
    sessions = {}
    # i: (n sentences, last day, logged?) ; 1 spent, 2 excluded, 3 too short, 4 outside window,
    # 5 never logged; the rest are the frame
    spec = {1: (300, "2026-09-10", True), 2: (300, "2026-09-10", True), 3: (10, "2026-09-10", True),
            4: (300, "2026-10-30", True), 5: (300, "2026-09-10", False)}
    for i in range(6, 18):
        spec[i] = (rnd.choice((120, 700)), f"2026-09-{10 + i:02d}", True)
    for i, (n, day, logged) in spec.items():
        lines = []
        for k in range(n):
            role = "user" if k % 2 == 0 else "assistant"
            ts = f"{day}T{10 + k // 60:02d}:{k % 60:02d}:00.000Z"
            lines.append(json.dumps({"type": role, "timestamp": ts,
                                     "message": {"role": role, "content": sentence(i, k) +
                                                 " Seguimos com o resto do trabalho do dia."}}))
        sub = "agent-a" if i % 2 else "agent-b"
        (arc / sub / f"{uuid(i)}.jsonl").write_text("\n".join(lines) + "\n")
        sessions[i] = (n, day, logged)
    # session 18: two long messages, processed when only the first existed (production's rule:
    # fewer than 3 messages, never sent to the model)
    big = lambda k0: " ".join(sentence(18, k) for k in range(k0, k0 + 40))
    (arc / "agent-b" / f"{uuid(18)}.jsonl").write_text("\n".join(json.dumps(e) for e in [
        {"type": "user", "timestamp": "2026-09-20T10:00:00.000Z", "message": {"role": "user", "content": big(0)}},
        {"type": "assistant", "timestamp": "2026-09-20T10:05:00.000Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": big(40)}]}}]) + "\n")
    sessions[18] = (2, "2026-09-20", True)
    # a smaller duplicate copy of session 6 in the other directory: the larger one is kept
    (arc / "agent-a" / f"{uuid(6)}.jsonl").write_text(
        (arc / "agent-b" / f"{uuid(6)}.jsonl").read_text().split("\n", 1)[0] + "\n")
    json.dump({"sessions": [{"uuid": uuid(1)}]}, open(T / "spent.json", "w"))
    (T / "exclude.txt").write_text(uuid(2) + "\n")
    json.dump({"chosen": [{"uuid": uuid(2)}]}, open(T / "smoke-select.json", "w"))
    db = T / "snap.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, source_file TEXT, chunk_text TEXT, "
                "chunk_type TEXT, source_date TEXT, metadata TEXT, importance REAL)")
    con.execute("CREATE TABLE session_distill_log (id INTEGER PRIMARY KEY, session_key TEXT, agent TEXT, "
                "chunks_extracted INTEGER, message_count INTEGER, processed_at TEXT)")
    for i, (n, day, logged) in sessions.items():
        if not logged:
            continue
        mid = f"{day} {10 + (n // 2) // 60:02d}:{(n // 2) % 60:02d}:00"
        con.execute("INSERT INTO session_distill_log (session_key, agent, chunks_extracted, message_count,"
                    " processed_at) VALUES (?,?,?,?,?)", (f"boris:{uuid(i)}", "boris", 2, n // 2, mid))
        if i == 7:        # a second agent looked later: processed_at is the MAX
            con.execute("INSERT INTO session_distill_log (session_key, agent, chunks_extracted, "
                        "message_count, processed_at) VALUES (?,?,?,?,?)",
                        (f"forge:{uuid(i)}", "forge", 1, n, f"{day} 23:59:59"))
        if i % 3:         # some sessions keep units, the others have none
            for k in (0, 2):
                con.execute("INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, metadata,"
                            " importance) VALUES (?,?,?,?,?,?)",
                            (f"sessions/boris/boris:{uuid(i)}", f"[decision|boris] {sentence(i, k)}",
                             "distilled", day, json.dumps({"category": "decision"}), 0.7))
    con.commit()
    con.close()
    snapdir = T / "snapdir"
    snapdir.mkdir()
    with open(db, "rb") as f, gzip.open(snapdir / "daily-main-main-20261107030000-1-x.db.gz", "wb") as g:
        g.write(f.read())
    L = load("lme_t", HERE.parent / "paper3-construction/lme-run.py")
    ts = T / "session-distill.ts"
    ts.write_text("// deployed\nconst DISTILL_SYSTEM = `" + L.DISTILL_SYSTEM + "`;\nexport {};\n")
    return arc, snapdir, ts


# ------------------------------------------------------------------ stubs
PARAM = re.compile(r"parametro (p\d+x\d+) fica em (\d+) unidades")


def stub_post(url, body, hdr, timeout=180):
    usage = {"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20}}
    if "api.openai.com" in url:
        inp = body["input"]
        ref = inp.split("RESPOSTA DE REFERENCIA:\n---\n")[1].split("\n---")[0]
        cand = inp.split("RESPOSTA DO CANDIDATO:\n---\n")[1].split("\n---")[0]
        ok = ref in cand
        return {"model": "stub", "answers": [
            {"name": "contem", "probability": 0.9 if ok else 0.05},
            {"name": "contradiz", "probability": 0.8 if (not ok and re.search(r"\d", cand)) else 0.05},
            {"name": "nivel", "score": 1, "probabilities": []}]}
    if "systemInstruction" in body:                     # reader R0
        txt = body["contents"][0]["parts"][0]["text"]
        m = re.search(r"parametro (p\d+x\d+)\?", txt)
        found = None
        if m:
            for name, val in PARAM.findall(txt.split("PERGUNTA:")[0]):
                if name == m.group(1):
                    found = f"{val} unidades"
        return {"candidates": [{"content": {"parts": [{"text": found or "NAO SEI"}]},
                                "finishReason": "STOP"}], **usage}
    txt = body["contents"][0]["parts"][0]["text"]
    if txt.startswith("Você é um avaliador"):           # judge 2
        ref = txt.split("RESPOSTA DE REFERÊNCIA (verdade): ")[1].split("\n")[0]
        ans = txt.split("RESPOSTA A AVALIAR: ")[1].split("\n")[0]
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"correta": ref in ans})}]}}],
                **usage}
    # distiller: C0 keeps every third fact, C2 (with the event paragraph) every second
    block = txt.split("\n\nConversa:\n", 1)[1]
    step = 2 if "TAMBÉM OBRIGATÓRIO" in txt else 3
    mem = [{"text": f"o parametro {n} fica em {v} unidades", "category": "decision", "importance": 0.6}
           for n, v in PARAM.findall(block) if int(n.split("x")[1]) % step == 0]
    return {"candidates": [{"content": {"parts": [{"text": json.dumps({"memories": mem})}]}}],
            "modelVersion": "stub", **usage}


def stub_ask(prompt):
    w = prompt.split("\n\nTRECHO:\n", 1)[1]
    facts = []
    for sent in re.findall(r"Na sessao \d+ decidimos que o parametro p\d+x\d+ fica em \d+ unidades\.", w)[:3]:
        n, v = PARAM.search(sent).groups()
        cat = "decision" if "- decision:" in prompt else "identificador"
        facts.append({"pergunta": f"Qual o valor do parametro {n}?", "resposta": f"{v} unidades",
                      "citacoes": [sent], "categoria": cat})
    facts.append({"pergunta": "Qual o valor do parametro p0x0?", "resposta": "1 unidades",
                  "citacoes": ["texto que nao esta no trecho"], "categoria": facts[0]["categoria"] if facts else "decision"})
    facts.append({"pergunta": "sem resposta"})
    facts.append({"pergunta": "Q?", "resposta": "x", "citacoes": [w[:40]], "categoria": "outra"})
    return json.dumps({"fatos": facts}), "glm-stub"


def patch(mod):
    """Patch every lme-run and holdout-generate module object reachable from a script module."""
    seen = set()

    def walk(m):
        if id(m) in seen:
            return
        seen.add(id(m))
        for v in list(vars(m).values()):
            if isinstance(v, type(sys)) and getattr(v, "__file__", "") and str(HERE.parent) in v.__file__:
                if v.__file__.endswith("lme-run.py"):
                    v.post = stub_post
                if v.__file__.endswith("holdout-generate.py"):
                    v.ask = stub_ask
                walk(v)
    walk(mod)
    return mod


# ------------------------------------------------------------------ tests
def main():
    T = pathlib.Path(tempfile.mkdtemp(prefix="paper-d-test."))
    try:
        arc, snapdir, dts = make_world(T)
        P = T / "private"
        F = P / "freeze"
        host = [sys.executable, "-I", str(HERE / "d-freeze.py"), "host", "--archive", str(arc),
                "--snapdir", str(snapdir), "--snapshot-date", "20261107", "--spent", str(T / "spent.json"),
                "--exclude", str(T / "exclude.txt"), "--distill-ts", str(dts), "--distill-js", "/nonexistent",
                "--end", "2026-10-29"]
        print("1. freeze host + commit")
        r = subprocess.run(host + ["--out", str(F)], capture_output=True, text=True)
        check(r.returncode == 0, f"host mode runs ({r.stderr.strip()[-200:]})")
        counts = json.loads(r.stdout)["counts"] if r.returncode == 0 else {}
        check(counts.get("excluded_spent") == 1 and counts.get("excluded_listed") == 1,
              f"exclusions counted {counts}")
        check(counts.get("eligible_never_logged") == 1 and counts.get("frame") == 13, "frame = eligible and logged")
        check(not (P / "snapshot.db").exists(), "the decompressed snapshot is deleted")
        prod = json.loads((F / "production.json").read_text())
        check(prod[uuid(7)]["processed_at"].endswith("23:59:59") and prod[uuid(7)]["chunks_extracted"] == 3,
              "processed_at is the MAX across agents, chunks_extracted the sum")
        check(all(not u["text"].startswith("[") for v in prod.values() for u in v["units"]),
              "the [category|agent] prefix is stripped from production units")
        fr = json.loads((F / "frame.json").read_text())
        check([o["uuid"] for o in fr["order"]] == load("dc", HERE / "d-common.py").draw(
            [o["uuid"] for o in fr["order"]]), "the order is the seeded shuffle of the sorted frame")
        check(fr["order"][[o["uuid"] for o in fr["order"]].index(uuid(6))]["path"].startswith("agent-b"),
              "the largest copy of a session is kept")
        cm = [sys.executable, "-I", str(HERE / "d-freeze.py"), "commit", "--private", str(P),
              "--freeze-date", "2026-11-07"]
        r = subprocess.run(cm + ["--out", str(P / "FREEZE-COMMITMENT.json")], capture_output=True, text=True)
        check(r.returncode == 0 and "equal" in r.stdout, f"commit writes, deployed C0 equal ({r.stderr[-160:]})")
        fc = json.loads((P / "FREEZE-COMMITMENT.json").read_text())
        check(fc["deployed"]["distill_system_equals_c0"] and fc["copied"] == 13, "commitment content")
        s0 = F / "sessions" / f"{fr['order'][0]['uuid']}.jsonl"
        keep = s0.read_bytes()
        s0.write_bytes(keep + b"\n")
        r = subprocess.run(cm + ["--out", str(T / "x.json")], capture_output=True, text=True)
        check(r.returncode != 0 and "manifest" in r.stderr, "a changed frozen file is refused")
        s0.write_bytes(keep)
        # the registered freeze is not smoke; downstream smoke steps must refuse it, so rebuild as smoke
        shutil.rmtree(F)
        r = subprocess.run(host + ["--out", str(F), "--smoke", "--seed", "7"], capture_output=True, text=True)
        r2 = subprocess.run(cm + ["--out", str(P / "FREEZE-COMMITMENT.json"), "--smoke"], capture_output=True, text=True)
        check(r.returncode == 0 and r2.returncode == 0, "smoke freeze for the downstream steps")
        r = subprocess.run(host + ["--out", str(T / "f2"), "--seed", "7"], capture_output=True, text=True)
        check(r.returncode != 0 and "registered seed" in r.stderr, "a registered freeze refuses another seed")

        print("2. freeze run, ssh and scp shimmed")
        shim = T / "bin"
        shim.mkdir()
        (shim / "ssh").write_text('#!/bin/bash\nwhile [ "$1" = -o ]; do shift 2; done\nshift\nexec bash -c "$*"\n')
        (shim / "scp").write_text('#!/bin/bash\nargs=()\nfor x in "$@"; do case "$x" in -q|-r) ;; '
                                  '*) args+=("${x#*:}") ;; esac; done\nexec cp -R "${args[@]}"\n')
        for f in ("ssh", "scp"):
            os.chmod(shim / f, 0o755)
        env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}")
        extra = (f"--archive {arc} --snapdir {snapdir} --spent {T / 'spent.json'} --distill-ts {dts} "
                 f"--distill-js /nonexistent")
        dirty = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain", "--", "."],
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            print("  skip run-mode test: paper-d-c2-production has uncommitted changes (HEAD is archived)")
        else:
            P2 = T / "private2"
            import datetime as dt
            day = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
            shutil.copy(next(snapdir.iterdir()), snapdir / f"daily-main-main-{day}030000-2-y.db.gz")
            r = subprocess.run([sys.executable, "-I", str(HERE / "d-freeze.py"), "run", "--host", "stub",
                                "--private", str(P2), "--exclude-from", str(T / "smoke-select.json"),
                                "--smoke", "--seed", "7", "--host-extra", extra],
                               capture_output=True, text=True, env=env)
            check(r.returncode == 0 and (P2 / "FREEZE-COMMITMENT.json").exists(),
                  f"run mode end to end ({(r.stderr or r.stdout).strip()[-200:]})")
            check(not list(pathlib.Path("/var/tmp").glob("paper-d-freeze.*")), "the host directory is removed")
            (snapdir / f"daily-main-main-{day}030000-2-y.db.gz").unlink()
            r = subprocess.run([sys.executable, "-I", str(HERE / "d-freeze.py"), "run", "--host", "stub",
                                "--private", str(P2), "--exclude-from", str(T / "smoke-select.json"),
                                "--smoke", "--seed", "7"], capture_output=True, text=True, env=env)
            check(r.returncode != 0 and "made once" in r.stderr, "a second freeze into the same dir is refused")

        print("3. generate")
        gen = patch(load("dgen_t", HERE / "d-generate.py"))
        rc, out = call(gen, "--private", str(P), "--smoke")
        qc = json.loads((P / "QUESTIONS-COMMITMENT.json").read_text())
        check(rc is None and qc["questions"]["primary"] > 0, f"questions written {qc['questions']}")
        d = qc["drops"]["primary"]
        check(all(d.get(k, 0) > 0 for k in ("malformed", "category_outside", "citation_not_verbatim")),
              f"drops by reason {d}")
        qs = [json.loads(l) for l in open(P / "questions.jsonl")]
        full = {}
        for q in qs:
            sess = load("dsel_t", HERE / "d-select.py")
            if q["uuid"] not in full:
                full[q["uuid"]] = gen.C.layout(gen.C.turns(F / "sessions" / f"{q['uuid']}.jsonl", sess))[0]
        check(all(all(c in full[q["uuid"]][q["ev_lo"]:q["ev_hi"]] for c in q["citations"]) for q in qs),
              "every citation lies inside its evidence region")
        check(all(len({q["window"] for q in qs if q["uuid"] == u}) <= 2 for u in full), "at most two windows")
        long_ = [u for u in full if len(full[u]) >= 60_000]
        check(any(len({q["window"] for q in qs if q["uuid"] == u}) == 2 for u in long_) and
              all(len({q["window"] for q in qs if q["uuid"] == u}) == 1 for u in full if len(full[u]) < 40_000),
              "the middle window only when it does not overlap the first")
        P3 = T / "private3"
        shutil.copytree(P, P3, ignore=shutil.ignore_patterns("questions.jsonl", "QUESTIONS-COMMITMENT.json"))
        gen.C.N_SESSIONS, gen.C.BLOCK, gen.C.TARGET_PRIMARY, gen.C.N_MAX = 4, 2, 10 ** 6, 8
        call(gen, "--private", str(P3), "--smoke")
        q3 = json.loads((P3 / "QUESTIONS-COMMITMENT.json").read_text())
        check(q3["sessions_used"] == 8 and q3["extension_sessions"] == 4, "extension in blocks up to the maximum")
        gen.C.TARGET_PRIMARY = 1
        call(gen, "--private", str(P3), "--smoke")
        q3 = json.loads((P3 / "QUESTIONS-COMMITMENT.json").read_text())
        check(q3["sessions_used"] == 4, "no extension when the target is reached")
        gen.C.N_SESSIONS, gen.C.BLOCK, gen.C.TARGET_PRIMARY, gen.C.N_MAX = 80, 10, 232, 120

        tiny = T / "tiny.jsonl"
        tiny.write_text("\n".join(json.dumps(e) for e in [
            {"type": "user", "timestamp": "2026-09-01T10:00:00Z", "message": {"role": "user", "content": "x" * 4000}},
            {"type": "assistant", "timestamp": "2026-09-01T10:01:00Z",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "HEARTBEAT_OK"}]}},
            {"type": "assistant", "timestamp": "2026-09-01T10:02:00Z",
             "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t"}]}},
            {"type": "assistant", "timestamp": "2026-09-01T10:03:00Z",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "resposta longa o bastante"}]}},
            {"type": "user", "timestamp": "2026-09-01T11:00:00Z", "message": {"role": "user", "content": "depois"}}]))
        st = gen.C.prod_messages(tiny)
        check(len(st) == 3 and gen.C.visible_count(st, "2026-09-01 10:30:00") == 2,
              "production's message count: heartbeat and tool-only events dropped, prefix by processed_at")

        print("4. run")
        run = patch(load("drun_t", HERE / "d-run.py"))
        rc, out = call(run, "--repo", str(HERE.parent), "--private", str(P), "--smoke")
        check(rc == 0 and "estimate only" in out and not (P / "run" / "cache.sqlite").exists(),
              "without --yes nothing is called")
        rc, out = call(run, "--repo", str(HERE.parent), "--private", str(P), "--smoke", "--yes")
        res = json.loads((P / "run" / "results.json").read_text())
        check(rc == 0 and "sha256" in out and "accuracy" not in out.lower(), "run prints counts and hash only")
        arms = {r["arm"] for r in res["rows"]}
        check(arms == {"A", "C0", "C2", "C2-cut", "P", "V"}, f"every arm has rows {sorted(arms)}")
        y = lambda arm: sum(r["j1"] for r in res["rows"] if r["arm"] == arm)
        check(y("A") > y("C2") > y("C0") and y("C2-cut") == 0, f"stub arms ordered A {y('A')} > C2 {y('C2')} "
              f"> C0 {y('C0')}, C2-cut {y('C2-cut')}")
        cf = res["counterfactual"]
        check(cf and all(r["has_altered"] or not r["has_original"] for r in cf) and
              sum(r["has_altered"] for r in cf) > 0, f"counterfactual: {len(cf)} rows, altered number served")
        S = res["sessions"]
        check(any(s["visible_turns"] < s["turns"] for s in S.values()), "V reads a strict prefix where processed_at is earlier")
        s18 = S.get(uuid(18))
        check(s18 is not None and s18["visible_messages"] < 3 and s18["units"]["V"] == 0 and s18["units"]["C0"] > 0,
              "a session production never sent to the model: V empty by rule, C0 distils its full prose")
        rc2, _ = call(run, "--repo", str(HERE.parent), "--private", str(P), "--smoke", "--yes")
        res2 = json.loads((P / "run" / "results.json").read_text())
        check(res2["meta"]["calls"]["cached"] > 0 and res2["meta"]["usd"] == 0, "a rerun is served from the cache")
        (P / "run" / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
        qb = (P / "questions.jsonl").read_bytes()
        (P / "questions.jsonl").write_bytes(qb.replace(b"unidades", b"unidade", 1))
        check(refuses(lambda: call(run, "--repo", str(HERE.parent), "--private", str(P), "--smoke"),
                      "questions.jsonl"), "a changed questions file is refused before any call")
        (P / "questions.jsonl").write_bytes(qb)
        check(refuses(lambda: call(run, "--repo", str(HERE.parent), "--private", str(P), "--smoke", "--cap", "20"),
                      "US$ 10"), "a cap above US$ 10 is refused")

        print("5. human sample")
        hum = load("dhum_t", HERE / "d-human.py")
        H = [sys.executable, "-I", str(HERE / "d-human.py")]
        r = subprocess.run(H + ["make", "--private", str(P), "--n", "20"], capture_output=True, text=True)
        check(r.returncode != 0 and "--smoke" in r.stderr, "n other than 60 needs --smoke")
        r = subprocess.run(H + ["make", "--private", str(P), "--n", "20", "--smoke"], capture_output=True, text=True)
        check(r.returncode == 0, f"sheet made ({r.stderr[-160:]})")
        sheet = (P / "human-sample.csv").read_text()
        head = next(csv.reader(io.StringIO(sheet)))
        check(head == hum.COLS, f"the sheet has only item, question, reference, answer, grade: {head}")
        rows = list(csv.reader(io.StringIO(sheet)))
        for row in rows[1:]:
            row[4] = "s" if row[2] in row[3] else "n"
        buf = io.StringIO()
        csv.writer(buf).writerows(rows)
        good = buf.getvalue()
        bad = rows[1][3]
        rows[1][3] = bad + " (editado)"
        buf2 = io.StringIO()
        csv.writer(buf2).writerows(rows)
        (P / "human-sample.csv").write_text(buf2.getvalue())
        r = subprocess.run(H + ["commit", "--private", str(P), "--n", "20", "--smoke"], capture_output=True, text=True)
        check(r.returncode != 0 and "texts" in r.stderr, "an edited answer in the sheet is refused")
        (P / "human-sample.csv").write_text(good)
        r = subprocess.run(H + ["commit", "--private", str(P), "--n", "20", "--smoke"], capture_output=True, text=True)
        hc = json.loads((P / "HUMAN-COMMITMENT.json").read_text()) if r.returncode == 0 else {}
        check(r.returncode == 0 and hc.get("kappa") == 1.0, f"commit; human = judge here, kappa {hc.get('kappa')}")

        print("6. read")
        rd = load("drd_t", HERE / "d-read.py")
        rc, out = call(rd, "--repo", str(HERE.parent), "--private", str(P), "--smoke")
        rj = json.loads((P / "read" / "reading.json").read_text())
        check(rc == 0 and "CONTROLS" in out and set(rj["controls"]) ==
              {"ceiling", "positive", "counterfactual", "fidelity"}, "controls read first")
        fid = rj["controls"]["fidelity"]
        check(fid["sessions_sent"] == len(res["sessions"]) - 1, f"fidelity read only where production distilled ({fid['sessions_sent']})")
        h1 = rj["hypotheses"]["H-D1"]["j1"]
        check(h1["estimate"] > 0 and h1["ci95"][0] <= h1["estimate"] <= h1["ci95"][1], f"H-D1 {h1}")
        check(rj["interpret"] == all(v["pass"] is not False for v in rj["controls"].values()),
              f"interpret follows the gates {rj['controls']['fidelity']}")
        res_b = (P / "run" / "results.json").read_bytes()
        (P / "run" / "results.json").write_bytes(res_b.replace(b'"usd"', b'"usd" ', 1))
        check(refuses(lambda: call(rd, "--repo", str(HERE.parent), "--private", str(P), "--smoke"),
                      "results.json"), "a results.json other than the human sample's is refused")
        (P / "run" / "results.json").write_bytes(res_b)

        print("7. order of the public history")
        order_tests(T, load("dc7", HERE / "d-common.py"))
    finally:
        shutil.rmtree(T, ignore_errors=True)
        for p in pathlib.Path("/var/tmp").glob("paper-d-freeze.*"):
            shutil.rmtree(p, ignore_errors=True)
    print(f"\n{'ALL PASS' if not FAILS else f'{len(FAILS)} FAILED'}")
    return 1 if FAILS else 0


def order_tests(T, C):
    g = lambda repo, *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True)
    origin, repo = T / "origin.git", T / "repo"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True, capture_output=True)
    g(repo, "config", "user.email", "t@t")
    g(repo, "config", "user.name", "t")
    g(repo, "config", "commit.gpgsign", "false")
    d = repo / C.D
    d.mkdir()

    def commit(name, body="{}", to="main"):
        (d / name).write_text(body)
        g(repo, "add", str(d / name))
        g(repo, "commit", "-q", "--no-verify", "-m", name)
        g(repo, "push", "-q", "origin", f"HEAD:{to}")
        return g(repo, "rev-parse", "HEAD").stdout.strip()

    commit("PREREGISTRATION.md", "x")
    g(repo, "tag", "-a", C.TAG, "-m", "t")
    g(repo, "push", "-q", "origin", C.TAG)
    f = commit("FREEZE-COMMITMENT.json", '{"a": 1}')
    q = commit("QUESTIONS-COMMITMENT.json", '{"b": 1}')
    h = commit("HUMAN-COMMITMENT.json", '{"c": 1}')
    ok = True
    try:
        C.ordered(repo, [("FREEZE", f), ("QUESTIONS", q), ("HUMAN", h)])
    except SystemExit as e:
        ok = False
        print("   ", e)
    check(ok, "the registered order passes")
    check(refuses(lambda: C.ordered(repo, [("FREEZE", q), ("QUESTIONS", q)]), "not written once"),
          "a wrong commit for a commitment is refused")
    check(refuses(lambda: C.ordered(repo, [("FREEZE", f), ("QUESTIONS", f)]), "own commit"),
          "two commitments in one commit are refused")
    h2 = commit("FREEZE-COMMITMENT.json", '{"a": 2}')
    check(refuses(lambda: C.ordered(repo, [("FREEZE", f), ("QUESTIONS", q), ("HUMAN", h)]), "written once"),
          "a commitment rewritten after its push is refused")
    g(repo, "reset", "-q", "--hard", h)
    g(repo, "push", "-q", "-f", "origin", "HEAD:main")
    del h2
    tagc = g(repo, "rev-parse", f"{C.TAG}^{{commit}}").stdout.strip()
    check(refuses(lambda: C.ordered(repo, [("FREEZE", tagc)]), "own commit"), "a commitment at the tag is refused")
    g(repo, "checkout", "-q", "-b", "side", tagc)
    s = commit("FREEZE-COMMITMENT.json", '{"a": 3}', to="side")
    check(refuses(lambda: C.ordered(repo, [("FREEZE", s)]), "not on origin/main"),
          "a commitment off origin/main is refused")


if __name__ == "__main__":
    sys.exit(main())
