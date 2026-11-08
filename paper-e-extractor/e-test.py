#!/usr/bin/env python3
"""Offline tests of the Paper E runner and analysis. No network: the Batch API, the reader and
both judges are fakes. Synthetic instances, temporary directories.

  python3 -I e-test.py          prints each check, ends with ALL PASS or exits 1
"""
import argparse
import importlib.util
import json
import pathlib
import sqlite3
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ER = load("e_run", "e-run.py")
EA = load("e_analyze", "e-analyze.py")
EP = ER.e_prompts
EB = ER.e_batch
LME = ER.lme
FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


# ------------------------------------------------------------------ fakes
def fake_units_text(block, shape):
    mem = [{"text": "F:" + block, "category": "context", "importance": 0.8},
           {"text": "low", "category": "context", "importance": 0.2}]
    return json.dumps(mem if shape == "list" else {"memories": mem})


class FakeGemini:
    """Files, batches, list, download. Response shape per request key: '0'-'3' list form,
    'e' error line, 'f' missing from the output, anything else the object form."""

    def __init__(self, polls_before_done=1):
        self.files, self.batches, self.creates, self.polls_before_done = {}, {}, 0, polls_before_done
        self.n = 0

    def __call__(self, method, url, body=None, headers=None, timeout=300):
        self.n += 1
        if "/upload/v1beta/files" in url:
            return 200, {"X-Goog-Upload-URL": f"fake://upload/{self.n}"}, b"{}"
        if url.startswith("fake://upload/"):
            name = f"files/in{self.n}"
            self.files[name] = body
            return 200, {}, json.dumps({"file": {"name": name}}).encode()
        if ":batchGenerateContent" in url:
            self.creates += 1
            b = json.loads(body)["batch"]
            name = f"batches/b{self.creates}"
            self.batches[name] = {"file": b["input_config"]["file_name"], "dn": b["display_name"],
                                  "polls": 0, "model": url.split("/models/")[1].split(":")[0]}
            return 200, {}, json.dumps({"name": name}).encode()
        if "/v1beta/batches?" in url:
            ops = [{"name": n, "metadata": {"displayName": b["dn"]}} for n, b in self.batches.items()]
            return 200, {}, json.dumps({"operations": ops}).encode()
        if "/v1beta/batches/" in url:
            name = "batches/" + url.split("/v1beta/batches/")[1].split("?")[0]
            b = self.batches[name]
            b["polls"] += 1
            if b["polls"] <= self.polls_before_done:
                return 200, {}, json.dumps({"name": name, "metadata": {"state": "BATCH_STATE_RUNNING"}}).encode()
            return 200, {}, json.dumps({"name": name, "metadata": {
                "state": "BATCH_STATE_SUCCEEDED", "output": {"responsesFile": f"files/out-{name[8:]}"}}}).encode()
        if "/download/v1beta/files/out-" in url:
            bname = "batches/" + url.split("files/out-")[1].split(":")[0]
            lines = []
            for ln in self.files[self.batches[bname]["file"]].decode().splitlines():
                req = json.loads(ln)
                k = req["key"]
                block = req["request"]["contents"][0]["parts"][0]["text"].split("\n\nConversa:\n", 1)[1]
                if k[-1] == "f":
                    continue
                if k[-1] == "e":
                    lines.append({"key": k, "error": {"code": 13, "message": "internal"}})
                    continue
                txt = fake_units_text(block, "list" if k[-1] in "0123" else "dict")
                lines.append({"key": k, "response": {
                    "candidates": [{"content": {"parts": [{"text": txt}]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 100},
                    "modelVersion": self.batches[bname]["model"]}})
            return 200, {}, "\n".join(json.dumps(x) for x in lines).encode()
        raise AssertionError(f"unexpected call {method} {url}")


def fake_post(url, body, hdr, timeout=180):
    """reader, judge 2 (Gemini) and judge 1 (OpenAI Decisions) for the read phase; sync distill."""
    if "api.openai.com" in url:
        ref = body["input"].split("RESPOSTA DE REFERENCIA:\n---\n")[1].split("\n---")[0]
        cand = body["input"].split("RESPOSTA DO CANDIDATO:\n---\n")[1].split("\n---")[0]
        yes = ref in cand
        return {"model": "gpt-6-luna", "answers": [
            {"name": "contem", "probability": 0.9 if yes else 0.1},
            {"name": "contradiz", "probability": 0.05},
            {"name": "nivel", "score": 3.0 if yes else 0.0, "probabilities": []}]}
    if "systemInstruction" in body:                       # reader
        text = body["contents"][0]["parts"][0]["text"]
        material = text.split("MATERIAL:\n", 1)[1]
        ans = "a resposta é CODE-OK" if "CODE-OK" in material else "NAO SEI"
        return {"candidates": [{"content": {"parts": [{"text": ans}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
                "modelVersion": "gemini-3.8-flash"}
    text = body["contents"][0]["parts"][0]["text"]
    if "Você é um avaliador" in text:                      # judge 2
        ok = "RESPOSTA A AVALIAR: a resposta é CODE-OK" in text
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"correta": ok})}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}}
    block = text.split("\n\nConversa:\n", 1)[1]                # sync distill
    return {"candidates": [{"content": {"parts": [{"text": fake_units_text(block, "dict")}]},
                            "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 100},
            "modelVersion": "fake"}


def synth():
    """3 instances; the answer session of each holds CODE-OK."""
    data, man = {}, {"confirm": ["q1", "q2", "q3"], "control_subsample": ["q1"]}
    for i, q in enumerate(man["confirm"]):
        sess = [[{"role": "user", "content": f"sessão {q}-{j} " + "texto de enchimento " * 30}]
                for j in range(3)]
        sess[1][0]["content"] += f" o código é CODE-OK para {q}"
        data[q] = {"question_id": q, "question_type": "single-session-user",
                   "question": "qual o código?", "question_date": "2023/05/01 (Mon) 10:00",
                   "answer": "CODE-OK", "haystack_sessions": sess,
                   "haystack_session_ids": [f"{q}-s{j}" for j in range(3)],
                   "haystack_dates": [f"2023/04/0{j+1} (Sat) 10:00" for j in range(3)],
                   "answer_session_ids": [f"{q}-s1"]}
    return data, man


# ------------------------------------------------------------------ tests
def t_prompts_and_parser():
    print("prompts and parser")
    check("C2 is byte-identical to Paper 3's", EP.sha("C2") == EP.C2_SHA256)
    check("P keeps C0's output contract", EP.PROMPTS["P"].endswith(LME.DISTILL_SYSTEM[LME.DISTILL_SYSTEM.index(LME._ANCHOR):]))
    check("P drops C0's category list", "Decisões tomadas" not in EP.PROMPTS["P"] and "Ignore:" not in EP.PROMPTS["P"])
    u, ok = EP.parse_memories('{"memories": [{"text": "a", "importance": 0.7}, {"text": "b", "importance": 0.4}]}')
    check("object form: kept >= 0.5 only", ok and [x["text"] for x in u] == ["a"])
    u, ok = EP.parse_memories('[{"text": "c", "importance": 0.9}]')
    check("top-level list accepted", ok and [x["text"] for x in u] == ["c"])
    check("bare [] is a parsed empty block", EP.parse_memories("[]") == ([], True))
    check("invalid JSON is a failed block", EP.parse_memories("not json") == ([], False))
    check("empty text is a failed block", EP.parse_memories("") == ([], False))
    check("non-numeric importance dropped, block parsed",
          EP.parse_memories('{"memories": [{"text": "d", "importance": "0.9"}]}') == ([], True))


def t_bodies_and_keys():
    print("request bodies and cache keys")
    bL, bF = ER.request_body("L", "C2", "x"), ER.request_body("F", "C2", "x")
    check("L body equals Paper 3's distill body",
          bL == {"contents": [{"role": "user", "parts": [{"text": LME.PROMPTS["C2"] + "\n\nConversa:\nx"}]}],
                 "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}})
    gF = dict(bF["generationConfig"])
    check("F body differs only by thinkingBudget 0",
          gF.pop("thinkingConfig") == {"thinkingBudget": 0} and gF == bL["generationConfig"]
          and bF["contents"] == bL["contents"])
    keys = {ER.dkey(e, c, "x") for e in "LF" for c in ("C0", "C2", "P")}
    check("six distinct keys per block", len(keys) == 6)


def t_seed(tmp):
    print("seed from Paper 3")
    src = tmp / "p3.sqlite"
    db = sqlite3.connect(src)
    db.execute("CREATE TABLE c (k TEXT PRIMARY KEY, kind TEXT, v TEXT)")
    db.execute("INSERT INTO c VALUES (?,?,?)", (LME.h("distill", "C0", LME.PROMPTS["C0"], "b1"), "distill",
                                                json.dumps({"units": [{"text": "u"}], "failed": False})))
    db.execute("INSERT INTO c VALUES (?,?,?)", (LME.h("distill", "C2", LME.PROMPTS["C2"], "b1"), "distill",
                                                json.dumps({"units": [], "failed": True})))
    db.commit()
    ER.P3_CACHE = src
    cache = LME.Cache(str(tmp / "seed-cache.sqlite"))
    need = {("L", "C0", "b1"), ("L", "C2", "b1"), ("L", "P", "b1"), ("F", "C0", "b1")}
    n, skipped = ER.seed(cache, need)
    check("copies a good flash-lite distillation", n == 1 and cache.get(ER.dkey("L", "C0", "b1"))["via"] == "paper3")
    check("leaves a Paper 3 failure to distill again", skipped == 1 and cache.get(ER.dkey("L", "C2", "b1")) is None)
    check("never seeds P or the flash extractor",
          cache.get(ER.dkey("L", "P", "b1")) is None and cache.get(ER.dkey("F", "C0", "b1")) is None)


def t_batch(tmp):
    print("batch path")
    out = tmp / "run"
    out.mkdir()
    fake = FakeGemini(polls_before_done=1)
    EB.TRANSPORT = fake
    ER.CHUNK = 4
    cache = LME.Cache(str(out / "cache.sqlite"))
    sp = ER.Spend(out, 5.0)
    blocks = [f"bloco {i} " + "x" * 50 for i in range(10)]
    need = {(e, "P", b) for e in "LF" for b in blocks}
    todo = ER.todo_of(cache, need)
    check("20 requests to do", len(todo) == 20)
    ER.distill_batch(out, cache, sp, todo, "t", max_inflight=2, wait=False, poll=0)
    st = json.loads((out / "batches.json").read_text())
    check("chunks by extractor, 4 per chunk", [c["n"] for c in st] == [4, 4, 2, 4, 4, 2]
          and {c["ext"] for c in st} == {"L", "F"})
    check("at most max_inflight submitted on the first pass", fake.creates == 2)
    check("nothing ingested while running", all(c["state"] != "done" for c in st))
    ER.distill_batch(out, cache, sp, ER.todo_of(cache, need), "t", max_inflight=2, wait=True, poll=0)
    st = json.loads((out / "batches.json").read_text())
    check("every chunk done", all(c["state"] == "done" for c in st), [c["state"] for c in st])
    check("each chunk created exactly once", fake.creates == len(st), f"{fake.creates} creates")
    left = ER.todo_of(cache, need)
    exp_left = sum(1 for k, *_ in todo if k[-1] in "ef")
    check("error and missing lines stay to do", len(left) == exp_left, f"{len(left)} vs {exp_left}")
    lst = [cache.get(k) for k, *_ in todo if k[-1] in "0123"]
    check("list-form answers parsed", lst and all(v and not v["failed"] and len(v["units"]) == 1 for v in lst))
    v = next(cache.get(k) for k, *_ in todo if k[-1] not in "0123ef")
    check("object-form answers parsed, low importance dropped", len(v["units"]) == 1 and v["via"] == "batch")
    n_ok = len(todo) - exp_left
    exp_usd = sum((1000 * ER.PRICE[e][0] + 100 * ER.PRICE[e][1]) * 0.5
                  for k, e, *_ in todo if k[-1] not in "ef")
    check("batch spend at half the list price", abs(sp.led.usd - exp_usd) < 1e-9, f"{sp.led.usd} vs {exp_usd}")
    before = fake.creates
    ER.distill_batch(out, cache, sp, ER.todo_of(cache, need), "t", max_inflight=2, wait=True, poll=0)
    check("a rerun submits nothing", fake.creates == before)
    # a process that died between create and recording the batch
    st = json.loads((out / "batches.json").read_text())
    st[0]["state"], st[0]["batch"] = "new", None
    (out / "batches.json").write_text(json.dumps(st))
    ER.distill_batch(out, cache, sp, [], "t", max_inflight=2, wait=True, poll=0)
    st = json.loads((out / "batches.json").read_text())
    check("duplicate guard adopts the batch by display name", fake.creates == before and st[0]["batch"] == "batches/b1")
    ER.distill_sync(cache, sp, ER.todo_of(cache, need), workers=2)
    check("sync clears the residue", ER.todo_of(cache, need) == [])
    sp.save()
    sp.lockf.close()


def t_cap(tmp):
    print("cap")
    out = tmp / "cap"
    out.mkdir()
    fake = FakeGemini()
    EB.TRANSPORT = fake
    cache = LME.Cache(str(out / "cache.sqlite"))
    sp = ER.Spend(out, 0.0005)
    need = {("F", "P", f"b{i}") for i in range(4)}
    ER.distill_batch(out, cache, sp, ER.todo_of(cache, need), "c", max_inflight=4, wait=True, poll=0)
    check("a chunk past the cap is held, not submitted", fake.creates == 0)
    sp.lockf.close()
    sp2 = ER.Spend(out, 1.0)
    check("spend is cumulative across processes", sp2.prior == sp.led.usd - sp.prior)
    try:
        ER.Spend(out, 1.0)
        check("second process on the same out dir refused", False)
    except SystemExit:
        check("second process on the same out dir refused", True)
    sp2.lockf.close()


def t_frozen():
    print("freeze")
    try:
        ER.frozen_check()
        check("distill/read refuse before the tag exists", ER.TAG in ER.subprocess.run(
            ["git", "-C", str(HERE), "tag", "-l", ER.TAG], capture_output=True, text=True).stdout)
    except SystemExit as e:
        check("distill/read refuse before the tag exists", "does not exist" in str(e))


def t_read(tmp):
    print("read phase")
    out = tmp / "read"
    out.mkdir()
    data, man = synth()
    EB.TRANSPORT = FakeGemini(polls_before_done=0)
    ER.CHUNK = 1000
    cache = LME.Cache(str(out / "cache.sqlite"))
    sp = ER.Spend(out, 5.0)
    need, sblocks = ER.needs(man, data)
    a = argparse.Namespace(workers=2)
    try:
        ER.read(a, out, man, data, sblocks, cache, sp, need)
        check("read refuses with distillations missing", False)
    except SystemExit as e:
        check("read refuses with distillations missing", "no distillation" in str(e))
    ER.distill_batch(out, cache, sp, ER.todo_of(cache, need), "r", 4, True, 0)
    ER.distill_sync(cache, sp, ER.todo_of(cache, need), 2)
    ER.read(a, out, man, data, sblocks, cache, sp, need)
    rows = [json.loads(l) for l in open(out / "rows.ndjson")]
    check("6 cells per instance plus the positive control", len(rows) == 3 * 6 + 1, len(rows))
    pos = [r for r in rows if r["cell"] == "F_C2_pos"]
    check("positive control only on control_subsample", [r["qid"] for r in pos] == ["q1"])
    check("positive control holds no answer session", pos[0]["evidence_kept"] == 0 and not pos[0]["correct"])
    main = [r for r in rows if r["cell"] != "F_C2_pos"]
    check("every full-window cell answers (fake extractor keeps the code)",
          all(r["correct"] and r["correct_j2"] for r in main))
    check("extractor recorded per row", {r["extractor"] for r in main} == set(ER.MODELS.values()))
    rc = json.loads((out / "receipt.json").read_text())
    check("receipt counts the distillations by source",
          sum(rc["distill_by_source"].values()) == len(need) and rc["rows"] == 19)
    sp.lockf.close()


def t_analysis():
    print("analysis")
    data = {}
    rows = []
    # 40 instances in 20 clusters of 2 (shared answer session); designed cells:
    #   L_C0 = 0, L_C2 = 1 for all; F_C0 = 1 for half, F_C2 = 1 for all -> I = -0.5 exactly
    for i in range(40):
        q = f"q{i:02d}"
        data[q] = {"answer_session_ids": [f"s{i // 2}"]}
        y = {"L_C0": 0, "L_C2": 1, "L_P": 1, "F_C0": i % 2, "F_C2": 1, "F_P": 1}
        for c, v in y.items():
            rows.append({"qid": q, "cell": c, "correct": v, "correct_j2": v, "abstained": not v,
                         "served_chars": 100, "question_type": "t"})
        if i < 10:
            rows.append({"qid": q, "cell": "F_C2_pos", "correct": 0, "correct_j2": 0,
                         "abstained": True, "served_chars": 50, "question_type": "t"})
    txt, J = EA.analyze(rows, data)
    check("interaction estimate exact", abs(J["primary"]["est"] + 0.5) < 1e-9, J["primary"])
    check("clusters from shared answer sessions", J["clusters"] == 20)
    check("controls pass on designed cells", J["controls"]["interpret"])
    check("verdict: shrinks", "shrinks" in J["primary"]["verdict"])
    rows2 = [dict(r, correct=1) if r["cell"] == "F_C2_pos" else r for r in rows]
    _, J2 = EA.analyze(rows2, data)
    check("failed positive control blocks interpretation",
          not J2["controls"]["interpret"] and J2["primary"]["verdict"] == "not interpreted")
    rows3 = [r for r in rows if not (r["qid"] == "q00" and r["cell"] == "F_P")]
    _, J3 = EA.analyze(rows3, data)
    check("instance missing a cell is left out and named", J3["n"] == 39 and J3["incomplete"] == ["q00"])
    txt_b, _ = EA.analyze(rows, data)
    check("analysis is deterministic", txt_b == txt)


def main():
    LME.post = fake_post            # no test may reach the network
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        t_prompts_and_parser()
        t_bodies_and_keys()
        t_seed(tmp)
        t_batch(tmp)
        t_cap(tmp)
        t_frozen()
        t_read(tmp)
        t_analysis()
    print("\nALL PASS" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
