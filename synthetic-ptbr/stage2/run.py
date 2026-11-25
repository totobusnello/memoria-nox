#!/usr/bin/env python3
"""Step 2 runner (PREREGISTRATION.md §7).

    python3 -I run.py <instrument> smoke|full|rerun [--dry]

Instruments, in the registered order: closed oracle pool reg reg2 envelope gold repass premise.
`--dry` builds every request and prints the counts and a hash of the bodies; it calls nothing and
needs no key. Without `--dry` the runner refuses unless the pre-registration tag is an ancestor of
HEAD, the working tree of stage2/ is clean, the human annotations are committed and complete, and
the instruments this one depends on have a full run.

Every attempt goes to ledger.json before and after it is sent. A call starts only if the spend so far
plus US$ 0.01 for each call in flight, itself included, stays within the US$ 20 ceiling.
"""
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import judges as J  # noqa: E402

ROOT = HERE.parent
REPO = ROOT.parent
TAG = "synthetic-ptbr-stage2-prereg"
ORDER = ["closed", "oracle", "pool", "reg", "reg2", "envelope", "gold", "repass", "premise"]
DEPENDS = {"oracle": ["closed"], "repass": ["closed", "oracle"], "reg2": ["reg"]}
RUNS = HERE / "runs"
LEDGER = HERE / "ledger.json"
ANNOT = HERE / "human" / "annotations.tsv"
CODES = {"C", "P", "D", "M", "F", "?"}
WORKERS = 4
SMOKE_N = 10
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
DECISIONS_URL = "https://api.openai.com/v1/decisions"


def load():
    data = json.loads((HERE / "pairs.json").read_text())
    plan = json.loads((ROOT / "plan" / "plan.json").read_text())
    chunks = json.loads((ROOT / "results" / "3.11.1" / "chunks-baseline.json").read_text())
    return data, {q["id"]: q["text"] for q in plan["queries"]}, {c["id"]: c["text"] for c in chunks}


def read_run(instrument, mode="full"):
    p = RUNS / f"{instrument}-{mode}.jsonl"
    if not p.exists():
        return None
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def primary(instrument):
    """The rerun replaces the first full run as primary when it exists (§7)."""
    return read_run(instrument, "rerun") or read_run(instrument, "full")


def units(instrument, data, qtext, text):
    """Each unit: (key, query id, chunk id or None)."""
    pairs = data["pairs"]
    if instrument == "closed":
        return [(qid, qid, None) for qid in qtext]
    if instrument in ("oracle", "pool", "reg", "reg2", "envelope"):
        return [(f"{p['query']}:{p['chunk']}", p["query"], p["chunk"]) for p in pairs]
    if instrument == "gold":
        seen = {(p["query"], p["chunk"]) for p in pairs}
        extra = [(g["query"], g["chunk"]) for g in data["gold_check"]
                 if g["as_gold"] == "random" and (g["query"], g["chunk"]) not in seen]
        return [(f"{q}:{c}", q, c) for q, c in [(p["query"], p["chunk"]) for p in pairs] + extra]
    if instrument == "premise":
        return [(f"{pairs[i]['query']}:{pairs[i]['chunk']}", pairs[i]["query"], pairs[i]["chunk"])
                for i in data["premise_pairs"]]
    if instrument == "repass":
        oracle = primary("oracle") or []
        eligible = {r["key"] for r in oracle
                    if r["parsed"].get("valid") and r["parsed"]["label"] and not r["parsed"]["quote_ok"]}
        return [(f"{p['query']}:{p['chunk']}", p["query"], p["chunk"]) for p in pairs
                if f"{p['query']}:{p['chunk']}" in eligible]
    raise ValueError(instrument)


def closed_answers():
    rows = primary("closed") or []
    return {r["key"]: r["parsed"].get("resposta") for r in rows if r["parsed"].get("valid")}


def build_bodies(instrument, data, qtext, text):
    closed = closed_answers() if instrument in ("oracle", "repass") else {}
    out = []
    for key, qid, cid in units(instrument, data, qtext, text):
        b = J.body(instrument, qtext[qid], text.get(cid) if cid is not None else None,
                   closed.get(qid))
        out.append((key, qid, cid, b))
    return out


# ------------------------------------------------------------------ preconditions
def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)


def annotations_ok():
    if not ANNOT.exists():
        return "human/annotations.tsv is missing"
    if git("ls-files", "--error-unmatch", str(ANNOT)).returncode:
        return "human/annotations.tsv is not committed"
    if git("diff", "--quiet", "HEAD", "--", str(ANNOT)).returncode:
        return "human/annotations.tsv has uncommitted changes"
    rows = [l.split("\t") for l in ANNOT.read_text().splitlines()[1:] if l.strip()]
    codes = {int(r[0]): (r[1].strip() if len(r) > 1 else "") for r in rows}
    if sorted(codes) != list(range(1, 101)):
        return "annotations must have rows 1..100"
    bad = [k for k, c in codes.items() if c not in CODES]
    if bad:
        return f"rows without a valid code: {bad[:10]}"
    return None


