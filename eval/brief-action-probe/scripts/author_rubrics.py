#!/usr/bin/env python3
"""§6.2 rubrics (GPT, from the input alone) and §2.1 relevance diagnostic (Gemini). Refuses to overwrite.
B1 items come from the archived snapshot recorded in the manifest (spec v3.2)."""
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from probe.llm import gemini_json, openai_json  # noqa: E402
from probe.snapshots import build_index  # noqa: E402

ROOT = "/root/medicoes/7b"
RUBRIC = """An AI agent ({agent}) receives the input below as its next turn. Without guessing hidden
context, state what a correct FIRST action must do and must not do, which tool arguments are required,
and any external fact stated in the input itself. Return JSON with keys: must (list of strings),
must_not (list), required_args (list of argument names), external_facts (list, only facts present in the
input). INPUT:
{input}"""
RELEVANCE = """A request leaves one argument implicit: "{arg}". Below are memory items the agent had.
Is the implicit argument present in any item? Return JSON {{"present": true|false, "item_id": <id or null>}}.
REQUEST: {request}
ITEMS:
{items}"""


def main():
    for p in ("rubrics.jsonl", "relevance.jsonl"):
        if os.path.exists(f"{ROOT}/{p}"):
            sys.exit(f"{p} exists: frozen")
    units = [json.loads(l) for l in open(f"{ROOT}/manifest.jsonl")]
    tmp = f"{ROOT}/rubrics.jsonl.partial"
    done = {json.loads(l)["unit_id"] for l in open(tmp)} if os.path.exists(tmp) else set()
    with open(tmp, "a", encoding="utf-8") as f:
        for u in units:
            if u["unit_id"] in done:
                continue
            text = open(f"{ROOT}/inputs/{u['unit_id']}.txt", encoding="utf-8").read()
            r = openai_json(RUBRIC.format(agent=u["agent"], input=text[:6000]))
            f.write(json.dumps({"unit_id": u["unit_id"], **{k: r.get(k, []) for k in
                    ("must", "must_not", "required_args", "external_facts")}}, ensure_ascii=False) + "\n")
            f.flush()
    os.rename(tmp, f"{ROOT}/rubrics.jsonl")
    idx = build_index((e["persona"], e["text"]) for e in map(json.loads, open(f"{ROOT}/snapshots.jsonl", encoding="utf-8")))
    snap = {(p, s["generated_iso"]): s for p, ss in idx.items() for s in ss}
    hreq = {h["h_id"]: h for h in (json.loads(l) for l in open(f"{ROOT}/h_requests.jsonl", encoding="utf-8"))}
    with open(f"{ROOT}/relevance.jsonl", "w", encoding="utf-8") as f:
        for u in units:
            if u["stratum"] != "H":
                continue
            s = snap[(u["b1_persona"], u["b1_generated_iso"])]
            items = "\n".join(f"[{i['id']}] {i['text']}" for i in s["items"])
            h = hreq[u["unit_id"]]
            r = gemini_json(RELEVANCE.format(arg=h["implicit_argument"], request=h["request"], items=items))
            f.write(json.dumps({"unit_id": u["unit_id"], "present": bool(r.get("present")),
                                "item_id": r.get("item_id")}) + "\n")
    print("rubrics and relevance written")


if __name__ == "__main__":
    main()
