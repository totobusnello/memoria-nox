#!/usr/bin/env python3
"""Paper A, prospective part: write the holdout questions (PREREGISTRATION.md §3, §5 step 2).

  python3 -I holdout-generate.py --db <snapshot.db> --draw <private>/draw.json \
      --out <private>/holdout-v1.jsonl --commit HOLDOUT-COMMITMENT.json

Takes the drawn passages stratum by stratum, in draw order, and asks the writer model for one
question per passage until each stratum's quota is filled. A passage the model calls IMPOSSIVEL,
or an answer that is not one line, is skipped and counted as a replacement. Every call is cached
in <out>.cache.jsonl, so a resumed run never pays twice.

The holdout (questions, anchors, file names) goes to --out, which must be outside the repository.
--commit receives only what may be public: sha256 of the holdout, of the draw, of the prompt and of
this script; n and per-stratum counts; replacements; the model; and the lexical-overlap terciles.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
MODEL = "glm-5.3"
MAX_CALLS = 200
ANCHOR_CHARS = 160
STOP = set("""a o as os um uma uns umas de da do das dos em na no nas nos por para com sem que
qual quais como quando onde porque e ou se ao aos à às é são foi ser está estão isso este esta
the of and to in is for on with""".split())


def sha(b):
    return hashlib.sha256(b).hexdigest()


def inside_repo(p):
    return subprocess.run(["git", "-C", str(pathlib.Path(p).resolve().parent), "rev-parse"],
                          capture_output=True).returncode == 0


def content_words(t):
    return {w for w in re.findall(r"\w+", t.lower()) if len(w) >= 4 and w not in STOP}


def overlap(q, chunk):
    a, b = content_words(q), content_words(chunk)
    return len(a & b) / len(a | b) if a | b else 0.0


def key():
    return pathlib.Path(os.path.expanduser("~/.config/glm/token")).read_text().strip()


def ask(prompt):
    body = json.dumps({"model": MODEL, "temperature": 0, "max_tokens": 2048,
                       "thinking": {"type": "enabled"}, "reasoning_effort": "low",
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for i in range(4):
        try:
            r = urllib.request.Request(URL, data=body, method="POST", headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {key()}"})
            with urllib.request.urlopen(r, timeout=180) as resp:
                d = json.loads(resp.read())
            return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip(), d.get("model")
        except Exception as e:      # retried, then raised: a failed call is never a skipped passage
            if i == 3:
                raise
            time.sleep(5 * (i + 1))


def main():
    ap = argparse.ArgumentParser()
    for k in ("--db", "--draw", "--out", "--commit"):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    if inside_repo(a.out):
        sys.exit("refusing: --out is inside a git repository; the holdout is private")
    prompt_t = (HERE / "holdout-prompt.txt").read_text(encoding="utf-8")
    draw_b = pathlib.Path(a.draw).read_bytes()
    draw = json.loads(draw_b)
    if draw.get("smoke") and not a.commit.endswith(".smoke.json"):
        sys.exit("refusing: a smoke draw can only write a commitment named *.smoke.json")
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    cache_p = pathlib.Path(a.out + ".cache.jsonl")
    cache = {}
    if cache_p.exists():
        for l in cache_p.read_text().splitlines():
            e = json.loads(l)
            cache[e["k"]] = e
    calls, rows, repl = 0, [], {}
    for s in sorted(draw["quota"]):
        got, repl[s] = 0, 0
        for cand in draw["strata"][s]:
            if got == draw["quota"][s]:
                break
            text = con.execute("SELECT chunk_text FROM chunks WHERE id = ?",
                               (cand["chunk_id"],)).fetchone()[0]
            p = prompt_t.replace("{chunk}", text)
            k = sha((MODEL + "\0" + p).encode())
            if k not in cache:
                calls += 1
                if calls > MAX_CALLS:
                    sys.exit(f"stopped: more than {MAX_CALLS} calls")
                ans, model = ask(p)
                cache[k] = {"k": k, "answer": ans, "model": model}
                with cache_p.open("a") as fh:
                    fh.write(json.dumps(cache[k], ensure_ascii=False) + "\n")
            ans = cache[k]["answer"]
            if ans.upper().startswith("IMPOSSIVEL") or "\n" in ans or not ans:
                repl[s] += 1
                continue
            got += 1
            # query_id is an integer because the v3 tooling casts it (audits/2026-10-27-v3-rescore.py);
            # 9001.. cannot collide with the 1..66 of the v1-v3 gold sets
            rows.append({"query_id": 9000 + len(rows) + 1, "holdout_id": f"{s}{got:02d}",
                         "stratum": s, "category": f"holdout-{s}", "status": "accepted", "query": ans,
                         "gold": [{"source_file": cand["source_file"],
                                   "anchor": text[:ANCHOR_CHARS], "chunk_id": cand["chunk_id"]}],
                         "overlap": round(overlap(ans, text), 4),
                         "writer_model": cache[k]["model"]})
        if got < draw["quota"][s]:
            sys.exit(f"stratum {s}: frame exhausted at {got} of {draw['quota'][s]}")
    blob = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode()
    pathlib.Path(a.out).write_bytes(blob)
    ov = sorted(r["overlap"] for r in rows)
    commit = {"holdout_sha256": sha(blob), "n": len(rows),
              "per_stratum": {s: sum(r["stratum"] == s for r in rows) for s in draw["quota"]},
              "replacements": repl, "writer_model_requested": MODEL,
              "writer_models_served": sorted({r["writer_model"] or "?" for r in rows}),
              "draw_sha256": sha(draw_b), "prompt_sha256": sha(prompt_t.encode()),
              "script_sha256": sha(pathlib.Path(__file__).read_bytes()),
              "overlap_terciles": [ov[len(ov) // 3], ov[2 * len(ov) // 3]],
              "new_calls_this_run": calls}
    pathlib.Path(a.commit).write_text(json.dumps(commit, indent=1) + "\n")
    print(json.dumps(commit, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
