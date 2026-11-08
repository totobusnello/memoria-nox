#!/usr/bin/env python3
"""Paper E runner: writing criterion {C0, C2, P} x extractor {flash-lite, flash}. Standard library.

Everything except the extractor and criterion P is the Paper 3 confirmatory instrument, imported
from paper3-construction/lme-run.py (tag paper3-prereg-v1.3): blocking, serving, question text,
reader R3, judge 1 and judge 2, and their cache keys. Instances: the 242 of v13-manifest.json.

Cells (full window = every session of the haystack):
  L_C0 L_C2 L_P     extractor gemini-2.5-flash-lite (the Paper 3 extractor), body as Paper 3
  F_C0 F_C2 F_P     extractor gemini-2.5-flash, the same body plus thinkingBudget 0
  L_C2_pos F_C2_pos C2 without the answer sessions, on the 40 instances of control_subsample
Every distillation, every answer and every grade is made in this run, through the same path for
both extractors: nothing is carried over from Paper 3 (v1.1 of this plan; the Codex review of
v1.0's draft found that reusing Paper 3's flash-lite distillations tied the extractor to the
date and path of the call).

Phases:
  plan          counts and cost estimate, spends nothing
  batch-test    the batch path end to end on blocks of SPENT instances only; allowed before the tag
  distill       --via batch (half price; resumable; never submits a chunk twice), then
                --via sync for whatever the batches did not return or returned invalid
  read          reader + both judges on every cell; writes rows.ndjson and receipt.json

distill and read also need --cap-usd (at most 160), and refuse to run unless the tag
paper-e-prereg-v1.0 exists, every file of FROZEN is byte-identical to its copy at the tag, the
Paper 3 modules equal their copies at paper3-prereg-v1.3, and the dataset has the manifest's hash.

  python3 -I e-run.py plan --out <dir>
  GEMINI_API_KEY=... python3 -I e-run.py distill --via batch --out <dir> --cap-usd 160 [--wait]
  GEMINI_API_KEY=... python3 -I e-run.py distill --via sync --out <dir> --cap-usd 160
  GEMINI_API_KEY=... OPENAI_API_KEY=... python3 -I e-run.py read --out <dir> --cap-usd 160
"""
import argparse
import atexit
import fcntl
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e_batch  # noqa: E402
import e_prompts  # noqa: E402

lme = e_prompts.lme
P3 = HERE.parent / "paper3-construction"
TAG = "paper-e-prereg-v1.0"
FROZEN = ("e-run.py", "e_prompts.py", "e_batch.py", "e-analyze.py", "e-test.py",
          "PREREGISTRATION.md")
P3_TAG = "paper3-prereg-v1.3"
P3_FROZEN = ("lme-run.py", "lme-analyze.py")
MANIFEST_SHA = "f9c7df69bc7d4f8ce77f2b1b138e73a12d67ebfd72cbeb95918f039b95688ff3"
READER = "R3"
CAP_MAX = 160.0
CHUNK = 20_000
BATCH_FACTOR = 0.5

MODELS = {"L": "gemini-2.5-flash-lite", "F": "gemini-2.5-flash"}
GEN = {"L": {"responseMimeType": "application/json", "temperature": 0.1},
       "F": {"responseMimeType": "application/json", "temperature": 0.1,
             "thinkingConfig": {"thinkingBudget": 0}}}
PRICE = {"L": (0.10e-6, 0.40e-6), "F": (0.30e-6, 2.50e-6)}   # list, standard tier, 2026-11-08
# smoke means (SMOKE-RESULT.md), US$ per call at the standard price; used only for the cap check
EST = {("L", "C0"): 1.0e-4, ("L", "C2"): 1.3e-4, ("L", "P"): 1.31e-4,
       ("F", "C0"): 5.02e-4, ("F", "C2"): 6.05e-4, ("F", "P"): 7.96e-4}
CELLS = {"L_C0": ("L", "C0"), "L_C2": ("L", "C2"), "L_P": ("L", "P"),
         "F_C0": ("F", "C0"), "F_C2": ("F", "C2"), "F_P": ("F", "P"),
         "L_C2_pos": ("L", "C2"), "F_C2_pos": ("F", "C2")}
