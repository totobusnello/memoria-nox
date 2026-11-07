#!/usr/bin/env python3
"""Paper B2: offline tests of the registered scripts. No network, no model call, no snapshot.

  python3 -I b2-test.py

A fake `claude -p`, fake judges, a synthetic Paper B outcome built so every figure is known in
advance, and throwaway git repositories with a bare origin, through which every subcommand runs end
to end, with rewrites and with none. Checks that guard something are also
run against an input built to break them.
"""
import csv
import importlib.util
import io
import json
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


X = load("b2", "b2.py")
C, B = X.C, X.B
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


# ------------------------------------------------------------------ the repairer call
def fake_runner(payload, rc=0):
    def run(cmd, **kw):
        return types.SimpleNamespace(returncode=rc, stdout=json.dumps(payload), stderr="boom")
    return run


def cli_payload(ans, usd=0.03):
    return {"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": usd,
            "structured_output": ans, "stop_reason": "end_turn",
            "usage": {"input_tokens": 2, "cache_creation_input_tokens": 3000,
                      "cache_read_input_tokens": 0, "output_tokens": 500,
                      "output_tokens_details": {"thinking_tokens": 200}},
            "modelUsage": {"claude-opus-5-5": {}}}


def t_call():
    cmd = C.claude_cmd()
    flag = lambda f: cmd[cmd.index(f) + 1]
    check("repairer is claude-opus-5-5 at effort medium",
          flag("--model") == "claude-opus-5-5" and flag("--effort") == "medium")
    check("no tools, no setting source (no hook, no CLAUDE.md), no MCP server, no session",
          flag("--tools") == "" and flag("--setting-sources") == "" and "--strict-mcp-config" in cmd
          and flag("--mcp-config") == '{"mcpServers":{}}' and "--no-session-persistence" in cmd)
    check("the protocol's system prompt replaces Claude Code's",
          "--system-prompt" in cmd and "--append-system-prompt" not in cmd
          and flag("--system-prompt") == C.SYSTEM)
    check("structured output against the schema", json.loads(flag("--json-schema")) == C.SCHEMA)
    good = {"acao": "rewrite", "oito_palavras": "a b c", "nova_origem": "x", "novo_predicado": "y",
            "novo_destino": "z", "motivo": "m"}
    run = lambda msg, **k: C.call_claude(msg, runner=fake_runner(cli_payload(good)))
    ans, rec = run("m")
    check("an answer is read with served model, tokens and cost",
          ans == good and rec["served"] == ["claude-opus-5-5"] and rec["tin"] == 3002
          and rec["tout"] == 500 and rec["thinking"] == 200 and rec["usd"] == 0.03)
    ans, _ = C.call_claude("m", runner=fake_runner(cli_payload(dict(good, acao="maybe"))))
    check("mutation: an action outside the schema is no answer", ans is None)
    ans, _ = C.call_claude("m", runner=fake_runner(cli_payload(None)))
    check("mutation: a missing structured output is no answer", ans is None)
    try:
        C.call_claude("m", runner=fake_runner(cli_payload(good), rc=1))
        check("a failed CLI raises (so the run stops and resumes)", False)
    except RuntimeError:
        check("a failed CLI raises (so the run stops and resumes)", True)


