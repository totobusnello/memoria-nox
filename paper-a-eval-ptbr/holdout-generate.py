#!/usr/bin/env python3
"""Paper A, prospective part: write the holdout questions (PREREGISTRATION.md §3, §5 step 2).

  python3 -I holdout-generate.py --db <snapshot.db> --draw <private>/draw.json \
      --out <private>/holdout-v1.jsonl --commit HOLDOUT-COMMITMENT.json

Takes the drawn passages stratum by stratum, in draw order, and asks the writer model for one
question and one verbatim evidence span per passage until each stratum's quota is filled. An
output is accepted only if it passes every check in VALIDATION below; otherwise the passage is
skipped, the reason is counted, and the next draw of the same stratum is used. Every call is
cached in <out>.cache.jsonl, so a resumed run never pays twice.

VALIDATION (fixed before the draw, PREREGISTRATION.md §3):
  impossible   the model answered IMPOSSIVEL
  format       not PERGUNTA: on one line followed by EVIDENCIA: (which may span lines)
  length       the question has more than 25 words, or is empty
  copy         the question shares a run of 4 or more consecutive words with the passage
  evidence     the evidence span, whitespace-normalised, is not a substring of the passage,
               or is shorter than 30 or longer than 300 characters

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
MAX_WORDS, COPY_RUN, EV_MIN, EV_MAX = 25, 4, 30, 300
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
    """Share of the QUESTION's content words that occur in the passage. Question-side, so a long
    passage does not dilute it (a Jaccard over the union did, as both reviews pointed out)."""
    a, b = content_words(q), content_words(chunk)
    return len(a & b) / len(a) if a else 0.0


def ws(t):
    return re.sub(r"\s+", " ", t).strip()


def words(t):
    return re.findall(r"\w+", t.lower())


def longest_shared_run(q, chunk):
    qa, ca = words(q), words(chunk)
    grams = {tuple(ca[i:i + n]) for n in range(1, 9) for i in range(len(ca) - n + 1)}
    best = 0
    for n in range(1, 9):
        if any(tuple(qa[i:i + n]) in grams for i in range(len(qa) - n + 1)):
            best = n
    return best


def validate(ans, chunk):
    if ans.strip().upper().startswith("IMPOSSIVEL"):
        return "impossible", None, None
    m = re.fullmatch(r"\s*PERGUNTA:\s*(.+?)\s*\n\s*EVIDENCIA:\s*(.+?)\s*", ans, flags=re.S)
    # the question must be one line; the evidence may span lines, because it is copied from a
    # passage that has line breaks (the first smoke rejected 2 valid outputs for exactly that)
    if not m or "\n" in m.group(1):
        return "format", None, None
    q, ev = ws(m.group(1)), ws(m.group(2))
    if not q or len(q.split()) > MAX_WORDS:
        return "length", None, None
    if longest_shared_run(q, chunk) >= COPY_RUN:
        return "copy", None, None
    if not (EV_MIN <= len(ev) <= EV_MAX) or ev not in ws(chunk):
        return "evidence", None, None
    return None, q, ev


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
    import importlib.util
    spec = importlib.util.spec_from_file_location("draw", HERE / "holdout-draw.py")
    dr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dr)
    if draw.get("snapshot_db_sha256") != dr.SNAPSHOT_DB_SHA or dr.file_sha(a.db) != dr.SNAPSHOT_DB_SHA:
        sys.exit("refusing: the draw or --db is not the registered snapshot")
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    cache_p = pathlib.Path(a.out + ".cache.jsonl")
    cache = {}
    if cache_p.exists():
        for l in cache_p.read_text().splitlines():
            e = json.loads(l)
            cache[e["k"]] = e
    calls, rows, repl, reasons = 0, [], {}, {}
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
            why, q, ev = validate(cache[k]["answer"], text)
            if why:
                repl[s] += 1
                reasons[why] = reasons.get(why, 0) + 1
                continue
            got += 1
            # query_id is an integer because the v3 tooling casts it (audits/2026-10-27-v3-rescore.py);
            # 9001.. cannot collide with the 1..66 of the v1-v3 gold sets
            rows.append({"query_id": 9000 + len(rows) + 1, "holdout_id": f"{s}{got:02d}",
                         "stratum": s, "category": f"holdout-{s}", "status": "accepted", "query": q,
                         # gold for H-A1 is the drawn chunk id itself, checked by the sha256 of its
                         # text; the evidence span is the anchor H-A2 follows into later snapshots
                         "gold": [{"source_file": cand["source_file"], "anchor": ev,
                                   "chunk_id": cand["chunk_id"],
                                   "chunk_text_sha256": sha(text.encode("utf-8"))}],
                         "overlap": round(overlap(q, text), 4),
                         "longest_shared_run": longest_shared_run(q, text),
                         "writer_model": cache[k]["model"]})
        if got < draw["quota"][s]:
            sys.exit(f"stratum {s}: frame exhausted at {got} of {draw['quota'][s]}")
    blob = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode()
    pathlib.Path(a.out).write_bytes(blob)
    ov = sorted(r["overlap"] for r in rows)
    commit = {"holdout_sha256": sha(blob), "n": len(rows),
              "per_stratum": {s: sum(r["stratum"] == s for r in rows) for s in draw["quota"]},
              "replacements": repl, "rejection_reasons": reasons,
              "cache_sha256": sha(cache_p.read_bytes()) if cache_p.exists() else None,
              "writer_model_requested": MODEL,
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