POS = ("L_C2_pos", "F_C2_pos")


def h(*parts):
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def dkey(ext, crit, block):
    return h("e-distill", MODELS[ext], json.dumps(GEN[ext], sort_keys=True),
             e_prompts.PROMPTS[crit], block)


def request_body(ext, crit, block):
    return {"contents": [{"role": "user", "parts": [
        {"text": e_prompts.PROMPTS[crit] + "\n\nConversa:\n" + block}]}],
        "generationConfig": GEN[ext]}


def response_value(d, ext, factor):
    """GenerateContentResponse -> cache value (units already filtered) and its cost."""
    c = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or [])
    units, ok = e_prompts.parse_memories(txt)
    u = d.get("usageMetadata") or {}
    tin = u.get("promptTokenCount", 0) or 0
    tout = (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0)
    pin, pout = PRICE[ext]
    return ({"units": units, "failed": not ok, "model_version": d.get("modelVersion"),
             "finish": c.get("finishReason"), "tin": tin, "tout": tout},
            (tin * pin + tout * pout) * factor)


# ------------------------------------------------------------------ the design
def load(a):
    man_path = P3 / "v13-manifest.json"
    if hashlib.sha256(man_path.read_bytes()).hexdigest() != MANIFEST_SHA:
        sys.exit("v13-manifest.json is not the Paper 3 confirmatory manifest")
    man = json.load(open(man_path))
    data = {r["question_id"]: r for r in json.load(open(a.data))}
    return man, data


def needs(man, data):
    """-> {(ext, crit, block)} the cells reference, and per instance its session blocks."""
    need, sblocks = set(), {}
    for q in man["confirm"]:
        sb = [lme.session_blocks(s) for s in data[q]["haystack_sessions"]]
        sblocks[q] = sb
        for ext, crit in set(CELLS.values()):
            for bl in sb:
                for b in bl:
                    need.add((ext, crit, b))
    return need, sblocks