def t_repair_one(tmp):
    text = "A Entidade 1 contratou a Entidade 7 em 2026 pelo valor de R$ 1000 conforme cláusula 1."
    item = {"source": "Entidade 1", "predicate": "contratou", "target": "Entidade 7"}
    calls, logged = [], []

    def caller(ans, served=("claude-opus-5-5",)):
        served = list(served)
        def c(msg):
            calls.append(msg)
            return ans, {"served": served, "usd": 0.02, "tin": 1, "tout": 1,
                         "thinking": 0, "stop": "end_turn", "turns": 2}
        return c

    cache, led = B.Cache(tmp / "rc.sqlite"), B.Ledger(cap=1.0)
    keep = {"acao": "keep", "oito_palavras": "A Entidade 1 contratou a Entidade 7 em",
            "nova_origem": "", "novo_predicado": "", "novo_destino": "", "motivo": "ok"}
    v = C.repair_one(cache, led, item, text, caller(keep))
    check("a keep carries a quote that passes the check", v["action"] == "keep" and v["quote_ok"])
    C.repair_one(cache, led, item, text, caller(keep))
    check("a repeat is served from the cache, not asked again", len(calls) == 1 and led.cached == 1)
    check("the message is exactly the triple and the chunk (no label, verdict or grade)",
          calls[0] == C.user_message(item, text) and calls[0] == (
              "TRIPLA:  (Entidade 1) --[contratou]--> (Entidade 7)\n\nTRECHO (a evidência "
              "registrada):\n---\n" + text + "\n---"))
    item2 = dict(item, target="Entidade 9")
    v = C.repair_one(cache, led, item2, text, caller(None))
    check("no answer keeps the relation unchanged and is counted",
          v["action"] == "keep" and v["no_answer"] and not v["quote_ok"])
    bad = dict(keep, oito_palavras="A Entidade 2 contratou a Entidade 7 em")
    v = C.repair_one(cache, led, dict(item, target="Entidade 8"), text, caller(bad))
    check("mutation: a quote not in the chunk fails the check", not v["quote_ok"])
    check("cap aborts", raises(B.Ledger(cap=0.0).add, 0.01))
    same = dict(keep, acao="rewrite", nova_origem=" entidade 1", novo_predicado="Contratou",
                novo_destino="Entidade 7 ")
    v = C.repair_one(cache, led, dict(item, predicate="contratou "), text, caller(same))
    check("a rewrite identical to the original is a keep",
          v["action"] == "keep" and v["rewrite_identical"] and v["new"] is None)
    sw = dict(keep, acao="rewrite", nova_origem="Entidade 7", novo_predicado="foi contratada por",
              novo_destino="Entidade 1")
    v = C.repair_one(cache, led, dict(item, target="Entidade 7", source="Entidade 1",
                                      predicate="x"), text, caller(sw), logged.append)
    check("a rewrite that swaps the pair is classed 'swapped'", v["pair"] == "swapped")
    check("every attempt is logged with its cost", logged and logged[-1]["status"] == "answered"
          and logged[-1]["usd"] == 0.02)
    check("mutation: a served model other than the registered one stops the run",
          raises(C.repair_one, cache, led, dict(item, target="Entidade 3"), text,
                 caller(keep, ("claude-sonnet-5-5",)), logged.append))

    def broken(msg):
        raise RuntimeError("rc=1")
    n0 = len(logged)
    try:
        C.repair_one(cache, led, dict(item, target="Entidade 4"), text, broken, logged.append)
        ok = False
    except RuntimeError:
        ok = True
    check("a transport error is logged, left unanswered and raised for a resume",
          ok and logged[n0]["status"] == "transport_error"
          and cache.get(B.sha_bytes(json.dumps([C.REPAIRER["model"], C.REPAIRER["effort"], C.SYSTEM,
                        C.user_message(dict(item, target="Entidade 4"), text)]).encode())) is None)


