#!/usr/bin/env python3
"""Offline tests for step 2. No network, no key. Run: python3 -I test-stage2.py

Each check has a sabotage that must make it fail; `--sabotage` runs them and expects failures.
"""
import ast
import hashlib
import inspect
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import judges as J  # noqa: E402
import prompts as P  # noqa: E402
import run as RUN  # noqa: E402
import analyze as A  # noqa: E402
import pairs as PAIRS  # noqa: E402

REPO = HERE.parent.parent
SOURCES = {
    ("582a8cee", "audits/2026-10-22-gold-oracle.py"): {"CLOSED": "CLOSED", "JUDGE": "ORACLE"},
    ("b3dcc47c", "audits/2026-10-22-gold-repass.py"): {"P": "REPASS"},
    ("0c628152", "audits/2026-10-22-gold-pooling.py"): {"P": "POOL"},
    ("0c628152", "eval/judge-relevance.py"): {"PREDICATE": "REG_PREDICATE", "LEVEL_Q": "REG_LEVEL_Q",
                                               "LEVELS": "REG_LEVELS"},
    ("0c063e73", "audits/2026-10-27-judge-reread-full.py"): {"PRED": "ENVELOPE_PRED"},
}
# RESPONDE comes from a file removed from the public tree on 2026-11-08 (it carried private
# anchors); its prompt string is pinned by hash, taken from the private file.
RESPONDE_SHA256_16 = "147fa6c40b2279d3"
failures = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


def show(commit, path):
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def consts(code, names):
    out = {}
    for n in ast.parse(code).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and n.targets[0].id in names:
            out[n.targets[0].id] = ast.literal_eval(n.value)
    return out


def funcs(code, names):
    t = ast.parse(code)
    return {n.name: ast.get_source_segment(code, n) for n in t.body
            if isinstance(n, ast.FunctionDef) and n.name in names}


def test_sources(p=P):
    for (commit, path), m in SOURCES.items():
        code = show(commit, path)
        check(f"source {path}@{commit} is reachable", code is not None)
        if code is None:
            continue
        got = consts(code, set(m))
        for src_name, ours in m.items():
            check(f"prompt {ours} equals {src_name} of {path}", got.get(src_name) == getattr(p, ours))
    check("GOLD_RESPONDE matches the pinned hash",
          hashlib.sha256(p.GOLD_RESPONDE.encode()).hexdigest()[:16] == RESPONDE_SHA256_16)
    src = funcs(show("582a8cee", "audits/2026-10-22-gold-oracle.py") or "", {"jload", "norm"})
    mine = funcs(inspect.getsource(J), {"jload", "norm"})
    check("jload copied verbatim", src.get("jload") == mine.get("jload"))
    check("norm copied verbatim", src.get("norm") == mine.get("norm"))


def test_bodies():
    q, t = "Qual é a tiragem?", "x" * 7000
    for i, n in (("closed", 1200), ("oracle", 1200), ("repass", 900), ("pool", 700), ("premise", 700)):
        g = J.body(i, q, t)["generationConfig"]
        check(f"{i}: temperature 0, maxOutputTokens {n}, JSON mime",
              g == {"temperature": 0.0, "maxOutputTokens": n, "responseMimeType": "application/json"})
    reg = J.body("reg", q, t)
    check("reg: raw chunk cut at 6000", reg["input"] == t[:6000])
    check("reg: predicate contem_resposta + score nivel with 4 levels",
          [x["name"] for x in reg["questions"]] == ["contem_resposta", "nivel"]
          and len(reg["questions"][1]["levels"]) == 4)
    check("reg2 identical to reg", J.body("reg2", q, t) == reg)
    env = J.body("envelope", q, t)
    check("envelope: wrapped chunk, one predicate named relevante",
          env["input"] == f"TRECHO:\n---\n{t[:6000]}\n---" and [x["name"] for x in env["questions"]] == ["relevante"])
    gold = J.body("gold", q, t)
    check("gold: wrapped chunk, one predicate named responde",
          gold["input"] == env["input"] and [x["name"] for x in gold["questions"]] == ["responde"])
    check("oracle: closed answer defaults to NAO SEI", "NAO SEI" in J.body("oracle", q, "abc")["contents"][0]["parts"][0]["text"])


def gem(obj_text):
    return {"candidates": [{"content": {"parts": [{"text": obj_text}]}}]}