# ------------------------------------------------------------------ guards
def frozen_check(data_path, man):
    """-> the commit the tag resolves to. Refuses unless the whole executable chain is the
    registered one: this run's files at TAG, Paper 3's modules at P3_TAG, the dataset's hash."""
    top = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    if subprocess.run(["git", "-C", top, "rev-parse", "-q", "--verify", f"refs/tags/{TAG}"],
                      capture_output=True).returncode != 0:
        sys.exit(f"tag {TAG} does not exist: the pre-registration is not frozen yet")
    for tag, d, files in ((TAG, HERE, FROZEN), (P3_TAG, P3, P3_FROZEN)):
        rel = d.relative_to(top)
        for f in files:
            at_tag = subprocess.run(["git", "-C", top, "show", f"{tag}:{rel / f}"],
                                    capture_output=True).stdout
            if at_tag != (d / f).read_bytes():
                sys.exit(f"{rel / f} differs from its copy at {tag}")
    hs = hashlib.sha256()
    with open(data_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            hs.update(chunk)
    if hs.hexdigest() != man["sha256"]:
        sys.exit("the dataset's sha256 is not the one the manifest records")
    return subprocess.run(["git", "-C", top, "rev-parse", f"{TAG}^{{commit}}"],
                          capture_output=True, text=True).stdout.strip()


class Spend:
    """Cumulative across processes (as Paper 3 §14.10): one lock per out dir, one spend file per
    process, the next process starts from their sum."""

    def __init__(self, out, cap):
        self.lockf = open(out / "run.lock", "w")
        try:
            fcntl.flock(self.lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(f"another process holds {out}/run.lock")
        self.dir = out / "spend"
        self.dir.mkdir(exist_ok=True)
        self.prior = sum(json.loads(f.read_text())["usd"] for f in sorted(self.dir.glob("*.json")))
        self.mine = self.dir / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}.json"
        self.led = lme.Ledger(cap)
        self.led.usd = self.prior
        self.lock, self.k = threading.Lock(), 0
        base = self.led.add

        def add(kind, usd):
            try:
                base(kind, usd)
            finally:
                self.k += 1
                if self.k % 20 == 0 or (self.led.cap and self.led.usd > self.led.cap):
                    self.save()
        self.led.add = add
        atexit.register(self.save)

    def stopped(self):
        """checked before every paid call; the cap can be passed only by calls already in flight"""
        return bool(self.led.cap) and self.led.usd >= self.led.cap

    def save(self):
        if not self.dir.exists():
            return
        with self.lock:
            tmp = self.mine.with_suffix(".tmp")
            tmp.write_text(json.dumps({"usd": round(self.led.usd - self.prior, 6),
                                       "calls": dict(self.led.n),
                                       "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
            tmp.replace(self.mine)


# ------------------------------------------------------------------ distill
def todo_of(cache, need, retry_invalid=False):
    """Missing distillations; with retry_invalid, also those a batch returned invalid, which get
    one sync attempt (§8 step 3)."""
    out = []
    for e, c, b in need:
        k = dkey(e, c, b)
        v = cache.get(k)
        if v is None or (retry_invalid and v.get("failed") and v.get("via") == "batch"):
            out.append((k, e, c, b))
    return sorted(out)


def run_id(out):
    """A per-out-dir identity in every batch display name, so no other run's batch is adopted."""
    p = out / "run-id"
    if not p.exists():
        p.write_text(uuid.uuid4().hex[:10])
    return p.read_text().strip()


def make_chunks(out, todo, prefix):
    """Written once: the chunk manifest fixes which requests each batch carries, so a restart
    resubmits nothing and the display name identifies a chunk across processes."""
    st_path = out / "batches.json"
    if st_path.exists():
        return json.loads(st_path.read_text())
    cdir = out / "chunks"
    cdir.mkdir(exist_ok=True)
    groups = {}
    for k, e, c, b in todo:
        groups.setdefault(e, []).append((k, e, c, b))
    chunks = []
    for e in sorted(groups):
        items = groups[e]
        for i in range(0, len(items), CHUNK):
            cid = f"{prefix}-{run_id(out)}-{e}-{i // CHUNK:03d}"
            part = items[i:i + CHUNK]
            with open(cdir / f"{cid}.jsonl", "w") as f:
                for k, e2, c, b in part:
                    f.write(json.dumps({"key": k, "request": request_body(e2, c, b)}) + "\n")
            (cdir / f"{cid}.meta.json").write_text(json.dumps(
                {k: [e2, c] for k, e2, c, _ in part}))
            chunks.append({"id": cid, "ext": e, "n": len(part),
                           "est_usd": sum(EST[(e2, c)] for _, e2, c, _ in part) * BATCH_FACTOR,
                           "state": "new", "batch": None})
    st_path.write_text(json.dumps(chunks, indent=1))
    return chunks


def save_chunks(out, chunks):
    tmp = out / "batches.json.tmp"
    tmp.write_text(json.dumps(chunks, indent=1))
    tmp.replace(out / "batches.json")


def ingest(out, cache, sp, ch, lines):
    meta = json.loads((out / "chunks" / f"{ch['id']}.meta.json").read_text())
    got = bad = 0
    for ln in lines:
        k = ln.get("key")
        if k not in meta:
            continue
        resp = ln.get("response")
        if not resp:
            bad += 1
            continue
        if cache.get(k) is not None:      # ingested by an interrupted earlier pass: no new charge
            got += 1
            continue
        ext, crit = meta[k]
        v, usd = response_value(resp, ext, BATCH_FACTOR)
        sp.led.add("distill", usd)
        if v["failed"]:
            sp.led.n["failed"] += 1
        cache.put(k, "distill", dict(v, via="batch"))
        got += 1
    ch["ingested"], ch["errors"] = got, bad
    ch["missing"] = len(meta) - got - bad
    sp.save()
    return got


def distill_batch(out, cache, sp, todo, prefix, max_inflight, wait, poll):
    chunks = make_chunks(out, todo, prefix)
    while True:
        inflight = [c for c in chunks if c["state"] == "submitted"]
        est_inflight = sum(c["est_usd"] for c in inflight)
        held = quota_held = False
        for ch in chunks:
            if ch["state"] != "new" or len(inflight) >= max_inflight:
                continue
            if sp.led.cap and sp.led.usd + est_inflight + ch["est_usd"] > sp.led.cap:
                held = True
                print(f"  {ch['id']}: held, would pass the cap (spent US$ {sp.led.usd:.2f}, "
                      f"in flight ~US$ {est_inflight:.2f}, this ~US$ {ch['est_usd']:.2f})")
                continue
            existing = e_batch.list_display_names()
            if ch["id"] in existing:          # created by a process that died before recording it
                ch["batch"] = existing[ch["id"]]
            else:
                try:
                    fname = e_batch.upload_jsonl(out / "chunks" / f"{ch['id']}.jsonl", ch["id"])
                    ch["batch"] = e_batch.create(MODELS[ch["ext"]], fname, ch["id"])
                except RuntimeError as ex:    # queue quota: hold, retry on a later pass
                    if "HTTP 429" not in str(ex) and "RESOURCE_EXHAUSTED" not in str(ex):
                        raise
                    print(f"  {ch['id']}: held by the provider's queue quota ({str(ex)[:90]})",
                          flush=True)
                    quota_held = True
                    break
            ch["state"] = "submitted"
            save_chunks(out, chunks)
            inflight.append(ch)
            est_inflight += ch["est_usd"]
            print(f"  {ch['id']}: submitted as {ch['batch']} ({ch['n']} requests)", flush=True)
        for ch in [c for c in chunks if c["state"] == "submitted"]:
            state, rf, _ = e_batch.get(ch["batch"])
            ch["last_state"] = state
            if state in e_batch.TERMINAL_OK and rf:
                n = ingest(out, cache, sp, ch, e_batch.download(rf))
                ch["state"] = "done"
                print(f"  {ch['id']}: done, {n} ingested, {ch['errors']} errors, "
                      f"{ch['missing']} missing · US$ {sp.led.usd:.2f}", flush=True)
            elif state in e_batch.TERMINAL_BAD:
                ch["state"] = "bad"
                print(f"  {ch['id']}: {state}; its requests stay to distill", flush=True)
            save_chunks(out, chunks)
        open_ = [c for c in chunks if c["state"] in ("new", "submitted")]
        if not open_ or not wait:
            break
        running = any(c["state"] == "submitted" for c in chunks)
        if not running and held:
            print("  nothing in flight and the next chunk would pass the cap; stopping")
            break
        if running or quota_held:
            time.sleep(poll)
    return chunks


def distill_sync(cache, sp, todo, workers):
    """The last attempt (§8 step 3): a block that still fails here is recorded as failed and
    served empty, never left missing."""
    def one(t):
        if sp.stopped():
            return "skipped"
        k, e, c, b = t
        try:
            d = lme.post(lme.gurl(MODELS[e]), request_body(e, c, b),
                         {"Content-Type": "application/json"}, timeout=300)
        except Exception as ex:
            sp.led.n["failed"] += 1
            cache.put(k, "distill", {"units": [], "failed": True, "via": "sync",
                                     "error": str(ex)[:160], "tin": 0, "tout": 0})
            return "error"
        v, usd = response_value(d, e, 1.0)
        cache.put(k, "distill", dict(v, via="sync"))
        sp.led.add("distill", usd)
        return "ok"
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, todo))
    print(f"  sync: {res.count('ok')} ok, {res.count('error')} errors, "
          f"{res.count('skipped')} skipped at the cap · US$ {sp.led.usd:.2f}")


# ------------------------------------------------------------------ read
def build_jobs(man, data, sblocks, cache):
    jobs, missing = [], 0
    ctrl = set(man["control_subsample"])
    for q in man["confirm"]:
        r = data[q]
        ev = lme.evidence(r)
        allv = list(range(len(r["haystack_sessions"])))
        for cell, (ext, crit) in CELLS.items():
            if cell in POS and q not in ctrl:
                continue
            sess = [i for i in allv if i not in ev] if cell in POS else allv
            ub = []
            for bl in sblocks[q]:
                row = []
                for b in bl:
                    v = cache.get(dkey(ext, crit, b))
                    if v is None or (v.get("failed") and v.get("via") == "batch"):
                        missing += 1
                        v = {"units": []}
                    row.append(v["units"])
                ub.append(row)
            mat = lme.serve(ub, sess, r)
            jobs.append({"variant": q, "qid": q, "cell": cell, "extractor": MODELS[ext],
                         "criterion": crit, "question_type": r["question_type"],
                         "reference": str(r["answer"]), "question": lme.question_text(r),
                         "q_plain": r["question"], "sessions": len(sess),
                         "evidence_kept": len(ev & set(sess)), "evidence_total": len(ev),
                         "served_chars": len(mat), "material": mat})
    return jobs, missing


def failure_table(cache, need):
    """failed blocks and kept units per extractor x criterion (§8: reported beside the primary)"""
    tab = {}
    for e, c, b in need:
        v = cache.get(dkey(e, c, b)) or {}
        d = tab.setdefault(f"{MODELS[e]}|{c}", {"blocks": 0, "failed": 0, "units": 0})
        d["blocks"] += 1
        d["failed"] += int(bool(v.get("failed")))
        d["units"] += len(v.get("units") or [])
    for d in tab.values():
        d["failed_share"] = round(d["failed"] / d["blocks"], 6)
        d["over_1pct"] = d["failed_share"] > 0.01
        d["units_per_block"] = round(d["units"] / d["blocks"], 4)
    return dict(sorted(tab.items()))


def read(a, out, man, data, sblocks, cache, sp, need, tag_commit=None):
    jobs, missing = build_jobs(man, data, sblocks, cache)
    if missing:
        sys.exit(f"{missing} block references have no final distillation yet (missing, or "
                 f"invalid from a batch without the sync retry); run distill first")

    def run(j):
        if sp.stopped():
            raise SystemExit(f"cap reached: US$ {sp.led.usd:.2f}")
        av = lme.answer(cache, sp.led, j["material"] or "(vazio)", j["question"], READER)
        jv = lme.judge(cache, sp.led, j["reference"], av["text"], j["q_plain"])
        j2 = lme.judge2(cache, sp.led, j["reference"], av["text"], j["q_plain"])
        row = {k: v for k, v in j.items() if k != "material"}
        row.update({"answer": av["text"], "finish": av.get("finish"),
                    "answer_model_version": av.get("model_version"),
                    "abstained": lme.abstained(av["text"]), "judge": jv,
                    "correct": (jv.get("contem") or 0) > lme.THR,
                    "judge2": j2, "correct_j2": bool(j2.get("correta")),
                    "material_sha256": hashlib.sha256(j["material"].encode()).hexdigest()})
        return row

    rows, t0 = [], time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        for n, row in enumerate(ex.map(run, jobs)):
            rows.append(row)
            if (n + 1) % 100 == 0 or n + 1 == len(jobs):
                print(f"  read {n+1}/{len(jobs)} · US$ {sp.led.usd:.2f} · {time.time()-t0:.0f}s",
                      flush=True)
    with open(out / "rows.ndjson", "w") as f:
        for row in sorted(rows, key=lambda x: (x["qid"], x["cell"])):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    dist = [cache.get(dkey(e, c, b)) for e, c, b in sorted(need)]
    receipt = {
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tag": TAG, "tag_commit": tag_commit, "rows": len(rows),
        "instances": len(man["confirm"]),
        "manifest_sha256": MANIFEST_SHA,
        "files_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in FROZEN},
        "prompt_sha256": {c: e_prompts.sha(c) for c in e_prompts.PROMPTS},
        "extractors": MODELS, "generation_config": GEN, "reader": READER,
        "reader_spec": list(lme.READERS[READER][:3]),
        "judges": [lme.JMODEL, lme.GMODEL],
        "distill_by_source": {s: sum(1 for v in dist if v.get("via") == s)
                              for s in ("batch", "sync")},
        "distill_failed": sum(1 for v in dist if v.get("failed")),
        "failures_by_cell": failure_table(cache, need),
        "distill_model_versions": sorted({v.get("model_version") for v in dist
                                          if v.get("model_version")}),
        "answer_versions": sorted({r["answer_model_version"] for r in rows
                                   if r.get("answer_model_version")}),
        "spend_usd_cumulative": round(sp.led.usd, 4),
        "batches": json.loads((out / "batches.json").read_text()) if (out / "batches.json").exists() else [],
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in ("rows", "distill_by_source", "distill_failed",
                                              "spend_usd_cumulative")}))