# ------------------------------------------------------------------ a Paper B outcome known in advance
def synthetic():
    """300 relations: 270 supported (B), 30 unsupported. Repair: of the supported, keep 265 and
    delete 5; of the unsupported, delete 20 and rewrite 10. Every rewrite is supported."""
    sample, fin, prim = [], {}, {}
    for i in range(1, 301):
        sample.append({"relation_id": i, "source": f"Entidade {i}", "predicate": "contratou",
                       "target": f"Entidade {i + 1}", "relation_reason": ["role", "mention"][i % 2],
                       "bucket": "vault", "chunk_text": f"A Entidade {i} contratou a Entidade {i + 1} "
                       f"em 2026 conforme cláusula {i}."})
        fin[i] = (1, "judges") if i <= 270 else (0, "human")
        act = "keep" if i <= 265 else "delete" if i <= 270 else "delete" if i <= 290 else "rewrite"
        prim[str(i)] = {"action": act, "quote_ok": act != "delete", "no_answer": False,
                        "pair": "same" if act == "rewrite" else None,
                        "new": ({"source": f"Entidade {i}", "predicate": "assinou com",
                                 "target": f"Entidade {i + 1}"} if act == "rewrite" else None)}
    mm = {str(i): {"action": "delete", "quote_ok": False, "no_answer": False} for i in range(1, 31)}
    fz = {"seed": 99, "sample": sample, "mismatch": []}
    rep = {"primary": prim, "mismatch": mm}
    rw = X.rewrites(fz, rep)
    res = {n: {str(rid): {"verified": True, "claims": True} for rid, _, _ in rw}
           for n in ("judge1", "judge2")}
    res["judge2"]["291"]["verified"] = False          # one disagreement
    ctl = {"judge1": {"passes": True}, "judge2": {"passes": True}}
    return fz, fin, ctl, rep, rw, res