def test_parse(parse=J.parse):
    chunk = "O prazo do site novo ficou em 32 dias."
    ok = parse("pool", gem('{"trecho_responde": true, "oito_palavras": "O prazo do site novo ficou em"}'), chunk)
    check("pool valid response parses, leg passes", ok["valid"] and ok["label"] and ok["citacao_confere"])
    check("string 'false' is not a boolean", not parse("pool", gem('{"trecho_responde": "false", "oito_palavras": ""}'), chunk)["valid"])
    check("missing field is a missing label", not parse("pool", gem('{"oito_palavras": "x"}'), chunk)["valid"])
    check("unparseable text is a missing label", not parse("oracle", gem("não sei responder"), chunk)["valid"])
    check("no candidates is a missing label", not parse("oracle", {"candidates": []}, chunk)["valid"])
    o = parse("oracle", gem('{"trecho_responde": true, "sem_fonte_ja_responde": false, "citacao_verbatim": ""}'), chunk)
    check("oracle: empty quote fails the check", o["valid"] and not o["quote_ok"] and not o["label_source_rule"])
    d = {"answers": [{"name": "contem_resposta", "probability": 0.7}, {"name": "nivel", "score": 3}]}
    r = parse("reg", d)
    check("decisions: p 0.7 is positive", r["valid"] and r["label"] and r["p"] == 0.7)
    check("decisions: p exactly 0.5 is negative", parse("reg", {"answers": [{"name": "contem_resposta", "probability": 0.5}]})["label"] is False)
    check("decisions: boolean probability is invalid", not parse("gold", {"answers": [{"name": "responde", "probability": True}]})["valid"])
    check("decisions: wrong answer name is invalid", not parse("gold", {"answers": [{"name": "relevante", "probability": 0.9}]})["valid"])
    check("premise: unknown relation is invalid", not parse("premise", gem('{"relacao": "talvez"}'))["valid"])


def test_citation(fx_expected=None):
    exp = fx_expected or {
        "table row, quote de-tabulated": (False, False, False),
        "table row, quote copied with pipes": (True, True, True),
        "<u> wrapping dropped in the quote": (False, False, False),
        "escaped currency sign unescaped in the quote": (False, False, False),
        "drift into paraphrase after 13 characters": (False, False, False),
        "drift into paraphrase after 30 characters": (False, False, False),
        "drift into paraphrase after 53 characters": (False, False, False),
        "longer than 160 characters, diverging after 160": (True, False, False),
        "verbatim, differing only in accents and spacing": (True, True, True),
        "assembled from two places": (False, False, False),
        "empty quote": (False, False, False),
        "verbatim but under 12 normalised characters": (True, True, False),
    }
    got = {r["case"]: (r["oracle_160"], r["whole_quote"], r["eight_words"]) for r in A.fixtures()[0]}
    check("citation fixtures give the expected vetoes", got == exp)


def test_pairs():
    data = PAIRS.build()
    c = data["counts"]
    check("population matches the pre-registration",
          c["pairs"] == 555 and c["T_true"] == 89 and c["R_true"] == 59 and c["context_negative_pairs"] == 15
          and c["by_source"] == {"top": 500, "truth_outside_top": 5, "context_negative": 0, "random": 50})
    check("human sample strata 30/15/10/45", c["human_sample"] ==
          {"truth": 30, "context_negative": 15, "false_premise": 10, "other_false": 45})
    check("premise sample 55 + 30 + 25", c["premise_pairs"] == 110)
    check("committed pairs.json and SHEET.md match pairs.py",
          PAIRS.OUT.read_text() == PAIRS.dump(data) and PAIRS.SHEET.read_text() == PAIRS.sheet(data))
    sheet = PAIRS.SHEET.read_text()
    check("sheet carries no key, source or chunk id",
          all(w not in sheet for w in ('"T"', "truth_outside", "context_negative", "top1", "chunk")))


def test_budget():
    prices = json.loads((HERE / "prices.json").read_text())
    b = RUN.Budget.__new__(RUN.Budget)
    b.prices = dict(prices, ceiling_usd=0.035)
    b.lock = __import__("threading").Lock()
    b.entries, b.in_flight = [], 0
    check("three calls of 0.01 fit under 0.035", all(b.reserve() for _ in range(3)))
    check("a fourth in flight is refused", not b.reserve())
    usd = RUN.cost(prices, "gemini-2.5-flash-lite", {"promptTokenCount": 1_000_000, "candidatesTokenCount": 1_000_000})
    check("gemini cost from usage", abs(usd - 0.50) < 1e-9)


