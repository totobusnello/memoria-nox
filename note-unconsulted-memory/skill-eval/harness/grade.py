#!/usr/bin/env python3
"""Blind grader for K tasks (PROTOCOL.md section 6, H2). W+/W- and G are scored from tool calls.

The grader sees the task prompt, the decisive fact, the pass criterion and the reply text. It never
sees the arm, the tool calls or the run id. Model: a different family from the model under test.

A "pass" must quote the reply verbatim; the quote is checked mechanically, because an LLM grader
can claim support it does not have. A pass whose quote is not in the reply is re-asked once, and
if it fails again the run is marked grader_invalid (reported, never counted as pass or fail).

Usage:
  grade.py calibrate --bank tasks.jsonl --out calib.jsonl     # oracle and null replies per K task
  grade.py runs --bank tasks.jsonl --results runs/<label>/results.jsonl --out graded.jsonl
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path

MODEL = os.environ.get("GRADER_MODEL", "gemini-4-argon")
KEYFILE = Path(os.environ.get("GEMINI_KEY_FILE", Path.home() / ".config/secrets/GEMINI_API_KEY"))

INSTRUCTIONS = """You grade one reply from an AI assistant to an engineering request.
You get the request, the DECISIVE FACT the reply needs, the PASS CRITERION, and the reply.
Judge only whether the reply meets the pass criterion. Style, length and extra content do not matter.
A reply that asks for more information or gives generic steps without the decisive fact FAILS.
A reply that mentions the fact but then proceeds as if it did not matter FAILS.
If the verdict is pass, evidence_quote must be copied verbatim from the reply (one contiguous span,
at most 300 characters) and must show the criterion being met. If fail, evidence_quote may be empty."""

SCHEMA = {"type": "object", "properties": {
    "verdict": {"type": "string", "enum": ["pass", "fail"]},
    "evidence_quote": {"type": "string"},
    "reason": {"type": "string"}}, "required": ["verdict", "evidence_quote", "reason"]}

NULL_REPLY = ("Sure. Here is how to do it. 1. Find where this is configured: search the repository "
              "and the server config for the relevant setting. 2. Change the value as requested and keep "
              "the old value in a comment. 3. Restart the affected service and check the logs and health "
              "endpoint. 4. Commit the change with a clear message. If you share the file, I can give you "
              "the exact diff.")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def ask(task: dict, reply: str) -> dict:
    key = KEYFILE.read_text().strip()
    body = {
        "systemInstruction": {"parts": [{"text": INSTRUCTIONS}]},
        "contents": [{"role": "user", "parts": [{"text":
            f"REQUEST:\n{task['prompt']}\n\nDECISIVE FACT:\n{task['decisive_fact']}\n\n"
            f"PASS CRITERION:\n{task['pass_criterion']}\n\nREPLY:\n<<<\n{reply}\n>>>"}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                             "responseSchema": SCHEMA},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    for attempt in range(4):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            out = json.loads(text)
            out["model_version"] = data.get("modelVersion")
            return out
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError) as e:
            err = e
            time.sleep(2 ** attempt * 3)
    return {"verdict": "error", "evidence_quote": "", "reason": f"grader call failed: {err}"}


def grade(task: dict, reply: str) -> dict:
    for attempt in (1, 2):
        g = ask(task, reply)
        if g["verdict"] != "pass":
            g["quote_ok"] = None
            return g
        g["quote_ok"] = bool(g["evidence_quote"]) and norm(g["evidence_quote"]) in norm(reply)
        if g["quote_ok"]:
            return g
    g["verdict"] = "grader_invalid"
    return g


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["calibrate", "runs"])
    p.add_argument("--bank", required=True)
    p.add_argument("--results")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    bank = {t["id"]: t for t in map(json.loads, open(a.bank)) if t["set"] == "K"}
    done = set()
    if Path(a.out).exists():
        done = {(r["kind"], r["key"]) for r in map(json.loads, open(a.out))}
    with open(a.out, "a") as out:
        if a.mode == "calibrate":
            for t in bank.values():
                oracle = (f"Before doing this, one thing matters: {t['decisive_fact']} "
                          "So I would not do it the way you asked; here is what I recommend instead, "
                          "following from that.")
                for kind, reply, expect in (("oracle", oracle, "pass"), ("null", NULL_REPLY, "fail")):
                    if (kind, t["id"]) in done:
                        continue
                    g = grade(t, reply)
                    out.write(json.dumps({"kind": kind, "key": t["id"], "expect": expect, **g}) + "\n")
                    out.flush()
                    print(t["id"], kind, g["verdict"], file=sys.stderr)
        else:
            for r in map(json.loads, open(a.results)):
                t = bank.get(r["task"])
                if not t or ("run", r["run_id"]) in done:
                    continue
                g = grade(t, r.get("result") or "")
                out.write(json.dumps({"kind": "run", "key": r["run_id"], "task": r["task"],
                                      "arm": r["arm"], **g}) + "\n")
                out.flush()
                print(r["run_id"], g["verdict"], file=sys.stderr)


if __name__ == "__main__":
    main()