def t_reading(tmp):
    fz, fin, ctl, rep, rw, res = synthetic()
    check("rewrites are the 10 rewritten relations", [r for r, _, _ in rw] == list(range(291, 301)))
    sel = X.select(rw, res, 7)
    org = dict(sel)
    check("the disagreement is on the sheet", org.get(291) == "disagree")
    check("the rest go on as random (fewer than 30)", sum(o == "random" for o in org.values()) == 9)
    check("selection is reproducible", sel == X.select(rw, res, 7))
    sheet = tmp / "s.csv"
    X.write_sheet(sheet, rw, sel)
    raw = sheet.read_text(encoding="utf-8")
    check("the sheet shows the rewrite, not the original triple",
          "assinou com" in raw and "--[contratou]-->" not in raw)
    rows = list(csv.reader(io.StringIO(raw)))
    graded_rows = [rows[0]] + [r[:-1] + ["s"] for r in rows[1:]]
    with open(sheet, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, delimiter=";").writerows(graded_rows)
    graded = X.read_sheet(sheet, rw, sel)
    check("a graded sheet with ';' reads back", len(graded) == len(sel))
    bad = [r[:] for r in graded_rows]
    bad[1][1] = bad[1][1].replace("assinou com", "contratou")
    with open(tmp / "b.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(bad)
    check("mutation: an edited triple is refused", raises(X.read_sheet, tmp / "b.csv", rw, sel))

    out = X.reading(fz, fin, ctl, rep, rw, res, graded, 7)
    P, R = out["B2_P"], out["B2_R"]
    check("precision before is 270/300", P["precision_before"]["supported"] == 270
          and P["precision_before"]["n"] == 300)
    check("precision after is 275/275 (265 kept + 10 supported rewrites)",
          P["precision_after"]["supported"] == 275 and P["precision_after"]["n"] == 275)
    check("difference is +0.1 and its bootstrap interval holds it",
          P["difference"] == 0.1 and P["difference_bootstrap95"][0] <= 0.1 <= P["difference_bootstrap95"][1])
    check("retention (kept unchanged) is 265/270", R["supported"] == 265 and R["n"] == 270)
    rn0 = out["reported_not_interpreted"]
    check("decomposition: filter-only precision 265/265 and supported outputs 270 -> 275",
          rn0["precision_after_if_rewrites_were_deletes"]["supported"] == 265
          and rn0["precision_after_if_rewrites_were_deletes"]["n"] == 265
          and rn0["supported_outputs_before_after"] == [270, 275])
    check("transitions from unsupported: 20 deleted, 10 same-pair rewrites supported",
          rn0["transitions_from_paper_b_unsupported"] == {"delete": 20, "rewrite_same_supported": 10})
    rn = out["reported_not_interpreted"]
    check("correction 30/30 and damage 5/270",
          rn["correction_rate_on_paper_b_unsupported"]["supported"] == 30
          and rn["damage_rate_on_paper_b_supported"]["supported"] == 5)
    check("positive control passes when every mismatched relation is acted on",
          out["controls"]["positive_mismatch"]["passes"] and out["instrument"]["interpreted"])
    pub = json.dumps(out, ensure_ascii=False)
    check("reading carries no entity name or chunk text", "Entidade" not in pub and "contratou" not in pub)

    rep_m = json.loads(json.dumps(rep))
    for k in list(rep_m["mismatch"])[:4]:
        rep_m["mismatch"][k]["action"] = "keep"
    out_m = X.reading(fz, fin, ctl, rep_m, rw, res, graded, 7)
    check("mutation: keeping 4 of 30 mismatched fails the positive control",
          not out_m["controls"]["positive_mismatch"]["passes"] and not out_m["instrument"]["interpreted"])
    rep_r = json.loads(json.dumps(rep))
    for i in range(1, 11):                      # rewrite 10 supported relations into new facts
        rep_r["primary"][str(i)].update(action="rewrite", pair="new", new={
            "source": "Outra", "predicate": "p", "target": "Coisa"})
    rw_r = X.rewrites(fz, rep_r)
    res_r = {n: {str(rid): {"verified": True, "claims": True} for rid, _, _ in rw_r}
             for n in ("judge1", "judge2")}
    out_r = X.reading(fz, fin, ctl, rep_r, rw_r, res_r, [], 7)
    check("mutation: replacing supported facts with other supported facts is not retention",
          out_r["B2_R"]["supported"] == 255
          and out_r["reported_not_interpreted"]["supported_output_retention_lenient"]["supported"] == 265)
    rep_d = json.loads(json.dumps(rep))
    for v in rep_d["primary"].values():
        v["action"] = "delete"
    out_d = X.reading(fz, fin, ctl, rep_d, [], {"judge1": {}, "judge2": {}}, [], 7)
    check("mutation: deleting everything shows retention 0",
          out_d["B2_R"]["supported"] == 0 and out_d["B2_P"]["precision_after"]["n"] == 0)
    graded_n = [(i, o, 0) for i, o, _ in graded]
    out_n = X.reading(fz, fin, ctl, rep, rw, res, graded_n, 7)
    check("mutation: a human 'n' on a rewrite lowers precision after",
          out_n["B2_P"]["precision_after"]["supported"] == 275 - len(graded_n))
    ctl_f = {"judge1": {"passes": False}, "judge2": {"passes": False}}
    only_dis = [g for g in graded if g[1] == "disagree"]       # 9 rewrites left off the sheet
    out_f = X.reading(fz, fin, ctl_f, rep, rw, res, only_dis, 7)
    check("no passing Paper B judge: primary unavailable, universe not shrunk",
          not out_f["instrument"]["primary_available"] and "B2_P" not in out_f)
    fin_m = dict(fin)
    del fin_m[5]
    out_g = X.reading(fz, fin_m, ctl, rep, rw, res, graded, 7)
    check("a relation without Paper B's label: primary unavailable",
          not out_g["instrument"]["primary_available"] and "B2_R" not in out_g)
    out_p = X.reading(fz, fin, ctl, rep, rw, res, only_dis, 7)
    check("passing judges label the rewrites off the sheet",
          out_p["reported_not_interpreted"]["rewrite_label_source"] == {"human": 1, "judges": 9})

    empty = tmp / "e.csv"
    X.write_sheet(empty, [], [])
    check("zero rewrites: an empty sheet reads back as no grades", X.read_sheet(empty, [], []) == [])
    with open(empty, "a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(["1", "x", "y", "s"])
    check("mutation: a row on an empty selection is refused", raises(X.read_sheet, empty, [], []))
    res_mk = json.loads(json.dumps(res))
    rw_mk = [(rid, it, t + " exceto quando houver aditivo.") for rid, it, t in rw]
    sel_mk = X.select(rw_mk, res_mk, 7)
    check("marker stratum: agreed rewrites on a chunk with a marker all go on the sheet",
          sum(o == "marker" for _, o in sel_mk) == 9)


# ------------------------------------------------------------------ the public history
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
        (d / (f"{name}-COMMITMENT.json" if name else "README.md")).write_text(
            json.dumps({"step": name}) if name else msg)
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", msg)
        git(work, "push", "-q", "origin", "main")
        return git(work, "rev-parse", "HEAD")

    base = commit(msg="base")
    check("no tag: refused", raises(C.tag_commit, work))
    git(work, "tag", C.TAG)
    git(work, "push", "-q", "origin", C.TAG)
    check("tag found and clean", C.tag_commit(work) == base)
    r = commit("REPAIR", "repair")
    j = commit("JUDGES", "judges")
    com = C.ordered(work, [("REPAIR", r), ("JUDGES", j)])
    check("B2 commitments in order are accepted", com["JUDGES"]["_commit"] == j)
    check("out-of-order names are refused", raises(C.ordered, work, [("JUDGES", j)]))
    check("Paper B's step names are refused in B2's chain", raises(C.ordered, work, [("FREEZE", r)]))
    (d / "REPAIR-COMMITMENT.json").write_text(json.dumps({"step": "REPAIR", "v": 2}))
    git(work, "commit", "-qam", "rewrite")
    git(work, "push", "-q", "origin", "main")
    check("a commitment rewritten later is refused", raises(C.ordered, work, [("REPAIR", r)]))


def t_e2e(tmp, rewrite_some):
    """Every subcommand through a throwaway repository: repair, judge, sheet, grades, read, each
    commitment committed and pushed before the next step, Paper B's side replaced by a synthetic
    outcome. Run with and without rewrites."""
    import argparse
    tag = f"e2e{int(rewrite_some)}"
    origin, work = tmp / f"{tag}-origin.git", tmp / f"{tag}-work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    git(work, "config", "user.email", "t@t")
    git(work, "config", "user.name", "t")
    d = work / C.D
    d.mkdir()
    for f in X.SCRIPTS:
        shutil.copy(HERE / f, d / f)

    def push(msg):
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", msg)
        git(work, "push", "-q", "origin", "main")
        return git(work, "rev-parse", "HEAD")

    push("base")
    git(work, "tag", C.TAG)
    git(work, "push", "-q", "origin", C.TAG)
    fz, fin, ctl, _, _, _ = synthetic()
    fz["mismatch"] = [{"relation_id": i, "chunk_text": "Outro documento sem as entidades."}
                      for i in range(1, 31)]
    fzc = {"_commit": "f" * 40, "freeze_json_sha256": "0" * 64}
    old = (X.HERE, X.b_freeze, X.b_labels)
    X.HERE = d
    X.b_freeze = lambda pb, ref, repo: (fzc, fz)
    X.b_labels = lambda pb, refs, repo: (fz, fin, ctl, {"FREEZE": fzc["_commit"]})

    def repairer(msg):
        i = int(msg.split("(Entidade ", 1)[1].split(")", 1)[0])
        if "Outro documento" in msg:
            act = "delete"
        elif rewrite_some and i > 290:
            act = "rewrite"
        else:
            act = "keep" if i <= 265 else "delete"
        chunk = msg.split("---\n", 1)[1]
        return ({"acao": act, "oito_palavras": "" if act == "delete" else " ".join(chunk.split()[:8]),
                 "nova_origem": f"Entidade {i}" if act == "rewrite" else "",
                 "novo_predicado": "assinou com" if act == "rewrite" else "",
                 "novo_destino": f"Entidade {i + 1}" if act == "rewrite" else "", "motivo": "t"},
                {"served": ["claude-opus-5-5"], "usd": 0.01, "tin": 10, "tout": 5, "thinking": 1,
                 "stop": "end_turn", "turns": 2})

    def judge_fake(judge, prompt):
        chunk = prompt.split("---\n", 2)[1]
        return (json.dumps({"sustenta": True, "oito_palavras": " ".join(chunk.split()[:8]),
                            "erro": "nenhum", "motivo": "t"}), 10, 5, judge["model"])

    p2, pb = tmp / f"{tag}-p2", tmp / f"{tag}-pb"
    ns = lambda refs: argparse.Namespace(private=str(p2), b_private=str(pb), b_freeze_ref="x",
                                         b_refs=["a", "b", "c", "d"], refs=refs)
    try:
        X.repair(ns([]), caller=repairer, repo=work, version=lambda: "test-cli")
        rc = json.loads((d / "REPAIR-COMMITMENT.json").read_text())
        check(f"[{tag}] repair commitment: 330 answers, attempts logged, no action count",
              rc["answers"] == {"primary": 300, "mismatch": 30} and rc["attempts"] == {"answered": 330}
              and "keep" not in json.dumps(rc) and rc["repairer"]["cli_version_last_run"] == "test-cli")
        r = push("repair")
        check(f"[{tag}] repair refuses to run twice", raises(
            X.repair, ns([]), caller=repairer, repo=work, version=lambda: "x"))
        X.judge(ns([r]), callers={"judge1": judge_fake, "judge2": judge_fake}, repo=work)
        j = push("judges")
        X.sheet(ns([r, j]), repo=work)
        sc = json.loads((d / "SHEET-COMMITMENT.json").read_text())
        check(f"[{tag}] sheet rows = rewrites", sc["rows"] == (10 if rewrite_some else 0))
        s_ = push("sheet")
        sheet = p2 / "human-sheet.csv"
        rows = list(csv.reader(io.StringIO(sheet.read_text(encoding="utf-8"))))
        with open(sheet, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows([rows[0]] + [x[:-1] + ["s"] for x in rows[1:]])
        X.grades(ns([r, j, s_]), repo=work)
        h = push("human")
        X.read(ns([r, j, s_, h]), repo=work)
        out = json.loads(next(d.glob("READING-*.json")).read_text())
        want_r = 265
        check(f"[{tag}] reading end to end: positive control, retention {want_r}/270",
              out["instrument"]["primary_available"] and out["controls"]["positive_mismatch"]["passes"]
              and out["B2_R"]["supported"] == want_r and out["B2_R"]["n"] == 270
              and out["B2_P"]["precision_after"]["n"] == (275 if rewrite_some else 265)
              and out["reported_not_interpreted"]["list_price_usd"]["repair_all_attempts"] == 3.3)
        pub = "".join(f.read_text() for f in d.glob("*.json"))
        check(f"[{tag}] no public file carries an entity name or chunk text",
              "Entidade" not in pub and "contratou" not in pub and "assinou" not in pub)
        orig = (p2 / "repairs.json").read_text()
        (p2 / "repairs.json").write_text(orig + " ")
        check(f"[{tag}] mutation: a private file changed after its commitment is refused",
              raises(X.read, ns([r, j, s_, h]), repo=work))
        (p2 / "repairs.json").write_text(orig)
        (p2 / "judges.json").rename(p2 / "judges.json.bak")
        fzc_other = dict(fzc, _commit="e" * 40)
        X.b_freeze = lambda pb, ref, repo: (fzc_other, fz)
        try:
            X.judge(ns([r]), callers={"judge1": judge_fake, "judge2": judge_fake}, repo=work)
            msg = ""
        except SystemExit as e:
            msg = str(e)
        check(f"[{tag}] mutation: another Paper B freeze is refused", "another Paper B freeze" in msg)
    finally:
        X.HERE, X.b_freeze, X.b_labels = old


def t_cli():
    check("judge without its repair ref is refused",
          raises(X.main, ["judge", "--private", "/x", "--b-private", "/y", "--b-freeze-ref", "c"]))
    check("read without Paper B's four refs is refused",
          raises(X.main, ["read", "--private", "/x", "--b-private", "/y", "--refs", "a,b,c,d"]))


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="paper-b2-test-"))
    try:
        t_call()
        t_repair_one(tmp)
        t_reading(tmp)
        t_order(tmp)
        t_e2e(tmp, True)
        t_e2e(tmp, False)
        t_cli()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(FAILS)} failures" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