def fake_runs(tmp, flip=None):
    """Write primary runs for a judge that agrees with T on every pair (flip: keys to invert)."""
    data, qtext, text = RUN.load()
    runs = pathlib.Path(tmp) / "runs"
    runs.mkdir()
    flip = flip or set()
    keys = [(f"{p['query']}:{p['chunk']}", p) for p in data["pairs"]]
    def w(name, rows):
        (runs / f"{name}-full.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    for i in ("reg", "reg2", "envelope", "gold"):
        rows = []
        for k, p in keys:
            lab = p["T"] != (k in flip)
            rows.append({"key": k, "parsed": {"valid": True, "p": 0.9 if lab else 0.1, "label": lab}})
        for g in data["gold_check"]:
            k = f"{g['query']}:{g['chunk']}"
            if i == "gold" and all(k != kk for kk, _ in keys):
                rows.append({"key": k, "parsed": {"valid": True, "p": 0.9 if g["T"] else 0.1, "label": g["T"]}})
        w(i, rows)
    w("oracle", [{"key": k, "parsed": {"valid": True, "label": p["T"], "quote_ok": True, "whole_quote_ok": True,
                                         "quote": "x" if p["T"] else "", "sem_fonte_ja_responde": False}} for k, p in keys])
    w("pool", [{"key": k, "parsed": {"valid": True, "label": p["T"], "citacao_confere": True,
                                       "label_with_leg": p["T"]}} for k, p in keys])
    w("repass", [])
    w("premise", [])
    w("closed", [])
    ann = pathlib.Path(tmp) / "annotations.tsv"
    lines = ["row\tcode\tnote"]
    for s in sorted(data["human_sample"], key=lambda x: x["row"]):
        lines.append(f"{s['row']}\t{'C' if data['pairs'][s['pair']]['T'] else 'F'}\t")
    ann.write_text("\n".join(lines) + "\n")
    return runs, ann


def test_end_to_end():
    old = RUN.RUNS, RUN.ANNOT
    with tempfile.TemporaryDirectory() as tmp:
        RUN.RUNS, RUN.ANNOT = fake_runs(tmp)
        try:
            rep, _ = A.analyze()
        finally:
            RUN.RUNS, RUN.ANNOT = old
    c = rep["against_T"]["reg/all"]
    check("a judge equal to T scores precision 1, recall 1, kappa 1",
          c["precision"]["value"] == 1.0 and c["recall"]["value"] == 1.0 and c["kappa"] == 1.0)
    check("stability: identical runs change no label (P3 seen)", rep["predictions"]["P3"]["result"] == "seen again")
    check("human sample equal to T disagrees nowhere", rep["human"]["weighted_disagreement"] == 0.0)
    data = PAIRS.build()
    import metrics as M
    plan = json.loads((HERE.parent / "plan" / "plan.json").read_text())
    rankings = json.loads((HERE.parent / "results" / "3.11.1" / "rankings.json").read_text())
    exp = []
    for q in plan["queries"]:
        if q["kind"] != "fact":
            continue
        rank = [x["id"] for x in rankings[q["id"]]][:10]
        R = {p["chunk"] for p in data["pairs"] if p["query"] == q["id"] and p["R"]}
        T = {p["chunk"] for p in data["pairs"] if p["query"] == q["id"] and p["T"]}
        exp.append(M.ndcg_gold(rank, M.pooled(R, T, rank)))
    check("pooled nDCG from a judge equal to T equals step 1's pooled",
          rep["stability"]["ndcg_pooled"]["reg"] == round(sum(exp) / len(exp), 4))
    one_neg = next(f"{p['query']}:{p['chunk']}" for p in data["pairs"] if not p["T"] and p["kind"] == "fact")
    with tempfile.TemporaryDirectory() as tmp:
        RUN.RUNS, RUN.ANNOT = fake_runs(tmp, flip={one_neg})
        try:
            rep2, _ = A.analyze()
        finally:
            RUN.RUNS, RUN.ANNOT = old
    check("one flipped label shows as one false positive", rep2["against_T"]["reg/all"]["fp"] == 1)


def test_annotations():
    old = RUN.ANNOT
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "a.tsv"
        p.write_text("row\tcode\tnote\n" + "".join(f"{i}\t\t\n" for i in range(1, 101)))
        RUN.ANNOT = p
        try:
            check("an uncommitted or blank annotation file is refused", RUN.annotations_ok() is not None)
        finally:
            RUN.ANNOT = old


def main():
    if "--sabotage" in sys.argv:
        class Bad:
            pass
        for k in dir(P):
            if k.isupper():
                setattr(Bad, k, getattr(P, k))
        Bad.POOL = P.POOL.replace("8 primeiras", "oito primeiras")
        before = len(failures)
        test_sources(Bad)
        test_citation({"empty quote": (True, True, True)})
        bad_parse = lambda i, r, c=None: {"valid": True, "label": False, "citacao_confere": False,  # noqa: E731
                                          "quote_ok": True, "label_source_rule": True, "p": 0.5}
        test_parse(bad_parse)
        caught = len(failures) - before
        print(f"sabotage: {caught} failures caught")
        sys.exit(0 if caught >= 3 else 1)
    test_sources()
    test_bodies()
    test_parse()
    test_citation()
    test_pairs()
    test_budget()
    test_annotations()
    test_end_to_end()
    print(f"{'FAILED' if failures else 'all passed'}: {len(failures)} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
