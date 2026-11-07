#!/usr/bin/env python3
"""Paper B2: offline tests of the registered scripts. No network, no model call, no snapshot.

  python3 -I b2-test.py

A fake `claude -p`, fake judges, a synthetic Paper B outcome built so every figure is known in
advance, and a throwaway git repository with a bare origin. Checks that guard something are also
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
    calls = []

    def caller(ans):
        def c(msg):
            calls.append(msg)
            return ans, {"served": ["claude-opus-5-5"], "usd": 0.02, "tin": 1, "tout": 1,
                         "thinking": 0, "stop": "end_turn"}
        return c

    cache, led = B.Cache(tmp / "rc.sqlite"), B.Ledger(cap=1.0)
    keep = {"acao": "keep", "oito_palavras": "A Entidade 1 contratou a Entidade 7 em",
            "nova_origem": "", "novo_predicado": "", "novo_destino": "", "motivo": "ok"}
    v = C.repair_one(cache, led, item, text, caller(keep))
    check("a keep carries a quote that passes the check", v["action"] == "keep" and v["quote_ok"])
    C.repair_one(cache, led, item, text, caller(keep))
    check("a repeat is served from the cache, not asked again", len(calls) == 1 and led.cached == 1)
    check("the message carries the triple and the chunk only",
          "Entidade 1" in calls[0] and "contratou" in calls[0] and "verified" not in calls[0])
    item2 = dict(item, target="Entidade 9")
    v = C.repair_one(cache, led, item2, text, caller(None))
    check("no answer keeps the relation unchanged and is counted",
          v["action"] == "keep" and v["no_answer"] and not v["quote_ok"])
    bad = dict(keep, oito_palavras="A Entidade 2 contratou a Entidade 7 em")
    v = C.repair_one(cache, led, dict(item, target="Entidade 8"), text, caller(bad))
    check("mutation: a quote not in the chunk fails the check", not v["quote_ok"])
    check("cap aborts", raises(B.Ledger(cap=0.0).add, 0.01))


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
    check("retention is 265/270", R["supported"] == 265 and R["n"] == 270)
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
    check("no passing judge: rewrites off the sheet are excluded and counted",
          out_f["reported_not_interpreted"]["excluded"].get("rewrite_without_label", 0) == 9)
    out_p = X.reading(fz, fin, ctl, rep, rw, res, only_dis, 7)
    check("passing judges label the rewrites off the sheet",
          not out_p["reported_not_interpreted"]["excluded"]
          and out_p["reported_not_interpreted"]["rewrite_label_source"] == {"human": 1, "judges": 9})


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
        t_cli()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(FAILS)} failures" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