# ------------------------------------------------------------------ batch-test
def batch_test(a, out, data, man):
    """Spent stage-1 blocks only, crit P on both extractors: proves upload, create, poll,
    download, key mapping and parsing before the real run. No reader, no judge."""
    s1 = json.load(open(P3 / "stage1-manifest.json"))["stage1"]
    v13b = {b for q in man["confirm"] for s in data[q]["haystack_sessions"] for b in lme.session_blocks(s)}
    pool = sorted({b for q in s1 for s in data[q]["haystack_sessions"]
                   for b in lme.session_blocks(s)} - v13b)
    sample = random.Random("paper-e-batch-test-v1").sample(pool, a.n)
    need = {(e, "P", b) for e in ("L", "F") for b in sample}
    cache = lme.Cache(str(out / "cache.sqlite"))
    sp = Spend(out, 1.0)                      # fixed cap: the test never spends past US$ 1
    chunks = distill_batch(out, cache, sp, todo_of(cache, need), "paper-e-batchtest",
                           a.max_inflight, True, a.poll)
    vals = [cache.get(dkey(e, c, b)) for e, c, b in sorted(need)]
    res = {"requested": len(need), "cached": sum(v is not None for v in vals),
           "failed_parse": sum(1 for v in vals if v and v.get("failed")),
           "units_kept_mean": round(sum(len(v["units"]) for v in vals if v) / max(1, sum(v is not None for v in vals)), 2),
           "model_versions": sorted({v.get("model_version") for v in vals if v and v.get("model_version")}),
           "spend_usd": round(sp.led.usd, 5),
           "chunks": [{k: c.get(k) for k in ("id", "n", "state", "last_state", "ingested", "errors", "missing")}
                      for c in chunks]}
    (out / "batch-test.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1, sort_keys=True))


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["plan", "batch-test", "distill", "read"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.path.expanduser(
        "~/datasets/longmemeval/longmemeval_s_cleaned.json"))
    ap.add_argument("--via", choices=["batch", "sync"], default="batch")
    ap.add_argument("--cap-usd", type=float, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-inflight", type=int, default=4)
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--poll", type=int, default=60)
    ap.add_argument("--n", type=int, default=30, help="batch-test: blocks")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    man, data = load(a)

    if a.phase == "batch-test":
        out.mkdir(parents=True, exist_ok=True)
        return batch_test(a, out, data, man)

    need, sblocks = needs(man, data)
    if a.phase == "plan":
        per = {}
        for e, c, _ in need:
            per[(e, c)] = per.get((e, c), 0) + 1
        est = sum(n * EST[k] for k, n in per.items())
        rows = len(man["confirm"]) * 6 + len(POS) * len(man["control_subsample"])
        print(f"{len(man['confirm'])} instances, {rows} rows; distinct distillations:")
        for k in sorted(per):
            print(f"  {MODELS[k[0]]:22s} {k[1]:3s} {per[k]:>7,}")
        print(f"  ~US$ {est:.0f} standard, ~US$ {est * BATCH_FACTOR:.0f} batch; "
              f"reading ~US$ {rows * 0.028:.0f}")
        return

    if a.cap_usd <= 0 or a.cap_usd > CAP_MAX:
        sys.exit(f"--cap-usd is required and at most {CAP_MAX}")
    tag_commit = frozen_check(a.data, man)
    out.mkdir(parents=True, exist_ok=True)
    cache = lme.Cache(str(out / "cache.sqlite"))
    sp = Spend(out, a.cap_usd)
    print(f"tag {TAG} at {tag_commit[:12]}; cumulative spend before this process: "
          f"US$ {sp.prior:.2f} (cap {a.cap_usd})")
    if a.phase == "distill":
        if a.via == "batch":
            todo = todo_of(cache, need)
            print(f"{len(todo)} distillations to do")
            distill_batch(out, cache, sp, todo, "paper-e", a.max_inflight, a.wait, a.poll)
        else:
            todo = todo_of(cache, need, retry_invalid=True)
            print(f"{len(todo)} distillations to do (missing, or invalid from a batch)")
            distill_sync(cache, sp, todo, a.workers)
        print(f"left: {len(todo_of(cache, need, retry_invalid=True))}")
        return
    read(a, out, man, data, sblocks, cache, sp, need, tag_commit)


if __name__ == "__main__":
    main()