def preconditions(instrument, mode):
    if git("merge-base", "--is-ancestor", TAG, "HEAD").returncode:
        return f"tag {TAG} is not an ancestor of HEAD"
    if git("status", "--porcelain", "--", str(HERE / "pairs.json"), str(HERE / "judges.py"),
           str(HERE / "prompts.py"), str(HERE / "run.py"), str(HERE / "prices.json")).stdout.strip():
        return "frozen stage2 files have local changes"
    err = annotations_ok()
    if err:
        return err
    for dep in DEPENDS.get(instrument, []):
        if primary(dep) is None:
            return f"{instrument} needs a full run of {dep} first"
    if mode == "rerun":
        first = read_run(instrument, "full")
        if first is None:
            return "no full run to re-run"
        missing = sum(1 for r in first if not r["parsed"].get("valid"))
        if missing * 10 <= len(first):
            return f"re-run not allowed: {missing} of {len(first)} missing (needs over 10%)"
        if read_run(instrument, "rerun") is not None:
            return "already re-run once"
    return None


# ------------------------------------------------------------------ ledger and budget
class Budget:
    def __init__(self, prices):
        self.prices = prices
        self.lock = threading.Lock()
        self.entries = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
        self.in_flight = 0

    def spent(self):
        return sum(e.get("usd", 0.0) for e in self.entries)

    def reserve(self):
        with self.lock:
            r = self.prices["reserve_per_call_usd"]
            if self.spent() + r * (self.in_flight + 1) > self.prices["ceiling_usd"]:
                return False
            self.in_flight += 1
            return True

    def settle(self, entry):
        with self.lock:
            self.in_flight -= 1
            self.entries.append(entry)
            LEDGER.write_text(json.dumps(self.entries, ensure_ascii=False, indent=0) + "\n")


def cost(prices, model, usage):
    pr = prices[model]
    if model.startswith("gemini"):
        i = usage.get("promptTokenCount") or 0
        o = (usage.get("candidatesTokenCount") or 0) + (usage.get("thoughtsTokenCount") or 0)
    else:
        i, o = usage.get("input_tokens") or 0, usage.get("output_tokens") or 0
    return (i * pr["input"] + o * pr["output"]) / 1e6


def send(instrument, b):
    if instrument in J.GEMINI:
        url = GEMINI_URL.format(m=J.GEMINI_MODEL)
        headers = {"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    else:
        url = DECISIONS_URL
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    req = urllib.request.Request(url, data=json.dumps(b).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.load(r)


def one(instrument, mode, unit, budget, text):
    key, qid, cid, b = unit
    model = J.GEMINI_MODEL if instrument in J.GEMINI else J.DECISIONS_MODEL
    sha = hashlib.sha256(json.dumps(b, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    attempts, resp = [], None
    for a in range(5):
        if not budget.reserve():
            attempts.append({"attempt": a + 1, "status": "ceiling"})
            break
        t0 = datetime.datetime.now(datetime.timezone.utc).isoformat()
        status, usage, err = None, {}, None
        try:
            status, resp = send(instrument, b)
            usage = resp.get("usageMetadata") or resp.get("usage") or {}
        except urllib.error.HTTPError as e:
            status, err = e.code, e.read().decode(errors="replace")[:300]
        except Exception as e:  # timeouts and network errors
            status, err = "error", f"{type(e).__name__}: {str(e)[:200]}"
        usd = cost(budget.prices, model, usage)
        entry = {"t": t0, "instrument": instrument, "mode": mode, "unit": key, "attempt": a + 1,
                 "body_sha256": sha, "status": status, "usage": usage, "usd": usd}
        budget.settle(entry)
        attempts.append({k: entry[k] for k in ("t", "attempt", "status", "usd")} | ({"error": err} if err else {}))
        if err is None:
            break
        retry = status == "error" or status == 429 or (isinstance(status, int) and status >= 500)
        resp = None
        if not retry:
            break
        time.sleep(2 * (a + 1))
    parsed = J.parse(instrument, resp, text.get(cid)) if resp is not None else {"valid": False}
    returned = (resp or {}).get("modelVersion") or (resp or {}).get("model")
    return {"key": key, "query": qid, "chunk": cid, "body_sha256": sha, "attempts": attempts,
            "model_returned": returned, "response": resp, "parsed": parsed}


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ORDER or sys.argv[2] not in ("smoke", "full", "rerun"):
        sys.exit(__doc__)
    instrument, mode, dry = sys.argv[1], sys.argv[2], "--dry" in sys.argv
    data, qtext, text = load()
    bodies = build_bodies(instrument, data, qtext, text)
    if mode == "smoke":
        bodies = bodies[:SMOKE_N]
    digest = hashlib.sha256(json.dumps([b for *_, b in bodies], sort_keys=True,
                                       ensure_ascii=False).encode()).hexdigest()[:16]
    if dry:
        print(f"{instrument} {mode}: {len(bodies)} requests, bodies {digest}")
        return
    err = preconditions(instrument, mode)
    if err:
        sys.exit(f"refused: {err}")
    out = RUNS / f"{instrument}-{mode}.jsonl"
    if out.exists() and mode != "smoke":
        sys.exit(f"refused: {out.name} exists; runs are not repeated (§7)")
    RUNS.mkdir(exist_ok=True)
    budget = Budget(json.loads((HERE / "prices.json").read_text()))
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(lambda u: one(instrument, mode, u, budget, text), bodies))
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    missing = sum(1 for r in rows if not r["parsed"].get("valid"))
    cut = sum(1 for r in rows if any(a["status"] == "ceiling" for a in r["attempts"]))
    print(f"{instrument} {mode}: {len(rows)} units, {missing} missing, {cut} cut by the ceiling, "
          f"ledger US$ {budget.spent():.4f}")


if __name__ == "__main__":
    main()
